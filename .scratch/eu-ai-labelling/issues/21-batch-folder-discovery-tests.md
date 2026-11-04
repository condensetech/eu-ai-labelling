# 21: Pin batch folder discovery rules with tests

**What to build:** Follow-up from 07 (Batch image labelling). The folder discovery rules of `label_tool score` are not pinned by any test, so a change to them would pass the suite:
- uppercase suffixes (`IMG.JPG`) are accepted as images;
- hidden files (dotfiles such as `.hidden.png`) are skipped;
- subfolders are not scanned (`sub/inner.png` is not listed).

Non-recursion is stated as an open point in ticket 07 and as behaviour in the `label_tool.py` docstring. Evidence: in a `/tmp` copy, a case-sensitive suffix check, removing the dotfile filter and replacing `iterdir()` with `rglob("*")` left `tests/test_score_batch.py` and `tests/e2e/test_batch_reference.py` at 13 passed.

Add to `tests/test_score_batch.py`:
- one CLI test with `IMG.JPG`, `.hidden.png` and `sub/inner.png` next to a normal image, asserting that only the top-level, non-hidden images (including the uppercase-suffix one) appear under `images`;
- a test that mixes a folder and a file in one `score` call.

**Blocked by:** None

**Status:** resolved

Source: ticket 07 (Batch image labelling), review findings (minor).

- [x] A CLI test asserts that `IMG.JPG` is listed under `images`
- [x] A CLI test asserts that `.hidden.png` is not listed
- [x] A CLI test asserts that `sub/inner.png` is not listed
- [x] A test scores a folder and a file in one call

## Triage (2026-11-02)

Do this together with ticket 20, which touches the same code.

## Comments

**What changed:** No production code changed. Tests were added to `tests/test_score_batch.py` that pin the folder discovery rules: uppercase suffixes (`IMG.JPG`) are listed under `images`, dotfiles (`.hidden.png`) are skipped, and subfolders (`sub/inner.png`) are not scanned. A further test scores a folder and a file in one call.

**How tested:** `uv run pytest` passes (330 passed, 35 skipped). The batch tests are 14 in `tests/test_score_batch.py`. Mutation probes from the ticket (case-sensitive suffix, removed dotfile filter, `rglob`) fail the new tests.
