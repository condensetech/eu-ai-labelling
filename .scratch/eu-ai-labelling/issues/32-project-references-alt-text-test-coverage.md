# 32: Test coverage for reference alt text and the headless reference eval

**What to build:** Follow-up from 10 (Updating references and alt text in a project). Two coverage gaps:

- `alt` extraction in `label_tool references` is tested only for Markdown images and for an HTML `<img>` with a double-quoted alt. A missing alt (documented as `null`), a single-quoted alt and a JSX `alt={"..."}` are untested. Probes show `<img src=images/hero.png>` returns `html-img` with alt null, and no test pins this. The alt-regex branches could break and the suite would still pass.
- The alt-text criterion in `tests/e2e/test_project_references.py::test_alt_text_gains_the_mention_in_the_documents_language` is checked on the written procedure by regex. The only headless behavioural check is the one scenario in `tests/evals/scenarios/markdown-site-references.json`, which has English and Italian Markdown posts and the `generated` variant. It does not cover `modified`, an existing alt that is empty or already mentions AI, an HTML page with `lang="fr"`, or the `textLabelLanguage` override. The rules "Keep the original description", "already says AI" and "empty alt" are asserted only through `re.search`.

Fix: add one table-driven test in `tests/test_references.py` covering an `<img>` with no alt, one with a single-quoted alt, and one with a JSX alt prop, asserting the expected `alt` value or null for each. Optionally add a second headless scenario with an HTML page with `lang="fr"`, the `modified` variant, or an image with an empty alt. Alternatively, record that the current coverage is accepted given the headless cost.

**Blocked by:** None

**Status:** resolved

Source: ticket 10 (Updating references and alt text in a project), review findings (minor).

- [x] A table-driven test in `tests/test_references.py` pins the alt value for no alt, single-quoted alt and JSX alt
- [x] Either a headless scenario covers `modified`, empty alt or an HTML `lang="fr"` page, or the decision to accept the coverage is recorded in this ticket

## Triage (2026-11-02)

Do the table-driven test. The current headless coverage is accepted, so add no new headless scenario.

## Comments

- What changed: no production change. Coverage added in `tests/test_references.py`.
- How tested: `test_reports_the_alt_text_of_an_img_tag`, a table-driven test over no alt (`<img src=images/hero.png>`), single-quoted alt and JSX `alt={"..."}`, each asserting the `alt` and `alt_expression` values. `uv run pytest` passes.
- Decision (from triage): the headless reference coverage is accepted, so no new headless scenario is added. The alt-text rules stay checked by the existing headless scenario and the procedure regex checks.
