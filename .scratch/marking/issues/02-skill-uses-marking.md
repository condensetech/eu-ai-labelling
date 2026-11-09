# 02: The skill uses the Marking when settling the Icon Variant

**What to build:** Step 2 of `SKILL.md` runs `marking` on each image and video, and treats a precise result as context: it settles the Icon Variant without asking. Vague signals are quoted in the origin question. The batch, "required?" and report rules follow the [spec](../spec.md).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `SKILL.md` step 2:
  - run `marking` on each image and video before deciding whether to ask;
  - a precise result settles the variant as context does;
  - a vague result is quoted in the origin question;
  - no Marking is never mentioned and never counts as evidence.
- [ ] The user's word beats the Marking: label as they said, without asking. The preview and report state the mismatch as a fact, with no verdict.
- [ ] When the user named the variant and the Marking agrees, the final report says so in one line.
- [ ] `c2pa: unavailable`: say that C2PA wasn't checked, only when asking the origin question.
- [ ] **A batch of files** and `references/batch.md`:
  - files settled by a precise Marking are never named in the one message;
  - a batch with nothing open is labelled without a question;
  - the batch report lists the files settled by Marking.
- [ ] `references/image.md` and `references/video.md`:
  - the preview and the report say which Marking settled the variant;
  - the report says the Labelled Copy no longer carries the original's Marking.
- [ ] **Whether a Label is required:** mention a Marking found as a fact, with no legal verdict.
- [ ] The **An Existing Label** wording about Marking stays: a Marking is still not an Existing Label.
- [ ] Doc tests for each changed reference.
- [ ] Eval scenarios 1–6 from the spec. The `unknown-origin` and `video-unknown-origin` evals still pass unchanged.
