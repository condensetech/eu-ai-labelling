# Labelling a video

Videos get the **Fully AI-Generated** (`generated`) or **Partially AI-Modified** (`modified`) EU Icon incorporated into the picture of a new video file, the **Labelled Copy** `<name>.ai-label.<ext>`, next to the original. The original file is never changed. Only local files are labelled: a URL to download or a live stream is out of scope, and so is audio on its own.

The Label is the official EU Icon on an opaque **backing plate** (white behind a black icon, black behind a white one), at a fixed corner, with the same size and margin defaults as an image (`references/image.md`, **Defaults**), measured on the video as displayed. It stays at that corner, unchanged, and shows either for the whole video (**continuous**) or for a few seconds at a time, at regular intervals (**periodic**): step 3. The corner is chosen from frames of the video and short labelled excerpts (step 4), and never changes during playback.

## Tools

Video work needs FFmpeg's `ffmpeg` and `ffprobe`, installed on the user's machine. The plugin never installs or downloads them, and images, documents and sites never need them.

## What can be labelled

`video-tools` lists the validated labelling `paths`; this version has six. The container is read from the file itself, not its name: a MOV named `.mp4` is labelled as a MOV, and a Matroska file named `.webm` is not a WebM. Each path needs one video stream, of any length, in SDR or, for `mp4-hevc-hdr10`, in HDR10 or, for `mp4-hevc-hlg`, in HLG, with audio and subtitle tracks only in the codecs listed, and no other streams.

- **`mp4-h264-sdr`**: an MP4 file with H.264 video (8-bit 4:2:0, 4:2:2 or 4:4:4), any number of audio tracks (AAC, MP3, ALAC, AC-3, E-AC-3, Opus or FLAC) and of `mov_text` subtitle tracks. A constant or variable frame rate, a start offset and a rotation by 90, 180 or 270 degrees are all kept. Re-encoded as H.264 with libx264, CRF 16.
- **`mov-h264-sdr`**: a MOV (QuickTime) file with H.264 video (8-bit 4:2:0, 4:2:2 or 4:4:4), any number of audio tracks (AAC, MP3, ALAC, AC-3 or 16- or 24-bit PCM) and of `mov_text` subtitle tracks. A constant or variable frame rate, a start offset and a rotation by 90, 180 or 270 degrees are all kept. Re-encoded as H.264 with libx264, CRF 16.
- **`webm-vp9-sdr`**: a WebM file with VP9 video (8-bit 4:2:0), at a constant frame rate, not stored rotated, with no audio or one Opus or Vorbis audio track, and no subtitles. Re-encoded as VP9 with libvpx-vp9, CRF 20.
- **`webm-vp8-sdr`**: a WebM file with VP8 video (8-bit 4:2:0), at a constant frame rate, not stored rotated, with no audio or one Opus or Vorbis audio track, and no subtitles. Re-encoded as VP8 with libvpx, CRF 10.
- **`mp4-hevc-hdr10`**: an MP4 file with HEVC Main 10 video in HDR10 (10-bit 4:2:0, BT.2020 primaries, PQ transfer, BT.2020 non-constant matrix, limited range) carrying mastering display metadata, at a constant frame rate, not stored rotated, with any number of audio tracks (AAC, MP3, ALAC, AC-3, E-AC-3, Opus or FLAC) and of `mov_text` subtitle tracks. Re-encoded as HEVC Main 10 with libx265, CRF 14, keeping its `hvc1` or `hev1` tag.
- **`mp4-hevc-hlg`**: an MP4 file with HEVC Main 10 video in HLG (10-bit 4:2:0, BT.2020 primaries, HLG transfer `arib-std-b67`, BT.2020 non-constant matrix, limited range), with or without static metadata, at a constant frame rate, not stored rotated, with any number of audio tracks (AAC, MP3, ALAC, AC-3, E-AC-3, Opus or FLAC) and of `mov_text` subtitle tracks. Re-encoded as HEVC Main 10 with libx265, CRF 14, keeping its `hvc1` or `hev1` tag.

Only these combinations are validated: another codec inside MOV or WebM (ProRes, AV1, HEVC, ...), another pixel format or another container (Matroska, AVI, ...) is not. A path is usable only when this FFmpeg build has what it needs: `video-tools` reports each path's `available` and `missing` (for example `encoder libvpx-vp9`).

