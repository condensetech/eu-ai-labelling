"""The Marking as evidence for the Icon Variant, stated once in SKILL.md.

The `marking` command is taken verbatim from SKILL.md (only its placeholder
filled in) and run from the user's project, never from the skill folder. The
references only say where the Marking shows in the preview and the report, and
point to SKILL.md. Whether the agent settles, asks and reports as the rule
says is judged by the headless runs in tests/evals (the `marking-*` scenarios).
"""

from __future__ import annotations

import re

import markings
from helpers import SKILL_DIR, SKILL_MD, doc_command, run_json, section, step

RULE = "A Marking"


def rule() -> str:
    return section(SKILL_MD.read_text(), RULE)


def reference(name: str) -> str:
    return (SKILL_DIR / "references" / name).read_text()


def marking_command(file: str) -> list[str]:
    # SKILL.md sits one folder above the references doc_command reads from.
    return doc_command("../SKILL.md", "marking", {"<file>": file})


def test_the_marking_command_run_from_the_users_project_settles_the_variant(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    markings.png(project / "photo.png", xmp=markings.xmp_packet("compositeWithTrainedAlgorithmicMedia"))

    code, report = run_json(marking_command("photo.png"), project)

    assert code == 0, report
    assert report["settled"] == "modified"


def test_every_field_the_rule_names_is_one_marking_prints(tmp_path):
    fields = set(re.findall(r"`([a-z_0-9]+)` \(", rule()))
    assert {"settled", "settled_by", "quotes", "c2pa"} <= fields, fields
    markings.png(tmp_path / "photo.png")

    code, report = run_json(marking_command("photo.png"), tmp_path)

    assert code == 0, report
    assert fields <= set(report), fields - set(report)


def test_the_rule_keeps_the_marking_to_the_icon_variant():
    text = rule()
    assert "**Marking**" in text and "Provider" in text
    assert "never says whether a Label is required" in text
    assert "not an Existing Label" in text
    assert "image" in text and "video" in text


def test_a_precise_marking_settles_the_variant_as_context_does():
    text = rule()
    precise = text.split("**Precise**", 1)[1].split("\n- ", 1)[0]
    assert "as context does" in precise and "don't ask" in precise
    assert "`settled_by`" in precise and "preview and the report" in precise


def test_a_vague_marking_is_quoted_in_the_origin_question():
    text = rule()
    vague = text.split("**Vague**", 1)[1].split("\n- ", 1)[0]
    assert "`quotes`" in vague and "origin question" in vague
    assert "from scratch" in vague


def test_no_marking_is_never_mentioned_nor_evidence():
    text = rule()
    none = text.split("**None**", 1)[1].split("\n- ", 1)[0]
    assert "never mention" in none
    assert "no evidence" in none


def test_c2pa_unavailable_is_said_only_with_the_origin_question():
    text = rule()
    unavailable = text.split("`c2pa` is `unavailable`", 1)[1].split("\n- ", 1)[0]
    assert "only when you ask the origin question" in unavailable
    assert "never" in unavailable and "labelling" in unavailable


def test_the_users_word_wins_and_a_mismatch_is_a_fact():
    text = rule()
    word = text.split("**The user's word wins.**", 1)[1].split("\n- ", 1)[0]
    assert "label as they said" in word and "without asking" in word
    assert "mismatch as a fact" in word and "preview and the report" in word
    assert "which one is right" in word, "no ban on a verdict"
    assert "agrees" in word and "one line" in word and "preview doesn't" in word


def test_the_labelled_copy_no_longer_carries_the_marking():
    assert "no longer carries the original's Marking" in rule()


def test_step_2_reads_the_marking_of_each_image_and_video_before_asking():
    settle = step(SKILL_MD.read_text(), "Settle the Icon Variant")
    assert f"**{RULE}**" in settle
    assert "each image and video" in settle
    assert settle.index(f"**{RULE}**") < settle.index("ask one plain question")
    assert "precise Marking" in settle


def test_a_batch_never_names_a_file_a_precise_marking_settled():
    batch = section(SKILL_MD.read_text(), "A batch of files")
    assert "precise Marking" in batch and "never name it" in batch
    assert "nothing else is open" in batch and "without a question" in batch


def test_the_batch_report_lists_the_files_settled_by_marking():
    report = step(reference("batch.md"), "Report the batch")
    assert "**Settled by Marking:**" in report and "`settled_by`" in report
    assert "SKILL.md **A Marking**" in report


def test_the_batch_report_says_when_a_marking_agrees_with_the_users_word():
    report = step(reference("batch.md"), "Report the batch")
    settled = report.split("**Settled by Marking:**", 1)[1].split("\n   - **", 1)[0]
    assert "contradicts the user's word" in settled
    assert "agrees with the user's word" in settled and "one line" in settled


def test_the_image_preview_and_report_name_the_marking():
    image = reference("image.md")
    assert "SKILL.md **A Marking**" in step(image, "Show a preview")
    report = section(image, "Report")
    assert "SKILL.md **A Marking**" in report and "no longer carries the original's Marking" in report


def test_the_video_review_and_report_name_the_marking():
    video = reference("video.md")
    assert "SKILL.md **A Marking**" in step(video, "Show it for approval")
    report = section(video, "Report")
    assert "SKILL.md **A Marking**" in report and "no longer carries the original's Marking" in report


def test_the_skill_report_points_to_the_image_report():
    assert "`references/image.md`" in step(SKILL_MD.read_text(), "Report")


def test_whether_a_label_is_required_mentions_a_marking_as_a_fact():
    required = section(SKILL_MD.read_text(), "Whether a Label is required")
    assert f"**{RULE}**" in required
    assert "Marking" in required and "as a fact" in required
