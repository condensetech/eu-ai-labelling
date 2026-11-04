# 15: Headless ask-when-top-right-unsuitable scenario

**What to build:** Follow-up from 02 (Smart image placement). The only headless test of the ask-the-user branch is `test_skill_asks_before_labelling_when_every_corner_is_busy`, which covers only the all-busy case. The acceptance criterion also requires asking when the top-right is unsuitable and no corner is clearly better. That case is untested. Add a headless fixture with a plain flat image, a large text or face-like subject in the top-right, and all other corners comparable. Assert that no copy is written. Tighten the ask assertion to require at least two named corners in the reply. The current all-busy test passes on the weak signal of no copy plus the word "corner" appearing in the reply.

**Blocked by:** None

**Status:** resolved

Source: ticket 02 (Smart image placement), review finding (minor).

- [x] A headless fixture with a top-right subject and comparable other corners exists, and the test asserts no copy is written
- [x] The ask assertion requires at least two named corners in the reply

## Comments

- Added `make_poster` in `tests/e2e/test_headless_claude.py`: a 1200x800 flat poster with a large face filling the top-right and a line of large text in each other corner, so `score` flags no busy corner and only the image shows the top-right is unsuitable.
- Added `test_skill_asks_when_the_top_right_covers_a_face_and_no_corner_is_clearly_better`: asserts no tool call, the source image is unchanged, nothing but `photo.png` is written, and the reply names at least two corners.
- Factored the ask check into `assert_asks_which_corner`, now used by the all-busy test too. It counts distinct named corners (`named_corners`), replacing the weak "corner" word check.
- Tested: the headless tests are opt-in and skipped in the default `uv run pytest` run; they were not executed against a live agent here. The default suite passes (323 passed, 35 skipped).
