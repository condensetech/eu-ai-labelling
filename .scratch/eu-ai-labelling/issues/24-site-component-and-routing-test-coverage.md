# 24: Test coverage for site component hover and SKILL routing

**What to build:** Follow-up from 08 (Site integration). Some site behaviour is not asserted by any test:

- `tests/evals/test_skill_evals.py::check_site_component` only requires the string `Escape` or `.esc`, a `<button`, `aria-expanded` and `aria-controls`. It does not require a hover handler, so a generated component without hover opening still passes. The second-layer rules for Vue, Astro and plain HTML, and the `auto` background option, are checked only by framework-name headings or not at all. Fix: also require a hover handler (`onMouseEnter`, `@mouseenter` or `mouseenter`) and a `hidden` or `v-show` binding on the details. Add these to the canned accept and reject tests.
- `tests/e2e/test_site_reference.py::test_generated_component_has_no_runtime_dependency_on_the_plugin` greps the adaptation rules only for the phrases "no runtime dependency on the plugin" and "never ... skill folder", plus the four framework names. Escape focus-return and pinning rules for Vue and Astro are not asserted.
- `tests/e2e/test_site_reference.py::test_skill_routes_a_site_request_to_the_site_reference` checks step 4 for `references/site.md` and a site match in step 2 only. Step 1's recognition of a site as a kind of content, and the rule that the Disclosure Assessment is skipped for sites, are not tested. The only coverage is the opt-in headless eval, which declares `outcome: null`. Fix: add a `SKILL.md` assertion that step 1 names a site as a kind of content and that the assessment is skipped for sites.

**Blocked by:** None

**Status:** resolved

Source: ticket 08 (Site integration), review findings (minor).

- [x] `check_site_component` requires a hover handler and a `hidden` or `v-show` binding, with canned accept and reject cases
- [x] The no-dependency and framework rules are asserted for Vue and Astro as well as React, including the Escape focus-return rule
- [x] A `SKILL.md` test asserts step 1 names a site and that the assessment is skipped for sites

## Comments

- `check_site_component` now requires a hover handler (`onMouseEnter`, `@mouseenter` or `mouseenter`) and a `hidden` or `v-show` binding on the details, with canned accept and reject cases in `tests/evals/test_skill_evals.py`.
- `tests/e2e/test_site_reference.py` asserts the no-runtime-dependency and framework rules for Vue and Astro as well as React, including the Escape focus-return rule. The adaptation rules in `skills/eu-ai-labelling/references/site.md` were updated to match.
- A `SKILL.md` test asserts that step 1 names a site as a kind of content and that the Disclosure Assessment is skipped for sites.

Tested with `uv run pytest`: 336 passed, 35 skipped (headless and opt-in eval tests stay skipped).
