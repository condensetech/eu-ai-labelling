# 10: Update approved video references in a project

**What to build:** After approving a video Labelled Copy, a user can have the project's player references updated to use it while preserving existing descriptions and tracks and adding no extra disclosure around the player.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** resolved

- [x] Find and update literal source references on HTML video elements and source elements belonging to video players, targeting the corresponding approved Labelled Copy. Distinguish these uses from image/picture sources and unrelated elements.
- [x] Apply changes only after final approval or an explicit preview waiver for that exact copy. Changed copies require renewed approval; failed, refused, skipped or unapproved copies must not replace project references.
- [x] Preserve existing visible and accessible descriptions, subtitles, transcripts, track elements and unrelated player attributes. Do not introduce an extra disclosure, alter image alt text for a video, or manufacture a new accessible-description requirement.
- [x] Preserve ordinary links and unrelated content. Use the existing conservative inspection approach for framework components, imports, data and computed references; report unresolved, dynamic and external uses instead of claiming they were updated.
- [x] Keep standalone-video delivery independent of project integration. Report changed uses and remaining references accurately, without claiming that an external system or published site changed.
- [x] Make repeat runs idempotent and avoid relabelling or inventing additional copies when references already point at the approved result.
- [x] Demonstrate a direct video source, nested video sources, a picture-source control case, an existing description/subtitle track, a plain-link control case, and a dynamic reference that must be reported. Verify approval gating, repeat runs and isolation of unrelated files.
- [x] Integrate per-file approved outcomes when the batch workflow is available without making that workflow a prerequisite. Format and HDR extensions should work through the same reference mechanism rather than requiring special rewrite rules.
- [x] Update project-reference instructions and workflow evaluations so video handling is explicit and image/text behaviour remains unchanged.

## Comments

Extended `references` (tests/unit/test_video_references.py, tests/docs/test_video_reference.py). For an original whose extension is a video's, the output carries `media: "video"`; only a literal `src` on a `<video>` (`html-video`) or on a `<source>` inside an open `<video>` (`html-video-source`) is rewritten by `--apply`. Framework components (`<Video>`, mixed-case tags), imports, `poster`/`data-` attributes and data fields are `other` (`needs_hand_edit`, unchanged); `dynamic`, `external` and `unresolved` are reported as for images; an `<img>`, a `<source>` in a `<picture>` or `<audio>` (or outside any open `<video>`: a self-closing JSX `<video />` or a commented-out tag opens nothing) and a Markdown image are `not_a_player`. Links stay. A video's entries carry no `alt`, `--apply` needs no wording, and `--wording`/`--alt-mention`/`--lang` are a `usage` error: no alt text or disclosure is ever written. Image behaviour is unchanged (the `<video>` tag is scanned only for a video). Repeat runs find nothing left and no copy is ever created. MOV and WebM go through the same rule.

Approval gating is skill-level: step 7 of `references/video.md` runs only for a final copy (approved or preview-waived), after re-approval of a changed copy, and never for a failed, refused, skipped or unapproved one; the tool itself only requires that the Labelled Copy exists. The step went in as step 7, after the error step 6, so steps 1-6 keep their numbers. Left out: a headless workflow eval scenario (needs a model run), and batch integration beyond "run step 7 for each final copy", since ticket 09 is not built yet.
