# 07: Produce an HDR10 Labelled Copy

**What to build:** A user can label a supported HDR10 video, review representative previews and receive a validated HDR Labelled Copy without an automatic conversion to SDR.

**Blocked by:** 04 - Choose a fixed position using scenes and previews.

**Status:** ready-for-agent

- [ ] Deliver a documented, validated HDR10 processing path that checks the installed decoder, filter, pixel-format and encoder capabilities and retains a supported source container and codec. Use an actual HDR10 fixture rather than an SDR fixture carrying HDR tags.
- [ ] Preserve the required bit depth, colour primaries, PQ transfer function, matrix/range and relevant HDR metadata throughout decoding, compositing and encoding. Do not assume that a successful encode or copied tags proves HDR preservation.
- [ ] Map the EU Icon and backing plate deliberately into the video's colour/luminance space so the Label remains readable without unintended clipping or brightness changes. Verify the underlying picture outside the Label region against a suitable re-encoding tolerance.
- [ ] Address metadata correctness after modifying pixels, including mastering and content-light information where relevant. If preservation or correct output metadata cannot be established, stop and explain the limitation before proposing an alternative.
- [ ] Carry the HDR treatment through scene samples, labelled excerpts and the full Labelled Copy. Do not silently change previews to SDR or claim that an SDR viewing environment verifies HDR appearance; describe any unavailable rendering/display validation explicitly.
- [ ] Recognise HDR10+, Dolby Vision and other profiles distinctly. Continue only through a validated preservation path for the actual profile/build; otherwise stop and ask, without claiming they are universally impossible or silently discarding their additional metadata.
- [ ] Retain the agreed timing, Creative Work, fixed-position, atomic-output and approval behaviour. Unsupported source characteristics continue to follow the existing stop-and-ask contract rather than becoming silent conversions.
- [ ] Demonstrate real HDR10 output, decoded colour/bit-depth and metadata checks, Label luminance handling, missing-capability rejection, and detection of unvalidated HDR profiles. Distinguish automated evidence, actual visual review and unavailable HDR-display verification in the completion report.
- [ ] Update the video instructions and support claims to describe the verified path and the remaining build/profile limitations. Keep SDR output and previews working.
