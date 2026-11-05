# 01: Start the video workflow and check available tools

**What to build:** A user requesting a Label for a local video receives an accurate inspection of the file and the available FFmpeg tools, or actionable installation guidance. This first slice establishes the video entry point without claiming that rendering is already available.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Recognise local video requests and route them to the video workflow. Keep URL downloads, live streams and audio-only labelling outside the agreed scope; do not change the existing image, text or site workflows.
- [x] Check both ffmpeg and ffprobe in the environment executing the skill. Distinguish missing, unusable and available tools, and do not make their installation a prerequisite for image-only use.
- [x] When either tool is unavailable, ask the user to install the tools, provide platform-appropriate guidance and repeat the checks afterwards. Never install or download executables automatically.
- [x] Windows guidance covers the approved WinGet package, an archive/manual-Path alternative, and reopening the terminal and hosting application before retrying. Provide corresponding guidance for macOS and Linux without claiming an untested platform was validated.
- [x] Read actual stream, timing, orientation and colour information without modifying the source. Explain unreadable inputs and inspection failures through the existing structured error/reporting conventions.
- [x] Report available decoders, filters, pixel formats and encoders relevant to a processing path, while distinguishing tool capability from an implemented and validated labelling path. An extension or successful version check must not become a claim that any video can be preserved.
- [x] Demonstrate tool-present, each-tool-missing, unusable-tool, malformed-input and Windows executable-lookup cases. Verify that image labelling still works when neither executable is available; distinguish simulated platform checks from native execution.
- [x] Update the user-facing entry instructions and setup documentation to describe precisely the capability delivered by this slice. Return a clear not-yet-supported outcome for rendering until a validated renderer is available.

## Comments

Implemented `video-tools` and `video-inspect` in label_tool, `references/video.md`, SKILL.md routing and README setup (tests/unit/test_video_tools.py, tests/docs/test_video_reference.py). Verified natively on macOS with FFmpeg 9.0.2. The Windows PATHEXT lookup and the Windows/Linux guidance are exercised only through the simulated platform (LABEL_TOOL_PLATFORM); no native Windows or Linux run. `video-apply` returned `video_not_supported_yet` until ticket 02.
