---
name: eu-ai-labelling
description: Apply the official EU Icons as visible labels on AI-generated or AI-modified content (EU AI Act Article 50). Use when the user asks to label, disclose or mark content as AI-generated or AI-modified, asks whether content needs an AI label, or invokes eu-ai-labelling.
---

# EU AI labelling

Helps the user put a visible **Label** (an official **EU Icon**) on content that AI generated or modified, following Article 50(4) of the EU AI Act and Section 2 of the Code of Practice on transparency of AI-generated content.

## Paths

Every path in this skill and its reference files to `scripts/`, `assets/` or `references/` is relative to **this skill's folder**: the directory that holds this `SKILL.md`. Commands run from the user's project, not from here, so in commands `<skill folder>` stands for that folder's absolute path. Pass the user's files (images, `--document`, `--root`, `--to`) as absolute paths too. Two values are not filesystem paths: `--icon-path` is the path the published document loads the icon from (`references/text.md` says which), and the `FILE` of `--alt-mention FILE=TEXT` is copied as `references` printed it.

- `scripts/label_tool.py`: the CLI that does all deterministic work. Each subcommand prints one JSON object; on failure it exits non-zero and prints `{"error": {"code", "message"}}`.
- `assets/icons/`: the official EU Icon SVGs, which label_tool renders and copies; `assets/icons/SOURCE.md` records where they came from.
- `references/`: one procedure per content type, loaded only when that type is being labelled.

Run the CLI with `uv run <skill folder>/scripts/label_tool.py <subcommand> ...`. When `uv` is missing, use `python3 <skill folder>/scripts/label_tool.py ...` provided Pillow and resvg-py are installed; if neither works, tell the user to install `uv`.

## Steps

When the user only asks whether a Label is required, answer as **Whether a Label is required** says, and enter these steps only once they ask for a Label.

