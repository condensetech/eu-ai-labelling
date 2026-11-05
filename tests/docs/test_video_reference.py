"""references/video.md: the commands the agent runs for a video, run as written.

PATH is replaced so the real ffmpeg and ffprobe are reached only through
wrappers, as in tests/unit/test_video_tools.py.
"""

from __future__ import annotations

import os
import subprocess

from helpers import SKILL_DIR, SKILL_MD, doc_command, step
from videos import flat_mp4, needs_ffmpeg, real_tools, without_tools

pytestmark = needs_ffmpeg

VIDEO_MD = SKILL_DIR / "references" / "video.md"


def run_doc(argv, cwd, env):
    import json
    import shutil

    argv = [shutil.which(argv[0]) or argv[0], *argv[1:]]
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=600, env={**os.environ, **env})
    return proc.returncode, json.loads(proc.stdout)


def test_the_tools_check_runs_as_written(tmp_path):
    code, report = run_doc(doc_command("video.md", "video-tools", {}), tmp_path, real_tools(tmp_path / "bin"))

    assert code == 0, report
    assert report["ready"] is True


def test_the_tools_check_gives_install_steps_when_missing(tmp_path):
    code, report = run_doc(doc_command("video.md", "video-tools", {}), tmp_path, without_tools(tmp_path))

    assert code == 0
    assert report["ready"] is False and report["install"]["steps"]


def test_the_inspection_runs_as_written(tmp_path):
    video = flat_mp4(tmp_path / "clip.mp4")

    code, info = run_doc(doc_command("video.md", "video-inspect", {"<video>": str(video)}), tmp_path,
                         real_tools(tmp_path / "bin"))

    assert code == 0, info
    assert info["video"]["codec"] == "h264"


def test_the_reference_never_installs_tools_itself():
    text = VIDEO_MD.read_text()
    assert "Never run an install command yourself" in text
    assert "run `video-tools` again" in text


def test_the_skill_routes_local_videos_and_keeps_urls_out():
    identify = step(SKILL_MD.read_text(), "Identify the content")
    assert "video" in identify and "URL" in identify and "live stream" in identify
