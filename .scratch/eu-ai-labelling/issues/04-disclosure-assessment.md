# 04: Disclosure Assessment

**What to build:** Before labelling, the skill runs the guided Disclosure Assessment. It answers from context what it can and asks only the rest:
- content type;
- generated vs modified;
- for images, the Deepfake test;
- for text, the Public-Interest Text test and the Editorial Responsibility check, including the reminder that spell-checks, automated review or cursory approval don't count and that an AI edit after sign-off voids the exception;
- the Creative Work check.

It returns a Disclosure Outcome (Required, Not Required or Unclear) with a recommended Icon Variant, a one-line reason and a "not legal advice" note. It always offers a Voluntary Label, and notes that using the icons without signing the Code doesn't signal adherence. For Unclear outcomes it points to the official guidance and the AI Act Service Desk. It reminds the user that text generated before 2 August 2026 but published after it needs a Label. When the user names a variant explicitly, the assessment is skipped. This ticket also sets up the skill eval harness.

**Blocked by:** 01

**Status:** resolved

- [x] The skill contains the assessment flow and the outcome format, using GLOSSARY.md vocabulary
- [x] An eval harness exists and runs scenario prompts against the skill with expected outcomes
- [x] Eval: politician deepfake gives Required with Fully AI-Generated
- [x] Eval: face swap in an authentic photo gives Required with Partially AI-Modified
- [x] Eval: news article reviewed by a named editor gives Not Required, with a Voluntary Label offered
- [x] Eval: unreviewed AI-written public-interest blog post gives Required
- [x] Eval: an explicitly named variant skips the assessment

## Comments

Built: `SKILL.md` runs the Disclosure Assessment before labelling. It covers content type, generated vs modified, the Deepfake test for images, the Public-Interest Text test and Editorial Responsibility check for text, and the Creative Work check. It returns a Disclosure Outcome (Required, Not Required or Unclear) with a recommended Icon Variant, a one-line reason and the "not legal advice" note. It always offers a Voluntary Label, notes that the icons without signing the Code do not signal adherence, points Unclear outcomes to the official guidance and the AI Act Service Desk, and reminds users about text published after 2 August 2026. A named variant skips the assessment. The eval harness is in `tests/evals/` (scenarios in `tests/evals/scenarios/`, opt-in via `EU_AI_LABELLING_E2E_DIR`). The README documents it.

Tested:
- Default suite: `uv run pytest` gives 70 passed, 16 skipped (headless runs are opt-in).
- Evals: 8 of 8 passed in 106s with `EU_AI_LABELLING_E2E_DIR=<scratchpad> uv run pytest tests/evals`. The five outcome and variant evals in the acceptance criteria above are covered by these scenarios.

Follow-ups (non-blocking, from review):
- 12: named Basic for images and the text follow-up wording in SKILL.md step 2 and 3 (`12-named-variant-and-text-outcome-wording.md`).
- 13: tighter eval assertions and negation in the reminder checks (`13-eval-assertion-strength.md`).
- 14: Creative Work eval scenario (`14-creative-work-eval-scenario.md`).
