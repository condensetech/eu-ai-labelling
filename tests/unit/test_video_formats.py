"""`label_tool video-apply` on MOV and WebM: the copy keeps the source's container and codec.

Every measurement here decodes or probes the output with the real ffmpeg and
ffprobe, independently of what label_tool reports about itself.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import sha256
from videos import (
    FFMPEG, changed, fake_tool, ffmpeg, flat_mp4, frame_images, frame_times, needs_encoder, needs_ffmpeg, probe,
    real_tool, real_tools, streams, tool_env, video_stream,
)

pytestmark = needs_ffmpeg

SIZE = "640x360"
VPX_FAST = ("-deadline", "realtime", "-cpu-used", "8")


def apply(label_tool, tmp_path, video, *args, env=None):
    return label_tool("video-apply", video, *args, env=env or real_tools(tmp_path / "bin"))


def unsupported(label_tool, tmp_path, video):
    result = apply(label_tool, tmp_path, video, "--variant", "generated")
    assert result.returncode != 0
    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    return [i["code"] for i in result.json["error"]["issues"]]


def stream_md5(path: Path, selector: str) -> str:
    """The MD5 of a stream's packets, copied out without decoding."""
    proc = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-map", selector, "-c", "copy", "-f", "md5", "-"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def major_brand(path: Path) -> str:
    return (probe(path)["format"].get("tags") or {}).get("major_brand", "").strip()


def ebml_doctype(path: Path) -> str:
    head = path.read_bytes()[:64]
    at = head.find(b"\x42\x82")
    return head[at + 3: at + 3 + (head[at + 2] & 0x7F)].decode()


def assert_label_in_top_right(source: Path, copy: Path):
    before, after = frame_images(source)[10], frame_images(copy)[10]
    left, top, right, bottom = changed(before, after)
    assert left > 320 and bottom < 180


def assert_same_picture_timing(source: Path, copy: Path):
    out, src = video_stream(copy), video_stream(source)
    assert (out["width"], out["height"], out["pix_fmt"]) == (src["width"], src["height"], src["pix_fmt"])
    assert frame_times(copy) == pytest.approx(frame_times(source), abs=0.001)
    assert float(probe(copy)["format"]["duration"]) == pytest.approx(float(probe(source)["format"]["duration"]),
                                                                     abs=0.04)


# --- MOV --------------------------------------------------------------------------

@pytest.mark.parametrize("audio", [None, "aac", "pcm_s16le", "pcm_s24le"])
def test_a_mov_gets_a_mov_copy_with_h264_and_its_audio_untouched(tmp_path, label_tool, audio):
    extra = ("-c:a", audio) if audio else ()
    video = flat_mp4(tmp_path / "clip.mov", seconds=2, size=SIZE, audio=bool(audio), extra=extra)
    before = sha256(video)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mov"
    assert result.json["labelled_copy"] == str(copy)
    assert sha256(video) == before
    assert major_brand(copy) == "qt"
    assert video_stream(copy)["codec_name"] == "h264"
    assert_same_picture_timing(video, copy)
    assert_label_in_top_right(video, copy)
    assert [s["codec_name"] for s in streams(copy, "audio")] == ([audio] if audio else [])
    if audio:
        assert stream_md5(copy, "0:a:0") == stream_md5(video, "0:a:0")
    assert result.json["path"] == "mov-h264-sdr"
    assert "H.264" in result.json["video"]["note"]


# --- WebM -------------------------------------------------------------------------

@needs_encoder("libvpx-vp9")
@pytest.mark.parametrize("audio", [False, True], ids=["silent", "opus"])
def test_a_webm_gets_a_webm_copy_with_vp9_and_its_audio_untouched(tmp_path, label_tool, audio):
    video = flat_mp4(tmp_path / "clip.webm", seconds=2, size=SIZE, audio=audio, codec="libvpx-vp9", extra=VPX_FAST)
    before = sha256(video)

    result = apply(label_tool, tmp_path, video, "--variant", "modified")

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.webm"
    assert result.json["labelled_copy"] == str(copy)
    assert sha256(video) == before
    assert ebml_doctype(copy) == "webm"
    assert video_stream(copy)["codec_name"] == "vp9"
    assert_same_picture_timing(video, copy)
    assert_label_in_top_right(video, copy)
    assert [s["codec_name"] for s in streams(copy, "audio")] == (["opus"] if audio else [])
    if audio:
        assert stream_md5(copy, "0:a:0") == stream_md5(video, "0:a:0")
    assert result.json["path"] == "webm-vp9-sdr"
    assert "VP9" in result.json["video"]["note"] and "H.264" not in result.json["video"]["note"]


