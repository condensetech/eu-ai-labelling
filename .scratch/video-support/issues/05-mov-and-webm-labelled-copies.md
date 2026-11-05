# 05: Produce MOV and WebM Labelled Copies

**What to build:** A user can label supported MOV and WebM files through the same complete workflow without having every video converted to MP4.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** resolved

- [x] Deliver at least one documented, validated SDR codec profile for each of MOV and WebM, with representative real input/output fixtures. Select processing based on actual container and stream characteristics rather than the filename alone.
- [x] Preserve the source container and video codec when supported, and retain compatible audio without an unapproved conversion. Do not introduce an automatic common publishing format as a shortcut.
- [x] Check the installed build's required decoder, encoder, pixel-format and muxing capabilities before rendering. Explain unsupported combinations and ask before a conversion, rather than silently changing or dropping characteristics.
- [x] Reuse the established Icon Variant, fixed backing plate, Labelled Copy naming, atomic replacement, validation and approval contracts. Respect visibility and preview features when they are present without making their tickets prerequisites for the baseline format extension.
- [x] Inspect the produced file to verify the declared container, video/audio codecs, dimensions, duration and cadence. Exercise inputs with and without audio and distinguish actual output validation from executable capability checks.
- [x] Demonstrate missing-encoder and incompatible-stream outcomes with no original modification or replacement of a previous valid copy. Preserve MP4 and image behaviour in regression checks.
- [x] Update the workflow instructions and support documentation with the combinations actually verified and any platform/build limitations. Do not imply that all codecs inside MOV or WebM are supported.

## Comments

Added three validated paths to `LABELLING_PATHS`: `mov-h264-sdr` (libx264 CRF 16, muxer `mov`, audio AAC/MP3/ALAC/AC-3/PCM 16- and 24-bit), `webm-vp9-sdr` (libvpx-vp9 CRF 20 `-b:v 0`, muxer `webm`, Opus/Vorbis) and `webm-vp8-sdr` (libvpx CRF 10 with a 50M ceiling, since VP8's CRF is constrained quality). Each path now carries `codec_title` and `quality`, so the `video.note` names the codec and encoder actually used. The container comes from the file (major brand `qt`, EBML DocType), and the copy keeps the original's extension and container: it is never converted to MP4. Tests in tests/unit/test_video_formats.py cover MOV with and without audio, VP9 and VP8 WebM with and without Opus, suffixes that lie both ways, a Matroska file named `.webm`, ProRes in MOV, AV1 in WebM, VP9 4:4:4, audio MOV can't copy (pcm_u8), colour tags kept, and a missing libvpx-vp9 encoder that keeps the previous copy and shows in `video-tools`. render_command now restates the source's missing colour tags as `unknown` (setparams) after the overlay, because the VP8 decoder tags frames BT.470BG that the source doesn't carry. This applies to every path, and the MP4 regression tests still pass. Fixtures are lavfi-generated real files, not checked-in samples. Subtitle codecs per path (`webvtt` for WebM) are declared but not exercised, because any subtitle track still stops as `additional_tracks`.
