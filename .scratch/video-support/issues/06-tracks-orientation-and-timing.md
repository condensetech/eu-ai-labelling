# 06: Preserve tracks, orientation and variable timing

**What to build:** Users can label supported videos with multiple audio tracks, subtitles, rotation or variable frame timing while keeping their playback characteristics. A file that cannot be preserved stops for a user decision instead of losing information silently.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** ready-for-agent

- [ ] Preserve supported audio and subtitle streams explicitly, including meaningful language, default/forced disposition and synchronisation information. Do not rely on automatic stream selection that could retain only one track.
- [ ] Keep displayed orientation and dimensions correct, including rotated source files. Avoid double rotation and ensure that the user-selected Label corner corresponds to the displayed video.
- [ ] Preserve variable frame timing, duration, audio/video synchronisation and relevant timestamp offsets. Do not silently normalise a variable-frame-rate source to a fixed rate.
- [ ] Identify unsupported streams, relevant metadata or muxing combinations before omitting or converting them. Explain the affected characteristics and ask how to proceed; a missing preservation path must not automatically strip tracks or normalise the file.
- [ ] Validate the actual produced stream inventory, meaningful metadata, displayed geometry and timing before replacing a previous Labelled Copy. Failure retains the original and previous valid copy.
- [ ] Demonstrate independent fixtures for multiple audio tracks, subtitles, rotation and variable frame timing, plus a combined representative case and a deliberately unsupported preservation case. Assess visible orientation and real synchronisation as well as probe metadata.
- [ ] Establish the behaviour with the baseline MP4 path so this ticket does not depend on the MOV/WebM extension. Where additional rendering or visibility paths are already available, verify that they retain the same preservation contract.
- [ ] Update user instructions and workflow evaluations to distinguish supported preservation from cases that require an explicit decision. Preserve the existing image workflows.
