"""`label_tool video-apply --visibility`: when the Label is shown, checked by decoding every frame.

The videos are tiny (160x90, 10 fps) so that minute-long ones stay fast. A
frame shows the Label when it differs from the same frame of the flat-colour
source; which frames do is measured with the real ffmpeg and ffprobe,
independently of what label_tool reports.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from helpers import sha256
from videos import (
    FFMPEG, fake_tool, flat_mp4, frames, frame_times, needs_ffmpeg, probe, real_tool, real_tools, streams, tool_env,
    video_stream,
)

pytestmark = needs_ffmpeg

SIZE = "160x90"
RATE = 10


def apply(label_tool, tmp_path, video, *args):
    return label_tool("video-apply", video, "--variant", "generated", *args, env=real_tools(tmp_path / "bin"))


def label_boxes(source: Path, copy: Path) -> dict[float, tuple | None]:
    """Each frame's playback time (from the first frame) and the box the Label covers in it, or None."""
    (before, size), (after, _) = frames(source, "gray"), frames(copy, "gray")
    times = frame_times(copy)
    assert len(before) == len(after) == len(times)
    boxes = {}
    for t, a, b in zip(times, before, after):
        diff = ImageChops.difference(Image.frombytes("L", size, a), Image.frombytes("L", size, b))
        boxes[round(t - times[0], 3)] = diff.point(lambda v: 255 if v > 24 else 0).getbbox()
    return boxes


def shown(boxes: dict) -> set[float]:
    return {t for t, box in boxes.items() if box}


def test_periodic_display_follows_the_window_and_recurrence(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=8, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video, "--visibility", "periodic", "--window", "1", "--every", "3")

    assert result.returncode == 0, result.json
    boxes = label_boxes(video, Path(result.json["labelled_copy"]))
    visible = shown(boxes)
    assert {0.0, 0.9, 3.0, 3.9, 6.0, 6.9} <= visible
    assert not {1.0, 2.9, 4.0, 5.9, 7.0, 7.9} & visible
    assert len({boxes[t] for t in visible}) == 1, "the same position and appearance at each recurrence"


def test_an_offset_start_neither_shifts_the_windows_nor_is_lost(tmp_path, label_tool):
    # Its timestamps start at 2.5 s, the audio a few ms before the video.
    video = flat_mp4(tmp_path / "clip.mp4", seconds=7.5, size=SIZE, rate=RATE, audio=True,
                     extra=("-output_ts_offset", "2.5"))
    assert float(video_stream(video)["start_time"]) == pytest.approx(2.5)

    result = apply(label_tool, tmp_path, video, "--visibility", "periodic", "--window", "2", "--every", "3")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    visible = shown(label_boxes(video, copy))
    assert {0.0, 1.9, 3.0, 4.9, 6.0, 7.4} <= visible, "the first window starts with playback; the last is cut short"
    assert not {2.0, 2.9, 5.0, 5.9} & visible
    assert float(video_stream(copy)["start_time"]) == pytest.approx(2.5, abs=0.001)
    (a_out,), (a_src,) = streams(copy, "audio"), streams(video, "audio")
    assert float(a_out["start_time"]) == pytest.approx(float(a_src["start_time"]), abs=0.001)
    assert frame_times(copy) == pytest.approx(frame_times(video), abs=0.001), "no frame inserted or moved"
    assert float(probe(copy)["format"]["duration"]) == pytest.approx(float(probe(video)["format"]["duration"]),
                                                                     abs=0.04), "the video is not extended"


@pytest.mark.parametrize("seconds", [59.5, 60])
def test_a_video_up_to_60_seconds_shows_the_label_throughout_by_default(tmp_path, label_tool, seconds):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=seconds, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    boxes = label_boxes(video, Path(result.json["labelled_copy"]))
    assert shown(boxes) == set(boxes)
    assert result.json["visibility"] == {"mode": "continuous", "requested": "auto", "threshold": 60}


def test_a_video_just_over_60_seconds_shows_it_5_seconds_every_60_by_default(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=60.5, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    boxes = label_boxes(video, Path(result.json["labelled_copy"]))
    visible = shown(boxes)
    assert visible == {t for t in boxes if t < 5 or t >= 60}, "0-5 s, then from 60 s to the end (cut to 0.5 s)"
    assert {4.9, 60.0, 60.4} <= visible and not {5.0, 59.9} & visible
    assert len({boxes[t] for t in visible}) == 1
    assert result.json["visibility"] == {"mode": "periodic", "requested": "auto", "threshold": 60,
                                         "window": 5, "every": 60}


def test_continuous_display_can_be_asked_for_a_long_video(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=61, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video, "--visibility", "continuous")

    assert result.returncode == 0, result.json
    boxes = label_boxes(video, Path(result.json["labelled_copy"]))
    assert shown(boxes) == set(boxes)
    assert result.json["visibility"]["mode"] == "continuous"


def test_the_threshold_can_be_configured(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=8, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video, "--threshold", "7.5")

    assert result.returncode == 0, result.json
    boxes = label_boxes(video, Path(result.json["labelled_copy"]))
    assert shown(boxes) == {t for t in boxes if t < 5}
    assert result.json["visibility"]["mode"] == "periodic"


P = ("--visibility", "periodic")


@pytest.mark.parametrize("settings", [
    (*P, "--window", "0"), (*P, "--every", "-60"), (*P, "--window", "nan"), (*P, "--every", "inf"),
    (*P, "--window", "60"), (*P, "--window", "10", "--every", "5"), ("--threshold", "0"),
    ("--threshold", "-1"), ("--visibility", "sometimes"),
], ids=lambda s: " ".join(s))
def test_invalid_timing_stops_before_rendering(tmp_path, label_tool, settings):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE, rate=RATE)
    before = sha256(video)

    result = apply(label_tool, tmp_path, video, *settings)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "usage"
    assert sha256(video) == before
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == ["clip.mp4"]


def test_timing_settings_that_do_not_apply_are_not_checked(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video, "--visibility", "continuous", "--every", "3", "--threshold", "0")

    assert result.returncode == 0, result.json
    assert result.json["visibility"]["mode"] == "continuous"


def test_a_last_window_cut_to_a_single_frame(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=5.1, size=SIZE, rate=RATE)

    result = apply(label_tool, tmp_path, video, "--visibility", "periodic")

    assert result.returncode == 0, result.json
    boxes = label_boxes(video, Path(result.json["labelled_copy"]))
    assert shown(boxes) == {t for t in boxes if t < 5}


def test_a_label_left_showing_outside_its_windows_fails_validation(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=4, size=SIZE, rate=RATE)
    bin_dir = tmp_path / "bin-no-timing"
    real_tool(bin_dir, "ffprobe")
    # An ffmpeg that renders the Label but drops its display timing.
    dropper = tmp_path / "drop_timing.py"
    dropper.write_text(f"import os, re, sys\nargs = [re.sub(r\":enable='[^']*'\", '', a) for a in sys.argv[1:]]\n"
                       f"os.execv({FFMPEG!r}, [{FFMPEG!r}, *args])\n")
    fake_tool(bin_dir, "ffmpeg", f'exec "{sys.executable}" "{dropper}" "$@"')

    result = label_tool("video-apply", video, "--variant", "generated", "--visibility", "periodic",
                        "--window", "1", "--every", "3", env=tool_env(bin_dir))

    assert result.json["error"]["code"] == "output_validation_failed", result.json
    assert not (tmp_path / "clip.ai-label.mp4").exists()
