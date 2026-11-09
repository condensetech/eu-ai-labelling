# Labelling a batch of files

Use this when the user asks to label a folder, a glob or several files in one request. Every file still gets its own **Labelled Copy**: an image burned in as `references/image.md` describes, a video as `references/video.md` describes. This file adds what changes for a batch: one listing, one message of questions, one question for every uncertain placement, one review and one summary. Read `references/image.md` too when the batch holds images, and `references/video.md` when it holds videos: their formats, corner rules, overrides and defaults all apply to each file. Images follow **Steps** below; videos follow **Videos in a batch**; a batch holding both runs the two side by side and ends with one review and one report.

By the time you get to **Steps**, SKILL.md steps 2 and 3 have settled each image's Icon Variant and that it is burned in. Images the user chose not to label, to leave as they are for their Existing Label, or to label with a caption, are left out here and listed in the summary.

## Listing a batch

SKILL.md step 1 lists the batch with this command, before any question is asked:

```
uv run <skill folder>/scripts/label_tool.py score <files>
```

`<files>` is what the user named, separated by spaces: a folder, the files a glob matches (expand it yourself), or the files listed. For a folder it takes only the files directly inside it, never its subfolders or hidden files. It writes nothing and prints JSON with:

- `images`: each image, with its `path` and `media: "image"` (and a first scoring, which step 1 of **Steps** redoes with the settled Icon Variant);
- `videos`: each video, by its file extension, with its `path` and `media: "video"`. Nothing is judged about a video here: whether and how it can be labelled is for its own `video-inspect` to say;
- `refused`: the images the tool can't label, with their `error`;
- `skipped`: existing Labelled Copies (`*.ai-label.*`, in any letter case), images and videos, each with its `path`, `media` and `reason`. They are never labelled again.

A folder's other files (documents, notes) are left out. On `no_images` (a folder with no image or video), tell the user and stop. Done when every file named is in one of the four lists, or set aside as not an image or video.

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
2. **Look at every image yourself.** Open each one in `images` with your image-viewing or file-reading tool and note where faces, text, logos and the main subject are, as in step 2 of `references/image.md`. An image's Existing Label is settled by the batch's one message (SKILL.md, **A batch of files**). An image whose Existing Label you first see now is uncertain, with no corner until the user answers, as SKILL.md **An Existing Label** says.
3. **Choose a corner for each image**, by the rules in step 3 of `references/image.md`. Placement is judged per image: never reuse one image's corner for another.
   - An image with a free corner gets it, starting from its `suggested_corner`.
   - An image with **no free corner** is uncertain. Don't ask about it yet: collect it.
   - A corner the user chose, for the batch or for one image, settles that image's corner. A size or colour choice settles only that parameter.

   Done when each image either has a corner or is in the uncertain list.
4. **Apply the label** to each image that has a corner, with the apply command from step 4 of `references/image.md`, one run per image. If `apply` fails for one image, note its `error.message`, list that image as refused and go on with the rest.
5. **Ask about every uncertain placement in one question.** If the uncertain list is not empty, ask a single question covering all of those images together and every uncertain video of the batch (**Videos in a batch**), in the same message as the preview of step 6 when some Labelled Copies are already written, and wait for the answer. Name each image with a short note per corner, e.g. "busy-street.png: top-left covers a face, bottom-right covers a shop sign; crowd.png: every corner busy". A file uncertain for an Existing Label gets the question of SKILL.md **An Existing Label**, files sharing it grouped by name. Accept one answer per file or one for all ("bottom-left for all of them"). Then apply those images the user wants labelled as in step 4 and preview them as in step 6.
6. **Show one preview for the batch.** Open each Labelled Copy and check it as in step 5 of `references/image.md`. Then show the user all of them together, with the batch's video Labelled Copies (**Videos in a batch**): each Labelled Copy's path, corner, colour, size and whether a plate was drawn, flagging any whose `meets_threshold` is false. Ask the user to approve them or ask for changes to specific files; re-run `apply` only for those, and preview the new copies again. An approval covers only the copies it names: a changed copy needs approval again.

   Done when every burn-in image has a final Labelled Copy (step 5 of `references/image.md` says when a copy is final), was switched to a caption, is refused, or the user chose to leave it unlabelled or to keep its Existing Label.
