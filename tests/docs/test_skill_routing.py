"""The skill routes each kind of content to its reference file.

Only the links are checked: that a step names the reference the agent must
follow there. Whether the agent follows it is judged by the headless runs in
tests/headless and tests/evals; that every path the skill names exists is
checked in tests/plugin/test_packaging.py.
"""

from __future__ import annotations

import pytest

from helpers import SKILL_DIR, step

ROUTES = [
    # document, step, reference it must link
    ("SKILL.md", "Label it", "references/image.md"),
    ("SKILL.md", "Label it", "references/text.md"),
    ("SKILL.md", "Label it", "references/creative-work.md"),
    ("SKILL.md", "Label it", "references/batch.md"),
    ("SKILL.md", "Label it", "references/site.md"),
    ("SKILL.md", "Label it", "references/video.md"),
    ("SKILL.md", "Label it", "references/update-references.md"),
    ("SKILL.md", "Report", "references/batch.md"),
    ("SKILL.md", "Report", "references/update-references.md"),
    ("references/image.md", "Show a preview", "references/update-references.md"),
    ("references/batch.md", "Update references", "references/update-references.md"),
]


@pytest.mark.parametrize("document, title, reference", ROUTES, ids=[f"{d}:{t}->{r}" for d, t, r in ROUTES])
def test_the_step_links_the_reference_to_follow(document, title, reference):
    assert f"`{reference}`" in step((SKILL_DIR / document).read_text(), title)
