# 05: Handle Existing Labels in a batch

**What to build:** Put the Existing Label question into the batch flow (`SKILL.md` **A batch of files** and `references/batch.md`). See [spec](../spec.md).

**Blocked by:** 02, 03

**Status:** resolved

- [x] The "label anyway?" question for files with an Existing Label goes into the batch's single message, with files grouped by name like the other per-file exceptions. It is never asked again for a file whose answer is settled.
- [x] A file the user declines goes under **Skipped** in the batch report, with the reason "Existing Label kept, no EU Icon added".
- [x] Doc test for `batch.md`. Eval scenario: a batch where one image has an Existing Label and the others don't.

**Note:** an image's Existing Label is seen before the single message and asked there. A video's shows only in its `video-preview` frames, which need that message's answers, so it is asked in the batch's one later placement question (step 5 of `batch.md`), before its `video-apply`.
