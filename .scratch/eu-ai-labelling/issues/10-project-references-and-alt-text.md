# 10: Updating references and alt text in a project

**What to build:** After producing a Labelled Copy inside a project, the agent finds references to the original image in the project's HTML, Markdown and source files, and updates them to point to the Labelled Copy. It updates the corresponding alt text to mention that the image is AI-generated or AI-modified. Finally it lists any references it couldn't update (e.g. a CMS or dynamic paths) so the user can fix them by hand.

**Blocked by:** 01

**Status:** resolved

- [x] References to the original are updated to the Labelled Copy
- [x] Alt text gains an AI-generated or AI-modified mention in the document's language
- [x] References that weren't updated are reported
- [x] Eval: a Markdown site referencing an image gets the updated path and alt text

## Comments

**Built:** `references` in `skills/eu-ai-labelling/scripts/label_tool.py` finds references to the original image in HTML, Markdown, text and source files, and reports the alt text and `alt_expression` of each image. The new `skills/eu-ai-labelling/references/update-references.md` tells the agent to repoint each reference to the Labelled Copy, update the alt text in the document's language (or `textLabelLanguage`), keep an existing description, never replace an `alt_expression`, and list every reference it could not update. `SKILL.md` and `references/image.md` and `references/batch.md` point to it.

**Tested:** `uv run pytest` (headless tests skipped): 286 passed, 33 skipped. Unit tests in `tests/test_references.py`, end-to-end tests in `tests/e2e/test_project_references.py` and `tests/e2e/test_batch_reference.py`, and a headless eval scenario in `tests/evals/scenarios/markdown-site-references.json` (run only with `EU_AI_LABELLING_E2E_DIR`).

**Follow-ups (review, minor):** 29 (alt attribute parsing in image tags), 30 (reference scan tokens, prose mentions and source file types), 31 (reference-style images and plain links), 32 (test coverage for reference alt text and the headless eval).
