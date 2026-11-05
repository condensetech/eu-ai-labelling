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
