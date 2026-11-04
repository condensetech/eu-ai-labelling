# 31: Reference-style Markdown images and plain links

**What to build:** Follow-up from 10 (Updating references and alt text in a project). Reference-style Markdown images and plain links are not handled:

- `![Trail][r]` with `[r]: img/hero.png` comes back as kind `other` with alt null. The alt text of `![Trail][r]` is never updated, because the procedure has no rule for this case.
- `[link](img/hero.png)` comes back as kind `other` with alt null. A link to the original is silently redirected to the Labelled Copy.
- The `<picture><source srcset="images/hero.png 1x">` form also comes back as `other` with alt null. Decide whether it is covered.

Fix: resolve the reference-style definition `[r]: ...` to its `![alt][r]` usage and report a markdown-image alt for it, so `update-references.md` can update the alt. Give links their own kind, or tell the agent in `update-references.md` to leave links alone. Decide and document how `<source srcset>` is handled.

**Blocked by:** None

**Status:** resolved

Source: ticket 10 (Updating references and alt text in a project), review findings (minor).

- [x] `![Trail][r]` with `[r]: img/hero.png` has its alt text updated, or the procedure says explicitly that it is left alone
- [x] A plain `[link](img/hero.png)` is reported with its own kind, or the procedure says to leave links unchanged
- [x] Each of these forms has a test in `tests/test_references.py`

## Triage (2026-11-02)

Decisions: update the alt of reference-style images. Leave plain links alone, and say so in `update-references.md`. Report `<source srcset>` as updatable, since it has no alt.

## Comments

- What changed: `markdown_kind` gives each reference its kind. A `[r]: path` definition is `markdown-definition`, with an `images` list (line and alt) of each `![alt][r]`, `![alt][]` or `![alt]` that uses it. A `[text](path)` link, or a definition that no image uses, is `link`. `<source srcset>` is `html-source` with no alt, and `<a href>` is `link`. `update-references.md` says to edit the alt of each image in `images` (keeping the label of `![alt][]` / `![alt]` by writing `![alt (mention)][alt]`), to edit the `<img>` alt for an `html-source`, and to leave `link` references unchanged.
- Decisions applied (from triage): reference-style images have their alt updated; plain links are left alone and the procedure says so; `<source srcset>` is reported as updatable.
- How tested: `test_a_reference_style_image_reports_the_definition_and_each_image_using_it`, `test_a_link_to_the_image_is_reported_as_a_link`, `test_a_linked_image_whose_link_points_to_the_original_reports_the_link`, `test_a_picture_source_is_updatable_and_has_no_alt`. Procedure checks in `tests/e2e/test_project_references.py` (`test_every_kind_the_tool_reports_has_a_rule`, `test_a_link_to_the_original_is_left_alone`). `uv run pytest` passes.
- Unaddressed minor review finding (not fixed here): `html_kind` uses `<(img|source|a)\b`, and `\b` matches before `-`, so custom elements such as `<a-custom href="img/hero.png">` are classified as `link` and left unchanged. Fix: use `<(img|source|a)(?![\w:.-])`.
