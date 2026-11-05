"""Test videos and measurements of what label_tool's video subcommands wrote.

The fixtures are real video files, encoded at test time by the ffmpeg found
on PATH; the measurements decode the output with ffprobe and ffmpeg
independently of label_tool. Tests that need them are skipped when ffmpeg or
ffprobe is not installed (`needs_ffmpeg`).
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

needs_ffmpeg = pytest.mark.skipif(not (FFMPEG and FFPROBE), reason="ffmpeg and ffprobe are not installed")


def has_encoder(name: str) -> bool:
    if not FFMPEG:
        return False
    listed = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return any(line.split()[1:2] == [name] for line in listed.splitlines() if line.startswith(" "))


def needs_encoder(name: str):
    return pytest.mark.skipif(not has_encoder(name), reason=f"this ffmpeg has no {name} encoder")


def ffmpeg(*args: str | Path) -> None:
    proc = subprocess.run([FFMPEG, "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def probe(path: Path) -> dict:
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def streams(path: Path, kind: str) -> list[dict]:
    return [s for s in probe(path)["streams"] if s["codec_type"] == kind]


def video_stream(path: Path) -> dict:
    return streams(path, "video")[0]


def frame_times(path: Path) -> list[float]:
    """The presentation time of every video frame, in seconds."""
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time,best_effort_timestamp_time",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    frames = json.loads(proc.stdout)["frames"]
    return [float(f.get("pts_time", f.get("best_effort_timestamp_time"))) for f in frames]


def frames(path: Path, pix_fmt: str = "rgb24") -> tuple[list[bytes], tuple[int, int]]:
    """Every decoded frame as raw pixels, in display orientation, and the frame size."""
    stream = video_stream(path)
    width, height = stream["width"], stream["height"]
    rotation = next((abs(int(d.get("rotation", 0))) for d in stream.get("side_data_list", [])
                     if "rotation" in d), 0)
    if rotation in (90, 270):
        width, height = height, width
    proc = subprocess.run(
        [FFMPEG, "-v", "error", "-i", str(path), "-map", "0:v:0", "-fps_mode", "passthrough",
         "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    per_pixel = {"rgb24": 3, "gray": 1, "gray16le": 2, "yuv444p16le": 6}[pix_fmt]
    size = width * height * per_pixel
    data = proc.stdout
    return [data[i:i + size] for i in range(0, len(data), size)], (width, height)


def frame_images(path: Path) -> list[Image.Image]:
    raw, size = frames(path)
    return [Image.frombytes("RGB", size, f) for f in raw]


def changed(before: Image.Image, after: Image.Image, threshold: int = 24):
    """The box of pixels that differ by more than `threshold` (re-encoding noise stays below it), or None."""
    diff = ImageChops.difference(before, after).convert("L")
    return diff.point(lambda v: 255 if v > threshold else 0).getbbox()


# --- Fixtures ------------------------------------------------------------------

def flat_mp4(path: Path, seconds: float = 2, size: str = "320x180", rate: int = 25, colour: str = "0x5aa0d2",
             audio: bool = False, codec: str = "libx264", extra: tuple = ()) -> Path:
    """A flat-colour video: any pixel the Label changes shows up as a difference."""
    args = ["-f", "lavfi", "-i", f"color=c={colour}:s={size}:r={rate}:d={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}"]
    args += ["-c:v", codec, "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "aac" if path.suffix in (".mp4", ".mov") else "libopus", "-shortest"]
    ffmpeg(*args, *extra, path)
    return path


def scene_video(path: Path, seconds: float = 2, size: str = "320x180") -> Path:
    """A moving test pattern, busy everywhere."""
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=s={size}:r=25:d={seconds}", "-c:v", "libx264", "-pix_fmt", "yuv420p", path)
    return path


def tracked_mp4(path: Path, audio: list[dict] = (), subtitles: list[dict] = (), seconds: float = 2,
                size: str = "320x180", video: Path | None = None, extra: tuple = ()) -> Path:
    """An MP4 with AAC audio tracks and mov_text subtitles, each `{language, title, disposition, ...}`.

    An audio track's `frequency` and `sample_rate` tell the tracks apart; a subtitle's `cues` are
    `(start, end, text)`. With `video`, its first video stream is copied instead of a flat colour."""
    args, maps, options = [], [], []
    if video:
        args += ["-i", video]
        maps += ["-map", "0:v:0"]
        options += ["-c:v", "copy"]
    else:
        args += ["-f", "lavfi", "-i", f"color=c=0x5aa0d2:s={size}:r=25:d={seconds}"]
        maps += ["-map", "0:v:0"]
        options += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    for n, track in enumerate(audio):
        args += ["-f", "lavfi", "-i", f"sine=frequency={track.get('frequency', 440 * (n + 1))}:"
                                      f"sample_rate={track.get('sample_rate', 48000)}:duration={seconds}"]
        maps += ["-map", f"{len(maps) // 2}:a:0"]
    for n, track in enumerate(subtitles):
        srt = path.with_name(f"{path.stem}.{n}.srt")
        cues = track.get("cues", [(0.2, 0.9, f"Line {n}"), (1.1, 1.8, f"Next {n}")])
        srt.write_text("".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n" for i, (a, b, text) in enumerate(cues, 1)))
        args += ["-i", srt]
        maps += ["-map", f"{len(maps) // 2}:s:0"]
    for kind, tracks in (("a", audio), ("s", subtitles)):
        for n, track in enumerate(tracks):
            for key in ("language", "title"):
                if track.get(key):
                    options += [f"-metadata:s:{kind}:{n}", f"{key}={track[key]}"]
            options += [f"-disposition:{kind}:{n}", track.get("disposition", "0")]
    ffmpeg(*args, *maps, *options, "-c:a", "aac", "-c:s", "mov_text", *extra, path)
    return path


def stamp(seconds: float) -> str:
    whole, millis = divmod(round(seconds * 1000), 1000)
    return f"00:00:{whole:02d},{millis:03d}"


def rotated(source: Path, path: Path, degrees: int) -> Path:
    """`source` with a display matrix rotating it by `degrees` on playback; the stored pixels are unchanged."""
    ffmpeg("-display_rotation", str(degrees), "-i", source, "-map", "0", "-c", "copy", path)
    return path


def variable_rate_mp4(path: Path, rates: tuple = (30, 10, 24), size: str = "160x90", offset: float = 0.0,
                      audio: bool = False) -> Path:
    """Segments of one second each at different frame rates, kept as they are: a variable frame rate video
    starting `offset` seconds into its timeline."""
    args, chain = [], ""
    for n, rate in enumerate(rates):
        args += ["-f", "lavfi", "-i", f"color=c=0x5aa0d2:s={size}:r={rate}:d=1"]
        chain += f"[{n}:v]"
    maps = ["-map", "[v]"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={len(rates)}"]
        maps += ["-map", f"{len(rates)}:a:0", "-c:a", "aac"]
    ffmpeg(*args, "-filter_complex", f"{chain}concat=n={len(rates)}:v=1[v]", *maps, "-fps_mode", "passthrough",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-output_ts_offset", str(offset), path)
    return path


QUADRANTS = {"tl": (0, 0), "tr": (1, 0), "bl": (0, 1), "br": (1, 1)}


def corner_scenes(path: Path, corners: tuple = ("tr", "bl", "br"), seconds_each: float = 1, size: str = "320x180",
                  rate: int = 25) -> Path:
    """A grey video in scenes of `seconds_each`: scene i has a white block filling the quarter of the
    picture at `corners[i]`, standing in for a face or a subtitle that competes for that corner."""
    width, height = map(int, size.split("x"))
    boxes = []
    for i, corner in enumerate(corners):
        qx, qy = QUADRANTS[corner]
        start, end = i * seconds_each, (i + 1) * seconds_each
        boxes.append(f"drawbox=x={qx * width // 2}:y={qy * height // 2}:w={width // 2}:h={height // 2}:"
                     f"color=white:t=fill:enable='gte(t,{start})*lt(t,{end})'")
    seconds = seconds_each * len(corners)
    ffmpeg("-f", "lavfi", "-i", f"color=c=0x606060:s={size}:r={rate}:d={seconds}", "-vf", ",".join(boxes),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", path)
    return path


def white_quadrant(image: Image.Image) -> str | None:
    """The corner whose quarter of `image` is (almost all) white, or None."""
    from PIL import ImageStat

    grey = image.convert("L")
    width, height = grey.size
    for corner, (qx, qy) in QUADRANTS.items():
        box = (qx * width // 2 + 4, qy * height // 2 + 4, (qx + 1) * width // 2 - 4, (qy + 1) * height // 2 - 4)
        if ImageStat.Stat(grey.crop(box)).mean[0] > 230:
            return corner
    return None


# --- Fake tools on PATH ----------------------------------------------------------

def tool_env(bin_dir: Path) -> dict:
    """An environment whose PATH holds only `bin_dir`. uv is found by absolute
    path and the interpreter through UV_PYTHON, so nothing else on PATH (such
    as a real ffmpeg next to Python) leaks into the lookup."""
    return {"PATH": str(bin_dir), "UV_PYTHON": sys.executable}


def fake_tool(bin_dir: Path, name: str, script: str) -> Path:
    """An executable `name` in `bin_dir` running the shell `script`."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{script}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def real_tool(bin_dir: Path, name: str, as_name: str | None = None) -> Path:
    """A wrapper `as_name` (default `name`) in `bin_dir` that runs the real ffmpeg or ffprobe."""
    real = {"ffmpeg": FFMPEG, "ffprobe": FFPROBE}[name]
    return fake_tool(bin_dir, as_name or name, f'exec "{real}" "$@"')


