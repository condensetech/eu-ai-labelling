# 03: Choose continuous or periodic Label visibility

**What to build:** A user chooses when the Label is visible and receives a video whose timing follows that choice, with predictable defaults for short and long videos.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** resolved

- [x] Ask for the visibility preference unless already provided, offering continuous or periodic display. When the user has no preference, use continuous display for videos up to and including 60 seconds and periodic display for longer videos.
- [x] The periodic default displays the Label for 5 seconds from the start and then for 5 seconds starting every 60 seconds. Measure recurrence between the starts of the windows, and truncate the last window at the end of the video.
- [x] Allow the agreed timing defaults and periodic duration/frequency to be configured, validate invalid settings before rendering, and report the effective settings. Do not add arbitrary lists of manually selected timeline intervals.
- [x] Derive timing from the playback timeline rather than assuming a frame count or letting a non-zero source timestamp shift the first appearance. Apply the Label and backing plate together without extending the video, shifting audio or inserting extra frames.
- [x] Honour explicit continuous display for a long video and explicit periodic display for a short video. Preserve the same position and appearance at each recurrence and the existing preview/approval rules after a timing change.
- [x] Verify videos below, exactly at and just above the 60-second threshold; frames immediately before and after display-window boundaries; customised timing; and a final window shorter than 5 seconds. Include checks of decoded output, not just the generated processing arguments.
- [x] Explain the defaults as product settings, not legal thresholds, and update the video instructions and relevant workflow evaluations with the demonstrated behaviour.

## Comments

`video-apply` takes `--visibility auto|continuous|periodic` (default `auto`), `--window` (5 s), `--every` (60 s, start to start) and `--threshold` (60 s: `auto` is continuous up to and including it). Only the settings the mode uses are validated, before rendering: positive, finite seconds and `window` < `every`, else `usage`. The result's `visibility` reports `requested`, `mode`, `threshold` (for `auto`) and `window`/`every` (for periodic). Periodic display is the overlay's `enable='lt(mod(t-START+1e-4,EVERY),WINDOW)'`, rendered with `-copyts`: without it ffmpeg rebased an offset source (start 2.5 s) to 0 and lost the audio's lead over the video, failing `audio_sync`. With it the offset and frame times are kept and the windows are measured from the first frame. The last window ends with the video; nothing is extended or inserted. `too_long` and `MAX_CONTINUOUS_S` are gone. `validate_output` also decodes a frame in the first hidden gap (`label_hidden`), kept at least a frame before the end.

Tests (tests/unit/test_video_visibility.py) decode every frame of 160x90, 10 fps videos: 59.5, 60 and 60.5 s defaults, frames either side of each window boundary, custom window/recurrence, explicit continuous on 61 s and periodic on 8 s, a configured threshold, a last window cut to one frame, the 2.5 s offset with audio, invalid settings, and a simulated ffmpeg that drops the timing (caught by `label_hidden`). references/video.md gains step 4 (ask for the visibility preference; defaults stated as product settings, not legal thresholds); steps 4-6 became 5-7. Left out: no video workflow eval exists yet (ticket 02 deferred them to the final eval commit), and auto Icon Colour still samples frames over the whole video, not only inside the windows.
