# Labelling a video

Videos get the **Fully AI-Generated** (`generated`) or **Partially AI-Modified** (`modified`) EU Icon incorporated into the picture of a new video file, the **Labelled Copy** `<name>.ai-label.<ext>`, next to the original. The original file is never changed. Only local files are labelled: a URL to download or a live stream is out of scope, and so is audio on its own.

The Label is the official EU Icon on an opaque **backing plate** (white behind a black icon, black behind a white one), at a fixed corner, with the same size and margin defaults as an image (`references/image.md`, **Defaults**), measured on the video as displayed. It stays at that corner, unchanged, for the whole video.

## Tools

Video work needs FFmpeg's `ffmpeg` and `ffprobe`, installed on the user's machine. The plugin never installs or downloads them, and images, documents and sites never need them.

## What can be labelled

`video-tools` lists the validated labelling `paths`; this version has one:

- **`mp4-h264-sdr`**: an MP4 file with one H.264 video stream in SDR (8-bit 4:2:0, 4:2:2 or 4:4:4), at a constant frame rate, not stored rotated, up to 60 seconds long, with no audio or one audio track (AAC, MP3, ALAC, AC-3, E-AC-3, Opus or FLAC), and no other tracks.

The copy keeps the container, the video codec, the dimensions, the frame timing and duration, the pixel format and colour tags; the audio track is copied as it is, without re-encoding. The video stream itself is re-encoded (H.264, CRF 16) to incorporate the Label: never call the copy lossless or bit-identical. Anything else (another codec, HDR, more tracks, rotation, a variable frame rate, a longer video) stops before rendering, as step 6 says: nothing is converted or dropped silently.

## Steps

1. **Check the tools.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-tools
   ```

   It prints `ready`, each tool's `status` (`available`, `missing`, or `unusable`: found, but it doesn't run) and, when `ready` is false, `install`: the `steps` for the user's `platform` and what to do `after`. Give the user those steps as written, ask them to install the tools, and wait. When they say they are done, run `video-tools` again. Never run an install command yourself. Done when `ready` is true.

   When `ready` is true it also lists `capabilities`, the decoders, encoders, filters, pixel formats and muxers this FFmpeg build has, and `paths`, the validated labelling paths with whether this build has what each needs (`available`, `missing`). A capability is not a validated labelling path: never tell the user a video can be labelled because its codec is listed.
2. **Inspect the video.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-inspect <video>
   ```

   It only reads the file, and prints its `container`, `video` (codec, dimensions as stored and as displayed, `rotation`, frame rate and whether it is constant, `pix_fmt`, `bit_depth` and `colour`, with its `dynamic_range`: `sdr`, `hdr10`, `hlg`, or another HDR profile), its `audio`, `subtitles` and `other_streams`, and `labelling`: whether it can be labelled (`supported`), on which `path`, and the `issues` in the way. Done when the command exits 0. If `supported` is false, go to step 6 with those `issues`. On an error, act on `error.code`:
   - `video_tools_missing`: go back to step 1.
   - `unreadable_video`: the file isn't a video ffprobe can read: tell the user what `error.message` says and stop.
   - `not_found`: find the file the user meant and run again.
3. **Choose the corner.** Use the top-right (`tr`), as the Code of Practice suggests, unless the user named another corner. A Creative Work video (artistic, satirical or fictional) gets the same incorporated Label: there is no caption for a video; ask the user which corner they want only when they said they care where it goes. Done when the corner is settled.
4. **Apply the Label.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-apply <video> --variant <generated|modified> --corner <tl|tr|bl|br>
   ```

   Add `--size <px>` (the icon's height, at least 24 px) or `--colour black|white` only for a user override; without them the tool takes the default size and the Icon Colour with the better contrast over sampled frames. It renders into a temporary file, checks the result, and only then replaces `<name>.ai-label.<ext>`. It prints `labelled_copy`, the parameters used (`variant`, `corner`, `colour`, `plate_box`), `video` (what was kept, and the `note` on re-encoding) and `validation`: the `checks` made on the produced file itself (container, codec, dimensions, pixel format, colour, frame count and timing, duration, audio and subtitle tracks, audio sync, and that the Label region changed while the rest of the picture didn't). Done when the command exits 0 and `labelled_copy` exists. On an error, follow step 6.
5. **Show it for approval.** Give the user the Labelled Copy's path to watch, with the corner, colour and size used, the `video.note` on re-encoding, and say the checks passed. Ask them to approve it or ask for a change.
   - If they ask for a change, run `video-apply` again with it. It replaces the previous Labelled Copy and still leaves the original untouched. A changed copy needs approval again.
   - A Labelled Copy is **final** once the user approves it, or when they said beforehand that they don't need a preview. A preview waiver skips only the user's review: the tool's checks always run.

   Done when the Labelled Copy is final. Don't run `references` or any alt-text update for a video: those are for images.
6. **When it can't be labelled as it is**, nothing was written, and the original and any previous Labelled Copy are unchanged. Act on `error.code`:
   - `preservation_unsupported` (or `labelling.supported` false in step 2): the video has characteristics this version can't keep. Tell the user, in plain words, what each entry of `issues` says, that nothing was converted or dropped, and ask how they want to proceed, for example converting the video themselves first. Don't convert anything on your own. An HDR video is never turned into SDR.
   - `render_failed`, `output_validation_failed`, `frame_extraction_failed`: tell the user what `error.message` says; the original and any previous Labelled Copy are unchanged.
   - `image_too_small`, `size_too_small`: the Label doesn't fit at that size: ask for another size, or stop when it was the default.
   - `labelled_copy`: the file is already a Labelled Copy: label its original instead.
   - `video_tools_missing`: go back to step 1.
   - `not_found`, `usage`: fix the command and run again.

## Report

Add to the report of `SKILL.md` step 5: the Labelled Copy's path, its Icon Variant and corner, what the copy kept (`video`), and that the video stream was re-encoded to incorporate the Label.
