# Labelling a batch of images

Use this when the user asks to label a folder of images or several images in one request. Every image still gets its own **Labelled Copy**, burned in as `references/image.md` describes; this file adds what changes for a batch: one scoring run, one question for every uncertain placement, one preview and one summary. Read `references/image.md` too: its formats, corner rules, overrides and defaults all apply to each image.

By the time you get here, SKILL.md steps 2 and 3 have settled each image's Icon Variant and that it is burned in. Images the user chose not to label, or to label with a caption, are left out here and listed in the summary.

## Steps

1. **Score the burn-in images.** List the images settled for burn-in, by path: never a folder, so an image left out or labelled with a caption can't slip back in. Run once per group of images that share the Icon Variant, the size the user asked for (`--size`, in pixels; none means the default) and the preferred corner (`--prefer`):

   ```
   uv run <skill folder>/scripts/label_tool.py score <images> --variant <generated|modified>
   ```

   `<images>` is the group's image paths, separated by spaces. Add the group's `--prefer <tl|tr|bl|br>` and `--size <px>`, as in step 1 of `references/image.md`; a size given as a share of the image is in pixels per image, so it can split a group. With two or more paths it prints JSON with:
   - `images`: one entry per image, with its `path` and the same fields a single `score` prints (`corners`, `ranking`, `suggested_corner`, `all_busy`, `plate_fits`, ...);
   - `refused`: the files the tool can't label (animated, SVG or another unsupported format, too small, unreadable or missing), each with its `path` and `error` (`code`, `message`);
   - `skipped`: existing Labelled Copies (`*.ai-label.*`, in any letter case), each with its `path` and `reason`. They are never labelled again.

   With a single path it prints that image's own `score` JSON, as in `references/image.md`: count it as that image's entry in `images`, or, on an error, as its refusal (a Labelled Copy is refused with `labelled_copy`: list it under **Skipped**). Done when every listed image is in `images`, `refused` or `skipped`. A refused file does not stop the batch: carry on with the others and list it in the summary.
2. **Look at every image yourself.** Open each one in `images` with your image-viewing or file-reading tool and note where faces, text, logos and the main subject are, as in step 2 of `references/image.md`.
3. **Choose a corner for each image**, by the rules in step 3 of `references/image.md`. Placement is judged per image: never reuse one image's corner for another.
   - An image with a free corner gets it, starting from its `suggested_corner`.
   - An image with **no free corner** is uncertain. Don't ask about it yet: collect it.
   - A corner the user chose, for the batch or for one image, settles that image's corner. A size or colour choice settles only that parameter.

   Done when each image either has a corner or is in the uncertain list.
4. **Apply the label** to each image that has a corner, with the apply command from step 4 of `references/image.md`, one run per image. If `apply` fails for one image, note its `error.message`, list that image as refused and go on with the rest.
5. **Ask about every uncertain placement in one question.** If the uncertain list is not empty, ask a single question covering all of those images together, in the same message as the preview of step 6 when some Labelled Copies are already written, and wait for the answer. Name each image with a short note per corner, e.g. "busy-street.png: top-left covers a face, bottom-right covers a shop sign; crowd.png: every corner busy". Accept one answer per image or one for all ("bottom-left for all of them"). Then apply those images as in step 4 and preview them as in step 6.
6. **Show one preview for the batch.** Open each Labelled Copy and check it as in step 5 of `references/image.md`. Then show the user all of them together: each Labelled Copy's path, corner, colour, size and whether a plate was drawn, flagging any whose `meets_threshold` is false. Ask the user to approve them or ask for changes to specific images; re-run `apply` only for those, and preview the new copies again.

   Done when every burn-in image has a final Labelled Copy (step 5 of `references/image.md` says when a copy is final), was switched to a caption, is refused, or the user chose to leave it unlabelled.
7. **Update references.** For each Labelled Copy of an image inside the project, follow `references/update-references.md`: run `references` once per original, point what it finds to the copy, and update the alt text. Done when every Labelled Copy has been through it.
8. **Report the batch.** End with a summary that lists:
   - **Labelled:** each Labelled Copy's path, its Icon Variant (Fully AI-Generated or Partially AI-Modified) and its corner (top-left, top-right, bottom-left or bottom-right), one line per image, with colour and plate where they differ from the default. When the whole batch shares one Icon Variant, it may go in the heading of the list instead of on each line;
   - **Refused:** each refused file and the reason, in plain words. For `animated_image`, `svg_image` and `unsupported_format`, give the `error.message` as written, word for word: it is already worded for the user;
   - **Skipped:** each file left without a Label and why: an existing Labelled Copy, or the user chose no Label for it.
   - **Captioned:** each image labelled with a caption, and the document it is in, as `references/creative-work.md` reports it.
   - **References:** the references updated and those not updated, across the batch, as `references/update-references.md` asks.

   Leave out a heading that has nothing under it.
