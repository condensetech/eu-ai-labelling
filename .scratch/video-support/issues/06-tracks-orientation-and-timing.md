# 06: Preserve tracks, orientation and variable timing

**What to build:** Users can label supported videos with multiple audio tracks, subtitles, rotation or variable frame timing while keeping their playback characteristics. A file that cannot be preserved stops for a user decision instead of losing information silently.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** resolved

- [x] Preserve supported audio and subtitle streams explicitly, including meaningful language, default/forced disposition and synchronisation information. Do not rely on automatic stream selection that could retain only one track.
- [x] Keep displayed orientation and dimensions correct, including rotated source files. Avoid double rotation and ensure that the user-selected Label corner corresponds to the displayed video.
- [x] Preserve variable frame timing, duration, audio/video synchronisation and relevant timestamp offsets. Do not silently normalise a variable-frame-rate source to a fixed rate.
- [x] Identify unsupported streams, relevant metadata or muxing combinations before omitting or converting them. Explain the affected characteristics and ask how to proceed; a missing preservation path must not automatically strip tracks or normalise the file.
- [x] Validate the actual produced stream inventory, meaningful metadata, displayed geometry and timing before replacing a previous Labelled Copy. Failure retains the original and previous valid copy.
- [x] Demonstrate independent fixtures for multiple audio tracks, subtitles, rotation and variable frame timing, plus a combined representative case and a deliberately unsupported preservation case. Assess visible orientation and real synchronisation as well as probe metadata.
- [x] Establish the behaviour with the baseline MP4 path so this ticket does not depend on the MOV/WebM extension. Where additional rendering or visibility paths are already available, verify that they retain the same preservation contract.
- [x] Update user instructions and workflow evaluations to distinguish supported preservation from cases that require an explicit decision. Preserve the existing image workflows.

## Comments

Built on `mp4-h264-sdr` (tests/unit/test_video_preservation.py, tests/docs/test_video_reference.py):

- **Tracks:** every audio and `mov_text` subtitle track is mapped by index. Each gets explicit `-map_metadata:s:N`, `-disposition:N` with all of its flags, and `title=`; MP4 reads a title back as `name`, and the muxer would otherwise drop it. Tested: packet MD5s, language, title, disposition, cue times and sync per track.
- **Rotation:** I kept the stored pixels and the display matrix. The source is decoded with `-noautorotate`. The Label, laid out on the displayed picture, is turned back (`transpose`/`hflip,vflip`) and placed at the stored coordinates of the chosen corner. The display matrix carries through unchanged.
  - The Label's size is padded to even and its position snapped to even, because overlay rounds a subsampled picture's x/y down to even, which rotation turns into a shift the other way.
  - Tested at 90/-90/180 and tr/bl: on the decoded, displayed picture, the Label must be at the corner, match an upright reference, and not match it turned 180 degrees.
  - A mirrored matrix, detected from the determinant, or a rotation that isn't a multiple of 90 still stops (`rotation_not_validated`).
- **Timing:** `-copyts` keeps the start offset. A concatenated 30/10/24 fps fixture with a 0.5 s offset keeps every frame time within 1 ms, plus its duration and audio packet times.
- **Validation:** new `orientation` and `start_time` checks. `frame_timing` now compares absolute times. `audio_sync` became `track_sync`, covering subtitles too. Track checks also compare titles. A real ffmpeg altered to lose a language, a forced flag, the rotation or the offset is caught by these checks: the copy is discarded and the previous one kept.
- **Still stops:** data, timecode or attachment streams and cover images (`additional_tracks`, naming the streams), any track codec MP4 can't carry unchanged (`audio_not_validated`, new `subtitles_not_validated`), and mirrored or odd rotations.
- **Other paths (after rebasing on 03 and 05):**
  - Each labelling path declares what it `preserves` (`tracks`, `rotation`, `variable_timing`), and every path's `needs.filters` lists the filters the render uses.
  - `mov-h264-sdr` preserves all three. The track, subtitle, rotation, VFR and combined tests run on both MP4 and MOV. QuickTime stores no `comment` or `forced` flag, so a MOV source has none to lose.
  - Both WebM paths preserve none of them yet. A second audio track or subtitles (`additional_tracks`), any rotation (`rotation_not_validated`) and VFR (`variable_frame_rate_not_validated`) still stop on WebM, and tests prove it.
  - Ticket 03's `enable` expression already subtracts the start time, so it works with `-copyts`.
- **Not done:**
  - Sync is proved on timestamps and packet identity, not by decoding the audio content.
  - No video workflow evals: ticket 02 deferred headless evals to the final eval commit.
  - WebM tracks, rotation and VFR aren't validated.