@needs_encoder("libvpx")
def test_a_vp8_webm_gets_a_vp8_copy(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.webm", seconds=2, size=SIZE, audio=True, codec="libvpx", extra=VPX_FAST)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.webm"
    assert ebml_doctype(copy) == "webm"
    assert video_stream(copy)["codec_name"] == "vp8"
    assert_same_picture_timing(video, copy)
    assert_label_in_top_right(video, copy)
    assert stream_md5(copy, "0:a:0") == stream_md5(video, "0:a:0")
    assert result.json["path"] == "webm-vp8-sdr"
    assert "VP8" in result.json["video"]["note"]

# --- What a file is, not what it is called ------------------------------------------

def test_a_mov_named_mp4_stays_a_mov(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=1, size=SIZE, extra=("-f", "mov"))
    assert major_brand(video) == "qt"

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    assert result.json["path"] == "mov-h264-sdr"
    assert major_brand(tmp_path / "clip.ai-label.mp4") == "qt"


def test_an_mp4_named_mov_stays_an_mp4(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mov", seconds=1, size=SIZE, extra=("-f", "mp4"))
    assert major_brand(video) != "qt"

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    assert result.json["path"] == "mp4-h264-sdr"
    assert major_brand(tmp_path / "clip.ai-label.mov") not in ("", "qt")


@needs_encoder("libvpx-vp9")
def test_a_webm_named_mkv_stays_a_webm(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mkv", seconds=1, size=SIZE, codec="libvpx-vp9", extra=(*VPX_FAST, "-f", "webm"))

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    assert result.json["path"] == "webm-vp9-sdr"
    assert ebml_doctype(tmp_path / "clip.ai-label.mkv") == "webm"


@needs_encoder("libvpx-vp9")
def test_a_matroska_named_webm_is_not_labelled_as_webm(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.webm", seconds=1, size=SIZE, codec="libvpx-vp9", extra=(*VPX_FAST, "-f", "matroska"))
    assert ebml_doctype(video) == "matroska"

    assert unsupported(label_tool, tmp_path, video) == ["container_not_validated"]
    assert not (tmp_path / "clip.ai-label.webm").exists()


# --- Combinations outside the validated paths ------------------------------------------


@needs_encoder("prores_ks")
def test_prores_in_a_mov_stops_rather_than_becoming_h264(tmp_path, label_tool):
    video = tmp_path / "clip.mov"
    ffmpeg("-f", "lavfi", "-i", f"color=c=0x5aa0d2:s={SIZE}:r=25:d=1", "-c:v", "prores_ks", video)
    before = sha256(video)

    assert unsupported(label_tool, tmp_path, video) == ["codec_not_validated"]
    assert sha256(video) == before
    assert not (tmp_path / "clip.ai-label.mov").exists()


@needs_encoder("libsvtav1")
def test_av1_in_a_webm_stops_rather_than_becoming_vp9(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.webm", seconds=1, size=SIZE, codec="libsvtav1")

    assert unsupported(label_tool, tmp_path, video) == ["codec_not_validated"]
    assert not (tmp_path / "clip.ai-label.webm").exists()


@needs_encoder("libvpx-vp9")
def test_a_vp9_webm_in_4_4_4_stops(tmp_path, label_tool):
    video = tmp_path / "clip.webm"
    ffmpeg("-f", "lavfi", "-i", f"color=c=0x5aa0d2:s={SIZE}:r=25:d=1", "-c:v", "libvpx-vp9", *VPX_FAST,
           "-pix_fmt", "yuv444p", video)

    assert unsupported(label_tool, tmp_path, video) == ["pixel_format_not_validated"]


def test_audio_a_mov_path_cannot_copy_stops(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mov", seconds=1, size=SIZE, audio=True, extra=("-c:a", "pcm_u8"))

    assert unsupported(label_tool, tmp_path, video) == ["audio_not_validated"]


@needs_encoder("libvpx-vp9")
def test_a_missing_vp9_encoder_stops_and_keeps_the_previous_copy(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.webm", seconds=1, size=SIZE, codec="libvpx-vp9", extra=VPX_FAST)
    assert apply(label_tool, tmp_path, video, "--variant", "generated").returncode == 0
    previous, before = sha256(tmp_path / "clip.ai-label.webm"), sha256(video)
    bin_dir = tmp_path / "bin-no-vp9"
    real_tool(bin_dir, "ffprobe")
    fake_tool(bin_dir, "ffmpeg", f'''
case "$*" in
  *-encoders*) "{FFMPEG}" "$@" | "{shutil.which('grep')}" -v libvpx-vp9;;
  *) exec "{FFMPEG}" "$@";;
esac''')

    result = apply(label_tool, tmp_path, video, "--variant", "modified", env=tool_env(bin_dir))

    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    issue = next(i for i in result.json["error"]["issues"] if i["code"] == "capability_missing")
    assert "libvpx-vp9" in issue["message"]
    assert sha256(tmp_path / "clip.ai-label.webm") == previous and sha256(video) == before
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == ["clip.ai-label.webm", "clip.webm"]
    tools = label_tool("video-tools", env=tool_env(bin_dir)).json
    webm = next(p for p in tools["paths"] if p["name"] == "webm-vp9-sdr")
    assert webm["available"] is False and "encoder libvpx-vp9" in webm["missing"]
    assert next(p for p in tools["paths"] if p["name"] == "mov-h264-sdr")["available"] is True


@needs_encoder("libvpx-vp9")
def test_a_webm_keeps_its_colour_tags(tmp_path, label_tool):
    tags = ("-vf", "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")
    video = flat_mp4(tmp_path / "clip.webm", seconds=1, size=SIZE, codec="libvpx-vp9", extra=(*VPX_FAST, *tags))

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    keys = ("color_primaries", "color_transfer", "color_space", "color_range")
    out, src = video_stream(tmp_path / "clip.ai-label.webm"), video_stream(video)
    assert {k: out.get(k) for k in keys} == {k: src.get(k) for k in keys} == dict(zip(keys, ("bt709",) * 3 + ("tv",)))
