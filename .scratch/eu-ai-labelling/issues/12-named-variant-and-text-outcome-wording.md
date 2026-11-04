# 12: Named variant and text outcome wording in SKILL.md

**What to build:** Follow-up from 04 (Disclosure Assessment). Two wording gaps in `skills/eu-ai-labelling/SKILL.md`:
- Step 2 lists "basic" as a named variant that skips the assessment. The image path cannot apply it: `label_tool.py` accepts only `generated` and `modified`. A user who names Basic for an image skips the assessment and then cannot be labelled. The model recovers only by improvising. Evidence: `label_tool.py apply a.png --variant basic` exits 1 with `argument --variant: invalid choice: 'basic' (choose from generated, modified)`. A headless run of `/eu-ai-labelling label photo.png with the basic icon` wrote nothing and asked for another variant. Fix: in step 2 say that Basic applies to text only; for an image a named Basic is not usable, so ask for Fully AI-Generated or Partially AI-Modified, or offer the assessment. Alternatively drop "basic" from the named variants for now.
- Step 3 asks whether to apply the recommended Basic Label for text, but step 4 says text is not labelled in this version. A Required text outcome and the Voluntary Label offer for Not Required text both end with an offer the skill cannot fulfil. Evidence: a headless run of `/eu-ai-labelling label post.md as fully AI-generated` replied "this version of the skill only labels images" and told the user to add the text label themselves. Fix: state in step 3 that for text the skill gives the outcome and recommended Label wording only and does not write a Labelled Copy yet; do not ask "apply the recommended Label" for text. The text scenarios in the evals set `labelled: false` and never check this follow-up.

**Blocked by:** None

**Status:** resolved

Source: ticket 04 (Disclosure Assessment).

- [x] Step 2 says Basic applies to text only and that a named Basic for an image is handled by asking for a usable variant or offering the assessment (or Basic is removed from the named variants)
- [ ] Step 3 says that for text the skill gives the outcome and recommended Label wording only, and does not ask to apply the Label
- [ ] An eval or headless check covers the named-Basic-for-image case and the text follow-up

## Triage (2026-11-02)

Narrowed: the text half is superseded by ticket 05, which labels Markdown and HTML documents and settles Basic for them in step 2. What remains is the image case: a user who names "basic" for an image skips the assessment, and `label_tool` cannot apply Basic. Decision: in step 2, say that Basic is for documents and sites only. For an image named as Basic, ask whether it is fully AI-generated or AI-modified. Drop the second and third criteria if they no longer apply after 05.

## Comments

- Done: step 2 of `skills/eu-ai-labelling/SKILL.md` now says Basic is for documents and sites only; a named "basic" for an image asks whether it is Fully AI-Generated or Partially AI-Modified and labels nothing until the user answers. The named-variant bullet no longer lists "basic".
- Not done: step 3 is unchanged. The text follow-up (no "apply the recommended Label" question for text) is not addressed here; left open as the triage noted ticket 05 supersedes the text half.
- Not covered: no headless check of the text follow-up. The image case is covered by `tests/e2e/test_install_and_label.py::test_a_basic_icon_named_for_an_image_is_settled_by_asking_generated_or_modified` and the `named-basic-for-an-image` scenario with canned-reply tests in `tests/evals/test_skill_evals.py`.
How tested: `uv run pytest` (319 passed, 34 skipped; headless evals skipped by default).
