"""`label_tool video-preview`: source frames and labelled excerpts to choose a fixed corner from.

The frames and excerpts are decoded with the real ffmpeg and ffprobe and
compared with the source and with what `video-apply` renders for the same
settings, independently of what label_tool reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

from helpers import sha256
from videos import (
    FFMPEG, changed, corner_scenes, fake_tool, flat_mp4, frame_images, frame_times, needs_ffmpeg, real_tool,
    real_tools, rotated, tool_env, white_quadrant,
)

pytestmark = needs_ffmpeg


def preview(label_tool, tmp_path, video, *args, env=None):
    return label_tool("video-preview", video, "--variant", "generated", *args, env=env or real_tools(tmp_path / "bin"))


def test_the_frames_come_from_every_scene(tmp_path, label_tool):
    video = corner_scenes(tmp_path / "clip.mp4", corners=("tr", "bl", "br"))

    result = preview(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    frames = result.json["frames"]
    times = [f["time"] for f in frames]
    assert times == sorted(times) and times[0] < 1 and times[-1] >= 2, "spread over the whole video"
    seen = set()
    for entry in frames:
        assert entry["status"] == "written"
        with Image.open(entry["path"]) as image:
            assert image.format == "PNG" and image.size == (320, 180)
            seen.add(white_quadrant(image))
    assert seen == {"tr", "bl", "br"}, "each scene's competing corner shows in some frame"
    assert Path(result.json["out"]) == tmp_path / "clip.mp4.label-preview"


def decoded_by_time(path: Path) -> dict[float, Image.Image]:
    """Every decoded frame of `path`, by its presentation time."""
    return {round(t, 3): image for t, image in zip(frame_times(path), frame_images(path))}


def test_excerpts_show_the_label_exactly_as_the_labelled_copy(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=12, size="320x180")
    settings = ("--corner", "bl", "--size", "30", "--colour", "white", "--visibility", "continuous")

    result = preview(label_tool, tmp_path, video, *settings)
    applied = label_tool("video-apply", video, "--variant", "generated", *settings, env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert applied.returncode == 0, applied.json
    copy = decoded_by_time(Path(applied.json["labelled_copy"]))
    source = decoded_by_time(video)
    starts = [e["start"] for e in result.json["excerpts"]]
    assert len(starts) == 3 and starts[0] == 0 and starts[-1] >= 9, "excerpts from the start, middle and end"
    compared = 0
    for entry in result.json["excerpts"]:
        assert entry["status"] == "written"
        for t, frame in decoded_by_time(Path(entry["path"])).items():
            box = changed(source[t], frame)
            assert box and box == changed(source[t], copy[t]), f"the same Label box at {t} s"
            difference = ImageChops.difference(copy[t], frame).convert("L").crop(box)
            assert ImageStat.Stat(difference).mean[0] < 2, f"the same Label pixels at {t} s, up to encoding noise"
            compared += 1
    assert compared >= 50
    for key in ("variant", "corner", "colour", "plate_box", "icon", "visibility"):
        assert result.json[key] == applied.json[key]


@pytest.mark.parametrize("degrees", [90, 180])
def test_a_rotated_video_previews_the_label_where_its_copy_has_it(tmp_path, label_tool, degrees):
    video = rotated(flat_mp4(tmp_path / "stored.mp4", seconds=2, size="320x180"), tmp_path / "clip.mp4", degrees)
    settings = ("--corner", "tr", "--colour", "black")

    result = preview(label_tool, tmp_path, video, *settings)
    applied = label_tool("video-apply", video, "--variant", "generated", *settings, env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert applied.returncode == 0, applied.json
    source, copy = decoded_by_time(video), decoded_by_time(Path(applied.json["labelled_copy"]))
    (entry,) = result.json["excerpts"]
    excerpt = decoded_by_time(Path(entry["path"]))
    assert excerpt
    for t, frame in excerpt.items():
        assert frame.size == source[t].size, "decoded as displayed"
        box = changed(source[t], frame)
        assert box and box == changed(source[t], copy[t]), f"the same Label box at {t} s"
        left, top, right, bottom = box
        assert right > frame.width - 20 and top < 20 and bottom < frame.height / 2, \
            "top-right of the picture as displayed"


@pytest.mark.parametrize("extra", [{}, {"audio": True, "extra": ("-output_ts_offset", "2.5")}],
                         ids=["silent", "offset-start-with-audio"])
@pytest.mark.parametrize("window, every", [(1, 6), (6, 9)], ids=["short-window", "long-window"])
def test_periodic_excerpts_cover_visible_windows_and_their_transitions(tmp_path, label_tool, extra, window, every):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=20, size="160x90", rate=10, **extra)

    result = preview(label_tool, tmp_path, video, "--visibility", "periodic", "--window", str(window),
                     "--every", str(every))

    assert result.returncode == 0, result.json
    source = decoded_by_time(video)
    first = min(source)
    excerpts = result.json["excerpts"]
    assert len(excerpts) >= 2
    for entry in excerpts:
        shown, hidden = set(), set()
        for t, frame in decoded_by_time(Path(entry["path"])).items():
            playback = round(t - first, 3)
            (shown if changed(source[t], frame) else hidden).add(playback)
            assert bool(changed(source[t], frame)) == (playback % every < window - 0.05), f"the timing at {playback} s"
        assert shown, f"the excerpt from {entry['start']} s shows the Label"
        if entry["start"] > 0 and window <= 4:
            assert hidden and min(hidden) < min(shown) < max(hidden), "it appears and disappears in the excerpt"
        elif entry["start"] > 0:
            assert hidden and (min(hidden) < min(shown) or max(shown) < max(hidden)), "it appears or disappears"
    assert result.json["visibility"] == {"requested": "periodic", "mode": "periodic", "window": window,
                                         "every": every}


def test_the_result_states_what_previews_do_not_establish(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2)

    result = preview(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    assert "cannot show" in result.json["sampling_note"] and "every frame" in result.json["sampling_note"]
    assert result.json["complete"] is True and result.json["failed"] == 0


def test_previews_never_touch_the_original_or_the_labelled_copy(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2)
    env = real_tools(tmp_path / "bin")
    assert label_tool("video-apply", video, "--variant", "generated", env=env).returncode == 0
    copy = tmp_path / "clip.ai-label.mp4"
    before = {video: sha256(video), copy: sha256(copy)}

    result = preview(label_tool, tmp_path, video, "--corner", "br", env=env)
    refused = preview(label_tool, tmp_path, video, "--out", copy, env=env)

    assert result.returncode == 0, result.json
    assert refused.returncode == 1 and refused.json["error"]["code"] == "usage"
    assert {p: sha256(p) for p in before} == before
    assert all(Path(e["path"]).parent == tmp_path / "clip.mp4.label-preview"
               for e in result.json["frames"] + result.json["excerpts"])


def test_previews_go_to_the_folder_asked_for(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2)

    out = tmp_path / "previews"
    out.mkdir()
    (out / "excerpt-notes.txt").write_text("the user's own file")
    assert preview(label_tool, tmp_path, video, "--out", out, "--frames", "6").returncode == 0

    result = preview(label_tool, tmp_path, video, "--out", out, "--frames", "3")

    assert result.returncode == 0, result.json
    assert len(result.json["frames"]) == 3
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["excerpt-notes.txt", *(Path(e["path"]).name for e in result.json["frames"] + result.json["excerpts"])]), \
        "an earlier preview's samples are replaced, and nothing else is removed"


def test_a_user_size_keeps_the_minimum_size_and_fit_checks(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1)

    too_small = preview(label_tool, tmp_path, video, "--size", "10")
    too_big = preview(label_tool, tmp_path, video, "--size", "170")

    assert too_small.json["error"]["code"] == "size_too_small"
    assert too_big.json["error"]["code"] == "image_too_small"
    assert not (tmp_path / "clip.mp4.label-preview").exists()


def failing_ffmpeg(tmp_path: Path, pattern: str) -> dict:
    """The real tools, except that ffmpeg fails on commands writing a file matching `pattern`."""
    bin_dir = tmp_path / "bin"
    real_tool(bin_dir, "ffprobe")
    fake_tool(bin_dir, "ffmpeg", f'case "$*" in *{pattern}*) echo "simulated failure" >&2; exit 1;; esac\n'
                                 f'exec "{FFMPEG}" "$@"')
    return tool_env(bin_dir)


def test_a_failed_excerpt_is_reported_not_passed_off_as_checked(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2)

    result = preview(label_tool, tmp_path, video, env=failing_ffmpeg(tmp_path, "excerpt-"))

    assert result.returncode == 0, result.json
    assert result.json["complete"] is False
    assert result.json["excerpts"] and all(e["status"] == "failed" and e["path"] is None
                                           and "simulated failure" in e["error"] for e in result.json["excerpts"])
    assert result.json["failed"] == len(result.json["excerpts"])
    assert not list((tmp_path / "clip.mp4.label-preview").glob("*excerpt-*"))
    assert all(e["status"] == "written" for e in result.json["frames"])


def test_a_failed_frame_is_reported(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2)

    result = preview(label_tool, tmp_path, video, "--colour", "black", env=failing_ffmpeg(tmp_path, "frame-02"))

    assert result.returncode == 0, result.json
    failed = [f for f in result.json["frames"] if f["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["path"] is None and "simulated failure" in failed[0]["error"]
    assert result.json["complete"] is False


def test_a_preview_that_makes_nothing_is_an_error(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2)

    result = preview(label_tool, tmp_path, video, "--colour", "black", env=failing_ffmpeg(tmp_path, "label-preview"))

    assert result.returncode == 1
    assert result.json["error"]["code"] == "preview_failed"
    assert "Nothing was checked" in result.json["error"]["message"]


def test_a_video_off_the_validated_paths_stops_before_any_preview(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, codec="libx265")

    result = preview(label_tool, tmp_path, video)

    assert result.json["error"]["code"] == "preservation_unsupported"
    assert not (tmp_path / "clip.mp4.label-preview").exists()
