# Labelling a video

Videos get the **Fully AI-Generated** (`generated`) or **Partially AI-Modified** (`modified`) EU Icon incorporated into the picture of a new video file, the **Labelled Copy** `<name>.ai-label.<ext>`, next to the original. The original file stays unchanged. Only local video files are labelled: URLs, live streams and audio on its own are out of scope.

The Label is the official EU Icon on an opaque **backing plate** (white behind a black icon, black behind a white one), at a fixed corner, with the same size and margin defaults as an image (`references/image.md`, **Defaults**), measured on the video as displayed. It stays at that corner, unchanged, and shows either for the whole video (**continuous**) or for a few seconds at a time, at regular intervals (**periodic**): step 3. The corner is chosen from frames of the video and short labelled excerpts (step 4), and holds for the whole playback.

## Tools

Video work uses the user's own installation of FFmpeg's `ffmpeg` and `ffprobe` (step 1). Images, documents and sites work without them.

## What can be labelled

The container is read from the file itself, not its name: a MOV named `.mp4` is labelled as a MOV, and a Matroska file named `.webm` is not a WebM. A video of any length, with one video stream, is labelled on one of the validated paths `video-tools` lists:

- **`mp4-h264-sdr`** and **`mov-h264-sdr`**: MP4 or MOV with 8-bit H.264 in SDR. They keep any number of audio tracks and `mov_text` subtitle tracks, a constant or variable frame rate, a start offset and a rotation by 90, 180 or 270 degrees.
- **`webm-vp9-sdr`** and **`webm-vp8-sdr`**: WebM with 8-bit VP9 or VP8 in SDR, stored upright, at a constant frame rate, with at most one Opus or Vorbis audio track.
- **`mp4-hevc-hdr10`** and **`mp4-hevc-hlg`**: MP4 with 10-bit HEVC in HDR10 or HLG, stored upright, at a constant frame rate, with any number of audio tracks and `mov_text` subtitle tracks.

Only these combinations are validated: another codec inside MOV or WebM (ProRes, AV1, HEVC, ...), another pixel format, colour or audio codec, or another container (Matroska, AVI, ...) stops at step 7, with the reason in `video-inspect`'s `labelling.issues`. `video-tools` reports whether this FFmpeg build has what each path needs (`available`, `missing`).

**HDR10 and HLG.** The copy keeps its HDR profile and is never converted to SDR, nor HLG to PQ: the 10-bit samples, colour tags and transfer stay, and the Label is composited in 10-bit YUV. The Label's black stays black and its white sits at reference white (ITU-R BT.2408), clear of the display's peak brightness: 203 cd/m2 in PQ for HDR10, 75% of the signal for HLG (203 cd/m2 on a 1000 cd/m2 display). The mastering display metadata is the source's: HDR10 needs it, HLG declares only what its source declares. Where the source declares content light levels, MaxCLL becomes at least the Label's white and MaxFALL rises by the most the Label's area can add; an unknown (0) or undeclared level stays so. The tool measures the copy's metadata, its decoded 10-bit values outside the Label and the backing plate's level; how it looks on an HDR display stays unverified. HDR10+ and Dolby Vision (their dynamic metadata would be lost), either profile in MOV or with H.264, and a rotated or variable-frame-rate HDR video stop at step 7.

The copy keeps the container, the video codec, the dimensions as stored and as displayed, the rotation, every frame's time, the start offset and duration, the pixel format and colour tags, and the original's file name extension; it is never converted to MP4. Every audio and subtitle track is copied as it is, without re-encoding, in the same order, with its language, title and default, forced or other disposition, and its timing relative to the video. On a rotated video the Label sits upright at the chosen corner of the picture as displayed. The video stream itself is re-encoded to incorporate the Label: never call the copy lossless or bit-identical.

Anything else stops before rendering, as step 7 says, with nothing converted or dropped.

## Steps

