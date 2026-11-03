"""The text reference: where a Label goes and what it says.

The Label itself is printed by `label_tool snippet` and the icon copied by
`label_tool copy-icons`: their output is tested in tests/unit/test_snippet.py
and the commands are run as written in test_label_snippets.py. Here,
what the reference says around them: how the language is settled and the
options it names. What the agent does with the instructions (the document's language, a
partly AI-made document) is judged by the headless runs in tests/evals
(scenarios with a `text_label`).
"""

from __future__ import annotations

import re

from helpers import SKILL_DIR, section

TEXT_MD = SKILL_DIR / "references" / "text.md"


def test_the_label_is_printed_and_the_icon_copied_by_label_tool_in_the_right_colour():
    """The commands themselves are run as written in test_label_snippets."""
    html = section(TEXT_MD.read_text(), "HTML")
    markdown = section(TEXT_MD.read_text(), "Markdown")
    assert "label_tool.py snippet --format html" in html
    assert re.search(r"\*\*Dark page background:\*\*[^\n]*`--dark`", html), "no dark-background rule"
    assert "label_tool.py copy-icons" in markdown and "label_tool.py snippet --format markdown" in markdown
    assert "`--colour white`" in markdown
    assert "cat " not in TEXT_MD.read_text() and " d` attributes" not in TEXT_MD.read_text()


def test_wording_lets_the_tool_word_the_label_and_says_when_to_step_in():
    """The phrases live in label_tool; the reference says how the language is
    settled and when the agent passes --lang or writes the label itself."""
    wording = section(TEXT_MD.read_text(), "Wording")

    assert not re.search(r"^\|", wording, re.M), "the wording table is back in the reference"
    assert "`--document`" in wording
    assert "ask the user" in wording, "language_unknown has no fallback"
    for case in ("`--lang <code>`", "`language_unknown`", "`language_not_listed`", '`--label "<text label>"`'):
        assert case in wording, f"Wording never says {case}"
