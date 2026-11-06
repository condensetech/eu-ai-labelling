"""`label_tool video-apply` and `video-preview` on HDR10: the copy stays HDR10, never SDR.

The fixtures are real HDR10 videos encoded by libx265 at test time (10-bit,
BT.2020, PQ, HDR10 SEI). Every measurement decodes the output to 10-bit code
values or probes its side data with the real ffmpeg and ffprobe,
independently of what label_tool reports about itself.
"""

from __future__ import annotations

import sys

import pytest
from PIL import Image, ImageStat

from helpers import sha256
from videos import (
    FFMPEG, FFPROBE, fake_tool, ffmpeg, frame_side_data, hdr10_video, hdr10plus_info, hlg_video, needs_encoder,
    needs_ffmpeg, planes_10bit, real_tool, real_tools, rotated, streams, tool_env, tracked_mp4, video_stream,
)

pytestmark = [needs_ffmpeg, needs_encoder("libx265")]

SIZE = "640x360"
MASTERING = {"red_x": "34000/50000", "red_y": "16000/50000", "green_x": "13250/50000", "green_y": "34500/50000",
             "blue_x": "7500/50000", "blue_y": "3000/50000", "white_point_x": "15635/50000",
             "white_point_y": "16450/50000", "min_luminance": "1/10000", "max_luminance": "10000000/10000"}
# SDR reference white (ITU-R BT.2408), 203 cd/m2, is PQ signal 0.5807 (SMPTE ST 2084; BT.2408 tabulates 58%):
# 64 + 876 * 0.5807 in 10-bit limited range.
REFERENCE_WHITE = 572.7


def apply(label_tool, tmp_path, video, *args, env=None):
    return label_tool("video-apply", video, "--variant", "generated", *args, env=env or real_tools(tmp_path / "bin"))


def unsupported(label_tool, tmp_path, video, env=None):
    result = apply(label_tool, tmp_path, video, env=env)
    assert result.returncode != 0
    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    return result.json["error"]["issues"]