1. **Check the tools.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-tools
   ```

   It prints `ready`, each tool's `status` (`available`, `missing`, or `unusable`: found, but it doesn't run) and, when `ready` is false, `install`: the `steps` for the user's `platform` and what to do `after`. Give the user those steps as written, ask them to install the tools, and wait. When they say they are done, run `video-tools` again. Never run an install command yourself: installing is the user's. Done when `ready` is true.

   When `ready` is true it also lists `capabilities` (what this FFmpeg build has) and `paths` (the validated labelling paths, each `available` or with what is `missing`). Whether a given video can be labelled comes from step 2's `labelling` alone, never from a listed codec.
2. **Inspect the video.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-inspect <video>
   ```

   It only reads the file, and prints its `container`, `video` (codec, dimensions, `rotation`, frame rate, `pix_fmt`, `colour` with its `dynamic_range`), `audio`, `subtitles`, `other_streams`, and `labelling`: whether it can be labelled (`supported`), on which `path`, and the `issues` in the way. Done when the command exits 0. If `supported` is false, go to step 7 with those `issues`. On an error, act on `error.code`:
   - `video_tools_missing`: go back to step 1.
   - `unreadable_video`: the file isn't a video ffprobe can read: tell the user what `error.message` says and stop.
   - `not_found`: find the file the user meant and run again.
3. **Choose when the Label shows.** Unless the user already said, ask whether they want the Label shown **continuously**, for the whole video, or **periodically**, for a few seconds at regular intervals, and say what happens without a preference: videos up to and including 60 seconds show it continuously, longer ones for 5 seconds from the start and then for 5 seconds every 60 seconds. Wait for the answer before previewing or labelling: a default the user hasn't chosen is not a preference. These are this plugin's product defaults, not legal thresholds. A Creative Work video gets the same choice. Map the answer to `--visibility`:
   - no preference: `auto` (the default): continuous up to `--threshold` seconds (default 60), periodic beyond.
   - continuously: `continuous`, whatever the length.
   - periodically: `periodic`, whatever the length. `--window <s>` is how long each appearance lasts (default 5) and `--every <s>` the time from the start of one appearance to the start of the next (default 60); `--window` must be shorter than `--every`.

   Only a window length and a recurrence can be set, with the first appearance at the start. Done when the visibility is settled.