def real_tools(bin_dir: Path) -> dict:
    real_tool(bin_dir, "ffmpeg")
    real_tool(bin_dir, "ffprobe")
    return tool_env(bin_dir)


def without_tools(tmp_path: Path) -> dict:
    empty = tmp_path / "empty-bin"
    empty.mkdir(exist_ok=True)
    return tool_env(empty)


def is_executable(path: Path) -> bool:
    return os.access(path, os.X_OK)


# --- HDR10 -----------------------------------------------------------------------

# A mastering display: Display P3 primaries, D65 white, 1000 to 0.0001 cd/m2, in x265's units
# (chromaticities in 0.00002, luminance in 0.0001 cd/m2).
MASTER_DISPLAY = "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)"
HDR10_TAGS = ("-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc", "-color_range", "tv")


def hdr10_video(path: Path, seconds: float = 1, size: str = "640x360", source: str = "testsrc2",
                max_cll: tuple | None = (1000, 400), mastering: bool = True, hdr10plus: Path | None = None,
                audio: bool = False, primaries: str = "bt2020", extra: tuple = ()) -> Path:
    """A real HDR10 video: 10-bit 4:2:0 HEVC Main 10 encoded by libx265 with PQ, BT.2020 and the HDR10
    SEI messages (mastering display, content light levels; HDR10+ dynamic metadata from `hdr10plus`).
    `source` is `testsrc2` (busy everywhere) or a colour (flat)."""
    content = (f"testsrc2=s={size}:r=25:d={seconds}" if source == "testsrc2"
               else f"color=c={source}:s={size}:r=25:d={seconds}")
    params = ["log-level=error", f"colorprim={primaries}", "transfer=smpte2084", "colormatrix=bt2020nc"]
    if mastering or max_cll or hdr10plus:
        params.append("hdr10=1")
    if mastering:
        params.append(f"master-display={MASTER_DISPLAY}")
    if max_cll:
        params.append(f"max-cll={max_cll[0]},{max_cll[1]}")
    if hdr10plus:
        params.append(f"dhdr10-info={hdr10plus}")
    args = ["-f", "lavfi", "-i", content]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}", "-c:a", "aac"]
    ffmpeg(*args, "-vf", "format=yuv420p10le", "-c:v", "libx265", "-preset", "ultrafast",
           "-x265-params", ":".join(params), *HDR10_TAGS, "-color_primaries", primaries, *extra, path)
    return path


