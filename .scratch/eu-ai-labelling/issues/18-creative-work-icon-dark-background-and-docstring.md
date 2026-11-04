# 18: Creative Work icon dark background and reference wording

**What to build:** Follow-up from 06 (Creative Work labels outside the frame). Two small wording fixes in the Creative Work feature:
- `skills/eu-ai-labelling/references/creative-work.md`, section "Icon next to the image": the nearby-icon HTML snippet is a hard-coded black disc (`fill="#000"`, white glyph paths) and says nothing about dark pages. The Caption section says the dark-background colours are the same as in `references/text.md`, but the icon section does not. Add one sentence to "Icon next to the image" pointing to the dark-background colours in `references/text.md` (or to `assets/icons/ai-basic-white.svg` for the Markdown copy), so a dark page does not get a black disc with no instruction to switch to the White Icon Colour.
- `tests/e2e/test_creative_work_reference.py`, module docstring: it says the headless evals cover scenarios with `creative_work` or `anchor`. The scenario field added for this feature is `below`; no `anchor` field exists in the schema. Change `anchor` to `below`.

Evidence: `references/text.md` line 55 gives the dark variant (`fill="#fff"` on the first path, `#1d1d1b` on the others). The README, `tests/evals/test_skill_evals.py` and `creative-work-caption-italian.json` all use `below`. This is a code-reading observation from the 06 review, not a reproduced failure.

**Blocked by:** None

**Status:** resolved

Source: ticket 06 (Creative Work labels outside the frame), review findings (minor).

- [x] The "Icon next to the image" section points to the dark-background colours in `references/text.md` (or `ai-basic-white.svg` for Markdown)
- [x] The e2e module docstring names `below`, not `anchor`

## Comments

- Done: "Icon next to the image" in `skills/eu-ai-labelling/references/creative-work.md` says the snippets use the Black Icon Colour and points dark pages to the dark-background colours in `references/text.md` (HTML) or `assets/icons/ai-basic-white.svg` (Markdown). Covered by `test_icon_next_to_the_image_says_how_to_colour_it_on_a_dark_background`.
- Done: the module docstring of `tests/e2e/test_creative_work_reference.py` names `below`, not `anchor`.
How tested: `uv run pytest` (319 passed, 34 skipped; headless evals skipped by default).
