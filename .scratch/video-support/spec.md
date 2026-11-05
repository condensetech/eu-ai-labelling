# Video support

Design confirmed by the user in Q15 on 2026-11-05. This specification records the agreed outcome of the grill-with-docs interview. Implementation and runtime validation remain to be done.

## Confirmed decisions

- Produce a new video file with the visible Label incorporated into its content. Preserve the original file.
- Accept local video files, individually or in batches. URL downloads and live streams are outside the initial scope.
- Ask the user for their Label visibility preference unless already supplied. The proposed defaults, accepted in Q8, are continuous visibility for videos up to and including 60 seconds, and 5 seconds at the beginning and every 60 seconds thereafter for longer videos. These values are configurable product defaults, not legal thresholds. Each visible period ends at the end of the video if fewer than 5 seconds remain.
- Initial visibility modes are continuous and configurable periodic display. Manually specified lists of timeline intervals are outside the initial scope.
- Use a fixed Label position with a contrast backing plate. Allow the user to change the position; automatic movement during playback is outside the initial scope.
- Prioritise fidelity to the source over normalising every video to one publishing format: preserve dimensions, duration, cadence and audio, and surface necessary conversions or losses. Establish supported processing combinations through implementation validation; apply the stop-and-ask policy below when preservation cannot be established.
- If processing cannot preserve characteristics such as HDR, audio tracks or subtitles, stop that file and ask the user how to proceed. Do not silently discard or convert these characteristics. Video re-encoding to incorporate the Label is inherent to the workflow and must not be represented as lossless preservation.
- For Creative Work videos, retain the incorporated Label and allow the user to choose position and visibility timing. Do not substitute an external caption for the video Label. This does not change the existing caption/burn-in choices for images.
- For videos in a project, extend reference updates to point to the approved Labelled Copy. For standalone files, deliver the Labelled Copy.
- Do not add a separate visible or accessible disclosure around the player by default. The incorporated Label supplies the requested disclosure. Preserve existing descriptions, subtitles and transcripts when updating references; do not treat video descriptions as image alt text.
- Initial container scope is MP4, MOV and WebM, preserving the original container where supported. HDR is not categorically excluded: preserve it through a supported, validated processing path. If preservation cannot be established, stop and ask as required by Q9. Never silently convert HDR to SDR.
- Choose a fixed Label position using representative frames from different scenes and short labelled excerpts, then submit the complete Labelled Copy for final approval. Explain the limits of sampling: it cannot establish that every frame is free of interference.
- Use an existing FFmpeg installation for video processing, with ffprobe for inspection. Do not bundle it or make it a mandatory plugin-installation dependency. Before processing video, check for both executables; if either is missing, ask the user to install the tools, give platform-specific instructions and check again. Do not install automatically. Image-only workflows must remain available without these tools.

## Design approval

The user confirmed the complete design in Q15, including the removal of the blanket SDR-only restriction and the decision not to add a disclosure around the player. No product-design questions remain open from this interview. Build-specific capabilities and preservation claims must still be implemented and verified against the requirements below.

## Implementation requirements derived from the agreed behaviour

- Check for both executables and the required decoders, filters, pixel formats and encoders before processing. File extensions or executable presence alone do not establish support.
- Inspect actual streams and colour characteristics. Keep the source container and codec where supported; seek a user decision when a conversion is necessary. Preserve audio/subtitle tracks, orientation, timing and relevant metadata where supported, and report unsupported cases before a destructive conversion or omission.
- Extend project-reference handling to literal `<video src>` and `<source src>` uses within a video player. Preserve ordinary links and use the existing conservative inspection/reporting approach for framework components, imports and computed references. Do not apply image alt-text updates to video sources.
- Treat capability validation and output validation as separate checks. An available encoder is not proof that the produced file retained the required characteristics.
- Validate HDR10 and HLG paths explicitly, including bit depth, colour primaries, transfer function, matrix/range, relevant metadata and the Label's colour/luminance mapping. Treat HDR10+, Dolby Vision and other profiles according to the actual build and verified end-to-end preservation, not a blanket claim of support or impossibility. If the path is not validated, stop and ask; merely copying metadata does not establish that it remains correct after modifying the video.

## Acceptance criteria to verify during implementation