**HDR10.** The copy stays HDR10 and is never converted to SDR: it keeps the 10-bit samples, the colour tags and the PQ transfer, and the Label is composited in 10-bit YUV without converting the video. The Label's white is mapped to SDR reference white in the PQ signal, 203 cd/m2, and its black stays black, so it doesn't glare at the display's peak brightness. The mastering display metadata is the source's. MaxCLL becomes at least 203 cd/m2, and MaxFALL is raised by the most the Label's area at 203 cd/m2 can add; a level the source declares unknown (0) or doesn't declare stays so. The tool checks the produced file's metadata, its decoded 10-bit values outside the Label against the source, and the backing plate's level. It can't check how the copy looks on an HDR display. HDR10+ (its dynamic metadata would be lost), Dolby Vision, HDR10 without mastering display metadata, HDR10 in MOV or with H.264, and a rotated or variable-frame-rate HDR10 video all stop (step 7).

**HLG.** The copy stays HLG and is never converted to SDR or PQ: it keeps the 10-bit samples, the colour tags and the HLG transfer in the stream itself, and the Label is composited in 10-bit YUV without converting the video. The Label's white is mapped to HDR reference white for HLG, 75% of the signal (203 cd/m2 on a 1000 cd/m2 display), and its black stays black. HLG needs no mastering display or content light levels, and the copy gets none the source doesn't declare: no HDR10 metadata is added. A source that declares them keeps its mastering display, and its content light levels are raised for the Label as for HDR10, at the luminance 75% HLG has on the mastering display's peak (203 cd/m2 at 1000 cd/m2, with BT.2100's system gamma for that peak). The tool checks that the copy's transfer is still HLG, its static metadata (exactly the source's), its decoded 10-bit values outside the Label against the source, and the backing plate's level. It can't check how the copy looks on an HDR display. HLG with HDR10+ or Dolby Vision metadata, HLG in MOV or with H.264, HLG with other colour tags, and a rotated or variable-frame-rate HLG video all stop (step 7).

The copy keeps the container, the video codec, the dimensions as stored and as displayed, the rotation, every frame's time, the start offset and duration, the pixel format and colour tags, and the original's file name extension; it is never converted to MP4. Every audio and subtitle track is mapped by name and copied as it is, without re-encoding, in the same order, with its language, title and default, forced or other disposition, and its timing relative to the video. On a rotated video the Label sits at the chosen corner of the picture as displayed, upright. The video stream itself is re-encoded to incorporate the Label: never call the copy lossless or bit-identical.

Anything else stops before rendering, as step 7 says: nothing is converted or dropped silently. That covers another codec, an HDR profile other than HDR10 or HLG on its path, a missing encoder, an audio or subtitle codec the container can't carry unchanged, a data, timecode or attachment stream, a cover image, a mirrored picture or a rotation that isn't a multiple of 90 degrees, and, in WebM, more tracks, rotation or a variable frame rate.

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
3. **Choose when the Label shows.** Unless the user already said, ask whether they want the Label shown **continuously**, for the whole video, or **periodically**, for a few seconds at regular intervals, and say what happens without a preference: videos up to and including 60 seconds show it continuously, longer ones for 5 seconds from the start and then for 5 seconds every 60 seconds. These are this plugin's product defaults, not legal thresholds. A Creative Work video gets the same choice. Map the answer to `--visibility`:
   - no preference: `auto` (the default): continuous up to `--threshold` seconds (default 60), periodic beyond.
   - continuously: `continuous`, whatever the length.
   - periodically: `periodic`, whatever the length. `--window <s>` is how long each appearance lasts (default 5) and `--every <s>` the time from the start of one appearance to the start of the next (default 60); `--window` must be shorter than `--every`.

   Only a window length and a recurrence can be set: a list of chosen moments in the video isn't supported. Done when the visibility is settled.
