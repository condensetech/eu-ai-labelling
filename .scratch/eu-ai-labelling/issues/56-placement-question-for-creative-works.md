# 56: Ask where the Label goes on a creative work, even with a named variant

**What to build:** "Label this satirical image as fully AI-generated" skips the assessment, and with it the Creative Work check, so the image is burned in without the off-frame choice the README promises.

Fix: tie the placement question to the image, not to an assessment. When the request or context presents the image as artistic, satirical or fictional, and the user hasn't said how to label it, ask: a caption below the image, or the icon burned into it. Otherwise burn in, and offer the caption at the preview.

**Blocked by:** 55

**Status:** resolved

Source: review of the skill (2026-11-04); the maintainer asked for a solution.

- [x] A named variant on a creative work still gets the placement question
- [x] A named variant on an ordinary image goes straight to burn-in
- [x] Eval scenarios for both

## Comments

- What changed: SKILL.md step 3 "Settle where an image's Label goes" asks Caption or Burn-in whenever the request or context presents the image as an artistic, satirical or fictional work and the user hasn't said how, whether or not they named the variant. Any other image is burned in; `references/image.md` step 5 lets the user switch to a caption at the preview.
- Evals: `satirical-ai-art` and the new `named-variant-on-a-creative-work` expect the placement question and no Labelled Copy; `named-variant-skips-assessment` is renamed `named-variant-on-a-photo` and still expects burn-in. `tests/docs/test_creative_work_reference.py` checks that step 3 offers exactly Caption and Burn-in, with or without a named variant.
