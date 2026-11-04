# 35: The tool prints the refusal sentence the user should read

**What to build:** `references/image.md` step 6 and `references/batch.md` step 8 ask the agent to say "<Animated images | SVG images> aren't supported yet" and that a still PNG, JPEG or WebP version can be labelled instead. `label_tool` prints a different sentence: `svg_refusal` says "SVG images are not supported: label a PNG, JPEG or WebP export of it instead", and the animated refusal says "label a still image instead". The agent has to rewrite one fixed sentence into another, and about 1 headless run in 4 misses the wording (`tests/headless/test_headless_claude.py::test_skill_relays_the_refusal_of_an_unsupported_image[diagram.svg...]`).

Fix: make `error.message` for `animated_image` and `svg_image` the exact sentence to show the user, and have `image.md` and `batch.md` tell the agent to relay it as written.

**Blocked by:** None

**Status:** resolved

Source: review of the skill for checks that can be made deterministic (2026-11-03).

- [x] `animated_image` and `svg_image` messages say "<Animated images | SVG images> aren't supported yet" and that a still PNG, JPEG or WebP version can be labelled instead
- [x] `image.md` and `batch.md` tell the agent to relay that message as written
- [x] `tests/unit/test_refusals.py` pins the wording
- [x] The headless refusal test passes on repeated runs

## Comments

- What changed: `label_tool.py` words both refusals as the user should read them, from one `STILL_ONLY` constant: "<file> is an SVG image. SVG images aren't supported yet: a still PNG, JPEG or WebP version can be labelled instead." (the animated one names the format and frame count first). The message names the file, not its full path. `image.md` step 6 and `batch.md` step 8 now say to give `error.message` as written, word for word, instead of asking for a sentence of their own.
- How tested: `tests/unit/test_refusals.py` pins the full sentence for `animated_image` and `svg_image`, for both `score` and `apply`. Fast suite: 370 passed, 1 xfailed (the existing URL-decoding xfail in `test_references.py`).
- Headless, `test_skill_relays_the_refusal_of_an_unsupported_image[diagram.svg...]`, 8 runs each with Sonnet: before 6/8 passed (2 failed on wording), after 8/8. All three formats plus the control: 4 passed. Eight runs is a small sample: at the old 3-in-4 pass rate, 8/8 happens about 1 time in 10.
