# 03: Choose continuous or periodic Label visibility

**What to build:** A user chooses when the Label is visible and receives a video whose timing follows that choice, with predictable defaults for short and long videos.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** ready-for-agent

- [ ] Ask for the visibility preference unless already provided, offering continuous or periodic display. When the user has no preference, use continuous display for videos up to and including 60 seconds and periodic display for longer videos.
- [ ] The periodic default displays the Label for 5 seconds from the start and then for 5 seconds starting every 60 seconds. Measure recurrence between the starts of the windows, and truncate the last window at the end of the video.
- [ ] Allow the agreed timing defaults and periodic duration/frequency to be configured, validate invalid settings before rendering, and report the effective settings. Do not add arbitrary lists of manually selected timeline intervals.
- [ ] Derive timing from the playback timeline rather than assuming a frame count or letting a non-zero source timestamp shift the first appearance. Apply the Label and backing plate together without extending the video, shifting audio or inserting extra frames.
- [ ] Honour explicit continuous display for a long video and explicit periodic display for a short video. Preserve the same position and appearance at each recurrence and the existing preview/approval rules after a timing change.
- [ ] Verify videos below, exactly at and just above the 60-second threshold; frames immediately before and after display-window boundaries; customised timing; and a final window shorter than 5 seconds. Include checks of decoded output, not just the generated processing arguments.
- [ ] Explain the defaults as product settings, not legal thresholds, and update the video instructions and relevant workflow evaluations with the demonstrated behaviour.
