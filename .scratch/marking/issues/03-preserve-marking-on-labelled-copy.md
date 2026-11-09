# 03: Keep the IPTC Marking on the Labelled Copy

**What to build:** The Labelled Copy of an image or a video keeps the original's IPTC DigitalSourceType (and the other IPTC AI fields) in its XMP, so the copy stays machine-readable as AI content. Signing a C2PA edit manifest is ticket 04. See [spec](../spec.md), section **Labelled Copy**, and the research findings below.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] `apply` copies `Iptc4xmpExt:DigitalSourceType`, and the IPTC AI fields when present, from the original's XMP into the Labelled Copy, for PNG, JPEG and WebP. The value stays as it is: adding a non-AI label doesn't change what the content is.
- [ ] `video-apply` does the same for MP4 and MOV. First check whether ffmpeg `-map_metadata` already carries the XMP `uuid` box. If it doesn't, write the XMP after encoding.
- [ ] The copy gets no `xmpMM:InstanceID` and no `dcterms:provenance` from the original: the first would misidentify the copy, and the second points validators at a remote manifest whose hard binding the copy fails.
- [ ] The original's C2PA manifest is not carried over, since its hard binding no longer matches.
- [ ] `label_tool.py marking` on the copy settles the same variant as on an original whose Marking was precise XMP or C2PA.
- [ ] Reports: the line saying the copy no longer carries the original's Marking (ticket 02) becomes "the copy keeps the IPTC DigitalSourceType; the original's C2PA provenance is not carried over", and appears only when the original had a Marking.
- [ ] Unit tests for each image format and MP4/MOV. Doc tests for the changed report wording.

## Research findings (2026-11-09)

From primary sources (AI Act, Code of Practice of 10 June 2026, Art. 50 Guidelines C(2026) 7702 of 5 Nov 2026, C2PA 2.2, IPTC):

- **No statutory duty on deployers** to keep the Marking. Art. 50(2) is on providers.
- **Code of Practice, Section 1, Measure 1.2(b):** providers must forbid deployers, in their terms, from intentionally removing or tampering with metadata markings. It makes an exception for replacing metadata "to maintain accurate and functional information" after processing.
- **Guidelines, paras (16) and (98):** distributors are "strongly encouraged to preserve the marking". Para (117) says the Marking doesn't replace the visible Label.
- **XMP:** copying DigitalSourceType is technically trivial. IPTC is silent on overlays, so keeping `trainedAlgorithmicMedia` is the honest reading. Copying the whole XMP block would leave a stale `xmpMM:InstanceID` and a dangling `dcterms:provenance`.
- **C2PA:** the correct representation of our edit is a new standard manifest: the original as a `parentOf` ingredient, then `c2pa.opened` and `c2pa.edited` ("Added EU AI icon"). It must be signed with an X.509 certificate. c2pa-rs refuses a self-signed one, and an untrusted chain validates as `Valid` with `signingCredential.untrusted`. This works for re-encoded MP4 too. That option is ticket 04.

Left open: whether a provider's terms treat a tool's side-effect stripping as "intentional removal". Each provider's terms differ, and they weren't reviewed.
