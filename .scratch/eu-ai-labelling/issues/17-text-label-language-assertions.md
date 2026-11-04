# 17: Text label language assertions

**What to build:** Follow-up from 05 (Text labelling). The headless text eval and the static test only check that the accessible name is non-empty. Nothing ties the language-specific icon name to the document's language. In `tests/e2e/test_text_reference.py::test_html_snippet_inlines_the_official_basic_icon_as_an_accessible_svg`, `svg.get("aria-label")` is only tested for truthiness. The Markdown snippet's alt text is checked only by a non-empty regex match. The eval `check_text_label` likewise requires only a non-empty `aria-label` or alt. Tighten these so that, when a scenario states the language-specific icon name (e.g. 'IA' for the Italian article), the `aria-label` or alt text must match it.

**Blocked by:** None

**Status:** resolved

Source: ticket 05 (Text labelling), review finding (minor).

- [x] The static test asserts the HTML `aria-label` and the Markdown alt text are non-empty and not the generic icon text
- [x] The text-label eval asserts the `aria-label` or alt equals the scenario's stated icon name when one is given (e.g. 'IA' for the Italian article)

## Comments

- Done: `test_html_snippet_inlines_the_official_basic_icon_as_an_accessible_svg` and the Markdown snippet test assert the icon name is non-empty, not generic, and equal to the English name in the Wording table (`assert_names_the_icon`).
- Done: `check_text_label` in `tests/evals/test_skill_evals.py` checks that the `aria-label` or alt equals `icon_name` when a scenario states one. `icon_name` is set to IA, AI or IA in the Italian, English and Creative Work scenarios; canned-broken Italian cases cover English and generic names.
How tested: `uv run pytest` (319 passed, 34 skipped; headless evals skipped by default).
