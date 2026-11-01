# 07: Batch image labelling

**What to build:** A creator asks to label every image in a folder. The Disclosure Assessment is asked once, with answers shared across the batch, and per-file questions appear only where files differ (e.g. some deepfake-like, some not). Placement is still judged per image, and all uncertain placements are gathered into a single question. Every image gets a Labelled Copy, and the agent reports a summary.

**Blocked by:** 02, 04

**Status:** resolved

- [x] The skill handles a folder or a list of images in one request
- [x] Shared assessment answers apply to all files; differing files get targeted questions
- [x] Uncertain placements are gathered into one question
- [x] The final summary lists each Labelled Copy, its variant and corner, and any skipped or refused files
- [x] Eval: a mixed folder triggers per-file questions only for the differing files

## Comments

**Built:** `label_tool score` now takes a folder, or several images, in one run. It prints `images` (each image's usual report plus its `path`), `refused` (animated, SVG, too small, unreadable or missing files, each with its `error`) and `skipped` (existing Labelled Copies, never labelled twice). A single image keeps the old output. A folder with no image fails with `no_images`. In `SKILL.md`, a folder, glob or list of files is a **batch**. The new "A batch of files" section asks the assessment once. Shared answers hold for every file, and per-file questions name only the files that differ. The outcome for settled files shows in the same message, and the step 3 decision comes once, after every file has its outcome. The new `references/batch.md` scores the batch, judges placement per image with the rules in `image.md`, applies each image that has a free corner, and gathers every uncertain placement into one question. That question shares a message with the batch preview. The procedure ends with a summary: each Labelled Copy with its Icon Variant and corner, then the refused and skipped files. The README documents the batch.

**Tested:** `tests/test_score_batch.py` covers batch `score` at the CLI seam. `tests/e2e/test_batch_reference.py` runs the batch `score` command from `batch.md` and the `apply` command from `image.md` exactly as written, from the user's project. It also checks the skill text against this ticket. New eval scenario `mixed-event-folder.json`, with the `batch_questions` expectation and canned-reply checks that reject weakened replies. New headless test `test_skill_labels_a_folder_asking_once_for_uncertain_placements`. The eval scenario and the headless test each passed one headless run.

**Open points:** a batch with mixed Icon Variants needs one `score` run per variant, or a listed subset per run. Batch `score` does not look inside subfolders.

**Follow-ups:** 20 (batch `score` semantics: labelled-copy case, explicit labelled copies, duplicates, dangling symlinks, empty folders), 21 (folder discovery tests: uppercase suffix, dotfiles, non-recursion, mixed folder and file), 22 (headless summary assertions: variant per copy line, refused and skipped not listed).
