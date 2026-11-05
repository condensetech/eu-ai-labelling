"""`label_tool video-apply`: a Labelled Copy of a video, checked by decoding it.

Every measurement here decodes the output with the real ffmpeg and ffprobe,
independently of what label_tool reports about itself.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from helpers import sha256, icon_match
from videos import (
    FFMPEG, changed, fake_tool, ffmpeg, flat_mp4, frame_images, frame_times, needs_ffmpeg, probe, real_tool,
    real_tools, streams, tool_env, video_stream,
)

pytestmark = needs_ffmpeg

SIZE = "640x360"


def apply(label_tool, tmp_path, video, *args, env=None):
    return label_tool("video-apply", video, *args, env=env or real_tools(tmp_path / "bin"))


def stream_md5(path: Path, selector: str) -> str:
    """The MD5 of a stream's packets, copied out without decoding."""
    proc = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-map", selector, "-c", "copy", "-f", "md5", "-"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def save_frame(image: Image.Image, path: Path) -> Path:
    image.save(path)
    return path


@pytest.mark.parametrize("variant, other", [("generated", "modified"), ("modified", "generated")])
def test_a_silent_mp4_gets_the_official_icon_in_the_top_right(tmp_path, label_tool, variant, other):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2, size=SIZE)
    before = sha256(video)

    result = apply(label_tool, tmp_path, video, "--variant", variant)

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    assert result.json["labelled_copy"] == str(copy)
    assert sha256(video) == before
    source, labelled = frame_images(video)[25], frame_images(copy)[25]
    left, top, right, bottom = changed(source, labelled)
    assert left > 320 and bottom < 180, "the Label is in the top-right"
    original_png = save_frame(source, tmp_path / "source.png")
    labelled_png = save_frame(labelled, tmp_path / "labelled.png")
    assert icon_match(original_png, labelled_png, variant) > icon_match(original_png, labelled_png, other)


def test_the_copy_keeps_container_codec_dimensions_and_timing(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=3, size=SIZE, rate=30)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    assert "mp4" in probe(copy)["format"]["format_name"]
    out, src = video_stream(copy), video_stream(video)
    assert out["codec_name"] == "h264"
    assert (out["width"], out["height"]) == (src["width"], src["height"])
    assert out["pix_fmt"] == src["pix_fmt"]
    assert frame_times(copy) == pytest.approx(frame_times(video), abs=0.001)
    assert float(probe(copy)["format"]["duration"]) == pytest.approx(float(probe(video)["format"]["duration"]), abs=0.04)


def test_audio_is_copied_untouched_and_in_sync(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2, size=SIZE, audio=True)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    assert stream_md5(copy, "0:a:0") == stream_md5(video, "0:a:0")
    (a_out,), (a_src,) = streams(copy, "audio"), streams(video, "audio")
    assert float(a_out["start_time"]) - float(video_stream(copy)["start_time"]) == pytest.approx(
        float(a_src["start_time"]) - float(video_stream(video)["start_time"]), abs=0.001)


def test_the_label_stays_fixed_through_playback(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2, size=SIZE)

    result = apply(label_tool, tmp_path, video, "--variant", "generated", "--corner", "bl")

    assert result.returncode == 0, result.json
    sources, labelled = frame_images(video), frame_images(Path(result.json["labelled_copy"]))
    boxes = {changed(sources[i], labelled[i]) for i in (0, 24, len(labelled) - 1)}
    assert len(boxes) == 1
    left, top, right, bottom = boxes.pop()
    assert right < 320 and top > 180, "the Label is in the bottom-left"


