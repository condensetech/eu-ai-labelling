"""`label_tool video-apply` keeps tracks, orientation and variable timing, or stops and asks.

Every measurement decodes or probes the output with the real ffmpeg and ffprobe,
independently of what label_tool reports about itself.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from helpers import sha256
from videos import (
    FFMPEG, FFPROBE, changed, fake_tool, ffmpeg, flat_mp4, frame_images, frame_times, needs_encoder, needs_ffmpeg,
    probe, real_tool, real_tools, rotated, streams, tool_env, tracked_mp4, variable_rate_mp4, video_stream,
)

pytestmark = needs_ffmpeg

SIZE = "640x360"
# The paths validated to keep tracks, rotation and variable timing.
CONTAINERS = pytest.mark.parametrize("suffix", [".mp4", ".mov"])


def apply(label_tool, tmp_path, video, *args, env=None):
    return label_tool("video-apply", video, "--variant", "generated", *args, env=env or real_tools(tmp_path / "bin"))


def stream_md5(path: Path, selector: str) -> str:
    """The MD5 of a stream's packets, copied out without decoding."""
    proc = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-map", selector, "-c", "copy", "-f", "md5", "-"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def described(stream: dict) -> dict:
    tags = stream.get("tags") or {}
    return {"codec": stream["codec_name"], "language": tags.get("language"),
            "title": tags.get("title") or tags.get("name"),
            "disposition": {k for k, v in stream["disposition"].items() if v}}


def offset(path: Path, stream: dict) -> float:
    return float(stream["start_time"]) - float(video_stream(path)["start_time"])


AUDIO = [{"language": "eng", "title": "English", "disposition": "default", "frequency": 440},
         {"language": "ita", "title": "Commento", "disposition": "comment", "frequency": 660, "sample_rate": 44100}]


@CONTAINERS
def test_every_audio_track_is_copied_with_its_language_title_disposition_and_sync(tmp_path, label_tool, suffix):
    video = tracked_mp4(tmp_path / f"clip{suffix}", audio=AUDIO, size=SIZE)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    source, labelled = streams(video, "audio"), streams(copy, "audio")
    assert [described(s) for s in labelled] == [described(s) for s in source]
    # QuickTime stores no `comment` flag, so a MOV source can't have one to lose.
    assert described(labelled[1]) == {"codec": "aac", "language": "ita", "title": "Commento",
                                      "disposition": {"comment"} if suffix == ".mp4" else set()}
    for n in range(2):
        assert stream_md5(copy, f"0:a:{n}") == stream_md5(video, f"0:a:{n}")
        assert offset(copy, labelled[n]) == pytest.approx(offset(video, source[n]), abs=0.001)


SUBTITLES = [{"language": "eng", "disposition": "0"},
             {"language": "fra", "title": "Forced FR", "disposition": "default+forced",
              "cues": [(0.5, 1.2, "Bonjour"), (1.4, 1.9, "Au revoir")]}]


