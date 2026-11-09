"""The shared Existing Label rule, stated once in SKILL.md.

Each reference only says where its check happens and points here. Whether the
agent stops, asks and reports as the rule says is judged by the headless runs
in tests/evals (scenarios with an `existing_label`).
"""

from __future__ import annotations

import re

from helpers import SKILL_MD, section, step

RULE = "An Existing Label"


def rule() -> str:
    return section(SKILL_MD.read_text(), RULE)


def test_the_rule_says_what_counts_as_an_existing_label():
    text = rule()
    assert "**Existing Label**" in text and "didn't apply" in text
    # Not this plugin's own Label or Labelled Copy, not Marking, not alt text alone.
    assert "<!-- eu-ai-labelling: ... -->" in text and "`*.ai-label.*`" in text
    assert "Marking" in text and "not an Existing Label" in text
    assert re.search(r"alt text alone", text, re.I)


def test_the_rule_stops_reports_and_asks_without_a_verdict():
    text = rule()
    assert "Stop before changing any file" in text
    for told in ("where", "what it says", "`generated`", "`modified`"):
        assert told in text, f"the rule never tells the user {told}"
    assert "sufficient or insufficient" in text, "no ban on an adequacy verdict"
    assert "add the EU Icon anyway" in text


def test_the_rule_leaves_the_existing_label_alone_unless_asked():
    text = rule()
    assert "already deals with the Existing Label" in text and "don't ask" in text
    assert "Never edit or remove the Existing Label" in text
    assert "explicitly asks" in text and "plain edit" in text


def test_the_rule_never_claims_an_absence():
    text = rule()
    assert "Never say none was found" in text
    # It holds when nothing is found too, so it can't sit in the "When it finds one" list.
    findings = text[text.index("When it finds one"):]
    absence = next(p for p in findings.split("\n\n") if "Never say none was found" in p)
    assert not absence.lstrip().startswith("- "), "the ban on absence claims reads as part of what to do on a find"


def test_the_report_says_nothing_of_existing_labels_when_none_was_found():
    report = step(SKILL_MD.read_text(), "Report")
    assert re.search(r"none was found, say nothing about Existing Labels", report)


def test_whether_a_label_is_required_looks_at_the_content_first():
    required = section(SKILL_MD.read_text(), "Whether a Label is required")
    assert re.search(r"Before answering, look at the content", required)
    for where in ("read the document", "open the image", "read the project", "frames you already opened"):
        assert where in required, f"no word on how to look: {where}"


def test_the_skill_applies_the_rule_where_it_labels_reports_and_answers():
    skill = SKILL_MD.read_text()
    assert f"**{RULE}**" in step(skill, "Label it")
    assert "Existing Label" in step(skill, "Report")
    required = section(skill, "Whether a Label is required")
    assert "Existing Label" in required and "as a fact" in required


CHECKS = ("text.md", "image.md", "creative-work.md", "video.md", "site.md")


def test_every_check_says_nothing_when_it_finds_none():
    # The agent reports what each check found: where the check runs, it must hear
    # that finding none is reported as nothing at all.
    references = SKILL_MD.parent / "references"
    for name in CHECKS:
        text = (references / name).read_text()
        check = next(p for p in re.split(r"\n(?=\s*(?:- |\d\. ))|\n\n", text) if "**An Existing Label:**" in p)
        assert "say nothing about Existing Labels" in check, f"{name}: the check never says what to write when it finds none"


def test_no_report_list_asks_for_a_line_when_none_was_found():
    references = SKILL_MD.parent / "references"
    for name in CHECKS:
        for line in (references / name).read_text().splitlines():
            if line.startswith("- each Existing Label found"):
                assert "only when you found one" in line, f"{name}: {line}"


def test_the_batch_and_required_answers_stay_silent_on_files_without_one():
    skill = SKILL_MD.read_text()
    assert "say nothing about Existing Labels" in section(skill, "Whether a Label is required")
    assert "say nothing about Existing Labels" in section(skill, "A batch of files")
