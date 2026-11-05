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


def test_the_apply_command_runs_as_written(tmp_path):
    video = flat_mp4(tmp_path / "clip.mp4", size="640x360")
    argv = doc_command("video.md", "video-apply", {"<video>": str(video), "<generated|modified>": "generated",
                                                   "<tl|tr|bl|br>": "tr"})

    code, result = run_doc(argv, tmp_path, real_tools(tmp_path / "bin"))

    assert code == 0, result
    assert result["labelled_copy"] == str(tmp_path / "clip.ai-label.mp4")


def test_the_reference_lists_exactly_the_validated_paths(tmp_path):
    from helpers import section

    _, report = run_doc(doc_command("video.md", "video-tools", {}), tmp_path, real_tools(tmp_path / "bin"))
    listed = section(VIDEO_MD.read_text(), "What can be labelled")

    import re
    assert set(re.findall(r"\*\*`([a-z0-9-]+)`\*\*", listed)) == {p["name"] for p in report["paths"]}


def test_videos_never_go_through_image_reference_updates_yet():
    assert "Don't run `references` or any alt-text update for a video" in VIDEO_MD.read_text()


def test_a_creative_work_video_gets_no_caption():
    third = step(SKILL_MD.read_text(), "Settle where an image's Label goes")
    assert "video" in third and "don't offer it a caption" in third
