"""references/video.md: the commands the agent runs for a video, run as written.

PATH is replaced so the real ffmpeg and ffprobe are reached only through
wrappers, as in tests/unit/test_video_tools.py.
"""

from __future__ import annotations

import os
import subprocess

from helpers import SKILL_DIR, SKILL_MD, doc_command, step
from videos import flat_mp4, needs_encoder, needs_ffmpeg, real_tools, without_tools

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


PLAYER = """\
<html lang="en"><body>
<video controls poster="media/still.png">
  <source src="media/clip.mp4" type="video/mp4">
  <track kind="subtitles" src="media/clip.en.vtt" srclang="en">
</video>
<p>A walk along the lake. <a href="media/clip.mp4">Download</a></p>
<img src="media/still.png" alt="The lake at dawn">
</body></html>
"""


def test_the_references_step_runs_as_written_on_the_approved_copy(tmp_path):
    """Step 7's command, after step 4's: the player's source points to the
    Labelled Copy, and nothing else on the page changes: no alt text, no
    disclosure, the track and the download link stay."""
    project = tmp_path / "site"
    (project / "media").mkdir(parents=True)
    video = flat_mp4(project / "media" / "clip.mp4", size="640x360")
    page = project / "index.html"
    page.write_text(PLAYER)
    env = real_tools(tmp_path / "bin")
    code, result = run_doc(doc_command("video.md", "video-apply", {
        "<video>": str(video), "<generated|modified>": "generated", "<tl|tr|bl|br>": "tr"}), project, env)
    assert code == 0, result

    code, result = run_doc(doc_command("video.md", "references", {
        "<video>": str(video), "<project root>": str(project)}), project, env)

    assert code == 0, result
    assert page.read_text() == PLAYER.replace('<source src="media/clip.mp4"', '<source src="media/clip.ai-label.mp4"')
    assert [(a["file"], a["kind"]) for a in result["applied"]] == [("index.html", "html-video-source")]


def test_the_references_step_waits_for_a_final_copy_and_explains_every_kind_and_reason():
    text = VIDEO_MD.read_text()
    seventh = step(text, "Point the project's players to it")
    assert "final" in seventh and "approve the new copy first" in seventh
    assert "failed, was refused or skipped" in seventh
    for word in ("`html-video`", "`html-video-source`", "`link`", "`other`", "`dynamic`", "`external`",
                 "`unresolved`", "`not_a_player`", "`needs_hand_edit`", "`applied`"):
        assert word in seventh, f"no rule for {word}"
    assert "never writes alt text" in seventh and "disclosure" in seventh
    assert "Don't run `references`" not in text
    assert "video" in step(SKILL_MD.read_text(), "Label it")


def test_a_creative_work_video_gets_no_caption():
    third = step(SKILL_MD.read_text(), "Settle where an image's Label goes")
    assert "video" in third and "don't offer it a caption" in third


def apply_as_written(tmp_path, video):
    argv = doc_command("video.md", "video-apply", {"<video>": str(video), "<generated|modified>": "generated",
                                                   "<tl|tr|bl|br>": "tr"})
    return run_doc(argv, tmp_path, real_tools(tmp_path / "bin"))


def test_the_apply_command_keeps_a_mov_a_mov(tmp_path):
    video = flat_mp4(tmp_path / "clip.mov", size="640x360", audio=True)

    code, result = apply_as_written(tmp_path, video)

    assert code == 0, result
    assert result["labelled_copy"] == str(tmp_path / "clip.ai-label.mov")
    assert result["path"] == "mov-h264-sdr"


@needs_encoder("libvpx-vp9")
def test_the_apply_command_keeps_a_webm_a_webm(tmp_path):
    video = flat_mp4(tmp_path / "clip.webm", size="640x360", audio=True, codec="libvpx-vp9",
                     extra=("-deadline", "realtime", "-cpu-used", "8"))

    code, result = apply_as_written(tmp_path, video)

    assert code == 0, result
    assert result["labelled_copy"] == str(tmp_path / "clip.ai-label.webm")
    assert result["path"] == "webm-vp9-sdr"


def test_the_reference_does_not_imply_every_codec_in_mov_or_webm():
    from helpers import section

    listed = section(VIDEO_MD.read_text(), "What can be labelled")
    assert "Only these combinations are validated" in listed
    assert "ProRes" in listed and "AV1" in listed
    assert "never converted to MP4" in listed
    assert "from the file itself, not its name" in listed


def test_the_reference_says_what_to_do_about_a_missing_capability():
    assert "`capability_missing`" in step(VIDEO_MD.read_text(), "When it can't be labelled as it is")


def test_the_readme_names_the_validated_combinations():
    from helpers import REPO_ROOT, section

    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    assert "MP4 or MOV with H.264" in videos and "WebM with VP9 or VP8" in videos
    assert "never converted to MP4" in videos
