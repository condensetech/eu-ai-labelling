# 09: Label video batches with independent outcomes

**What to build:** A user can request Labels for several local videos, answer shared questions once, review the results together and retry selected files without a failure discarding successful work.

**Blocked by:** 04 - Choose a fixed position using scenes and previews.

**Status:** ready-for-agent

- [ ] Discover videos from an explicitly supplied list, glob or folder using the existing batch scope. For a folder, inspect its direct files; exclude existing Labelled Copies and report them as skipped.
- [ ] Reuse answers already supplied for the batch. Group unresolved Icon Variant, visibility and placement questions into one message, distinguish shared answers from per-file exceptions and avoid asking again about resolved files.
- [ ] Keep placement specific to each video and apply the agreed short/long-video defaults per file when no explicit shared preference overrides them. Creative Work videos retain an incorporated Label.
- [ ] Process each file through its available validated rendering path. Do not hard-code a separate batch support matrix or require completion of every format/HDR extension before a baseline batch can work.
- [ ] Isolate inspection, capability, rendering, validation and preview failures. Continue independent eligible files, report pending decisions separately, preserve originals and previous valid copies, and clean partial outputs.
- [ ] Present one combined review that identifies each Labelled Copy, its effective settings, preview coverage and any failure/refusal/skip. Honour existing approval or explicit preview-waiver rules and rerender only the files the user requests.
- [ ] Expose per-file approval outcomes for later project-reference handling without routing unapproved or failed files through image-specific updates. Actual video-reference updates remain the responsibility of the separate reference ticket.
- [ ] Demonstrate a batch containing different durations, a shared answer, a per-file exception, an existing Labelled Copy and a failing file. Verify partial success, grouped questions, selective retry and renewed approval of changed copies. Exercise additional format/HDR handlers when they are present without making them blocking edges.
- [ ] Update batch instructions and workflow evaluations, preserving established image-batch behaviour.
