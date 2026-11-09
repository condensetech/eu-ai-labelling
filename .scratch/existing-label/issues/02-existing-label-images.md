# 02: Detect an Existing Label in images

**What to build:** Apply the Existing Label rule from 01 to images, both burn-in (`references/image.md`) and caption (`references/creative-work.md`). See [spec](../spec.md).

**Blocked by:** 01

**Status:** resolved

- [x] Before writing a Labelled Copy, look at the image for a disclosure visible in its pixels ("AI generated" text, another AI icon). In a document or page, also check for a caption near the image that already discloses AI involvement.
- [x] Alt text that mentions AI is not an Existing Label. It keeps its handling in `update-references.md`.
- [x] When one is found, follow the shared rule: report it, ask, and write no Labelled Copy or caption until the user answers.
- [x] Doc tests for `image.md` and `creative-work.md`. Eval scenario: an image fixture with "AI generated" in its pixels.
