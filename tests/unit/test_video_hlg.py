"""`label_tool video-apply` and `video-preview` on HLG: the copy stays HLG, never SDR or PQ.

The fixtures are real HLG videos encoded by libx265 at test time (10-bit, BT.2020, ARIB STD-B67 in the
VUI). Every measurement decodes the output to 10-bit code values or probes its tags and side data with the
real ffmpeg and ffprobe, independently of what label_tool reports about itself.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageStat

from helpers import sha256
from test_video_hdr import altered_ffmpeg, apply, changed_box, median, unsupported
from videos import (
    FFMPEG, MASTER_DISPLAY, fake_tool, ffmpeg, frame_side_data, hdr10plus_video, hlg_video, needs_encoder,
    needs_ffmpeg, planes_10bit, real_tool, real_tools, rotated, streams, tool_env, tracked_mp4, video_stream,
)

pytestmark = [needs_ffmpeg, needs_encoder("libx265")]

REFERENCE_WHITE = 721  # HDR reference white for HLG (ITU-R BT.2408), 75% signal: 64 + 0.75 * 876 in 10-bit limited range


def test_an_hlg_mp4_gets_an_hlg_copy_without_hdr10_metadata(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4")
    before = sha256(video)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    assert result.json["path"] == "mp4-hevc-hlg"
    assert sha256(video) == before
    stream = video_stream(copy)
    assert (stream["codec_name"], stream["profile"], stream["pix_fmt"]) == ("hevc", "Main 10", "yuv420p10le")
    assert (stream["color_primaries"], stream["color_transfer"], stream["color_space"], stream["color_range"]) == (
        "bt2020", "arib-std-b67", "bt2020nc", "tv")
    side = frame_side_data(copy)
    assert "Mastering display metadata" not in side and "Content light level metadata" not in side, side
    assert stream["codec_tag_string"] == video_stream(video)["codec_tag_string"]
    hdr = result.json["video"]["hdr"]
    assert hdr["dynamic_range"] == "hlg" and hdr["label_white_signal"] == 0.75 and "no HDR display" in hdr["note"]
    assert {"hdr_metadata", "hdr_picture", "label_level"} <= {c["check"] for c in result.json["validation"]["checks"]}


def test_an_hvc1_tagged_hlg_source_keeps_its_tag(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4", extra=("-tag:v", "hvc1"))

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    assert video_stream(tmp_path / "clip.ai-label.mp4")["codec_tag_string"] == "hvc1"


@pytest.mark.parametrize("colour, source, plate", [("black", "0x202020", REFERENCE_WHITE), ("white", "0xd0d0d0", 64)])
def test_the_label_is_mapped_to_hlg_reference_white(tmp_path, label_tool, colour, source, plate):
    video = hlg_video(tmp_path / "clip.mp4", source=source)

    result = apply(label_tool, tmp_path, video, "--colour", colour)

    assert result.returncode == 0, result.json
    (y0, _, _, size), (y1, _, _, _) = planes_10bit(video, 12), planes_10bit(tmp_path / "clip.ai-label.mp4", 12)
    left, top, right, bottom = changed_box(y0, y1, size)
    assert left > size[0] // 2 and bottom < size[1] // 2, "the Label is in the top-right"
    band = [y1[row * size[0] + left + 1] for row in range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3)]
    assert median(band) == pytest.approx(plate, abs=4), "the backing plate's level in the HLG signal"
    label = [b for a, b in zip(y0, y1) if abs(a - b) > 40]  # the plate's rounded corners show the source
    assert max(label) <= REFERENCE_WHITE + 10, "no Label pixel is brighter than 75% HLG"
    assert min(label) >= 64 - 10


def test_the_picture_outside_the_label_keeps_its_10_bit_hlg_values(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4")

    result = apply(label_tool, tmp_path, video, "--corner", "bl")

    assert result.returncode == 0, result.json
    before, after = planes_10bit(video, 12), planes_10bit(tmp_path / "clip.ai-label.mp4", 12)
    width, height = before[3]
    for plane, (a, b) in enumerate(zip(before[:3], after[:3])):
        w = width if plane == 0 else width // 2
        h = len(a) // w
        outside = [(y - x) for i, (x, y) in enumerate(zip(a, b)) if not (i % w < w // 2 and i // w > h // 2)]
        assert sum(abs(d) for d in outside) / len(outside) < 2, "only re-encoding noise outside the Label"
        assert abs(sum(outside) / len(outside)) < 0.5, "no shift of levels: no conversion to PQ or SDR"
    assert sum(v % 4 != 0 for v in after[0]) / len(after[0]) > 0.5, "10-bit precision, not 8-bit values scaled up"


def test_an_hlg_source_with_static_metadata_keeps_it(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4", source="0x202020", mastering=True, max_cll=(150, 60))

    result = apply(label_tool, tmp_path, video, "--colour", "black")

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    assert video_stream(copy)["color_transfer"] == "arib-std-b67"
    side, source = frame_side_data(copy), frame_side_data(video)
    assert side["Mastering display metadata"] == source["Mastering display metadata"]
    assert side["Content light level metadata"]["max_content"] == 203, "the white plate on a 1000 cd/m2 display"


def test_hlg_content_light_follows_the_mastering_display_peak(tmp_path, label_tool):
    # On a 4000 cd/m2 display BT.2100's system gamma is 1.2 + 0.42 log10(4) = 1.453, so 75% HLG shows at
    # about 581 cd/m2, not at the 203 cd/m2 of a 1000 cd/m2 display.
    peak_4000 = "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(40000000,1)"
    video = hlg_video(tmp_path / "clip.mp4", source="0x202020", mastering=peak_4000, max_cll=(150, 60))

    result = apply(label_tool, tmp_path, video, "--colour", "black")

    assert result.returncode == 0, result.json
    light = frame_side_data(tmp_path / "clip.ai-label.mp4")["Content light level metadata"]
    assert light["max_content"] == pytest.approx(581, abs=1)


def test_audio_and_subtitle_tracks_are_kept_in_an_hlg_copy(tmp_path, label_tool):
    picture = hlg_video(tmp_path / "picture.mp4", seconds=2)
    video = tracked_mp4(tmp_path / "clip.mp4", video=picture,
                        audio=[{"language": "eng", "disposition": "default"}, {"language": "ita"}],
                        subtitles=[{"language": "eng"}])

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    kept = [(s["codec_name"], s["tags"].get("language")) for s in streams(copy, "audio") + streams(copy, "subtitle")]
    assert kept == [("aac", "eng"), ("aac", "ita"), ("mov_text", "eng")]
    assert video_stream(copy)["color_transfer"] == "arib-std-b67"


def frame_grey(path: str) -> float:
    with Image.open(path) as frame:
        return ImageStat.Stat(frame.convert("L")).median[0]


def test_preview_frames_render_hlg_through_its_own_curve(tmp_path, label_tool):
    # Grey 0xc0c0c0 is about 75% of the signal, code value 721: HLG reference white. Shown as SDR code
    # values it would be a light grey, about 191.
    video = hlg_video(tmp_path / "clip.mp4", source="0xc0c0c0", seconds=2)
    assert median(planes_10bit(video, 0)[0]) == pytest.approx(REFERENCE_WHITE, abs=8)

    result = label_tool("video-preview", video, "--variant", "generated", env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert result.json["frame_rendering"] == "sdr_tone_mapped"
    assert "HLG" in result.json["hdr_note"] and "SDR" in result.json["hdr_note"]
    for entry in result.json["frames"]:
        assert 225 < frame_grey(entry["path"]) < 252, "reference white looks near white, not clipped"


def test_preview_frames_of_mid_grey_hlg_follow_the_hlg_curve_not_pq(tmp_path, label_tool):
    # 50% HLG is a quarter of reference white in display light (inverse OETF, system gamma 1.2): about 137
    # in sRGB. Read through the PQ curve it would be 92 cd/m2, about 179.
    video = hlg_video(tmp_path / "clip.mp4", source="0x808080", seconds=2)

    result = label_tool("video-preview", video, "--variant", "generated", env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert frame_grey(result.json["frames"][0]["path"]) == pytest.approx(137, abs=10)


def test_preview_excerpts_are_hlg_like_the_labelled_copy(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4", source="0x202020", seconds=3)
    settings = ("--variant", "generated", "--colour", "black", "--visibility", "continuous")

    result = label_tool("video-preview", video, *settings, env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    excerpt = result.json["excerpts"][0]["path"]
    stream = video_stream(excerpt)
    assert (stream["codec_name"], stream["pix_fmt"], stream["color_transfer"], stream["color_primaries"]) == (
        "hevc", "yuv420p10le", "arib-std-b67", "bt2020")
    assert "Mastering display metadata" not in frame_side_data(excerpt)
    (y0, _, _, size), (y1, _, _, _) = planes_10bit(video, 0), planes_10bit(excerpt, 0)
    left, top, right, bottom = changed_box(y0, y1, size)
    band = [y1[row * size[0] + left + 1] for row in range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3)]
    assert median(band) == pytest.approx(REFERENCE_WHITE, abs=4)


def test_a_rotated_hlg_video_stops(tmp_path, label_tool):
    video = rotated(hlg_video(tmp_path / "upright.mp4"), tmp_path / "clip.mp4", 90)

    assert [i["code"] for i in unsupported(label_tool, tmp_path, video)] == ["rotation_not_validated"]


def test_hlg_with_other_colour_tags_is_not_converted(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4", primaries="bt709")
    assert video_stream(video)["color_transfer"] == "arib-std-b67"

    issues = unsupported(label_tool, tmp_path, video)

    assert [i["code"] for i in issues] == ["colour_not_validated"]
    assert "primaries bt709" in issues[0]["message"] and "HLG" in issues[0]["message"]


def test_hlg_with_hdr10_plus_metadata_stops_rather_than_losing_it(tmp_path, label_tool):
    video = hdr10plus_video(tmp_path / "clip.mp4", hlg=True)
    assert "HDR Dynamic Metadata SMPTE2094-40 (HDR10+)" in frame_side_data(video), "real dynamic metadata"

    issues = unsupported(label_tool, tmp_path, video)

    assert [i["code"] for i in issues] == ["hdr_not_validated"] and "HDR10+" in issues[0]["message"]


def test_hlg_in_mov_has_no_path(tmp_path, label_tool):
    video = tmp_path / "clip.mov"
    ffmpeg("-i", hlg_video(tmp_path / "picture.mp4"), "-c", "copy", video)

    assert [i["code"] for i in unsupported(label_tool, tmp_path, video)] == ["codec_not_validated"]
    assert not (tmp_path / "clip.ai-label.mov").exists()


def test_a_build_without_libx265_stops_and_video_tools_says_so(tmp_path, label_tool):
    video = hlg_video(tmp_path / "clip.mp4")
    bin_dir = tmp_path / "bin-no-x265"
    real_tool(bin_dir, "ffprobe")
    fake_tool(bin_dir, "ffmpeg", f'''
case "$*" in
  *-encoders*) "{FFMPEG}" "$@" | grep -v libx265;;
  *) exec "{FFMPEG}" "$@";;
esac''')

    issues = unsupported(label_tool, tmp_path, video, env=tool_env(bin_dir))
    without = label_tool("video-tools", env=tool_env(bin_dir)).json
    with_it = label_tool("video-tools", env=real_tools(tmp_path / "bin")).json

    assert [i["code"] for i in issues] == ["capability_missing"] and "libx265" in issues[0]["message"]
    path = next(p for p in without["paths"] if p["name"] == "mp4-hevc-hlg")
    assert path["available"] is False and path["missing"] == ["encoder libx265"]
    assert next(p for p in with_it["paths"] if p["name"] == "mp4-hevc-hlg")["available"] is True


@pytest.mark.parametrize("pattern, replacement, check", [
    (r"(?<=.)\[labelled\]$", ",setparams=color_trc=smpte2084[labelled]", "colour"),  # signalled as PQ
    ("^log-level=error$", f"log-level=error:hdr10=1:master-display={MASTER_DISPLAY}:max-cll=1000,400",
     "hdr_metadata"),  # HDR10-only metadata injected
    (r"(?<=.)\[labelled\]$", ",lutyuv=y='val*0.9+20'[labelled]", "hdr_picture"),  # levels changed, tags kept
    (r"colorchannelmixer=rr=[0-9.]+:gg=[0-9.]+:bb=[0-9.]+", "colorchannelmixer", "label_level"),  # Label at peak
])
def test_an_hlg_copy_that_loses_its_signalling_or_levels_is_discarded(tmp_path, label_tool, pattern, replacement,
                                                                      check):
    video = hlg_video(tmp_path / "clip.mp4", source="0x202020")
    copy = tmp_path / "clip.ai-label.mp4"
    copy.write_bytes(b"previous copy")

    result = apply(label_tool, tmp_path, video, "--colour", "black", env=altered_ffmpeg(tmp_path, pattern, replacement))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "output_validation_failed", result.json
    failed = [c["check"] for c in result.json["error"]["checks"] if not c["passed"]]
    assert check in failed, result.json["error"]["checks"]
    assert copy.read_bytes() == b"previous copy"
    assert not list(tmp_path.glob(".*.tmp"))
