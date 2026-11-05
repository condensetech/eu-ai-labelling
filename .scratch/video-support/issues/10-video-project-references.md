# 10: Update approved video references in a project

**What to build:** After approving a video Labelled Copy, a user can have the project's player references updated to use it while preserving existing descriptions and tracks and adding no extra disclosure around the player.

**Blocked by:** 02 - Produce the first MP4 Labelled Copy.

**Status:** ready-for-agent

- [ ] Find and update literal source references on HTML video elements and source elements belonging to video players, targeting the corresponding approved Labelled Copy. Distinguish these uses from image/picture sources and unrelated elements.
- [ ] Apply changes only after final approval or an explicit preview waiver for that exact copy. Changed copies require renewed approval; failed, refused, skipped or unapproved copies must not replace project references.
- [ ] Preserve existing visible and accessible descriptions, subtitles, transcripts, track elements and unrelated player attributes. Do not introduce an extra disclosure, alter image alt text for a video, or manufacture a new accessible-description requirement.
- [ ] Preserve ordinary links and unrelated content. Use the existing conservative inspection approach for framework components, imports, data and computed references; report unresolved, dynamic and external uses instead of claiming they were updated.
- [ ] Keep standalone-video delivery independent of project integration. Report changed uses and remaining references accurately, without claiming that an external system or published site changed.
- [ ] Make repeat runs idempotent and avoid relabelling or inventing additional copies when references already point at the approved result.
- [ ] Demonstrate a direct video source, nested video sources, a picture-source control case, an existing description/subtitle track, a plain-link control case, and a dynamic reference that must be reported. Verify approval gating, repeat runs and isolation of unrelated files.
- [ ] Integrate per-file approved outcomes when the batch workflow is available without making that workflow a prerequisite. Format and HDR extensions should work through the same reference mechanism rather than requiring special rewrite rules.
- [ ] Update project-reference instructions and workflow evaluations so video handling is explicit and image/text behaviour remains unchanged.
