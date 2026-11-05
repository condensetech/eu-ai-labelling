"""references/video.md: the commands the agent runs for a video, run as written.

PATH is replaced so the real ffmpeg and ffprobe are reached only through
wrappers, as in tests/unit/test_video_tools.py.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

from helpers import REPO_ROOT, SKILL_DIR, SKILL_MD, doc_command, section, step
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


@pytest.mark.parametrize("visibility, timing", [("auto", []), ("continuous", []),
                                                ("periodic", ["--window", "0.5", "--every", "1"])])
def test_the_apply_command_runs_as_written(tmp_path, visibility, timing):
    video = flat_mp4(tmp_path / "clip.mp4", size="640x360")
    argv = doc_command("video.md", "video-apply", {"<video>": str(video), "<generated|modified>": "generated",
                                                   "<tl|tr|bl|br>": "tr", "<auto|continuous|periodic>": visibility})

    code, result = run_doc(argv + timing, tmp_path, real_tools(tmp_path / "bin"))

    assert code == 0, result
    assert result["labelled_copy"] == str(tmp_path / "clip.ai-label.mp4")
    assert result["visibility"]["requested"] == visibility


def test_the_reference_asks_for_the_visibility_and_states_the_defaults():
    choose = step(VIDEO_MD.read_text(), "Choose when the Label shows")
    assert "Unless the user already said, ask" in choose
    assert "**continuously**" in choose and "**periodically**" in choose
    assert "up to and including 60 seconds show it continuously" in choose
    assert "5 seconds from the start and then for 5 seconds every 60 seconds" in choose
    assert "not legal thresholds" in choose
    assert "a list of chosen moments in the video isn't supported" in choose


def test_the_reference_and_readme_no_longer_limit_the_length():
    assert "60 seconds" not in section(VIDEO_MD.read_text(), "What can be labelled")
    assert "of any length" in section(VIDEO_MD.read_text(), "What can be labelled")
    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    assert "up to 60 seconds, with" not in videos
    assert "periodically" in videos and "not legal thresholds" in videos


def test_a_visibility_change_needs_a_fresh_approval():
    approval = step(VIDEO_MD.read_text(), "Show it for approval")
    assert "including to the visibility or its timing" in approval
    assert "A changed copy needs approval again" in approval


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
    """Step 8's command, after step 5's: the player's source points to the
    Labelled Copy, and nothing else on the page changes: no alt text, no
    disclosure, the track and the download link stay."""
    project = tmp_path / "site"
    (project / "media").mkdir(parents=True)
    video = flat_mp4(project / "media" / "clip.mp4", size="640x360")
    page = project / "index.html"
    page.write_text(PLAYER)
    env = real_tools(tmp_path / "bin")
    code, result = run_doc(doc_command("video.md", "video-apply", {
        "<video>": str(video), "<generated|modified>": "generated", "<tl|tr|bl|br>": "tr",
        "<auto|continuous|periodic>": "auto"}), project, env)
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
                                                   "<tl|tr|bl|br>": "tr", "<auto|continuous|periodic>": "auto"})
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


@pytest.mark.parametrize("visibility, timing", [("auto", []), ("periodic", ["--window", "0.5", "--every", "1"])])
def test_the_preview_command_runs_as_written(tmp_path, visibility, timing):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=3, size="640x360")
    argv = doc_command("video.md", "video-preview", {"<video>": str(video), "<generated|modified>": "generated",
                                                     "<tl|tr|bl|br>": "tr", "<auto|continuous|periodic>": visibility})

    code, result = run_doc(argv + timing, tmp_path, real_tools(tmp_path / "bin"))

    assert code == 0, result
    assert result["out"] == str(tmp_path / "clip.mp4.label-preview")
    assert result["complete"] is True
    assert all(os.path.isfile(e["path"]) for e in result["frames"] + result["excerpts"])
    assert result["visibility"]["requested"] == visibility
    assert not (tmp_path / "clip.ai-label.mp4").exists(), "a preview writes no Labelled Copy"


def test_the_corner_is_chosen_from_the_previews_before_applying():
    text = VIDEO_MD.read_text()
    steps = re.findall(r"^\d\. \*\*([^*]+)\*\*", text, re.M)
    assert steps.index("Choose when the Label shows.") < steps.index("Preview and choose the corner.")
    assert steps.index("Preview and choose the corner.") < steps.index("Apply the Label.")
    preview = step(text, "Preview and choose the corner")
    assert "Open every written frame" in preview
    for interference in ("faces", "text", "subtitles", "main subject"):
        assert interference in preview
    assert "in every frame" in preview and "never plan to move it between scenes" in preview
    assert "**ask the user** which corner to use, and wait" in preview
    assert "never call it checked" in preview and "`preview_failed`" in preview
    assert "run `video-preview` again" in preview


def test_approval_says_what_previews_do_and_do_not_establish():
    approval = step(VIDEO_MD.read_text(), "Show it for approval")
    assert "`sampling_note`" in approval and "in every frame" in approval
    assert "the full Labelled Copy is what they approve" in approval
    assert "run step 4 again" in approval and "`size_too_small`" in approval


def test_the_cross_references_point_to_the_named_steps():
    text = VIDEO_MD.read_text()
    numbers = {title: int(n) for n, title in re.findall(r"^(\d)\. \*\*([^*.]+)", text, re.M)}
    assert numbers["Choose when the Label shows"] == 3 and "**periodic**): step 3" in text
    assert numbers["Preview and choose the corner"] == 4 and "the last preview (step 4)" in text
    assert numbers["When it can't be labelled as it is"] == 7 and "as step 7 says" in text
    assert numbers["Point the project's players to it"] == 8
    assert "goes through step 8 of `references/video.md`" in SKILL_MD.read_text()


def test_the_readme_explains_previews():
    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    assert "label-preview" in videos and "never moves during playback" in videos
    assert "can't prove the Label is clear in every frame" in videos


def test_the_reference_says_what_to_do_about_a_missing_capability():
    assert "`capability_missing`" in step(VIDEO_MD.read_text(), "When it can't be labelled as it is")


def test_the_readme_names_the_validated_combinations():
    from helpers import REPO_ROOT, section

    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    assert "MP4 or MOV with H.264" in videos and "WebM with VP9 or VP8" in videos
    assert "never converted to MP4" in videos


def test_tracks_rotation_and_variable_timing_are_labelled_as_the_reference_says(tmp_path):
    from helpers import section
    from videos import rotated, tracked_mp4, variable_rate_mp4

    timing = variable_rate_mp4(tmp_path / "timing.mp4", rates=(30, 12), size="640x360", offset=0.25)
    tracked = tracked_mp4(tmp_path / "tracked.mp4", video=timing,
                          audio=[{"language": "eng", "disposition": "default"}, {"language": "ita"}],
                          subtitles=[{"language": "fra", "disposition": "default+forced"}])
    video = rotated(tracked, tmp_path / "clip.mp4", 90)
    code, result = apply_as_written(tmp_path, video)

    assert code == 0, result
    listed = section(VIDEO_MD.read_text(), "What can be labelled")
    for kept in ("any number of audio tracks", "`mov_text` subtitle tracks", "variable frame rate",
                 "start offset", "rotation by 90, 180 or 270 degrees", "language, title and default, forced"):
        assert kept in listed


def test_a_stream_that_cant_be_kept_stops_with_an_issue_the_reference_explains(tmp_path):
    video = flat_mp4(tmp_path / "clip.mp4", size="640x360", extra=("-timecode", "01:00:00:00"))
    code, result = apply_as_written(tmp_path, video)

    assert code != 0 and result["error"]["code"] == "preservation_unsupported"
    when = step(VIDEO_MD.read_text(), "When it can't be labelled")
    for found in result["error"]["issues"]:
        assert f"`{found['code']}`" in when
    for name in ("additional_tracks", "audio_not_validated", "subtitles_not_validated", "rotation_not_validated"):
        assert f"`{name}`" in when
    assert "never drop a track" in when


def test_the_readme_says_what_a_video_copy_keeps_and_what_stops():
    from helpers import REPO_ROOT, section

    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    for said in ("every audio and subtitle track", "rotation", "variable frame rates", "mirrored picture",
                 "timecode"):
        assert said in videos