def test_an_hdr10_mp4_gets_an_hdr10_copy_with_its_mastering_metadata(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4")
    before = sha256(video)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    assert result.json["path"] == "mp4-hevc-hdr10"
    assert sha256(video) == before
    stream = video_stream(copy)
    assert (stream["codec_name"], stream["profile"], stream["pix_fmt"]) == ("hevc", "Main 10", "yuv420p10le")
    assert (stream["color_primaries"], stream["color_transfer"], stream["color_space"], stream["color_range"]) == (
        "bt2020", "smpte2084", "bt2020nc", "tv")
    side = frame_side_data(copy)
    mastering = {k: v for k, v in side["Mastering display metadata"].items() if k != "side_data_type"}
    assert mastering == MASTERING
    assert side["Content light level metadata"]["max_content"] == 1000, "the source's brightest pixel stays brightest"
    assert stream["codec_tag_string"] == video_stream(video)["codec_tag_string"]
    hdr = result.json["video"]["hdr"]
    assert hdr["label_white_nits"] == 203 and "no HDR display" in hdr["note"]
    assert {"hdr_metadata", "hdr_picture", "label_level"} <= {c["check"] for c in result.json["validation"]["checks"]}


def test_an_hvc1_tagged_source_keeps_its_tag(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", extra=("-tag:v", "hvc1"))

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    assert video_stream(tmp_path / "clip.ai-label.mp4")["codec_tag_string"] == "hvc1"


def changed_box(before: list, after: list, size: tuple, threshold: int = 40) -> tuple:
    """The box of luma samples that differ by more than `threshold` 10-bit code values."""
    width = size[0]
    points = [(i % width, i // width) for i, (a, b) in enumerate(zip(before, after)) if abs(a - b) > threshold]
    assert points, "nothing changed"
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def median(values: list) -> float:
    return sorted(values)[len(values) // 2]


@pytest.mark.parametrize("colour, source, plate", [("black", "0x202020", REFERENCE_WHITE), ("white", "0xd0d0d0", 64)])
def test_the_label_is_mapped_to_sdr_reference_white_not_to_peak_brightness(tmp_path, label_tool, colour, source,
                                                                            plate):
    video = hdr10_video(tmp_path / "clip.mp4", source=source)

    result = apply(label_tool, tmp_path, video, "--colour", colour)

    assert result.returncode == 0, result.json
    (y0, _, _, size), (y1, _, _, _) = planes_10bit(video, 12), planes_10bit(tmp_path / "clip.ai-label.mp4", 12)
    left, top, right, bottom = changed_box(y0, y1, size)
    assert left > size[0] // 2 and bottom < size[1] // 2, "the Label is in the top-right"
    band = [y1[row * size[0] + left + 1] for row in range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3)]
    assert median(band) == pytest.approx(plate, abs=4), "the backing plate's level in the PQ signal"
    label = [b for a, b in zip(y0, y1) if abs(a - b) > 40]  # the plate's rounded corners show the source
    assert max(label) <= REFERENCE_WHITE + 10, "no Label pixel is brighter than reference white"
    assert min(label) >= 64 - 10


def test_the_picture_outside_the_label_keeps_its_10_bit_pq_values(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4")

    result = apply(label_tool, tmp_path, video, "--corner", "bl")

    assert result.returncode == 0, result.json
    before, after = planes_10bit(video, 12), planes_10bit(tmp_path / "clip.ai-label.mp4", 12)
    width, height = before[3]
    for plane, (a, b) in enumerate(zip(before[:3], after[:3])):
        w = width if plane == 0 else width // 2
        h = len(a) // w
        outside = [(y - x) for i, (x, y) in enumerate(zip(a, b)) if not (i % w < w // 2 and i // w > h // 2)]
        assert sum(abs(d) for d in outside) / len(outside) < 2, "only re-encoding noise outside the Label"
        assert abs(sum(outside) / len(outside)) < 0.5, "no shift of levels: the transfer wasn't converted"
    assert sum(v % 4 != 0 for v in after[0]) / len(after[0]) > 0.5, "10-bit precision, not 8-bit values scaled up"


def test_content_light_levels_account_for_the_label_brighter_than_the_source(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", source="0x202020", max_cll=(150, 60))

    result = apply(label_tool, tmp_path, video, "--colour", "black")

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    light = frame_side_data(copy)["Content light level metadata"]
    assert light["max_content"] == 203, "MaxCLL: the white plate is at 203 cd/m2, above the source's 150"
    (y0, _, _, size), (y1, _, _, _) = planes_10bit(video, 12), planes_10bit(copy, 12)
    left, top, right, bottom = changed_box(y0, y1, size)
    bound = 60 + (right - left) * (bottom - top) / (size[0] * size[1]) * 203
    assert 60 < light["max_average"] <= bound + 1, "MaxFALL raised by at most the Label's share at 203 cd/m2"


def test_a_source_without_content_light_levels_gets_none_invented(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", max_cll=None)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    side = frame_side_data(tmp_path / "clip.ai-label.mp4")
    assert "Mastering display metadata" in side
    light = side.get("Content light level metadata", {"max_content": 0, "max_average": 0})
    assert (light["max_content"], light["max_average"]) == (0, 0), "unknown stays unknown"


def test_audio_and_subtitle_tracks_are_kept_in_an_hdr10_copy(tmp_path, label_tool):
    picture = hdr10_video(tmp_path / "picture.mp4", seconds=2)
    video = tracked_mp4(tmp_path / "clip.mp4", video=picture,
                        audio=[{"language": "eng", "disposition": "default"}, {"language": "ita", "title": "Italiano"}],
                        subtitles=[{"language": "eng", "disposition": "forced"}])

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = tmp_path / "clip.ai-label.mp4"
    kept = [(s["codec_name"], s["tags"].get("language")) for s in streams(copy, "audio") + streams(copy, "subtitle")]
    assert kept == [("aac", "eng"), ("aac", "ita"), ("mov_text", "eng")]
    assert streams(copy, "subtitle")[0]["disposition"]["forced"] == 1
    assert frame_side_data(copy)["Mastering display metadata"]


def test_a_rotated_hdr10_video_stops(tmp_path, label_tool):
    video = rotated(hdr10_video(tmp_path / "upright.mp4"), tmp_path / "clip.mp4", 90)

    assert [i["code"] for i in unsupported(label_tool, tmp_path, video)] == ["rotation_not_validated"]


def test_preview_frames_are_sdr_renderings_that_say_so(tmp_path, label_tool):
    # Grey 0x959595 lands at about code value 572 in the 10-bit PQ signal: SDR reference white, 203 cd/m2.
    video = hdr10_video(tmp_path / "clip.mp4", source="0x959595", seconds=2)
    assert median(planes_10bit(video, 0)[0]) == pytest.approx(REFERENCE_WHITE, abs=4)

    result = label_tool("video-preview", video, "--variant", "generated", env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert result.json["frame_rendering"] == "sdr_tone_mapped"
    assert "HDR" in result.json["hdr_note"] and "SDR" in result.json["hdr_note"]
    for entry in result.json["frames"]:
        with Image.open(entry["path"]) as frame:
            grey = ImageStat.Stat(frame.convert("L")).median[0]
        assert grey > 220, "reference white looks near white, not the dim grey of PQ code values shown as SDR"


def test_preview_excerpts_are_hdr10_like_the_labelled_copy(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", source="0x202020", seconds=3, max_cll=(150, 60))
    settings = ("--variant", "generated", "--colour", "black", "--visibility", "continuous")

    result = label_tool("video-preview", video, *settings, env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    excerpt = result.json["excerpts"][0]["path"]
    stream = video_stream(excerpt)
    assert (stream["codec_name"], stream["pix_fmt"], stream["color_transfer"], stream["color_primaries"]) == (
        "hevc", "yuv420p10le", "smpte2084", "bt2020")
    side = frame_side_data(excerpt)
    assert side["Mastering display metadata"] and side["Content light level metadata"]["max_content"] == 203
    (y0, _, _, size), (y1, _, _, _) = planes_10bit(video, 0), planes_10bit(excerpt, 0)
    left, top, right, bottom = changed_box(y0, y1, size)
    band = [y1[row * size[0] + left + 1] for row in range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3)]
    assert median(band) == pytest.approx(REFERENCE_WHITE, abs=4)


def test_hdr10_plus_stops_rather_than_losing_its_dynamic_metadata(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", hdr10plus=hdr10plus_info(tmp_path / "hdr10plus.json"))
    assert "HDR Dynamic Metadata SMPTE2094-40 (HDR10+)" in frame_side_data(video), "a real HDR10+ fixture"

    issues = unsupported(label_tool, tmp_path, video)

    assert [i["code"] for i in issues] == ["hdr_not_validated"]
    assert "HDR10+" in issues[0]["message"] and "dynamic metadata" in issues[0]["message"]
    assert not (tmp_path / "clip.ai-label.mp4").exists()


# What ffprobe reports for a Dolby Vision file, by where it reports it: the MP4's configuration box (dvcC or
# dvvC) as stream side data, the RPU as the first frame's side data, a DV-only sample entry as the codec tag.
DOLBY_VISION = {
    "stream": "for s in data.get('streams', []):\n"
              "    if s.get('codec_type') == 'video':\n"
              "        s.setdefault('side_data_list', []).append({'side_data_type': 'DOVI configuration record',\n"
              "            'dv_version_major': 1, 'dv_version_minor': 0, 'dv_profile': 8, 'dv_level': 4,\n"
              "            'rpu_present_flag': 1, 'el_present_flag': 0, 'bl_present_flag': 1,\n"
              "            'dv_bl_signal_compatibility_id': 1})\n",
    "frame": "for f in data.get('frames', []):\n"
             "    f.setdefault('side_data_list', []).extend([{'side_data_type': 'Dolby Vision RPU Data'},\n"
             "                                               {'side_data_type': 'Dolby Vision Metadata'}])\n",
    "codec_tag": "for s in data.get('streams', []):\n"
                 "    if s.get('codec_type') == 'video':\n"
                 "        s['codec_tag_string'] = 'dvh1'\n",
}


def dolby_vision_ffprobe(bin_dir, where: str) -> dict:
    """PATH with the real ffmpeg and a real ffprobe whose JSON reports Dolby Vision `where` (DOLBY_VISION)."""
    real_tool(bin_dir, "ffmpeg")
    script = bin_dir / "dovi.py"
    script.write_text(
        "import json, subprocess, sys\n"
        f"proc = subprocess.run([{FFPROBE!r}, *sys.argv[1:]], capture_output=True, text=True)\n"
        "sys.stderr.write(proc.stderr)\n"
        "try:\n"
        "    data = json.loads(proc.stdout)\n"
        "except json.JSONDecodeError:\n"
        "    sys.stdout.write(proc.stdout)\n"
        "    sys.exit(proc.returncode)\n"
        + DOLBY_VISION[where] +
        "json.dump(data, sys.stdout)\n"
        "sys.exit(proc.returncode)\n")
    fake_tool(bin_dir, "ffprobe", f'exec "{sys.executable}" "{script}" "$@"')
    return tool_env(bin_dir)


@pytest.mark.parametrize("where", sorted(DOLBY_VISION))
def test_dolby_vision_is_recognised_and_stops(tmp_path, label_tool, where):
    # Simulated: no encoder here writes Dolby Vision, so ffprobe reports an HDR10 fixture as Dolby Vision.
    video = hdr10_video(tmp_path / "clip.mp4")

    issues = unsupported(label_tool, tmp_path, video, env=dolby_vision_ffprobe(tmp_path / "bin-dovi", where))

    assert [i["code"] for i in issues] == ["hdr_not_validated"]
    assert "Dolby Vision" in issues[0]["message"]


def test_hdr10_without_mastering_metadata_stops(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", mastering=False, max_cll=None)
    assert video_stream(video)["color_transfer"] == "smpte2084"

    issues = unsupported(label_tool, tmp_path, video)

    assert [i["code"] for i in issues] == ["hdr_metadata_missing"]


def unreadable_mastering_ffprobe(bin_dir: Path, value: str) -> dict:
    """An ffprobe that reports the mastering display's peak luminance as `value`, as a file with
    partial or malformed metadata would."""
    real_tool(bin_dir, "ffmpeg")
    fake_tool(bin_dir, "ffprobe", f'''
case "$*" in
  *frame_side_data*) "{FFPROBE}" "$@" | /usr/bin/sed 's#"max_luminance": "[^"]*"#"max_luminance": "{value}"#';;
  *) exec "{FFPROBE}" "$@";;
esac''')
    return tool_env(bin_dir)


@pytest.mark.parametrize("make", [hdr10_video, lambda path: hlg_video(path, mastering=True)], ids=["hdr10", "hlg"])
@pytest.mark.parametrize("value", ["0/0", "N/A"])
def test_unreadable_mastering_metadata_stops_before_rendering(tmp_path, label_tool, make, value):
    video = make(tmp_path / "clip.mp4")
    env = unreadable_mastering_ffprobe(tmp_path / "bin-partial", value)

    issues = unsupported(label_tool, tmp_path, video, env=env)
    inspected = label_tool("video-inspect", video, env=env).json["labelling"]

    assert [i["code"] for i in issues] == ["hdr_metadata_missing"]
    assert "max_luminance" in issues[0]["message"]
    assert inspected["supported"] is False and inspected["issues"] == issues
    assert not (tmp_path / "clip.ai-label.mp4").exists()


def test_sdr_hevc_has_no_path(tmp_path, label_tool):
    sdr = tmp_path / "sdr.mp4"
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=s={SIZE}:r=25:d=1", "-c:v", "libx265", "-preset", "ultrafast",
           "-x265-params", "log-level=error", "-pix_fmt", "yuv420p", sdr)

    assert [i["code"] for i in unsupported(label_tool, tmp_path, sdr)] == ["codec_not_validated"]


def test_pq_with_other_colour_tags_is_not_converted(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4", primaries="bt709")

    issues = unsupported(label_tool, tmp_path, video)

    assert [i["code"] for i in issues] == ["colour_not_validated"]
    assert "primaries bt709" in issues[0]["message"]


def test_a_build_without_libx265_stops_and_video_tools_says_so(tmp_path, label_tool):
    video = hdr10_video(tmp_path / "clip.mp4")
    bin_dir = tmp_path / "bin-no-x265"
    real_tool(bin_dir, "ffprobe")
    fake_tool(bin_dir, "ffmpeg", f'''
case "$*" in
  *-encoders*) "{FFMPEG}" "$@" | grep -v libx265;;
  *) exec "{FFMPEG}" "$@";;
esac''')

    issues = unsupported(label_tool, tmp_path, video, env=tool_env(bin_dir))
    report = label_tool("video-tools", env=tool_env(bin_dir)).json

    assert [i["code"] for i in issues] == ["capability_missing"] and "libx265" in issues[0]["message"]
    path = next(p for p in report["paths"] if p["name"] == "mp4-hevc-hdr10")
    assert path["available"] is False and path["missing"] == ["encoder libx265"]


def test_video_tools_lists_what_the_hdr10_path_needs(tmp_path, label_tool):
    report = label_tool("video-tools", env=real_tools(tmp_path / "bin")).json

    path = next(p for p in report["paths"] if p["name"] == "mp4-hevc-hdr10")
    assert path["available"] is True, path


def altered_ffmpeg(tmp_path, pattern: str, replacement: str) -> dict:
    """PATH with the real ffprobe and a real ffmpeg whose arguments have `pattern` (a regex) replaced: a
    render that gets the HDR wrong while ffmpeg still succeeds."""
    bin_dir = tmp_path / "bin-altered"
    real_tool(bin_dir, "ffprobe")
    script = bin_dir / "alter.py"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "import os, re, sys\n"
        f"args = [re.sub({pattern!r}, {replacement!r}, a) for a in sys.argv[1:]]\n"
        f"os.execv({FFMPEG!r}, [{FFMPEG!r}, *args])\n")
    fake_tool(bin_dir, "ffmpeg", f'exec "{sys.executable}" "{script}" "$@"')
    return tool_env(bin_dir)


@pytest.mark.parametrize("pattern, replacement, check", [
    (r":max-cll=\d+,\d+", "", "hdr_metadata"),  # libx265 then copies the source's 150 cd/m2
    (r"(?<=.)\[labelled\]$",",lutyuv=y='val*0.9+20'[labelled]", "hdr_picture"),  # levels changed, tags kept
    (r"colorchannelmixer=rr=[0-9.]+:gg=[0-9.]+:bb=[0-9.]+", "colorchannelmixer", "label_level"),  # Label at peak
])
def test_a_copy_that_loses_the_hdr_treatment_is_discarded(tmp_path, label_tool, pattern, replacement, check):
    video = hdr10_video(tmp_path / "clip.mp4", source="0x202020", max_cll=(150, 60))
    copy = tmp_path / "clip.ai-label.mp4"
    copy.write_bytes(b"previous copy")

    result = apply(label_tool, tmp_path, video, "--colour", "black", env=altered_ffmpeg(tmp_path, pattern, replacement))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "output_validation_failed", result.json
    failed = [c["check"] for c in result.json["error"]["checks"] if not c["passed"]]
    assert check in failed, result.json["error"]["checks"]
    assert copy.read_bytes() == b"previous copy"
    assert not list(tmp_path.glob(".*.tmp"))
