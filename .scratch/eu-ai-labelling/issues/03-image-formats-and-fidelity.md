# 03: Image formats and fidelity

**What to build:** Labelling works on static PNG, JPEG and WebP images without degrading them. The Labelled Copy keeps the original's colour profile (ICC) and EXIF metadata, and JPEG copies are re-encoded at high quality. Animated GIF/WebP and SVG inputs are refused with a clear, structured error that the agent relays to the user.

**Blocked by:** 01

**Status:** resolved

- [x] PNG, JPEG and WebP inputs produce a Labelled Copy in the same format
- [x] ICC profile and EXIF are preserved in the Labelled Copy
- [x] JPEG copies are re-encoded at quality ≥ 95
- [x] Animated GIF, animated WebP and SVG inputs exit non-zero with a JSON error explaining they aren't supported
- [x] pytest covers each of the above through the CLI

## Comments

Built: `label_tool.py apply` now labels static PNG, JPEG and WebP images and writes the Labelled Copy in the same format as the input. The ICC profile and EXIF are carried over, and JPEG copies are re-encoded at quality 95. Animated GIF, animated WebP and SVG inputs are refused with a non-zero exit and a structured JSON error, which the skill (SKILL.md, references/image.md) tells the agent to pass on to the user. The README is updated to match.

Tested:
- Unit seam (`tests/test_formats.py`): pytest runs the label_tool CLI as a subprocess. It checks that the output format matches the input for each format, that ICC/EXIF are preserved, that JPEG quality is at least 95, and that animated/SVG inputs are refused with a JSON error.
- E2E (`tests/e2e/test_image_formats.py`, `tests/e2e/test_headless_claude.py`): headless Claude Code runs with the plugin in a throwaway project. It labels each supported format and relays the refusal for unsupported inputs.
- Full suite: 64 passed, 8 skipped (the skipped tests are gated headless runs).
