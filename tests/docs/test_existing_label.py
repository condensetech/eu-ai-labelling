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
    assert "Never say none was found" in rule()


def test_the_skill_applies_the_rule_where_it_labels_reports_and_answers():
    skill = SKILL_MD.read_text()
    assert f"**{RULE}**" in step(skill, "Label it")
    assert "Existing Label" in step(skill, "Report")
    required = section(skill, "Whether a Label is required")
    assert "Existing Label" in required and "as a fact" in required
