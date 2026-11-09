# 05: Handle Existing Labels in a batch

**What to build:** Put the Existing Label question into the batch flow (`SKILL.md` **A batch of files** and `references/batch.md`). See [spec](../spec.md).

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] The "label anyway?" question for files with an Existing Label goes into the batch's single message, with files grouped by name like the other per-file exceptions. It is never asked again for a file whose answer is settled.
- [ ] A file the user declines goes under **Skipped** in the batch report, with the reason "Existing Label kept, no EU Icon added".
- [ ] Doc test for `batch.md`. Eval scenario: a batch where one image has an Existing Label and the others don't.
