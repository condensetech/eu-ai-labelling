# Labelling an image

Images get the **Fully AI-Generated** (`generated`) or **Partially AI-Modified** (`modified`) EU Icon burned into the pixels of a **Labelled Copy**. The original file is never changed.

## Formats

- **Supported:** still PNG, JPEG and WebP. The Labelled Copy has the original's format, colour space (greyscale and CMYK stay so) and EXIF metadata, and keeps the colour profile (ICC) when it fits that colour space. Pixels are turned upright, so the EXIF orientation tag is dropped; 16-bit greyscale becomes 8-bit. JPEG copies are re-encoded at quality 95; lossless WebP stays lossless. A camera or phone JPEG with an embedded preview or gain map (MPO) is a still JPEG: its main image is labelled and the copy is a plain JPEG.
- **Refused:** animated GIF, animated WebP (any animated image), SVG, and every other format (BMP, TIFF, a still GIF and the like). Both `score` and `apply` exit non-zero with error code `animated_image`, `svg_image` or `unsupported_format` and write nothing. `apply` also refuses a Labelled Copy (`labelled_copy`): label the original.

## Steps

1. **Score the corners.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py score <image> --variant <generated|modified>
   ```

   When the user said which corner they prefer without insisting on it ("bottom-left if it's free"), add `--prefer <tl|tr|bl|br>`. A corner they insist on is an override (see **Overrides**). When they asked for a size, add the same `--size <px>` you will pass to `apply`, so the corners are judged at that size; score again if the size changes. It prints JSON. The fields the next steps use:
   - `corners`: for each of `tl`, `tr`, `bl`, `br`, `busy` (edge density above the threshold), `meets_threshold` (the best Icon Colour reaches 3:1 contrast) and `plate` (a backing plate will be needed);
   - `plate_fits`: false when the image is too small for a backing plate. A corner that needs a plate then gets a label below 3:1;
   - `preferred_corner`: the corner tried first, `preferred_from` where that comes from: `request`, the corner passed with `--prefer`, or `default`, the top-right, which the Code of Practice suggests;
   - `ranking`: the corners from most to least suitable, by these numbers alone, the preferred corner first when it is free (`suggested_corner` is its first entry);
   - `all_busy`: true when every corner is busy.

   Done when the command exits 0. On an error, follow step 6.
2. **Look at the image yourself.** Open it with your image-viewing or file-reading tool. Note where faces, text, logos and the main subject are. `score` sees only edges and contrast, so it can't tell a face from a patterned wall.
3. **Choose a corner.** A corner is **free** when `score` reports it not busy, and the icon there covers no face, text or main subject.
   - Start from `suggested_corner`. If it is free, use it.
   - If it isn't free but another corner is, use the free corner that comes first in `ranking`. When that is not the `preferred_corner`, tell the user why you didn't use it.
   - A corner that needs a plate (`plate` true) is still free if it is not busy: the plate gives it the contrast. But if `plate_fits` is false, prefer a corner whose `meets_threshold` is true.
   - If no corner is free, **ask the user** which corner to use, and wait for the answer before applying anything. That covers `all_busy` being true, and every corner being busy or covering a face, text or the main subject. List each corner with a short note, e.g. "top-left: sky, clean; bottom-right: covers the signature".

   A corner the user insists on (see **Overrides**) settles this step. A size or colour choice settles only that parameter: the corner is still chosen here. Done when a corner is settled.
4. **Apply the label.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py apply <image> --variant <generated|modified> --corner <tl|tr|bl|br>
   ```

   Add `--colour`, `--size`, `--plate` or `--no-plate` only for a user override. Without them the tool picks the Icon Colour and decides on the plate itself. It writes `<name>.ai-label.<ext>` next to the original and prints JSON with `labelled_copy` (its path), the parameters used (`variant`, `corner`, `colour`, `plate`) and `meets_threshold` (whether the label reaches 3:1 contrast; always true on a plate).

   Done when the command exits 0 and `labelled_copy` exists. If `meets_threshold` is false, tell the user in the preview (step 5) that the label is below 3:1 contrast and offer another corner, colour or a larger image.
5. **Show a preview.** Open the Labelled Copy with your image-viewing tool and check it yourself: the icon is readable and covers nothing important. Then give the user its path, the corner, colour and size used, and whether a plate was drawn. Ask them to approve it or ask for a change.
   - If the image is shown in a document or page and they would rather have a caption below it than an icon in the picture, follow `references/creative-work.md` instead. Delete the Labelled Copy if this run created it; one that existed before may already be shown by pages, so keep it and tell the user.
   - If they ask for a change, run `apply` again with the override. It replaces the previous Labelled Copy and still leaves the original untouched. Then show the new preview.
   - A Labelled Copy is **final** once the user approves it, or when they said beforehand that they don't need a preview. A copy re-applied after a change needs the same again.

   Done when the Labelled Copy is final, or the user switched to a caption and `references/creative-work.md` is done. When the image is inside the project you work in, then update the references to it and their alt text, as `references/update-references.md` says.
6. **On an error** from either command, the original is untouched and no Labelled Copy was written. Act on `error.code`:
   - `animated_image`, `svg_image`, `unsupported_format`: the message is already worded for the user: give it to them as written, word for word, and stop. Convert the file only if the user asks.
   - `size_too_small`, or `image_too_small` after a size, colour or plate the user chose: tell them why it doesn't fit and ask for another choice.
   - `image_too_small` with defaults only: the image is too small for even the smallest icon: tell the user and stop.
   - `labelled_copy`: the file is already a Labelled Copy: label its original instead.
   - `not_found`: find the file the user meant and run again.
   - `usage`: fix the command from its `--help` and run again.
   - Any other code (`unreadable_image`, `write_failed`, `internal`): tell the user what `error.message` says, in plain words, and stop.

## Overrides

The user can override any placement default. Pass their choice through as given:

- **Corner:** `--corner tl|tr|bl|br`, for top-left, top-right, bottom-left or bottom-right.
- **Size:** `--size <px>`, the icon's height in pixels. The minimum is 24 px, and the tool refuses anything smaller. An icon too large to fit inside the image's margins fails with `image_too_small`. For a size given as a share of the image, say "10%", compute the pixels from the image's shorter side.
- **Colour:** `--colour black|white`. An explicit colour gets no automatic plate. Add `--plate` if the user wants one.
- **Plate:** `--plate` forces a backing plate on; `--no-plate` forces it off. A forced plate on an image with no room for one fails with `image_too_small`.

## Defaults

These defaults are this plugin's own choices. The Code of Practice sets no minimum size, colour or margin.

- **Corner:** top-right (`tr`) when it is free, as the Code of Practice suggests, or the corner the user prefers (`score --prefer`).
- **Icon height:** 6% of the image's shorter side, at least 24 px. This is the height of the visible icon, not of the SVG canvas.
- **Margin:** 2% of the shorter side, from the two edges that meet at the corner.
- **Icon Colour:** black or white, whichever has the higher contrast against the area under the icon. Contrast is the WCAG ratio, measured against that area's least favourable pixels rather than its average, and it must reach at least 3:1.
- **Backing plate:** used when neither black nor white reaches 3:1. The plate is an opaque rounded rectangle behind the icon, in the opposite colour: white behind a black icon, black behind a white one. Its padding is 20% of the icon height, shrunk on small images to fit. When even a 2 px padding doesn't fit, the label goes on without a plate and `apply` reports `meets_threshold: false`.
- **Transparent images:** see-through pixels show whatever page the image sits on, so contrast is judged against both a white and a black page, and the worse result counts. A fully transparent corner gets a plate.
