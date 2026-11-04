# 22: Stronger summary assertions in the headless batch test

**What to build:** Follow-up from 07 (Batch image labelling). The last assertion of `tests/e2e/test_headless_claude.py::test_skill_labels_a_folder_asking_once_for_uncertain_placements` is weak:
- The Icon Variant check is `re.search(r"fully ai-generated|ai generated|\bgenerated\b", text)` applied to the whole reply. It passes if the word "generated" appears anywhere, so a summary without the variant still passes. The user prompt itself says "fully AI-generated", so the agent can echo it anywhere.
- Only the corner is checked per Labelled Copy line. The acceptance criterion says the summary lists the variant and corner for each copy.

Fix: apply the variant regex to each Labelled Copy's summary line, in the same loop as the corner check. For a single-variant batch, also assert that the refused and skipped files are not listed as labelled.

Evidence: the assertion loop `for name, corner in placed.items()` checks `CORNER_WORDS` against the copy's line, while the variant regex is applied to the whole reply.

The headless test is opt-in and needs `EU_AI_LABELLING_E2E_DIR`, so it is not run by the default suite.

**Blocked by:** None

**Status:** resolved

Source: ticket 07 (Batch image labelling), review findings (minor).

- [x] The Icon Variant is asserted on each Labelled Copy's summary line, not on the whole reply
- [x] For a single-variant batch, refused and skipped files are asserted not to be listed as labelled

## Comments

- `skills/eu-ai-labelling/references/batch.md` step 8 now requires the Icon Variant on every Labelled line, even when the whole batch shares one, so each summary line stands alone.
- `tests/e2e/test_batch_reference.py` asserts that wording is present in the Labelled bullet.
- `tests/e2e/test_headless_claude.py::test_skill_labels_a_folder_asking_once_for_uncertain_placements`: the Icon Variant regex (`GENERATED_VARIANT`) is now applied to each Labelled Copy's own summary line, in the same loop as the corner check. The whole-reply check is removed.
- For a single-variant batch, `loop.gif`, `logo.svg` and `old.ai-label.png` are asserted not to be listed as labelled (no Labelled Copy name, and no line giving both a variant and a corner unless it also names a real copy).
- Tested: the headless test is opt-in (`EU_AI_LABELLING_E2E_DIR`) and skipped in the default run; not executed live here. The batch reference test runs in `uv run pytest` and passes.
