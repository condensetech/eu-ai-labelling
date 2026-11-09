# Marking as evidence for the Icon Variant

The user confirmed this design on 2026-11-09, at the end of a grill-with-docs interview. It records what was agreed. Nothing has been implemented yet.

## Problem

Step 2 of `SKILL.md` settles the [Icon Variant](../../GLOSSARY.md) from what the user said or from context, and asks when neither settles it. It ignores the [Marking](../../GLOSSARY.md) a Provider often embeds in images and videos. Some Markings state exactly what the Icon Variant asks: C2PA and IPTC carry a DigitalSourceType. So the skill asks questions the file already answers. It also stays silent about Markings that would help the user answer.

## Confirmed decisions

- **What it's for.** A Marking is evidence for step 2 only. It never makes the skill say whether a Label is required. A Marking is still not an [Existing Label](../../GLOSSARY.md).
- **Content types:** images and videos only, including every image and video of a batch. Markdown, HTML and sites are unchanged.
- **Sources read:**
  1. IPTC DigitalSourceType in XMP, in images and in MP4/MOV.
  2. C2PA manifests: the Provider (claim generator / signer), the actions, their digitalSourceType, and whether the signature validates. The skill reports validity as a fact and doesn't judge whether a signer is trustworthy.
  3. EXIF/XMP `Software` and `CreatorTool`.
  4. PNG text chunks written by generators (`parameters`, `prompt`, `workflow`).
  5. Video container tags read with ffprobe (`encoder`, `comment`, `com.apple.quicktime.*`).

  Invisible watermarks (SynthID and similar) are out of scope: they can't be detected locally.
- **Grading:**
  - **Precise.** A DigitalSourceType of `trainedAlgorithmicMedia` gives `generated`, and `compositeWithTrainedAlgorithmicMedia` gives `modified`. It counts when it comes from XMP or from a C2PA manifest whose signature validates. A precise signal settles the Icon Variant as context does: the skill doesn't ask. The preview and the report say which Marking settled it.
  - **Vague.** These don't settle the Icon Variant; the origin question quotes them ("the file's metadata says Stable Diffusion made it: did AI create it from scratch, or edit an existing image?"):
    - `algorithmicallyEnhanced`, `compositeSynthetic` and `algorithmicMedia`;
    - an AI tool named in `Software`/`CreatorTool` or in container tags (step 2's rule holds: a tool's name alone doesn't say which variant);
    - generator PNG chunks;
    - the AI claims of a C2PA manifest whose signature doesn't validate: its precise codes, or an AI tool named as its generator or signer. An invalid manifest with no AI claim gives no signal: it says nothing about AI.
  - **Ignored.** `digitalCapture`, `digitalArt` and the other human-origin values, treated as if no Marking were found.
- **No Marking found** is never evidence that content isn't AI, and is never mentioned.
- **Conflicts inside one file:** the active C2PA manifest decides when its signature validates. Otherwise precise signals that disagree all become vague, and the question quotes each one. A valid active manifest whose own actions disagree (created by AI, then edited with AI) decides nothing: its signals become vague and the skill asks. An AI source type in an ingredient's manifest describes the ingredient, not the file, so it is vague.
- **The user's word wins** over the Marking. The skill labels as the user said, without asking. The preview and the report state the mismatch as a fact, with no verdict on which is right.
- **Agreement:** when the user named the variant and the Marking agrees, the final report says so in one line; the preview doesn't.
- **Batches:** a file settled by a precise Marking counts as settled by context, so the batch's one message never names it. When every file is settled and nothing else is open, the batch is labelled without a question. The batch report lists the files settled by Marking.
- **"Does it need a label?":** the answer mentions a Marking found as a fact ("the file's C2PA metadata says OpenAI generated it"), with no legal verdict.
- **C2PA unavailable** (`c2pa-python` missing under the `python3` fallback): the subcommand still reads the other sources and reports `c2pa: unavailable`. The skill mentions that C2PA wasn't checked only when it ends up asking the origin question. Labelling is never blocked on it.
- **Read errors:** when `marking` fails for any reason other than missing FFmpeg, the skill goes on as if the file carried no Marking.
- **Labelled Copy:** the copy keeps the original's IPTC DigitalSourceType and IPTC AI fields (ticket 03); the report says "the copy keeps the IPTC DigitalSourceType" when `apply` or `video-apply` printed a DigitalSourceType in `marking_kept`, and "the original's C2PA provenance is not carried over" when it printed `c2pa_left_behind`. A copy settles what its original settles, so an original whose precise signals contradict each other gives a copy with no DigitalSourceType. Signing a C2PA edit manifest on the copy (ticket 04) was discarded.

## Implementation shape

- A new deterministic subcommand `label_tool.py marking <file>` prints one JSON object. For each source it gives the signals found, its grade (precise/vague) and, when the grade is precise, the variant it settles. It also gives the overall result after the conflict rules: `settled: generated|modified|null`, plus the quotes for the question.
- `c2pa-python` is added to the script's inline dependencies.

## Testing

- Unit tests for `marking` on fixtures covering each source, each grade, the conflict rules and `c2pa: unavailable`.
- Doc tests for each changed reference.
- Eval scenarios:
  1. A valid C2PA `trainedAlgorithmicMedia` is labelled as generated without asking.
  2. An XMP `compositeWithTrainedAlgorithmicMedia` is labelled as modified.
  3. A vague `parameters` PNG chunk makes the skill ask, quoting it.
  4. The user's word contradicts the Marking: the file is labelled as the user said and the mismatch is stated.
  5. In a mixed batch, only the unmarked files are asked about.
  6. A video with an XMP DigitalSourceType.

  The existing `unknown-origin` evals keep their meaning: their fixtures carry no Marking.

## Not an ADR

This decision is easy to reverse, so it gets no ADR. The glossary needs no change: **Marking** already names the concept.