4. **Preview and choose the corner.** Start from the top-right (`tr`), as the Code of Practice suggests, or the corner the user named. Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-preview <video> --variant <generated|modified> --corner <tl|tr|bl|br> --visibility <auto|continuous|periodic>
   ```

   Add the same `--window`, `--every`, `--threshold`, `--size` and `--colour` you will pass to `video-apply` in step 5. It never changes the original or the Labelled Copy: it writes into its `out` folder, `<video>.label-preview` next to the video unless you add `--out <folder>`, and replaces the samples of an earlier preview there. It prints the settings `video-apply` will use (`variant`, `corner`, `colour`, `plate_box`: where the Label and its plate sit, in pixels of the picture as displayed, `margin` and `visibility`), then:
   - `frames`: source frames, without the Label, spread over the whole video (`--frames <n>`, default 5), each with its `time`, `path` (a PNG) and `status`;
   - `excerpts`: short labelled excerpts, each with its `start` and `end` on the playback timeline, `label_visible` (when the Label shows in it), `path` and `status`. They are rendered as `video-apply` renders the Labelled Copy, with the same Icon Variant, Icon Colour, size, position, backing plate and visibility timing, without audio or subtitles. For continuous display they come from the start, middle and end; for periodic display they cover the first, second and last windows, with the Label appearing and disappearing;
   - `complete` (false when a sample failed), `failed` (how many) and `sampling_note`.

   Open every written frame with your image-viewing tool, and note in each where faces, text, subtitles, logos and the main subject are. Scenes differ: a corner clean in one frame can hold a face or subtitles in another. A corner is **free** when, in every frame, the area of `plate_box`'s size at that corner, with its margin, covers no face, text, subtitle or main subject. The Label stays in one corner for the whole video: never plan to move it between scenes.
   - If the top-right or the user's corner is free, keep it.
   - Otherwise take a free corner, and tell the user why you didn't use the first one.
   - If no corner is free in every frame, **ask the user** which corner to use, and wait. List each corner with what it covers and when, e.g. "top-right: the speaker's face at 12 s; bottom-left: subtitles at 40 s and 75 s".
   - When the corner, the size or the colour changes, run `video-preview` again with it, so that the excerpts show the Label that will be applied.

   For an HDR10 or HLG video, `frame_rendering` is `sdr_tone_mapped` and `hdr_note` says what that means: the frames are SDR renderings, tone-mapped for viewing through the video's own curve (PQ, or HLG's), with reference white near white and highlights compressed. Judge corners on them for content and layout (faces, text, subtitles, subject) and contrast, never for HDR brightness or colour. The excerpts are HDR10 or HLG like the Labelled Copy: an SDR display or your image tools don't show their HDR appearance. Never tell the user that a preview verified how the copy looks in HDR.

   A sample whose `status` is `failed` was not made, and its `error` says why: never call it checked. Tell the user which times have no frame or excerpt, and choose the corner from the frames that were written. A user who said beforehand that they don't need a preview waives this review: skip the frames and use the top-right or their corner. A Creative Work video (artistic, satirical or fictional) gets the same incorporated Label: there is no caption for a video. Done when one corner is settled and the last `video-preview` ran with the settings step 5 will use. On an error, act on `error.code`: `preview_failed` (no frame and no excerpt could be made): tell the user what `error.message` says and that nothing was checked, and ask them which corner to use; any other code: as step 7 says.
5. **Apply the Label.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-apply <video> --variant <generated|modified> --corner <tl|tr|bl|br> --visibility <auto|continuous|periodic>
   ```

   Add `--window <s>`, `--every <s>` or `--threshold <s>` only for the timing the user asked for in step 3; the corner and any `--size` or `--colour` are those of the last preview (step 4). The first appearance starts with the first frame, measured on the playback timeline, and the last one ends with the video when less than a window remains: the video is never extended and no frame is added or moved.

   Add `--size <px>` (the icon's height, at least 24 px) or `--colour black|white` only for a user override; without them the tool takes the default size and the Icon Colour with the better contrast over sampled frames. It renders into a temporary file, checks the result, and only then replaces `<name>.ai-label.<ext>`. It prints `labelled_copy`, the parameters used (`variant`, `corner`, `colour`, `plate_box`, and `visibility`: the `mode` used, the `requested` one, the `threshold` for `auto`, and for periodic display the `window` and `every`), the `path` it took, `video` (what was kept, and the `note` naming the codec and encoder it re-encoded with) and `validation`: the `checks` made on the produced file itself (container, codec, dimensions, orientation, pixel format, colour, frame count and timing, start time, duration, each audio and subtitle track with its language, title and disposition, their sync with the video, that the Label region changed while the rest of the picture didn't, and, for periodic display, that it is unchanged between appearances; for HDR10 and HLG, `hdr_metadata`, `hdr_picture`: the decoded 10-bit values outside the Label against the source, and `label_level`: the backing plate's level in the PQ or HLG signal). For HDR10 and HLG, `video.hdr` gives the `dynamic_range`, the metadata the copy declares and its `note`. Done when the command exits 0 and `labelled_copy` exists. On an error, follow step 7.
6. **Show it for approval.** Give the user the Labelled Copy's path to watch, with the corner, colour, size and visibility used, the `video.note` on re-encoding, and say the checks passed. Say what the previews established and what they didn't: which frame times you looked at and what each corner held, which excerpts the user can watch, any sample that failed, and the `sampling_note`: sampled frames and excerpts can't show that the Label is clear of faces, text, subtitles and the main subject in every frame, so the full Labelled Copy is what they approve. For HDR10 and HLG, add `video.hdr`'s `note`: the checks measured the copy's 10-bit values and metadata, not its appearance, so ask them to watch it on an HDR display and player; on an SDR screen they don't see it as published. Ask them to watch it, then approve it or ask for a change.
   - If they ask for a change to the corner or the size, run step 4 again with it (the tool still refuses a size below 24 px, `size_too_small`, or one that doesn't fit, `image_too_small`), then `video-apply`. For any other change, including to the visibility or its timing, run `video-apply` again with it, after `video-preview` when they want to see excerpts first. It replaces the previous Labelled Copy and still leaves the original untouched. A changed copy needs approval again.
   - A Labelled Copy is **final** once the user approves it, or when they said beforehand that they don't need a preview. A preview waiver skips only the user's review: the tool's checks always run.

   The preview folder (`out` of step 4) is not part of the delivery: tell the user they can delete it. Done when the Labelled Copy is final. For a video inside the project, go on with step 8; for a file on its own, the Labelled Copy is the delivery.
7. **When it can't be labelled as it is**, nothing was written, and the original and any previous Labelled Copy are unchanged. Act on `error.code`:
   - `preservation_unsupported` (or `labelling.supported` false in step 2): the video has characteristics this version can't keep. Tell the user, in plain words, what each entry of `issues` says, that nothing was converted or dropped, and ask how they want to proceed, for example converting the video themselves first. Don't convert anything on your own, and never drop a track, strip a stream or straighten the picture to make it fit: a MOV or WebM is never turned into an MP4, and an HDR video is never turned into SDR. For a `capability_missing` issue, the video is on a validated path but this FFmpeg build lacks what it needs (named in the issue): tell the user, and offer to label it once they install a build that has it.
     By `issues` code:
     - `additional_tracks`: name the streams the message lists (data, timecode, attachment, cover image; in WebM, a second audio track or subtitles), which would be lost.
     - `audio_not_validated`, `subtitles_not_validated`: name the track codecs, which the container can't carry unchanged.
     - `rotation_not_validated`: say the picture is displayed mirrored, turned by an angle other than 90, 180 or 270 degrees, or, in WebM, HDR10 or HLG, rotated at all.
     - `variable_frame_rate_not_validated`: say the WebM's, HDR10 or HLG video's frames are unevenly spaced, and that the timing won't be normalised.
     - `hdr_not_validated`: name the HDR profile the message gives (HDR10+, Dolby Vision, HDR10 or HLG outside MP4 with HEVC, or an unrecognised transfer). For HDR10+ and Dolby Vision, say that labelling would lose their dynamic metadata. Never offer to convert it to SDR, or HLG to PQ, on your own; the user may convert or export it as HDR10 or HLG themselves first.
     - `hdr_metadata_missing`: the HDR10 video declares no mastering display, so the copy's metadata can't be established. Ask the user for a source that carries it; don't invent values.
     - `colour_not_validated`: name the colour tags the message lists; the tool won't convert primaries, matrix or range.
     - Any other code: say what its message says.
   - `render_failed`, `output_validation_failed`, `frame_extraction_failed`, `preview_failed`, `write_failed`: tell the user what `error.message` says; the original and any previous Labelled Copy are unchanged.
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

Add to the report of `SKILL.md` step 5: the Labelled Copy's path, its Icon Variant, corner and `visibility`, what the copy kept (`video`), and that the video stream was re-encoded to incorporate the Label. For HDR10 and HLG, say which checks measured the HDR (`hdr_metadata`, `hdr_picture`, `label_level`), that the frames you looked at were SDR renderings, and that no HDR display was used unless the user watched it on one. Add how the corner was chosen: the frame times you looked at, why that corner, and that sampling can't guarantee the Label is clear in every frame (or that the user waived the preview). After step 8, add **References updated** (each `applied` file and line, old path and new) and **References not updated** (each `needs_hand_edit` and `not_updatable` entry you didn't fix, with its file, line and reason in plain words). Say that only files in the project changed: a published site, a CMS or a copy uploaded elsewhere still shows the original until the user replaces it there.