def hdr10plus_info(path: Path, frames: int = 25) -> Path:
    """An HDR10+ (SMPTE ST 2094-40) metadata file for x265's `dhdr10-info`, one scene of `frames` frames."""
    scene = {
        "BezierCurveData": {"Anchors": [102, 205, 307, 410, 512, 614, 717, 819, 922], "KneePointX": 0,
                            "KneePointY": 0},
        "LuminanceParameters": {"AverageRGB": 100, "MaxScl": [900, 900, 900], "LuminanceDistributions": {
            "DistributionIndex": [1, 5, 10, 25, 50, 75, 90, 95, 99],
            "DistributionValues": [0, 10, 20, 40, 80, 120, 300, 500, 800]}},
        "NumberOfWindows": 1, "TargetedSystemDisplayMaximumLuminance": 400,
    }
    path.write_text(json.dumps({
        "JSONInfo": {"HDR10plusProfile": "B", "Version": "1.0"},
        "SceneInfo": [dict(scene, SceneFrameIndex=i, SceneId=0, SequenceFrameIndex=i) for i in range(frames)],
        "SceneInfoSummary": {"SceneFirstFrameIndex": [0], "SceneFrameNumbers": [frames]},
        "ToolInfo": {"Tool": "tests", "Version": "1"},
    }))
    return path


def frame_side_data(path: Path) -> dict:
    """The first frame's side data, by type, as ffprobe reports it."""
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-read_intervals", "%+#1",
         "-show_entries", "frame=side_data_list:frame_side_data", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    frames = json.loads(proc.stdout)["frames"]
    return {d["side_data_type"]: d for d in frames[0].get("side_data_list", [])}


def planes_10bit(path: Path, index: int) -> tuple[list, list, list, tuple[int, int]]:
    """Frame `index`'s Y, U and V planes as decoded 10-bit code values (no conversion), and its size."""
    from array import array

    stream = video_stream(path)
    width, height = stream["width"], stream["height"]
    proc = subprocess.run(
        [FFMPEG, "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf", f"select=eq(n\\,{index})", "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-"],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    values = array("H")
    values.frombytes(proc.stdout[: width * height * 3])  # 2 bytes a sample, chroma a quarter of luma each
    luma, chroma = width * height, width * height // 4
    return (list(values[:luma]), list(values[luma:luma + chroma]), list(values[luma + chroma:luma + 2 * chroma]),
            (width, height))


def pq_code(nits: float) -> float:
    """The 10-bit limited-range code value of `nits` cd/m2 under the PQ transfer (SMPTE ST 2084)."""
    m1, m2 = 2610 / 16384, 2523 / 4096 * 128
    c1, c2, c3 = 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32
    y = (nits / 10000) ** m1
    return 64 + 876 * ((c1 + c2 * y) / (1 + c3 * y)) ** m2
