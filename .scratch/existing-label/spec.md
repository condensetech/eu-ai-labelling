# Existing Label

The user confirmed this design on 2026-11-09, at the end of a grill-with-docs interview. It records what was agreed. Nothing has been implemented yet.

## Problem

The skill avoids adding a second Label only when the Label carries its own `<!-- eu-ai-labelling: ... -->` marker, and it skips `*.ai-label.*` copies. Content that already discloses AI involvement in some other way gets the EU Icon added anyway. Examples are a disclaimer line a person wrote, an "AI generated" text in an image's pixels, an on-screen notice in a video, and a site's own AI notice.

## Confirmed decisions

- **What counts.** An [Existing Label](../../GLOSSARY.md) is a visible disclosure of AI involvement that this plugin didn't apply. Marking (C2PA, IPTC, a Provider's watermark) is not an Existing Label. Claims that the content is exempt (for example, text under editorial control) stay out of scope: the skill still never judges whether a Label is required.
- **Alt text alone is not an Existing Label**, because sighted readers can't see it. It keeps its current handling in `update-references.md` (`alt_unchanged` and the wording check).
- **Content types:** Markdown/HTML, images, videos and sites. Each reference file runs the check at the step where the agent already reads the content: the document's text, the image or its preview, the sampled video frames, the project scan for sites.
- **When one is found:** stop before changing any file. Tell the user where the Existing Label is, what it says, and whether its wording matches the settled `generated`/`modified`. Ask whether to add the EU Icon anyway or leave the content as it is.
- **No adequacy verdict.** Never call an Existing Label sufficient or insufficient. A wording mismatch is stated as a fact.
- **Labelling anyway:** add the EU Icon in its usual place. Never edit or remove the Existing Label. Remove or replace it only when the user explicitly asks, as a plain edit outside the labelling procedure.
- **User already decided:** when the request already deals with the Existing Label ("burn it in even though it has a watermark", "replace our disclaimer with the EU label"), don't ask. The report still names the Existing Label.
- **No absence claims.** Mention an Existing Label only when one is found. Never report "no Existing Label found", because looking at an image by eye and sampling video frames can't guarantee that.
- **Batches:** the "label anyway?" question goes into the batch's single message, with files grouped by name like the other per-file exceptions. A file the user declines goes under **Skipped** with the reason "Existing Label kept, no EU Icon added".
- **"Does it need a label?":** when the content visibly has an Existing Label, the answer says so as a fact, alongside the official sources as today, with no legal verdict.

## Testing

- Doc tests in `tests/docs/` for each changed reference.
- Eval scenarios in `tests/evals/scenarios/`: a Markdown post with a disclaimer, an image with "AI generated" in its pixels, a batch with one such file, and a request that already says "label anyway". A video scenario only if its fixture is cheap to build.

## Not an ADR

This decision is easy to reverse, so it gets no ADR.