- The 60-second threshold, 5-second display windows, 60-second recurrence, custom periodic settings and end-of-file truncation match the agreed timing, including frames just before and after visibility boundaries.
- The Label and backing plate remain fixed and legible in sampled scenes; output previews do not overstate the coverage of sampling.
- Source files remain unchanged. Failed processing leaves any previous valid Labelled Copy intact and does not leave a partial copy at the destination.
- Dimension, timing, orientation, audio/subtitle stream and colour checks cover representative supported inputs; unsupported preservation cases stop for a user decision.
- Missing tools produce actionable installation guidance; image workflows still work without FFmpeg. Platform checks include Windows executable lookup.
- Batch failures are isolated, shared questions are grouped, existing Labelled Copies are excluded and only requested files are rerun.
- Reference updates occur only after approval or explicit preview waiver, target video uses correctly, preserve existing descriptions and tracks, and add no extra player disclosure.
- Automated checks are supplemented with visual review of representative video output. Platform-specific checks and HDR rendering must be reported as unverified when the corresponding environment or display is unavailable.

## Existing conventions to retain

These come from the current image and batch workflows and are not new video decisions:

- Ask once for shared batch preferences; group unresolved differences instead of repeating questions for each file. Placement remains specific to each file.
- Continue processing independent files when one fails or needs a decision; report failed, refused and skipped files individually.
- Write `<name>.ai-label.<ext>` beside the original. Exclude Labelled Copies from batch discovery. Re-running with changed parameters replaces the Labelled Copy, not the original; retain the previous valid copy if processing fails and clean partial output.
- Reuse the existing corner preferences and icon size/margin defaults unless the user overrides them, evaluating representative scenes as agreed above.
- Preview the result and obtain final approval, or honour an explicit preview waiver, before updating project references. A changed copy needs approval again. Present one combined batch review and rerun only requested files.
- Preserve unrelated links and content. Resolve references conservatively, report dynamic or unresolved uses and do not claim to have updated external systems.

Evidence: `skills/eu-ai-labelling/SKILL.md`, `references/image.md`, `references/batch.md` and `references/update-references.md` under that skill, plus the atomic-output behaviour in `scripts/label_tool.py`.

## Existing context

- The current skill explicitly excludes video/audio. This feature is intended to change the video boundary once the design is agreed and implemented.
- The current README promises no additional system packages beyond the image-processing prerequisites. A video dependency requires documenting the distinction between image and video setup.
- Glossary: [Labelled Copy](../../GLOSSARY.md) now includes images and videos.

No runtime behaviour has changed. The design is approved; support must not be presented as available until implemented and validated.

## Dependency guidance researched during the interview

FFmpeg is an optional external prerequisite for the video workflow, not an automatically installed plugin dependency. The official [download page](https://ffmpeg.org/download.html) links to third-party Windows builds, including Gyan.

On Windows, first check both commands in the environment running the skill:

```powershell
ffmpeg -version
ffprobe -version
```

If unavailable, offer this command for the user to run:

```powershell
winget install --id Gyan.FFmpeg.Essentials --exact --source winget
```

Then reopen the terminal and the application running the skill, and repeat both checks. If WinGet is unavailable, the user can download `ffmpeg-release-essentials.zip` from [Gyan's release builds](https://www.gyan.dev/ffmpeg/builds/#release-builds), extract it to a permanent location and add its `bin` directory to their user `Path`.

Sources checked on 2026-11-05: [Gyan build information](https://www.gyan.dev/ffmpeg/builds/), [Microsoft WinGet install documentation](https://learn.microsoft.com/windows/package-manager/winget/install), and [Microsoft package manifest exposing ffmpeg and ffprobe aliases](https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/g/Gyan/FFmpeg/Essentials/9.0.1/Gyan.FFmpeg.Essentials.installer.yaml). These instructions were researched, not executed or validated on a Windows machine during the interview.

Executable presence alone does not establish support for the chosen encoding workflow. Required filters and encoders must also be checked before processing. Burning the Label into video requires video re-encoding; fidelity must not be described as a bit-identical or universally lossless copy. See the official [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) and [filter documentation](https://ffmpeg.org/ffmpeg-filters.html#Timeline-editing).

## HDR research and correction

The SDR-only suggestion was a proposed scope restriction, not an established FFmpeg limitation. Official sources confirm 10-bit overlay formats and HDR encoding/metadata facilities: [FFmpeg overlay source](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_overlay.c), [x265 colour-signalling options](https://x265.readthedocs.io/en/master/cli.html#vui-video-usability-information-options), [x265 bitstream options](https://x265.readthedocs.io/en/master/cli.html#bitstream-options) and [FFmpeg libx265 source](https://ffmpeg.org/doxygen/trunk/libx265_8c_source.html).

Engineering inference: the filter chain must deliberately preserve video characteristics and map the icon into the video's colour/luminance space. Neither successful encoding nor retained metadata alone proves correct HDR output. These findings establish feasibility and validation requirements, not an implemented or tested HDR feature in this repository.