def packet_times(path: Path, selector: str) -> list:
    proc = subprocess.run([FFPROBE, "-v", "error", "-select_streams", selector, "-show_entries", "packet=pts_time",
                           "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return sorted(float(t.strip(",")) for t in proc.stdout.split())


def display_matrix(path: Path):
    return next((d["displaymatrix"] for d in video_stream(path).get("side_data_list", [])
                 if d.get("side_data_type") == "Display Matrix"), None)


@CONTAINERS
@pytest.mark.parametrize("degrees", [90, -90, 180])
@pytest.mark.parametrize("corner", ["tr", "bl"])
def test_a_rotated_video_gets_the_label_at_the_corner_of_the_displayed_picture(tmp_path, label_tool, suffix,
                                                                               degrees, corner):
    stored = flat_mp4(tmp_path / f"stored{suffix}", seconds=1, size=SIZE)
    video = rotated(stored, tmp_path / f"clip{suffix}", degrees)
    displayed = (360, 640) if degrees != 180 else (640, 360)
    # The same picture stored upright: its Label is how the rotated one must look on playback.
    (tmp_path / "upright").mkdir()
    upright = flat_mp4(tmp_path / "upright" / "clip.mp4", seconds=1, size="x".join(map(str, displayed)))

    result = apply(label_tool, tmp_path, video, "--corner", corner)
    reference = apply(label_tool, tmp_path, upright, "--corner", corner)

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    src, out = video_stream(video), video_stream(copy)
    assert (out["width"], out["height"]) == (src["width"], src["height"]) == (640, 360)
    assert display_matrix(copy) == display_matrix(video)
    source, labelled = frame_images(video)[12], frame_images(copy)[12]
    expected = frame_images(Path(reference.json["labelled_copy"]))[12]
    width, height = displayed
    assert labelled.size == source.size == displayed
    box = changed(source, labelled)
    left, top, right, bottom = box
    if corner == "tr":
        assert left > width / 2 and bottom < height / 2, box
    else:
        assert right < width / 2 and top > height / 2, box
    # Chroma subsampling may bleed one pixel past an odd plate edge, on a different side once rotated.
    assert box == pytest.approx(changed(frame_images(upright)[12], expected), abs=1)
    assert mean_difference(labelled.crop(box), expected.crop(box)) < 4, "the Label reads upright"
    assert mean_difference(labelled.crop(box).rotate(180), expected.crop(box)) > 20


@CONTAINERS
def test_variable_frame_timing_and_a_start_offset_are_kept_exactly(tmp_path, label_tool, suffix):
    video = variable_rate_mp4(tmp_path / f"clip{suffix}", rates=(30, 10, 24), offset=0.5, audio=True)
    source_times = frame_times(video)
    steps = {round(b - a, 3) for a, b in zip(source_times, source_times[1:])}
    assert {0.033, 0.1, 0.042} <= steps, "the fixture really is variable frame rate"

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    assert len(frame_times(copy)) == len(source_times)
    assert frame_times(copy) == pytest.approx(source_times, abs=0.001)
    assert float(video_stream(copy)["start_time"]) == pytest.approx(0.5, abs=0.001)
    assert float(probe(copy)["format"]["duration"]) == pytest.approx(float(probe(video)["format"]["duration"]),
                                                                     abs=0.001)
    (a_out,), (a_src,) = streams(copy, "audio"), streams(video, "audio")
    assert float(a_out["start_time"]) == pytest.approx(float(a_src["start_time"]), abs=0.001)
    assert packet_times(copy, "a:0") == pytest.approx(packet_times(video, "a:0"), abs=0.001)


@CONTAINERS
def test_rotation_vfr_several_audio_tracks_and_subtitles_together_are_all_kept(tmp_path, label_tool, suffix):
    timing = variable_rate_mp4(tmp_path / f"timing{suffix}", rates=(30, 12), size=SIZE, offset=0.25)
    tracked = tracked_mp4(tmp_path / f"tracked{suffix}", audio=AUDIO, subtitles=SUBTITLES, video=timing,
                          extra=("-output_ts_offset", "0.25"))
    video = rotated(tracked, tmp_path / f"clip{suffix}", 90)
    times = frame_times(video)
    assert times[0] > 0.2 and len({round(b - a, 3) for a, b in zip(times, times[1:])}) > 1

    result = apply(label_tool, tmp_path, video, "--corner", "tr")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    assert frame_times(copy) == pytest.approx(frame_times(video), abs=0.001)
    assert display_matrix(copy) == display_matrix(video)
    for kind in ("audio", "subtitle"):
        source, labelled = streams(video, kind), streams(copy, kind)
        assert [described(s) for s in labelled] == [described(s) for s in source]
        for n, (a, b) in enumerate(zip(source, labelled)):
            assert offset(copy, b) == pytest.approx(offset(video, a), abs=0.001)
            selector = f"{kind[0]}:{n}"
            assert stream_md5(copy, f"0:{selector}") == stream_md5(video, f"0:{selector}")
    source, labelled = frame_images(video)[5], frame_images(copy)[5]
    left, top, right, bottom = changed(source, labelled)
    assert labelled.size == (360, 640) and left > 180 and bottom < 320


@pytest.mark.parametrize("make, code", [
    (lambda tmp: flat_mp4(tmp / "clip.mp4", seconds=1, size=SIZE, extra=("-timecode", "01:00:00:00")),
     "additional_tracks"),
    (lambda tmp: mirrored(flat_mp4(tmp / "stored.mp4", seconds=1, size=SIZE), tmp / "clip.mp4"),
     "rotation_not_validated"),
    (lambda tmp: tracked_mp4(tmp / "clip.mp4", audio=AUDIO, size=SIZE, extra=("-c:a:1", "pcm_s16le")),
     "audio_not_validated"),
], ids=["data stream", "mirrored", "second audio track not copyable"])
def test_what_cant_be_preserved_stops_before_rendering_and_says_what(tmp_path, label_tool, make, code):
    video = make(tmp_path)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    assert [i["code"] for i in result.json["error"]["issues"]] == [code]
    assert not (tmp_path / "clip.ai-label.mp4").exists()


def webm(path: Path, *inputs: str, rate: int = 25, extra: tuple = ()) -> Path:
    """A one-second VP9 WebM, plus extra inputs (each a lavfi source) encoded as Opus tracks."""
    args = ["-f", "lavfi", "-i", f"color=c=0x5aa0d2:s=320x180:r={rate}:d=1"]
    for source in inputs:
        args += ["-f", "lavfi", "-i", source]
    maps = [a for n in range(len(inputs) + 1) for a in ("-map", str(n))]
    ffmpeg(*args, *maps, "-c:v", "libvpx-vp9", "-deadline", "realtime", "-cpu-used", "8", "-pix_fmt", "yuv420p",
           "-c:a", "libopus", *extra, path)
    return path


SINE = "sine=frequency=440:sample_rate=48000:duration=1"


@needs_encoder("libvpx-vp9")
@pytest.mark.parametrize("make, code", [
    (lambda tmp: webm(tmp / "clip.webm", SINE, SINE), "additional_tracks"),
    (lambda tmp: rotated(webm(tmp / "stored.webm"), tmp / "clip.webm", 90), "rotation_not_validated"),
    (lambda tmp: webm(tmp / "clip.webm", extra=("-vf", "setpts='if(lt(N,10),N*0.04,0.4+(N-10)*0.1)/TB'",
                                                "-fps_mode", "passthrough")),
     "variable_frame_rate_not_validated"),
], ids=["two audio tracks", "rotated", "variable frame rate"])
def test_what_webm_hasnt_been_validated_to_keep_still_stops(tmp_path, label_tool, make, code):
    video = make(tmp_path)
    info = label_tool("video-inspect", video, env=real_tools(tmp_path / "bin")).json
    assert info["labelling"]["path"] == "webm-vp9-sdr", info

    result = apply(label_tool, tmp_path, video)

    assert result.json["error"]["code"] == "preservation_unsupported", result.json
    assert [i["code"] for i in result.json["error"]["issues"]] == [code]
    assert not (tmp_path / "clip.ai-label.webm").exists()


def altering_ffmpeg(bin_dir: Path, drop: tuple = (), add: tuple = ()) -> dict:
    """A real ffmpeg that, when rendering the staged copy, drops `drop` arguments and adds `add` output options."""
    real_tool(bin_dir, "ffprobe")
    script = bin_dir / "alter.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(f'''import os, sys
args = sys.argv[1:]
if any(".tmp" in a for a in args):
    args = [a for a in args if a not in {list(drop)!r}]
    at = len(args) - 3  # before "-f <muxer> <staged>"
    args[at:at] = {list(add)!r}
os.execv({FFMPEG!r}, [{FFMPEG!r}, *args])
''')
    fake_tool(bin_dir, "ffmpeg", f'exec "{sys.executable}" "{script}" "$@"')
    return tool_env(bin_dir)


@pytest.mark.parametrize("make, drop, add, failed", [
    (lambda tmp: tracked_mp4(tmp / "clip.mp4", audio=AUDIO, size=SIZE), (), ("-metadata:s:a:1", "language=fra"),
     "audio_tracks"),
    (lambda tmp: tracked_mp4(tmp / "clip.mp4", audio=AUDIO, subtitles=SUBTITLES, size=SIZE), (),
     ("-disposition:s:1", "default"), "subtitle_tracks"),
    (lambda tmp: rotated(flat_mp4(tmp / "stored.mp4", seconds=1, size=SIZE), tmp / "clip.mp4", 90),
     ("-noautorotate",), (), "orientation"),
    (lambda tmp: variable_rate_mp4(tmp / "clip.mp4", offset=0.5), ("-copyts",), (), "start_time"),
], ids=["audio language", "subtitle forced flag", "rotation", "start offset"])
def test_a_copy_that_lost_a_characteristic_is_discarded(tmp_path, label_tool, make, drop, add, failed):
    video = make(tmp_path)
    assert apply(label_tool, tmp_path, video).returncode == 0
    previous = sha256(tmp_path / "clip.ai-label.mp4")

    result = apply(label_tool, tmp_path, video, "--corner", "bl", env=altering_ffmpeg(tmp_path / "alt", drop, add))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "output_validation_failed", result.json
    assert failed in [c["check"] for c in result.json["error"]["checks"] if not c["passed"]]
    assert sha256(tmp_path / "clip.ai-label.mp4") == previous
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def mirrored(source: Path, path: Path) -> Path:
    ffmpeg("-display_hflip", "-i", source, "-c", "copy", path)
    return path


def mean_difference(a, b) -> float:
    from PIL import ImageChops, ImageStat

    return ImageStat.Stat(ImageChops.difference(a, b).convert("L")).mean[0]


@CONTAINERS
def test_subtitle_tracks_are_copied_with_their_language_title_forced_flag_and_cue_times(tmp_path, label_tool,
                                                                                         suffix):
    video = tracked_mp4(tmp_path / f"clip{suffix}", audio=AUDIO[:1], subtitles=SUBTITLES, size=SIZE)

    result = apply(label_tool, tmp_path, video)

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    source, labelled = streams(video, "subtitle"), streams(copy, "subtitle")
    assert [described(s) for s in labelled] == [described(s) for s in source]
    # QuickTime stores no `forced` flag, so a MOV source can't have one to lose.
    assert described(labelled[1]) == {"codec": "mov_text", "language": "fra", "title": "Forced FR",
                                      "disposition": {"default", "forced"} if suffix == ".mp4" else {"default"}}
    for n in range(2):
        assert stream_md5(copy, f"0:s:{n}") == stream_md5(video, f"0:s:{n}")
        assert packet_times(copy, f"s:{n}") == pytest.approx(packet_times(video, f"s:{n}"), abs=0.001)
