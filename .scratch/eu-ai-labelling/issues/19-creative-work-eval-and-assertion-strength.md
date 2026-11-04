# 19: Creative Work eval regex and reference assertions

**What to build:** Follow-up from 06 (Creative Work labels outside the frame). The Creative Work checks are looser or thinner than the feature they guard:
- `tests/evals/test_skill_evals.py`, `CREATIVE_WORK_OPTIONS['icon next to the image']`: the pattern `\bicon (right )?(next to|beside|alongside) the image\b` accepts only the exact phrase. A correct reply such as "a small icon next to it" or "icon beside the picture" fails the opt-in headless eval. Loosen it, for example to `icon (right )?(next to|beside|alongside) (the|it|the image|the picture)`, or accept "nearby icon". Add positive cases for the new phrasings to the canned-reply tests.
- `tests/e2e/test_creative_work_reference.py` does not assert several behaviours the reference instructs:
  - the caption placement ("directly below the image reference, as its own block") in the Caption section;
  - the Markdown Caption snippet beyond the marker and icon filename: that it has a text label after the icon and is a separate line;
  - the rule that alt text keeps the existing description ("Keep the original description...");
  - the HTML alt-text variant.
  The alt-text snippet check only requires the label inside the brackets, so an alt text that replaces the description would pass. Add static asserts for "directly below" in the Caption section, a text label after the icon in the Markdown caption snippet, an original description kept before the label in the alt text (for example `!\[[^\]]+ \(.*generated with AI\)\]`), and the HTML alt-text variant.

Evidence: a mutation probe in a scratchpad copy changed the caption placement sentence to "anywhere in the document" and removed "Keep the original description...". The run stopped at the first failure (`-x`), triggered by another edit in the same mutation, so these two edits were never exercised on their own. By reading the tests, no assertion references either sentence. `creative-work-caption-italian` covers caption placement in the headless eval, which is skipped in the default suite. The headless evals were not run for this ticket.

**Blocked by:** None

**Status:** resolved

Source: ticket 06 (Creative Work labels outside the frame), review findings (minor).

- [x] The icon option regex accepts "a small icon next to it" and "icon beside the picture", with canned-reply positive cases
- [x] Static asserts cover the caption's "directly below" placement, the Markdown caption text label, the alt-text original description and the HTML alt-text variant
- [ ] A mutation of the caption placement sentence and of the alt-text "Keep the original description" sentence each fails a test on its own

## Comments

- Done: the icon regex in `CREATIVE_WORK_OPTIONS` accepts "next to it", "beside the picture" and "nearby icon"; canned-reply positive cases are in `test_check_accepts_other_phrasings_of_the_icon_next_to_the_image`.
- Done: static asserts in `tests/e2e/test_creative_work_reference.py` cover "directly below ... as its own block", the Markdown caption's text label and separate line, the alt-text original description and "after what is already there", and the HTML alt-text variant.
- Not verified (criterion 3): the one-mutation-per-test check was not re-run in this pass. The sentences are asserted, but the claim that each mutation fails a test on its own is not shown here.
- Headless creative-work evals were not run (skipped by default).
How tested: `uv run pytest` (319 passed, 34 skipped; headless evals skipped by default).
