# 06: Creative Work labels outside the frame

**What to build:** When the Disclosure Assessment judges an image a Creative Work, the skill offers a Label that doesn't hamper the work: a caption, alt text, or a small icon next to the image in the document or page where it is used. Burn-in remains available if the user prefers it. The user picks.

**Blocked by:** 04, 05

**Status:** resolved

- [x] For a Creative Work, the skill presents the outside-the-frame options plus burn-in and lets the user choose
- [x] The caption and nearby-icon options reuse the text-label conventions (Basic icon, translated label, marker)
- [x] Eval: satirical AI art is classified as a Creative Work and offered a label outside the frame

## Comments

**Built:** The Disclosure Outcome block gains a `Creative Work: Yes | No` line. For an image that is a Creative Work, step 3 of `SKILL.md` offers four options, in order: **Caption** (recommended), **Alt text**, **Icon next to the image** and **Burn-in**. It says why the first three exist (the Label must not hamper display or enjoyment of the work) and waits for the user to pick; a choice stated up front counts. Caption, alt text and the nearby icon route to the new `skills/eu-ai-labelling/references/creative-work.md`, and burn-in still goes through `references/image.md`. The new reference edits the document where the image is used, never the image. It reuses the text-label conventions: Basic EU Icon (inline accessible SVG for HTML, the official SVG copied with `cat` for Markdown), the text label in the document's language ("Immagine generata con IA") and the marker comment.

**Tested:** `tests/e2e/test_creative_work_reference.py` checks the routing, the four options and the snippets statically, and runs the Markdown copy step exactly as written. New eval scenarios: `satirical-ai-art.json` (Required, Fully AI-Generated, Creative Work, four options offered, nothing labelled) and `creative-work-caption-italian.json` (the Italian caption below the image reference, no Labelled Copy). Canned-reply checks in `tests/evals/test_skill_evals.py` show that the new expectations (`creative_work`, `below`) reject weakened replies and documents. Both scenarios passed one headless run each.

**Open points:** a document carrying a caption marker for an image counts as labelled under the marker rule that ticket 09's hook will use, even if its own text is unlabelled. The image file stays unlabelled, so the hook will still remind about it unless it's recorded as an Exemption. Ticket 14 (Creative Work eval scenario) is covered by `satirical-ai-art.json`, which asserts the not-hamper wording.

**Follow-ups:** 18 (Creative Work icon dark background and reference wording), 19 (Creative Work eval regex and reference assertions).
