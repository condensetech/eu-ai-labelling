# Labelling a video

Videos get the **Fully AI-Generated** (`generated`) or **Partially AI-Modified** (`modified`) EU Icon incorporated into the picture of a new video file, the **Labelled Copy** `<name>.ai-label.<ext>`, next to the original. The original file is never changed. Only local files are labelled: a URL to download or a live stream is out of scope, and so is audio on its own.

The Label is the official EU Icon on an opaque **backing plate** (white behind a black icon, black behind a white one), at a fixed corner, with the same size and margin defaults as an image (`references/image.md`, **Defaults**), measured on the video as displayed. It stays at that corner, unchanged, and shows either for the whole video (**continuous**) or for a few seconds at a time, at regular intervals (**periodic**): step 4.

## Tools

Video work needs FFmpeg's `ffmpeg` and `ffprobe`, installed on the user's machine. The plugin never installs or downloads them, and images, documents and sites never need them.

## What can be labelled

`video-tools` lists the validated labelling `paths`; this version has four. The container is read from the file itself, not its name: a MOV named `.mp4` is labelled as a MOV, and a Matroska file named `.webm` is not a WebM. Each path needs one video stream in SDR, of any length, with audio and subtitle tracks only in the codecs listed, and no other streams.

- **`mp4-h264-sdr`**: an MP4 file with H.264 video (8-bit 4:2:0, 4:2:2 or 4:4:4), any number of audio tracks (AAC, MP3, ALAC, AC-3, E-AC-3, Opus or FLAC) and of `mov_text` subtitle tracks. A constant or variable frame rate, a start offset and a rotation by 90, 180 or 270 degrees are all kept. Re-encoded as H.264 with libx264, CRF 16.
- **`mov-h264-sdr`**: a MOV (QuickTime) file with H.264 video (8-bit 4:2:0, 4:2:2 or 4:4:4), any number of audio tracks (AAC, MP3, ALAC, AC-3 or 16- or 24-bit PCM) and of `mov_text` subtitle tracks. A constant or variable frame rate, a start offset and a rotation by 90, 180 or 270 degrees are all kept. Re-encoded as H.264 with libx264, CRF 16.
- **`webm-vp9-sdr`**: a WebM file with VP9 video (8-bit 4:2:0), at a constant frame rate, not stored rotated, with no audio or one Opus or Vorbis audio track, and no subtitles. Re-encoded as VP9 with libvpx-vp9, CRF 20.
- **`webm-vp8-sdr`**: a WebM file with VP8 video (8-bit 4:2:0), at a constant frame rate, not stored rotated, with no audio or one Opus or Vorbis audio track, and no subtitles. Re-encoded as VP8 with libvpx, CRF 10.

Only these combinations are validated: another codec inside MOV or WebM (ProRes, AV1, HEVC, ...), another pixel format or another container (Matroska, AVI, ...) is not. A path is usable only when this FFmpeg build has what it needs: `video-tools` reports each path's `available` and `missing` (for example `encoder libvpx-vp9`).

The copy keeps the container, the video codec, the dimensions as stored and as displayed, the rotation, every frame's time, the start offset and duration, the pixel format and colour tags, and the original's file name extension; it is never converted to MP4. Every audio and subtitle track is mapped by name and copied as it is, without re-encoding, in the same order, with its language, title and default, forced or other disposition, and its timing relative to the video. On a rotated video the Label sits at the chosen corner of the picture as displayed, upright. The video stream itself is re-encoded to incorporate the Label: never call the copy lossless or bit-identical.

Anything else stops before rendering, as step 7 says: nothing is converted or dropped silently. That covers another codec or HDR, a missing encoder, an audio or subtitle codec the container can't carry unchanged, a data, timecode or attachment stream, a cover image, a mirrored picture or a rotation that isn't a multiple of 90 degrees, and, in WebM, more tracks, rotation or a variable frame rate.

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

   It only reads the file, and prints its `container`, `video` (codec, dimensions as stored and as displayed, `rotation`, frame rate and whether it is constant, `pix_fmt`, `bit_depth` and `colour`, with its `dynamic_range`: `sdr`, `hdr10`, `hlg`, or another HDR profile), its `audio`, `subtitles` and `other_streams`, and `labelling`: whether it can be labelled (`supported`), on which `path`, and the `issues` in the way. Done when the command exits 0. If `supported` is false, go to step 7 with those `issues`. On an error, act on `error.code`:
   - `video_tools_missing`: go back to step 1.
   - `unreadable_video`: the file isn't a video ffprobe can read: tell the user what `error.message` says and stop.
   - `not_found`: find the file the user meant and run again.