4. **Preview and choose the corner.** Start from the top-right (`tr`), as the Code of Practice suggests, or the corner the user named. Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-preview <video> --variant <generated|modified> --corner <tl|tr|bl|br> --visibility <auto|continuous|periodic>
   ```

   Add the same `--window`, `--every`, `--threshold`, `--size` and `--colour` you will pass to `video-apply` in step 5. It writes only into its `out` folder (`<video>.label-preview` next to the video, or `--out <folder>`), replacing an earlier preview's samples there. It prints the settings `video-apply` will use (`variant`, `corner`, `colour`, `plate_box`: where the Label and its plate sit on the picture as displayed, `margin`, `visibility`), then:
   - `frames`: source frames, without the Label, spread over the whole video (`--frames <n>`, default 5), each with its `time`, `path` (a PNG) and `status`;
   - `excerpts`: short excerpts rendered exactly as `video-apply` renders the Labelled Copy, without audio or subtitles, each with its `start`, `end`, `label_visible` (when the Label shows in it), `path` and `status`;
   - `complete` (false when a sample failed), `failed` (how many) and `sampling_note`.

   Open every written frame with your image-viewing tool, and note in each where faces, text, subtitles, logos and the main subject are. A corner clean in one scene can hold a face or subtitles in another. A corner is **free** when, in every frame, the area of `plate_box`'s size at that corner, with its margin, is clear of faces, text, subtitles and the main subject. The Label stays in one corner for the whole video.
   - If the top-right or the user's corner is free, keep it.
   - Otherwise take a free corner, and tell the user why you moved from the first one.
   - If no corner is free in every frame, **ask the user** which corner to use, and wait. List each corner with what it covers and when, e.g. "top-right: the speaker's face at 12 s; bottom-left: subtitles at 40 s and 75 s".
   - When the corner, the size or the colour changes, run `video-preview` again with it, so that the excerpts show the Label that will be applied.

   For an HDR10 or HLG video, `frame_rendering` is `sdr_tone_mapped` and `hdr_note` says what that means: the frames are SDR renderings, tone-mapped through the video's own curve. Judge corners on them for content, layout and contrast only. The excerpts are HDR like the Labelled Copy, so an SDR display shows neither their HDR appearance nor the copy's: say so to the user.

   A sample whose `status` is `failed` was not made, and its `error` says why: count it as unchecked, never call it checked, tell the user which times have no frame or excerpt, and choose from the frames that were written. A user who said beforehand that they don't need a preview waives this review: use the top-right or their corner. A Creative Work video (artistic, satirical or fictional) gets the same incorporated Label, with no caption. Done when one corner is settled and the last `video-preview` ran with the settings step 5 will use. On an error, act on `error.code`: `preview_failed` (no frame and no excerpt could be made): tell the user what `error.message` says and that nothing was checked, and ask them which corner to use; any other code: as step 7 says.
5. **Apply the Label.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py video-apply <video> --variant <generated|modified> --corner <tl|tr|bl|br> --visibility <auto|continuous|periodic>
   ```

   Add `--window <s>`, `--every <s>` or `--threshold <s>` only for the timing the user asked for in step 3; the corner and any `--size` (the icon's height, at least 24 px) or `--colour black|white` are those of the last preview (step 4). Without them the tool takes the default size and the Icon Colour with the better contrast over sampled frames.

   It renders into a temporary file, checks the result, and only then replaces `<name>.ai-label.<ext>`. It prints `labelled_copy`, the parameters used (`variant`, `corner`, `colour`, `plate_box`, `visibility`), the `path` it took, `video` (what was kept, and the `note` naming the codec and encoder it re-encoded with) and `validation`: the `checks` made on the produced file itself. For HDR10 and HLG these include `hdr_metadata`, `hdr_picture` (the decoded 10-bit values outside the Label against the source) and `label_level` (the backing plate's level), and `video.hdr` gives the `dynamic_range`, the metadata the copy declares and its `note`. Done when the command exits 0 and `labelled_copy` exists. On an error, follow step 7.
6. **Show it for approval.** Give the user the Labelled Copy's path to watch, with the corner, colour, size and visibility used, the `video.note` on re-encoding, and say the checks passed. Say what the previews established: which frame times you looked at and what each corner held, which excerpts they can watch, any sample that failed, and the `sampling_note`: sampled frames and excerpts can't show that the Label is clear of faces, text, subtitles and the main subject in every frame, so the full Labelled Copy is what they approve. For HDR10 and HLG, add `video.hdr`'s `note`: the checks measured the copy's 10-bit values and metadata, not its appearance, so ask them to watch it on an HDR display and player. Ask them to watch it, then approve it or ask for a change.
   - If they ask for a change to the corner or the size, run step 4 again with it (the tool still refuses a size below 24 px, `size_too_small`, or one that doesn't fit, `image_too_small`), then `video-apply`. For any other change, including to the visibility or its timing, run `video-apply` again with it, after `video-preview` when they want to see excerpts first. It replaces the previous Labelled Copy and leaves the original as it is. A changed copy needs approval again.
   - A Labelled Copy is **final** once the user approves it, or when they said beforehand that they don't need a preview. A preview waiver skips only the user's review: the tool's checks always run.

   Tell the user they can delete the preview folder (`out` of step 4): it is not part of the delivery. Done when the Labelled Copy is final. For a video inside the project, go on with step 8; for a file on its own, the Labelled Copy is the delivery.
7. **When it can't be labelled as it is**, nothing was written, and the original and any previous Labelled Copy are unchanged. Act on `error.code`:
   - `preservation_unsupported` (or `labelling.supported` false in step 2): the video has characteristics this version can't keep. Tell the user, in plain words, what each entry of `issues` says, that nothing was converted or dropped, and ask how they want to proceed, for example converting the video themselves first. Conversion is the user's decision: the copy keeps every track, stream and the picture as they are, a MOV or WebM stays a MOV or WebM, and an HDR video is never turned into SDR. By `issues` code:
     - `additional_tracks`: name the streams the message lists (data, timecode, attachment, cover image; in WebM, a second audio track or subtitles), which would be lost.
     - `audio_not_validated`, `subtitles_not_validated`: name the track codecs, which the container can't carry unchanged.
     - `rotation_not_validated`: say the picture is displayed mirrored, turned by an angle other than 90, 180 or 270 degrees, or rotated at all in WebM, HDR10 or HLG.
     - `variable_frame_rate_not_validated`: say the WebM's, HDR10 or HLG video's frames are unevenly spaced, and that the timing stays as it is.
     - `hdr_not_validated`: name the HDR profile the message gives (HDR10+, Dolby Vision, HDR10 or HLG outside MP4 with HEVC, or an unrecognised transfer). For HDR10+ and Dolby Vision, say that labelling would lose their dynamic metadata. Converting to SDR, or HLG to PQ, is the user's choice to make themselves first, never yours.
     - `hdr_metadata_missing`: the HDR video's mastering display is missing or unreadable, so the copy's metadata can't be established. Ask the user for a source that carries it; the copy takes only the source's values.
     - `colour_not_validated`: name the colour tags the message lists; the tool keeps primaries, matrix and range as they are.
     - `capability_missing`: the video is on a validated path, but this FFmpeg build lacks what it needs (named in the issue): tell the user, and offer to label it once they install a build that has it.
     - Any other code: say what its message says.
   - `render_failed`, `output_validation_failed`, `frame_extraction_failed`, `preview_failed`, `write_failed`: tell the user what `error.message` says; the original and any previous Labelled Copy are unchanged.
   - `image_too_small`, `size_too_small`: the Label doesn't fit at that size: ask for another size, or stop when it was the default.
   - `labelled_copy`: the file is already a Labelled Copy: label its original instead.
   - `video_tools_missing`: go back to step 1.
   - `usage`: fix the command and run again. For a timing setting `error.message` rejects (a window, recurrence or threshold that isn't a positive number of seconds, or a window not shorter than the recurrence), ask the user for another.
   - `not_found`: fix the command and run again.
8. **Point the project's players to it.** Only a final Labelled Copy (step 6) replaces references, and only one that `video-apply` just produced and the user approved: after a change, approve the new copy first. A video that failed, was refused or skipped, or is still waiting for approval, keeps every reference on the original; in a batch, run this step for each final copy only. Skip it when the user said to leave their pages alone, or the video is outside the project. The project root is chosen as `references/update-references.md` says. Run:

   ```
   uv run <skill folder>/scripts/label_tool.py references <video> --root <project root> --apply
   ```

   `<video>` is the original. It searches the project's files as for an image, and changes only the literal `src` of a `<video>` and of a `<source>` inside a `<video>`, in place, to the Labelled Copy's file name. It never writes alt text, a caption, a transcript or any disclosure around the player: the incorporated Label is the disclosure. Every other attribute (`<track>`, `poster`, `controls`, ...) stays as it is. It prints `media: "video"`, then:
   - `updatable`: each use of the original, with its `file`, `line`, `reference`, `replacement` and `kind`: `html-video` (a `<video src>`), `html-video-source` (a `<source src>` inside a `<video>`), `link` (an `<a href>` or Markdown link, which keeps pointing to the original) or `other`;
   - `applied`: each `html-video` and `html-video-source` now pointing to the Labelled Copy;
   - `needs_hand_edit`: each `other` use, unchanged (an import, a framework component such as `<Video src>`, a `poster` or `data-` attribute, a data field): read it, and if it plays the video, change its path to its `replacement` by hand;
   - `not_updatable`, unchanged, with its `reason`: `dynamic` (a path built at run or build time), `external` (a URL on another host), `unresolved` (it leads to no file in the project) or `not_a_player` (an `<img>`, a `<source>` inside a `<picture>` or an `<audio>`, or a Markdown image: no video player shows it there, so leave it).

   Done when the command exits 0. On `usage`, drop `--wording`, `--alt-mention` and `--lang`: a video takes none. On `no_labelled_copy`, finish steps 5 and 6 first; on `labelled_copy`, pass its original; on `not_found`, find the video the user meant; on `outside_project`, check `--root`. On `overlapping_edits`, no page changed: edit the page named by hand.

## Report

Add to the report of `SKILL.md` step 5: the Labelled Copy's path, its Icon Variant, corner and `visibility`, what the copy kept (`video`), and that the video stream was re-encoded to incorporate the Label. For HDR10 and HLG, say which checks measured the HDR (`hdr_metadata`, `hdr_picture`, `label_level`), that the frames you looked at were SDR renderings, and whether the user watched it on an HDR display. Add how the corner was chosen: the frame times you looked at, why that corner, and that sampling can't guarantee the Label is clear in every frame (or that the user waived the preview). After step 8, add **References updated** (each `applied` file and line, old path and new) and **References not updated** (each `needs_hand_edit` and `not_updatable` entry you didn't fix, with its file, line and reason in plain words). Say that only files in the project changed: a published site, a CMS or a copy uploaded elsewhere still shows the original until the user replaces it there.
