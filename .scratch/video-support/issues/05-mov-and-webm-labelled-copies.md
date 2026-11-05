# 05: Produce MOV and WebM Labelled Copies

**What to build:** A user can label supported MOV and WebM files through the same complete workflow without having every video converted to MP4.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** ready-for-agent

- [ ] Deliver at least one documented, validated SDR codec profile for each of MOV and WebM, with representative real input/output fixtures. Select processing based on actual container and stream characteristics rather than the filename alone.
- [ ] Preserve the source container and video codec when supported, and retain compatible audio without an unapproved conversion. Do not introduce an automatic common publishing format as a shortcut.
- [ ] Check the installed build's required decoder, encoder, pixel-format and muxing capabilities before rendering. Explain unsupported combinations and ask before a conversion, rather than silently changing or dropping characteristics.
- [ ] Reuse the established Icon Variant, fixed backing plate, Labelled Copy naming, atomic replacement, validation and approval contracts. Respect visibility and preview features when they are present without making their tickets prerequisites for the baseline format extension.
- [ ] Inspect the produced file to verify the declared container, video/audio codecs, dimensions, duration and cadence. Exercise inputs with and without audio and distinguish actual output validation from executable capability checks.
- [ ] Demonstrate missing-encoder and incompatible-stream outcomes with no original modification or replacement of a previous valid copy. Preserve MP4 and image behaviour in regression checks.
- [ ] Update the workflow instructions and support documentation with the combinations actually verified and any platform/build limitations. Do not imply that all codecs inside MOV or WebM are supported.
