"""The Creative Work reference: a caption below the image.

The caption is printed by `label_tool snippet` (run as
written in test_label_snippets.py); here, the options the reference
names and the examples it shows. Whether the agent asks where the Label goes
and lets the user pick is judged by the headless runs in tests/evals
(scenarios with `asks_placement` or `below`).
"""

from __future__ import annotations

import re

from helpers import SKILL_DIR, SKILL_MD, fenced, section, step

CREATIVE_MD = SKILL_DIR / "references" / "creative-work.md"
MARKER_FORM = re.compile(r"<!-- eu-ai-labelling: (generated|modified) -->")


def test_step_3_offers_a_caption_or_burn_in_even_with_a_named_variant():
    """The placement question belongs to the image, not to a named variant (ticket 56)."""
    step_3 = step(SKILL_MD.read_text(), "Settle where an image's Label goes")

    assert re.findall(r"^   - \*\*([^*]+)\*\*", step_3, re.M) == ["Caption", "Burn-in"]
    assert "whether or not they named the variant" in step_3


def test_markdown_caption_is_its_own_block_of_marker_icon_and_label():
    markdown = fenced(section(CREATIVE_MD.read_text(), "Caption"), "markdown")
    assert markdown, "the Caption section has no ```markdown snippet"

    lines = markdown[0].strip().splitlines()
    # Its own lines: the marker, then the icon followed by a visible text label.
    assert len(lines) == 2 and MARKER_FORM.fullmatch(lines[0].strip()), markdown[0]
    icon = re.fullmatch(r"!\[[^\]]+\]\(([^)\s]+)\) +(\S.*)", lines[1].strip())
    assert icon, f"the caption is not the icon followed by a text label: {lines[1]!r}"
    assert icon.group(1).endswith("ai-basic-black.svg")
    assert re.search(r"generated with AI", icon.group(2)), "the text label does not follow the icon"
    # Not on the image's line: the snippet holds no reference to the image itself.
    assert ".png" not in markdown[0]


def test_alt_text_mention_keeps_the_description_and_adds_the_label_without_a_marker():
    md = fenced(section(CREATIVE_MD.read_text(), "Alt text mention"), "markdown")
    assert md and not MARKER_FORM.search(md[0]), "the caption carries the marker, not the alt text"
    # The original description stays, and the text label follows it.
    assert re.search(r"!\[[^\]]+ \(.*generated with AI\)\]\(", md[0])


def test_the_caption_is_printed_by_label_tool_with_its_options():
    """The commands themselves are run as written in test_label_snippets."""
    caption = section(CREATIVE_MD.read_text(), "Caption")
    assert "--format html" in caption and "--format markdown" in caption
    assert "`--figcaption`" in caption, "no word on an image inside a <figure>"
    assert "`--dark`" in caption, "no word on a dark background"

