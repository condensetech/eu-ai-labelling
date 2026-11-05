# 02: Produce the first MP4 Labelled Copy

**What to build:** A user can label a short, simple SDR MP4, inspect the complete result and receive a new Labelled Copy while retaining the original. The first rendering path is deliberately bounded and must identify unsupported characteristics before processing them.

**Blocked by:** 01 - Start the video workflow and check available tools.

**Status:** resolved

- [x] Complete the skill-to-tool-to-result workflow for a documented, validated SDR MP4 profile: a short video up to 60 seconds, one constant-frame-rate video stream, and either no audio or one compatible audio stream. Keep the source container and video codec; preserve audio without an unapproved conversion.
- [x] Resolve the Fully AI-Generated or Partially AI-Modified Icon Variant from the user's supplied context, asking only when unresolved. Use the official EU Icon and preserve the existing separation between applying a Label and deciding legal obligations.
- [x] Incorporate a continuously visible Label at a fixed, user-adjustable corner with a contrast backing plate. Reuse existing Icon Colour, size, margin and corner conventions; keep both position and appearance stable during playback.
- [x] Creative Work videos use the same incorporated Label, with position chosen by the user when requested. Do not substitute an external caption, and do not change the caption/burn-in choices for Creative Work images.
- [x] Produce the conventional .ai-label copy beside the original. Exclude existing Labelled Copies from inputs, preserve the original bytes, replace an existing copy only after successful rendering and output validation, and retain the previous valid copy on any failure. Clean incomplete output and never write through a destination link into the original.
- [x] Verify actual output dimensions, duration, frame cadence, colour characteristics and audio synchronisation independently of the preflight checks. Explain that video re-encoding is inherent; do not describe the copy as bit-identical or universally lossless.
- [x] Detect inputs outside the currently validated path, including HDR, additional tracks, unsupported orientation/timing or missing codec capabilities, before silently discarding or converting anything. Explain the limitation and ask how to proceed; the baseline SDR path must not become a permanent exclusion of HDR.
- [x] Present the complete Labelled Copy for approval, or honour an explicit preview waiver. Changed parameters require a fresh approval. Until video-reference handling is implemented, do not send videos through image-specific reference or alt-text updates.
- [x] Demonstrate both Icon Variants, a silent input, an input with audio, rerendering, a destination-link case and interrupted/failed rendering using real representative video output. Include automated fidelity checks, visual review, structured failure checks, and instructions describing the actual supported profile.

## Comments

Implemented `video-apply` on the validated `mp4-h264-sdr` path (tests/unit/test_video_apply.py, tests/docs/test_video_reference.py): both Icon Variants checked against the official SVG in decoded frames, silent and audio inputs (audio packets byte-identical), rerendering, symlink and hard-link destinations, a simulated ffmpeg failure mid-write, missing encoder, mpeg4 and HDR stop-and-ask. Output validation decodes the staged file before it replaces the copy. Visual review: a 1280x720 test pattern frame checked by eye (legible black icon on white plate, top-right). Approval and preview waiver are skill-level instructions; headless evals come with the final eval commit.
