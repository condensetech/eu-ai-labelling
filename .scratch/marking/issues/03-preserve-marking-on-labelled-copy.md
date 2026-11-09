# 03: Preserve the Marking on the Labelled Copy

**What to build:** To be decided. Today an image's Labelled Copy keeps only EXIF and the ICC profile, so XMP (including IPTC DigitalSourceType) and any C2PA manifest are dropped. A video's copy keeps container tags through `-map_metadata`, but a C2PA manifest doesn't survive re-encoding in a usable state. See [spec](../spec.md), section **Labelled Copy**.

**Blocked by:** none

**Status:** needs-triage

Open questions:

- Should XMP be carried over to image copies as it is?
- For C2PA, should the copy carry a new manifest that records the original as an ingredient plus a labelling action? Who signs it, and with what key? Or should the copy carry no C2PA at all?
- Is there a Code of Practice expectation about deployers keeping a Provider's Marking that should drive this?