1. **Identify the content.** Find the file(s) the user means and their content type: image, video (a local video file) or text (Markdown or HTML). For any other content type (plain text, PDF, audio on its own), and for a video given as a URL to download or a live stream, tell the user this version labels images, local videos, Markdown and HTML, and adds label components to sites, and stop. A request to add AI labels to a website or web app as a reusable component ("add AI labels to my site") is a **site**: the content is the project itself, so there is no file to name. A folder, a glob or several files named in one request is a **batch**: list its files with the command in **Listing a batch** of `references/batch.md` (for a folder, the files directly inside it), which types each one as an image or a video and sets aside existing Labelled Copies (`*.ai-label.*`): they are never labelled again, so steps 2 and 3 skip them and the report lists them as skipped. Done when every file is named and typed.
2. **Settle the Icon Variant.** It says how AI was involved, which only the user knows for sure:
   - The user named the variant ("fully AI-generated", "AI-modified"): use it as given. **Fully AI-Generated** maps to `generated`, **Partially AI-Modified** to `modified`.
   - Otherwise answer from context first: what the user said about the content, or that you made it yourself in this session. The name of an AI tool alone ("made with Midjourney", "ChatGPT helped") doesn't say which: these tools both create and edit. If context doesn't say, ask one plain question: did AI create it from scratch, or edit something that already existed (a real photo, a text a person wrote)? From scratch is **Fully AI-Generated**; an edit of something real is **Partially AI-Modified**. Wait for the answer before labelling (for a batch, ask it with the batch's other questions, as **A batch of files** says).
   - **Basic** is for documents and sites only: an image or a video can't be labelled with it. When the user names "basic" for an image or a video, ask whether it is fully AI-generated or AI-modified, then use **Fully AI-Generated** or **Partially AI-Modified** as named, once they answer.
   - For a Markdown or HTML document the icon is always **Basic**; the answer sets only the wording: "fully AI-generated" (or "AI-generated", "written by AI") is `generated`, "partially AI-modified" (or "AI-modified", "edited with AI") is `modified`. If they named only "basic", ask whether the text was generated or modified.
   - For a **site** the component always shows the **Basic** icon, with a text label passed in per use: skip this step and step 3.
   - For a **batch**, see **A batch of files** below.

   Done when every file has its Icon Variant, which also sets the wording every reference uses: `generated` or `modified`.
3. **Settle where an image's Label goes.** By default the EU Icon is burned into a Labelled Copy of the image. When the request or context presents the image as an artistic, satirical or fictional work and the user hasn't said how to label it, ask before labelling, whether or not they named the variant:
   - **Caption**: the Basic EU Icon and a text label below the image, in the document or page that shows it;
   - **Burn-in**: the EU Icon burned into a Labelled Copy.

   When they already said how ("as a caption in post.md", "burn it in"), don't ask. For any other image, go on with burn-in; the preview (step 5 of `references/image.md`) lets the user switch to a caption. For a batch, ask once for every image it concerns. A **video** always carries the Label in its picture, Creative Work or not: don't offer it a caption, and skip this step for it (`references/video.md` settles when the Label shows and its corner, chosen from frames and labelled excerpts of the video). Done when the placement of each image is settled.
4. **Label it**, following the reference file for its content type:
   - Image, labelled with a **Caption**: read `references/creative-work.md`.
   - Image (any image file; the reference says which formats are refused), labelled by burn-in: read `references/image.md`.
   - A batch of images labelled by burn-in: read `references/batch.md` as well.
   - Video: read `references/video.md`; for a batch holding videos, read `references/batch.md` as well (**Videos in a batch**). In a batch of images and videos, each file follows its own reference.
   - Markdown or HTML document: read `references/text.md`.
   - Site (a reusable label component for a React, Vue, Astro or plain HTML project): read `references/site.md`.

   When the reference finds an Existing Label, follow **An Existing Label** below.

   A Labelled Copy of an image inside the project then goes through `references/update-references.md`, as the image and batch references say; a video's goes through step 8 of `references/video.md`, without any alt-text change.

   Done when the reference file's own completion criterion is met.
5. **Report** what the reference files you followed ask you to report: for an image the Labelled Copy's path and the parameters used, for a video what `references/video.md` asks, for a batch the summary in `references/batch.md`, and after a Labelled Copy inside the project the reference lists from `references/update-references.md`. Name every Existing Label found: where it is and what it says. Close with this note: "This is not legal advice."

## Whether a Label is required

Never say whether the law requires a Label for some content, nor guess it. Whether Article 50 applies depends on facts and legal judgement that belong to the user, or their legal adviser. When the user asks ("does this need a label?", "am I required to disclose this?"), say that the plugin applies Labels but doesn't decide whether one is required, and point them to the official sources:

- the Guidelines on Article 50: https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations
- the Code of Practice on transparency of AI-generated content: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
- the AI Act Service Desk: https://ai-act-service-desk.ec.europa.eu/

When the content visibly has an Existing Label, say so as a fact: where it is and what it says.

Then offer to apply a Label, and label only if they say so. Don't change any file before they answer.

## An Existing Label

An **Existing Label** is a visible disclosure of AI involvement that this plugin didn't apply: a disclaimer line, another AI icon, a "generated by" footer, an "AI generated" text in an image's pixels, an on-screen notice in a video, a site's own AI notice. A Label carrying this plugin's `<!-- eu-ai-labelling: ... -->` marker and a Labelled Copy (`*.ai-label.*`) keep their own handling. Marking (C2PA or IPTC metadata, a Provider's watermark) is not an Existing Label, and neither is alt text alone: sighted readers can't see it.

Each reference says where it looks for one, at the step where it already reads the content. When it finds one:

- **Stop before changing any file.** Tell the user where the Existing Label is, what it says, and whether its wording matches the `generated` or `modified` of step 2. Ask whether to add the EU Icon anyway or leave the content as it is, together with any question still open from steps 2 and 3, and wait.
- **Facts only.** State a wording mismatch as a fact. Never call an Existing Label sufficient or insufficient, nor say it makes the EU Icon needed or unneeded.
- **Already decided.** When the request already deals with the Existing Label ("label it anyway", "replace our disclaimer with the EU label"), don't ask; step 5 still names it.
- **Labelling anyway** adds the EU Icon in its usual place, as the reference says. Never edit or remove the Existing Label: remove or replace it only when the user explicitly asks, as a plain edit outside these steps.
- **Only what you found.** Mention an Existing Label only when you found one. Never say none was found: reading a picture by eye or sampling video frames can't rule one out.

## A batch of files

Ask the questions of steps 2 and 3 once for the whole batch, not once per file, together with each video's visibility question (step 3 of `references/video.md`):

- **Shared answers.** When the user or the context answers a question for the whole batch ("all of them were generated from scratch", "show it all the way through"), that answer holds for every file it concerns. Never ask again about a file whose answer is settled, by the user or by context.
- **Per-file exceptions.** Ask a per-file question only where files differ: context answers it for some files but not others, or the user said the files differ. An exception the user named ("all generated, except intro.mp4, which is an edited real clip") settles that file and leaves the shared answer for the rest. Name the file or files each question is about in the question itself, and group files that share the question ("Were crowd.png and stage.png generated from scratch, or are they real photos edited with AI?"). Don't name, in any question, a file whose answers context already settles.
- **One message.** Ask every open question, shared or per-file (Icon Variant, an image's caption or burn-in, a video's visibility), together in one message, and label nothing in the batch until they are answered. Say, for the visibility, what happens without a preference: it is settled per video by its length, `auto` (continuous up to 60 seconds, periodic beyond), so a batch of short and long videos needs no answer.
- **Placement.** The corner is chosen per image and per video, from that file's own pixels or frames: never ask one corner question for the batch up front. The files with no free corner are gathered into one later question (step 5 of `references/batch.md`). A corner the user chose for the whole batch is a shared answer; one named for a file is an exception.