7. **Update references.** For each final Labelled Copy of an image inside the project, follow `references/update-references.md`: run `references` once per original, point what it finds to the copy, and update the alt text. Done when every final image copy has been through it. A video's final copy goes through step 8 of `references/video.md` instead, never this one.
8. **Report the batch.** End with a summary that lists:
   - **Labelled:** each Labelled Copy's path, its Icon Variant (Fully AI-Generated or Partially AI-Modified) and its corner (top-left, top-right, bottom-left or bottom-right), one line per file, with colour and plate where they differ from the default, and the file's Existing Label, where it is and what it says, when it was labelled anyway. For a video add its visibility (continuous, or periodic with its window and recurrence) and that the copy was re-encoded, as `references/video.md` reports it. When the whole batch shares one Icon Variant, it may go in the heading of the list instead of on each line;
   - **Settled by Marking:** each file whose Icon Variant a precise Marking settled, with the Marking that settled it (`settled_by`), each file whose Marking contradicts the user's word, and the files whose Marking agrees with the user's word, in one line, as SKILL.md **A Marking** says. When `apply` or `video-apply` printed a `DigitalSourceType` in `marking_kept`, or `c2pa_left_behind`, for some copies, say once which copies keep what, as SKILL.md **A Marking** words it;
   - **Refused:** each refused file and the reason, in plain words. For `animated_image`, `svg_image` and `unsupported_format`, give the `error.message` as written, word for word: it is already worded for the user. A video that `video-inspect` or `video-apply` stopped with `preservation_unsupported` goes here, with each of its `issues` in plain words;
   - **Failed:** each video whose rendering, validation or preview failed (`render_failed`, `output_validation_failed`, `frame_extraction_failed`, `preview_failed`, `write_failed`, ...), with its `error.message`, and that its original and any previous Labelled Copy are unchanged;
   - **Waiting:** each file whose question the user hasn't answered, or whose copy they haven't approved yet, and what it waits for;
   - **Skipped:** each file left without a Label and why: an existing Labelled Copy, the user chose no Label for it, or "Existing Label kept, no EU Icon added" for a file whose Existing Label the user chose to keep.
   - **Captioned:** each image labelled with a caption, and the document it is in, as `references/creative-work.md` reports it.
   - **References:** the references updated and those not updated, across the batch, as `references/update-references.md` asks.

   Leave out a heading that has nothing under it. When anything is refused, failed or waiting, offer to retry those files once the user has acted on them: a retry runs only the files they name.

## Videos in a batch

Each video of the batch goes through `references/video.md`, steps 1 to 8, on its own; this section says only what the batch changes. Its Icon Variant and visibility come from the batch's one message of questions (SKILL.md, **A batch of files**): don't ask the visibility question of step 3 of `references/video.md` again for it, nor ask about its corner on its own in step 4 (step 3 below gathers it); it never has a caption to choose, Creative Work or not: a Creative Work video keeps its Label incorporated in the picture, with no caption.

1. **Check the tools once.** Run `video-tools` (step 1 of `references/video.md`) once for the batch, before the first video. When `ready` is false, the images go on; the videos wait for the tools and are listed under **Waiting**. Done when `ready` is true, or the videos are waiting.
2. **Inspect each video.** Run `video-inspect` on each one. Whether a video can be labelled, and on which path, comes from its own inspection, never from its extension, a format list or another video of the batch. A video with `supported` false, or whose `video-apply` stops with `preservation_unsupported`, is refused: note its `issues` and go on. It does not stop the batch. The listing's `media` only says which reference a file follows; it never says the file can be labelled. Done when each video is supported or refused.
3. **Preview each video.** Each video gets its own `video-preview`, with its own Icon Variant and visibility, and its own corner, chosen from its own frames by step 4 of `references/video.md`: never reuse one video's corner for another. A video with no free corner is uncertain: collect it into the one placement question of step 5 of **Steps**, with the uncertain images, instead of asking about it alone. A `preview_failed` video goes into that question too, saying that nothing was checked. A video whose frames show an Existing Label (step 4 of `references/video.md`, a preview waiver included) is uncertain too, with no corner until the user answers, as SKILL.md **An Existing Label** says. Done when each supported video has a corner, or is in the uncertain list.
4. **Apply each video** with its own `video-apply`, one run per video, as step 5 of `references/video.md` says. A video that fails is listed under **Failed** or **Refused** with its `error`; the batch goes on with the next. A failure never discards another file's Labelled Copy: each one is written and checked on its own, and the failed video's original and previous Labelled Copy stay as they were. Done when each video with a corner has a Labelled Copy, or is listed as failed or refused.
5. **Review them together.** Show the video Labelled Copies in the review of step 6 of **Steps**, each as step 6 of `references/video.md` says: path, Icon Variant, corner, colour, size and visibility, the re-encoding note, which frames and excerpts were looked at, and the `sampling_note`. Rerender only the files the user names, with `video-preview` and `video-apply` again for each; every other copy stays as it is. A changed copy needs approval again. A preview waiver given for the batch covers every video, never the tool's checks. Done when each video copy is final, or listed under **Waiting**.
6. **Point the project's players to each final copy** with step 8 of `references/video.md`, for each final video copy inside the project only: never for one that failed, was refused or skipped, or is waiting for approval. Done when every final video copy inside the project has been through it.

Done when every video has a final Labelled Copy, or is listed in the report as refused, failed, waiting or skipped.
