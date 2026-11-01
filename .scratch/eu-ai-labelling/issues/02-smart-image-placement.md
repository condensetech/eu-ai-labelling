# 02: Smart image placement

**What to build:** When labelling an image, the agent proposes the best corner instead of always using the top-right.
- `label_tool score` reports, for each corner, a busyness metric, the best Icon Colour and its contrast ratio, and whether the 3:1 threshold is met.
- The agent combines this with its own look at the image (faces, text, main subject) and prefers the top-right when it is free.
- It asks the user when the top-right is unsuitable and no corner is clearly better, or when every corner is busy.
- It shows a preview before the result is final.
- The Icon Colour is chosen automatically for at least 3:1 contrast. When neither black nor white reaches it, an opaque variant on a contrasting backing plate is used.
- The user can override the corner, size and colour.

**Blocked by:** 01

**Status:** resolved

- [x] `label_tool score <image>` outputs JSON with per-corner busyness, recommended colour, contrast ratio and a threshold flag, plus image dimensions
- [x] `apply` accepts colour, size and plate options; the plate fallback renders
- [x] pytest: a fixture with a busy top-right and a clean bottom-left ranks the corners accordingly
- [x] pytest: dark and light backgrounds yield white and black respectively, with contrast ≥ 3:1; a mid-grey noisy region reports the threshold not met
- [x] The skill instructs the agent to view the image, propose a corner, ask when in doubt and show a preview
- [x] User overrides for corner, size and colour are honoured

## Comments

`label_tool score <image> [--variant] [--size]` judges the area each corner's label would cover (sized for the padded plate, plus margin). It reports `busyness` (share of edge pixels), `busy` (above 0.10), the opaque Icon Colour with the better contrast, the WCAG `contrast` ratio, `meets_threshold` (3:1) and `plate`. It also gives image dimensions and format, a `ranking` with free corners first and the top-right leading them, `suggested_corner` and `all_busy`. Contrast is measured against the region's least favourable pixels (the 10th percentile darkest for a black icon, the lightest for a white one), not its average, so a noisy mid-grey region fails the threshold.

`apply` gains `--colour auto|black|white|black-50|white-50` (default auto, chosen as `score` does), `--size <px>` (icon height, refused below 24 px) and `--plate/--no-plate` (default: a plate only when the automatic colour can't reach 3:1). The plate is an opaque rounded rectangle in the opposite colour, padded 20% of the icon height and placed at the usual margin. Output adds `plate` and `plate_box`.

`references/image.md` now has the agent score the corners, look at the image itself (faces, text, subject), keep the top-right when it's free, otherwise take the first free corner in `ranking`, ask when no corner is free, apply, then preview the Labelled Copy and wait for approval. User overrides for corner, size, colour and plate are passed straight through.

Testing: pytest drives `score` and `apply` through the CLI subprocess seam: corner ranking, colour choice on dark and light backgrounds (21:1 literal for pure black and white), a noisy mid-grey region below threshold, top-right preference, all-busy flag, colour, 50% and size overrides, the minimum size refusal, plate fallback, and plate forced on or off. A mutation check confirmed each group fails when its behaviour is broken. E2E: the skill's own `score` command runs from a user project. Headless Claude Code scenarios cover moving off a busy top-right, asking when every corner is busy, honouring corner, size and colour overrides, and viewing and previewing the Labelled Copy. Codex validated statically only.

Review fix round 1:
- Transparent images: contrast is judged on the region composited over both a white and a black page, worse case counting, so hidden RGB under transparent pixels no longer decides the Icon Colour. `score` reports `transparent` per corner; a fully transparent corner gets a plate.
- Small images: `score` only refuses an image too small for the icon itself, and reports `plate_fits`. The plate padding shrinks to fit (down to 2 px). When no plate fits, `apply` in auto mode labels without one and reports `meets_threshold: false`; a forced `--plate` that cannot fit fails with `image_too_small`. `apply` now reports `meets_threshold` in every case.
- Tests: transparent PNGs (score and apply), boundary sizes (300x26, 300x23, 140x140), per-corner colour choice on a split light/dark image, and the plate fallback parametrised over both icon colours with the exact plate colour asserted. Mutants for each finding (corner region pinned to `tr`, same-colour plate, alpha ignored, padded-plate fit check in `score`, no padding shrink, erroring auto fallback) each fail the suite.

Review fix round 2 (rebased onto tickets 03 and 04):
- Merged with ticket 03's format handling. `score` and `apply` share one image loader, so `score` now refuses animated images and SVG with the same `animated_image` / `svg_image` errors as `apply`. The plate and icon are drawn on one overlay that is burned in through ticket 03's colour-space-preserving path, so a plated Labelled Copy stays greyscale or CMYK and keeps its ICC profile and EXIF. `references/image.md` keeps both the Formats section and the six-step placement procedure; step 6 carries the refusal wording for unsupported formats.
- Busyness border artefact: Pillow's `FIND_EDGES` copies the outermost pixels through unfiltered, so a flat light image reported its whole frame as edges (busyness 0.0133 per corner on a flat 1000x800 grey). Edges are now found on a copy with the border replicated one pixel outwards, then cropped back. Tests first: flat images in four colours and two sizes and a fully transparent image report busyness 0, and stripes running off the top edge still make the top corners busy.
- Tests: `score` refuses animated and SVG input; a plate keeps ICC and EXIF for PNG, JPEG and WebP, and keeps greyscale and CMYK in their colour space (mutation-checked against an RGB-only burn-in). E2E from the user's project: `apply` with the user's corner, size and colour overrides; the plate fallback; `score` refusing an animated GIF. Headless scenarios now pin `--model sonnet`.

Follow-ups: 15 (headless ask-when-top-right-unsuitable scenario), 16 (contrast threshold boundary tests).