def test_the_label_has_a_backing_plate(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.json["plate"] is True
    box = result.json["plate_box"]
    labelled = frame_images(Path(result.json["labelled_copy"]))[10]
    inset = (box["x"] + box["width"] // 2, box["y"] + 2)  # between the plate's top edge and the icon
    expected = (255, 255, 255) if result.json["colour"] == "black" else (0, 0, 0)
    assert all(abs(a - b) < 24 for a, b in zip(labelled.getpixel(inset), expected))


def test_the_result_does_not_claim_a_lossless_copy(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.json["video"]["re_encoded"] is True
    assert "not bit-identical" in result.json["video"]["note"]
    assert result.json["validation"]["passed"] is True


def test_rerendering_replaces_the_copy_and_keeps_the_original(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE)
    before = sha256(video)
    first = apply(label_tool, tmp_path, video, "--variant", "generated", "--corner", "tr")
    first_copy = sha256(Path(first.json["labelled_copy"]))

    second = apply(label_tool, tmp_path, video, "--variant", "generated", "--corner", "bl")

    assert second.returncode == 0, second.json
    assert sha256(Path(second.json["labelled_copy"])) != first_copy
    assert sha256(video) == before
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == ["clip.ai-label.mp4", "clip.mp4"]


@pytest.mark.parametrize("link", [os.symlink, os.link], ids=["symlink", "hard link"])
def test_a_copy_linked_to_the_original_is_replaced_not_written_through(tmp_path, label_tool, link):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE)
    before = sha256(video)
    link(video, tmp_path / "clip.ai-label.mp4")

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    assert sha256(video) == before
    assert not (tmp_path / "clip.ai-label.mp4").is_symlink()


def test_a_failed_render_keeps_the_previous_copy_and_leaves_no_partial_file(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE)
    apply(label_tool, tmp_path, video, "--variant", "generated")
    previous = sha256(tmp_path / "clip.ai-label.mp4")
    bin_dir = tmp_path / "broken-bin"
    real_tool(bin_dir, "ffprobe")
    # An ffmpeg that dies part-way through writing the output.
    fake_tool(bin_dir, "ffmpeg", f'''
case "$*" in
  *.tmp*) for last; do :; done; printf 'partial' > "$last"; echo 'Conversion failed!' >&2; exit 1;;
  *) exec "{FFMPEG}" "$@";;
esac''')

    result = apply(label_tool, tmp_path, video, "--variant", "modified", env=tool_env(bin_dir))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "render_failed"
    assert sha256(tmp_path / "clip.ai-label.mp4") == previous
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == ["clip.ai-label.mp4", "clip.mp4"]


def test_a_labelled_copy_is_refused(tmp_path, label_tool):
    copy = flat_mp4(tmp_path / "clip.ai-label.mp4", seconds=1, size=SIZE)

    result = apply(label_tool, tmp_path, copy, "--variant", "generated")

    assert result.json["error"]["code"] == "labelled_copy"


def test_a_codec_outside_the_validated_paths_stops_before_rendering(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE, codec="mpeg4")

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "preservation_unsupported"
    assert [i["code"] for i in result.json["error"]["issues"]] == ["codec_not_validated"]
    assert not (tmp_path / "clip.ai-label.mp4").exists()


def test_hdr_stops_before_rendering_rather_than_becoming_sdr(tmp_path, label_tool):
    video = tmp_path / "hdr.mp4"
    ffmpeg("-f", "lavfi", "-i", f"color=c=0x5aa0d2:s={SIZE}:r=25:d=1", "-vf",
           "format=yuv420p10le,setparams=color_primaries=bt2020:color_trc=arib-std-b67:colorspace=bt2020nc",
           "-c:v", "libx264", "-pix_fmt", "yuv420p10le", video)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    assert "hdr_not_validated" in [i["code"] for i in result.json["error"]["issues"]]
    assert not (tmp_path / "hdr.ai-label.mp4").exists()


def test_a_missing_encoder_stops_before_rendering(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE)
    bin_dir = tmp_path / "bin-no-x264"
    real_tool(bin_dir, "ffprobe")
    fake_tool(bin_dir, "ffmpeg", f'''
case "$*" in
  *-encoders*) "{FFMPEG}" "$@" | grep -v libx264;;
  *) exec "{FFMPEG}" "$@";;
esac''')

    result = apply(label_tool, tmp_path, video, "--variant", "generated", env=tool_env(bin_dir))

    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    issue = next(i for i in result.json["error"]["issues"] if i["code"] == "capability_missing")
    assert "libx264" in issue["message"]
