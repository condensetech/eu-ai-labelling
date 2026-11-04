# 14: Creative Work eval scenario

**What to build:** Follow-up from 04 (Disclosure Assessment). The assessment includes the Creative Work check, but no scenario or reply assertion exercises it. The cartoon-mascot scenario is a Deepfake-test failure, not a Creative Work case. Dropping the Creative Work step from `SKILL.md` would go undetected. Add a scenario under `tests/evals/scenarios/` for a creative or satirical realistic image (expected Required, Fully AI-Generated), and assert that the reply says the disclosure must not hamper the enjoyment of the work. Evidence: no scenario or check mentions creative, satirical or fictional content, or the "doesn't hamper display or enjoyment" wording.

**Blocked by:** None

**Status:** resolved

Source: ticket 04 (Disclosure Assessment).

- [x] A scenario for a creative or satirical realistic image exists, with expected outcome Required and variant Fully AI-Generated
- [x] The scenario checks that the reply says the label must not hamper display or enjoyment of the work

## Triage (2026-11-02)

Covered by ticket 06: `tests/evals/scenarios/satirical-ai-art.json` expects Required and Fully AI-Generated with `creative_work`, and `test_skill_evals.py` asserts NOT_HAMPER for it.
