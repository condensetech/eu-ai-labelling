# 16: Contrast threshold boundary tests

**What to build:** Follow-up from 02 (Smart image placement). No test sits near the 3:1 `CONTRAST_THRESHOLD` boundary. Backgrounds with contrast of about 2 or about 7 and above are the only ones exercised, so a drift of the threshold toward 2.1 is caught only indirectly through the plate tests in `test_apply`. A mutation probe setting the threshold to 2.5 failed only two parametrised `test_apply` plate cases and no `test_score.py` test. Add a `score` and `apply` case with a flat grey whose best contrast is about 2.8 (threshold not met, plate needed) and one at about 3.3 (threshold met, no plate needed).

**Blocked by:** None

**Status:** resolved

Source: ticket 02 (Smart image placement), review finding (minor).

- [x] `score` has a case at about 2.8 contrast reporting `meets_threshold` false, and one at about 3.3 reporting it true
- [x] `apply` at about 2.8 needs a plate, and at about 3.3 applies no plate

## Comments

- Added `grey_and_white_stripes` helper to `tests/test_score.py` and `make_grey_and_white_stripes` to `tests/test_apply.py`: 4 px stripes alternating flat grey and white, so the best icon is black judged against the grey.
- `test_score_judges_contrast_just_either_side_of_the_3_to_1_threshold` (grey 85, about 2.82:1, `meets_threshold` false; grey 95, about 3.29:1, true) checks each corner's contrast, colour, `meets_threshold` and `plate`.
- `test_apply_backs_the_icon_with_a_plate_only_below_the_3_to_1_threshold` (same two greys) checks a plate is drawn only at 2.82:1.
- Tested: `uv run pytest` passes (323 passed, 35 skipped). The contrast values sit close to the 3:1 boundary, so a threshold drift to 2.5 or 3.5 would fail these cases.