3. **Choose the corner.** Use the top-right (`tr`), as the Code of Practice suggests, unless the user named another corner. A Creative Work video (artistic, satirical or fictional) gets the same incorporated Label: there is no caption for a video; ask the user which corner they want only when they said they care where it goes. Done when the corner is settled.
4. **Choose when the Label shows.** Unless the user already said, ask whether they want the Label shown **continuously**, for the whole video, or **periodically**, for a few seconds at regular intervals, and say what happens without a preference: videos up to and including 60 seconds show it continuously, longer ones for 5 seconds from the start and then for 5 seconds every 60 seconds. These are this plugin's product defaults, not legal thresholds. A Creative Work video gets the same choice. Map the answer to `--visibility`:
   - no preference: `auto` (the default): continuous up to `--threshold` seconds (default 60), periodic beyond.
   - continuously: `continuous`, whatever the length.
   - periodically: `periodic`, whatever the length. `--window <s>` is how long each appearance lasts (default 5) and `--every <s>` the time from the start of one appearance to the start of the next (default 60); `--window` must be shorter than `--every`.

   Only a window length and a recurrence can be set: a list of chosen moments in the video isn't supported. Done when the visibility is settled.
5. **Apply the Label.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-apply <video> --variant <generated|modified> --corner <tl|tr|bl|br> --visibility <auto|continuous|periodic>
   ```

   Add `--window <s>`, `--every <s>` or `--threshold <s>` only for the timing the user asked for in step 4. The first appearance starts with the first frame, measured on the playback timeline, and the last one ends with the video when less than a window remains: the video is never extended and no frame is added or moved.

   Add `--size <px>` (the icon's height, at least 24 px) or `--colour black|white` only for a user override; without them the tool takes the default size and the Icon Colour with the better contrast over sampled frames. It renders into a temporary file, checks the result, and only then replaces `<name>.ai-label.<ext>`. It prints `labelled_copy`, the parameters used (`variant`, `corner`, `colour`, `plate_box`, and `visibility`: the `mode` used, the `requested` one, the `threshold` for `auto`, and for periodic display the `window` and `every`), the `path` it took, `video` (what was kept, and the `note` naming the codec and encoder it re-encoded with) and `validation`: the `checks` made on the produced file itself (container, codec, dimensions, orientation, pixel format, colour, frame count and timing, start time, duration, each audio and subtitle track with its language, title and disposition, their sync with the video, that the Label region changed while the rest of the picture didn't, and, for periodic display, that it is unchanged between appearances). Done when the command exits 0 and `labelled_copy` exists. On an error, follow step 7.
6. **Show it for approval.** Give the user the Labelled Copy's path to watch, with the corner, colour, size and visibility used, the `video.note` on re-encoding, and say the checks passed. Ask them to approve it or ask for a change.
   - If they ask for a change, including to the visibility or its timing, run `video-apply` again with it. It replaces the previous Labelled Copy and still leaves the original untouched. A changed copy needs approval again.
   - A Labelled Copy is **final** once the user approves it, or when they said beforehand that they don't need a preview. A preview waiver skips only the user's review: the tool's checks always run.

   Done when the Labelled Copy is final. For a video inside the project, go on with step 8; for a file on its own, the Labelled Copy is the delivery.
7. **When it can't be labelled as it is**, nothing was written, and the original and any previous Labelled Copy are unchanged. Act on `error.code`:
   - `preservation_unsupported` (or `labelling.supported` false in step 2): the video has characteristics this version can't keep. Tell the user, in plain words, what each entry of `issues` says, that nothing was converted or dropped, and ask how they want to proceed, for example converting the video themselves first. Don't convert anything on your own, and never drop a track, strip a stream or straighten the picture to make it fit: a MOV or WebM is never turned into an MP4, and an HDR video is never turned into SDR. For a `capability_missing` issue, the video is on a validated path but this FFmpeg build lacks what it needs (named in the issue): tell the user, and offer to label it once they install a build that has it.
     By `issues` code:
     - `additional_tracks`: name the streams the message lists (data, timecode, attachment, cover image; in WebM, a second audio track or subtitles), which would be lost.
     - `audio_not_validated`, `subtitles_not_validated`: name the track codecs, which the container can't carry unchanged.
     - `rotation_not_validated`: say the picture is displayed mirrored, turned by an angle other than 90, 180 or 270 degrees, or, in WebM, rotated at all.
     - `variable_frame_rate_not_validated`: say the WebM's frames are unevenly spaced, and that the timing won't be normalised.
     - Any other code: say what its message says.
   - `render_failed`, `output_validation_failed`, `frame_extraction_failed`: tell the user what `error.message` says; the original and any previous Labelled Copy are unchanged.
   - `image_too_small`, `size_too_small`: the Label doesn't fit at that size: ask for another size, or stop when it was the default.
   - `labelled_copy`: the file is already a Labelled Copy: label its original instead.
   - `video_tools_missing`: go back to step 1.
   - `usage`: fix the command and run again. For a timing setting `error.message` rejects (a window, recurrence or threshold that isn't a positive number of seconds, or a window not shorter than the recurrence), ask the user for another.
   - `not_found`: fix the command and run again.
8. **Point the project's players to it.** Only a final Labelled Copy (step 6) replaces references, and only one that `video-apply` just produced and the user approved: after a change, approve the new copy first. A video that failed, was refused or skipped, or is still waiting for approval, keeps every reference on the original; in a batch, run this step for each final copy only. Skip it when the user said to leave their pages alone, or the video is not inside the project. The project root is chosen as `references/update-references.md` says. Run:

   ```
   uv run <skill folder>/scripts/label_tool.py references <video> --root <project root> --apply
   ```

   `<video>` is the original. It searches the project's files as for an image, and changes only the literal `src` of a `<video>` and of a `<source>` inside a `<video>`, in place, to the Labelled Copy's file name. It never writes alt text, a caption, a transcript or any disclosure around the player: the incorporated Label is the disclosure. Tracks (`<track>` subtitles and descriptions), `poster`, `controls` and every other attribute stay as they are. It prints `media: "video"`, then:
   - `updatable`: each use of the original, with its `file`, `line`, `reference`, `replacement` and `kind`: `html-video` (a `<video src>`), `html-video-source` (a `<source src>` inside a `<video>`), `link` (an `<a href>` or Markdown link, which keeps pointing to the original) or `other`;
   - `applied`: each `html-video` and `html-video-source` now pointing to the Labelled Copy;
   - `needs_hand_edit`: each `other` use, unchanged (an import, a framework component such as `<Video src>`, a `poster` or `data-` attribute, a data field): read it, and if it plays the video, change its path to its `replacement` by hand;
   - `not_updatable`, unchanged, with its `reason`: `dynamic` (a path built at run or build time), `external` (a URL on another host), `unresolved` (it leads to no file in the project) or `not_a_player` (an `<img>`, a `<source>` inside a `<picture>` or an `<audio>`, or a Markdown image: no video player shows it there, so leave it).

   A second run finds nothing left: uses already pointing to the Labelled Copy are not uses of the original. Done when the command exits 0. On `usage`, drop `--wording`, `--alt-mention` and `--lang`: a video takes none. On `no_labelled_copy`, finish steps 5 and 6 first; on `labelled_copy`, pass its original; on `not_found`, find the video the user meant; on `outside_project`, check `--root`. On `overlapping_edits`, no page changed: edit the page named by hand.

## Report

Add to the report of `SKILL.md` step 5: the Labelled Copy's path, its Icon Variant, corner and `visibility`, what the copy kept (`video`), and that the video stream was re-encoded to incorporate the Label. After step 8, add **References updated** (each `applied` file and line, old path and new) and **References not updated** (each `needs_hand_edit` and `not_updatable` entry you didn't fix, with its file, line and reason in plain words). Say that only files in the project changed: a published site, a CMS or a copy uploaded elsewhere still shows the original until the user replaces it there.
