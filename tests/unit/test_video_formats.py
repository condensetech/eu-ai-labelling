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
def test_a_webm_whose_doctype_sits_late_in_its_header_is_still_read(tmp_path, label_tool):
    plain = flat_mp4(tmp_path / "plain.webm", seconds=1, size=SIZE, codec="libvpx-vp9", extra=VPX_FAST)
    data = plain.read_bytes()
    assert data[4] & 0x80, "a one-byte EBML header size"
    size, doctype = data[4] & 0x7F, data.find(b"\x42\x82")
    # A Void element (0xEC) of 41 bytes before the DocType puts its ID on the 63rd and 64th bytes.
    void = bytes([0xEC, 0x80 | 39]) + bytes(39)
    padded = tmp_path / "clip.webm"
    padded.write_bytes(data[:4] + bytes([0x80 | (size + len(void))]) + data[5:doctype] + void + data[doctype:])
    assert padded.read_bytes().find(b"\x42\x82") == 62
    assert probe(padded)["streams"], "ffprobe reads it"

    result = label_tool("video-inspect", padded, env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert result.json["container"]["format"] == "webm"


@needs_encoder("libvpx-vp9")
@pytest.mark.parametrize("cut", [5, 22, 25])
def test_a_truncated_webm_header_is_unreadable_not_an_internal_error(tmp_path, label_tool, cut):
    plain = flat_mp4(tmp_path / "plain.webm", seconds=1, size=SIZE, codec="libvpx-vp9", extra=VPX_FAST)
    cut_short = tmp_path / "clip.webm"
    cut_short.write_bytes(plain.read_bytes()[:cut])

    result = label_tool("video-inspect", cut_short, env=real_tools(tmp_path / "bin"))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "unreadable_video", result.json


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


# --- Chroma subsampling -------------------------------------------------------------

def chroma_planes(path: Path) -> tuple[bytes, bytes, int, int]:
    """The first frame's U and V planes, decoded at full resolution (4:4:4), and the frame size."""
    stream = video_stream(path)
    width, height = stream["width"], stream["height"]
    proc = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                           "-pix_fmt", "yuv444p", "-"], capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode()
    plane = width * height
    return proc.stdout[plane:2 * plane], proc.stdout[2 * plane:3 * plane], width, height


# 1-px stripes of opposite chroma, along the axis the pixel format keeps at full resolution: 4:2:0 averages
# each pair to grey (128). 4:4:4 keeps columns and rows; 4:2:2 keeps rows.
STRIPES = {"yuv444p": "mod(X,2)", "yuv422p": "mod(Y,2)"}


@pytest.mark.parametrize("suffix", [".mp4", ".mov"])
@pytest.mark.parametrize("pix_fmt", ["yuv444p", "yuv422p"])
def test_h264_4_4_4_and_4_2_2_keep_their_chroma_detail_outside_the_label(tmp_path, label_tool, pix_fmt, suffix):
    video = tmp_path / f"clip{suffix}"
    odd = STRIPES[pix_fmt]
    ffmpeg("-f", "lavfi", "-i", f"nullsrc=s={SIZE}:r=25:d=1", "-vf",
           f"format={pix_fmt},geq=lum=128:cb='if({odd},48,208)':cr='if({odd},208,48)'",
           "-c:v", "libx264", "-qp", "0", "-pix_fmt", pix_fmt, video)

    result = apply(label_tool, tmp_path, video, "--variant", "generated")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    assert video_stream(copy)["pix_fmt"] == pix_fmt
    (u0, v0, width, height), (u1, v1, *_) = chroma_planes(video), chroma_planes(copy)
    # The left half of the picture: the Label is in the top-right.
    left = [row * width + col for row in range(height) for col in range(width // 2)]
    for before, after in ((u0, u1), (v0, v1)):
        assert max(abs(before[i] - 128) for i in left) > 70, "the source has the stripes"
        change = sum(abs(after[i] - before[i]) for i in left) / len(left)
        assert change < 6, f"chroma changed by {change:.1f} on average outside the Label"
