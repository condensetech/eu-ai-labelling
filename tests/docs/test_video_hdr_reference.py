"""references/video.md and the README on HDR10 and HLG: the commands run as written on real HDR10 and HLG
videos, and the wording says what is verified, what isn't, and what stops."""

from __future__ import annotations

import pytest

from helpers import REPO_ROOT, SKILL_DIR, doc_command, section, step
from videos import hdr10_video, hlg_video, needs_encoder, needs_ffmpeg, real_tools

from test_video_reference import run_doc

pytestmark = [needs_ffmpeg, needs_encoder("libx265")]

VIDEO_MD = SKILL_DIR / "references" / "video.md"
SETTINGS = {"<generated|modified>": "generated", "<tl|tr|bl|br>": "tr", "<auto|continuous|periodic>": "auto"}


def test_an_hdr10_video_is_previewed_and_labelled_as_written(tmp_path):
    video = hdr10_video(tmp_path / "clip.mp4", seconds=2)
    env = real_tools(tmp_path / "bin")

    code, preview = run_doc(doc_command("video.md", "video-preview", {"<video>": str(video), **SETTINGS}), tmp_path, env)
    assert code == 0, preview
    assert preview["frame_rendering"] == "sdr_tone_mapped" and preview["hdr_note"]

    code, result = run_doc(doc_command("video.md", "video-apply", {"<video>": str(video), **SETTINGS}), tmp_path, env)
    assert code == 0, result
    assert result["path"] == "mp4-hevc-hdr10"


def test_the_reference_says_how_to_judge_hdr_previews_and_what_stays_unverified():
    text = VIDEO_MD.read_text()
    preview = step(text, "Preview and choose the corner")
    assert "`hdr_note`" in preview and "tone-mapped" in preview
    approval = step(text, "Show it for approval")
    assert "HDR display" in approval and "`video.hdr`" in approval
    listed = section(text, "What can be labelled")
    assert "never converted to SDR" in listed
    assert "203 cd/m2" in listed and "MaxCLL" in listed and "MaxFALL" in listed


@pytest.mark.parametrize("code", ["hdr_not_validated", "hdr_metadata_missing", "colour_not_validated"])
def test_every_hdr_issue_has_an_action(code):
    when = step(VIDEO_MD.read_text(), "When it can't be labelled")
    assert f"`{code}`" in when


def test_the_readme_names_the_hdr10_path_and_its_limits():
    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    assert "HDR10" in videos and "HEVC" in videos and "never converted to SDR" in videos
    for stops in ("HDR10+", "Dolby Vision"):
        assert stops in videos


def test_an_hlg_video_is_previewed_and_labelled_as_written(tmp_path):
    video = hlg_video(tmp_path / "clip.mp4", seconds=2)
    env = real_tools(tmp_path / "bin")

    code, preview = run_doc(doc_command("video.md", "video-preview", {"<video>": str(video), **SETTINGS}), tmp_path, env)
    assert code == 0, preview
    assert preview["frame_rendering"] == "sdr_tone_mapped" and "HLG" in preview["hdr_note"]

    code, result = run_doc(doc_command("video.md", "video-apply", {"<video>": str(video), **SETTINGS}), tmp_path, env)
    assert code == 0, result
    assert result["path"] == "mp4-hevc-hlg" and result["video"]["hdr"]["dynamic_range"] == "hlg"


def test_the_reference_says_how_hlg_is_kept_and_judged():
    text = VIDEO_MD.read_text()
    listed = section(text, "What can be labelled")
    hlg = listed[listed.index("**HLG.**"):]
    assert "never converted to SDR or PQ" in hlg and "75%" in hlg and "mastering display" in hlg
    assert "HLG" in step(text, "Preview and choose the corner")
    assert "HLG" in step(text, "Show it for approval")
    assert "HLG" in step(text, "When it can't be labelled")


def test_the_readme_names_the_hlg_path():
    videos = section((REPO_ROOT / "README.md").read_text(), "Videos")
    assert "HLG video in MP4 with HEVC" in videos and "never converted to SDR or PQ" in videos
