# 13: Tighten skill eval assertions

**What to build:** Follow-up from 04 (Disclosure Assessment). The eval harness in `tests/evals/test_skill_evals.py` is correct but its checks are loose, so a pass is one sample and can be flaky or hide regressions:
- Each eval runs the model once. The politician deepfake is the only control. Consider repeated runs or additional controls.
- `AFTER_SIGN_OFF` accepts any "after ... review" within 40 characters.
- The "voluntary label" check is satisfied by the output-format field name alone. It does not check that a Voluntary Label is offered. Fix: require an offer phrase near "voluntary label", such as "can apply", "offer" or "still allowed".
- The CODE_OF_PRACTICE and NOT_REVIEW reminder checks are sentence-scoped keyword matches with no negation. A reply such as "signing the Code of Practice signals adherence" passes, and so does "Spell-checks, automated review or cursory approval count as human review". Fix: add a negation token to these patterns, for example `(doesn't|does not|not|no) .*signal` and `(don't|do not|not|never) count`.
- The control test only shows that a wrong command makes `check()` fail on the deepfake scenario. It would also pass if the model never answered in the outcome format. Optionally add a second control that mutates the reply.

Evidence: 8 of 8 evals passed in 106s (`EU_AI_LABELLING_E2E_DIR=<scratchpad> uv run pytest tests/evals`). This is a code-reading observation, not a reproduced failure.

**Blocked by:** None

**Status:** resolved

Source: ticket 04 (Disclosure Assessment).

- [x] "voluntary label" requires an offer phrase in the same sentence or near it
- [x] The CODE_OF_PRACTICE and NOT_REVIEW reminder checks require a negation and reject the probe replies listed above
- [x] The AFTER_SIGN_OFF check requires that an AI edit voids sign-off
- [ ] Optionally: a second control that mutates the reply, and repeated runs for the headless evals

## Triage (2026-11-02)

Do the first three criteria. Skip repeated headless runs, which cost too many tokens; a mutated-reply control is fine.

## Comments

- Done: `VOLUNTARY_OFFER` and `offers_voluntary_label()` require an offer phrase within 120 characters of "voluntary label"; the "Voluntary Label named, not offered" mutation is in `WEAKENED_REMINDERS`.
- Done: `CODE_OF_PRACTICE` and `NOT_REVIEW` use a negation token that must govern the verb; `AFTER_SIGN_OFF` now needs an AI edit that voids sign-off. Mutation cases added for the probes.
- Not done (optional, criterion 4): repeated headless runs skipped per triage. The mutated-reply control is covered by the `WEAKENED_REMINDERS` cases, not a separate second control.
- Unaddressed minor review findings (not ticketed):
  1. VOLUNTARY_OFFER still contains the generic "would you like" and "want me to". They match the step-3 question "would you like me to apply the recommended label...", so a reply naming the field but offering no Voluntary Label still passes if that question is within 120 characters. Evidence: `offers_voluntary_label("- voluntary label: none.\nwould you like me to apply the recommended label, a different variant, or no label?")` returns True. Fix: drop "would you like" and "want me to", or require the offer phrase to name the label.
  2. CODE_OF_PRACTICE's negation can sit anywhere before "signal" or "adhere" in the sentence. "you are not required to sign the code of practice, but doing so signals adherence." still matches. Fix: require the negation to govern the verb, e.g. `(doesn't|does not|not) (signal|imply) adherence`, or reject signal/adhere without a negation within a few tokens before it.
How tested: `uv run pytest` (319 passed, 34 skipped; headless evals skipped by default).
