# Labelling an image with a caption

Use this when the user chose a **caption** for an image instead of burn-in (SKILL.md step 3, or the preview of `references/image.md`): a line below the image with the Basic EU Icon and the text label, plus the same text label added to the image's alt text for screen-reader users. It edits the **document or page where the image is used**, never the image. **Burn-in** is not done here: follow `references/image.md`.

The caption follows the same conventions as a text Label (`references/text.md`): the **Basic** EU Icon, a text label in the document's language, and a marker comment. label_tool prints the caption; you insert it into the document, in place.

## Steps

1. **Find where the image is shown.** Search the document the user named, or else the project's Markdown and HTML files, for the image's file name (for example `satire.png` in `![...](images/satire.png)` or `<img src=".../satire.png">`). Each match is a candidate: keep it only when its path leads to this image file (a `hero.png` in another folder is another image), and it shows the image rather than linking to it or quoting it in a code example. Resolve a relative path from that document, and a root-relative URL (`/hero.png`) from the folder the site serves at its root, such as `public/` or `static/`; ignore any `?query` or `#fragment` and decode `%20`-style escapes. When you can't tell where a candidate points, ask the user. For a reference-style image (`![alt][r]`), the caption goes below the image, not the definition.
   - **An Existing Label:** before adding or printing a caption, look at the image's pixels for an "AI generated" text or another AI icon, and read the text around each reference for a caption that already discloses AI involvement. Alt text that mentions AI is not one: it keeps its handling in **Alt text mention** below. When you find one, follow **An Existing Label** in SKILL.md, and add no caption until the user answers. When you find none, say nothing about Existing Labels.
   - If you find none, ask the user where the image is published. If it is outside the project (a CMS, a social network), ask its language and whether it takes HTML or Markdown, print the caption with `--lang <code>` in place of `--document` (for Markdown, `--icon-path` is the URL the icon is uploaded at), and give them the caption and the alt text mention to paste there, saying you couldn't place it yourself.
   - If a `<!-- eu-ai-labelling: ... -->` marker already sits next to that reference, reuse that caption: bring its marker and text label to the wording now settled, and check the alt text mention (below). Add no second caption.

   Done when every place to label is named, or the user has the snippet to paste.
2. **Settle the wording** (see **Wording**). Done when `wording` prints the text label for the document, or you have written it yourself.
3. **Add the caption and the alt text mention** at each reference, from the sections below. Leave every other line of the document as it was. Done when each reference carries both.

## Wording

The icon is always **Basic** (the official "AI" icon), whatever the image's Icon Variant: the variant sets only the wording (`generated` or `modified`, from SKILL.md step 2). The marker uses the same word, always in English.

The text label is in the **document's language** and names the image: label_tool's wording table gives its image phrasing, in English "Image generated with AI" or "Image modified with AI". `snippet --as caption` writes it itself from the document you pass with `--document`. Print it for the alt text, which you edit yourself, with:

```
uv run <skill folder>/scripts/label_tool.py wording --wording <generated|modified> --document <document>
```

Use its `image`. Which language the tool picks, and what to do on `language_unknown` or `language_not_listed`, is in `references/text.md` (**Wording**).

For a Markdown document, the caption references the official SVG copied into the project, as for a text Label. Copy it once, into the folder the project already keeps images or static files in (or `assets/` next to the document), as `references/text.md` describes:

```
uv run <skill folder>/scripts/label_tool.py copy-icons --to <assets folder>
```

Add `--colour white` on a dark background. Choose `--icon-path` below as step 2 of `references/text.md` (**Markdown**) says: relative to the document, or the served path for a folder served at the site root.

## Caption

Put the caption directly below the image reference, as its own block. Print it with `snippet --as caption`, and `--dark` on a dark background. Insert `snippet` as printed.

**HTML**: insert it right after the `<img>` (or after the element that wraps it, such as a `<picture>` or link).

```
uv run <skill folder>/scripts/label_tool.py snippet --format html --as caption --wording <generated|modified> --document <document>
```

When the image sits in a `<figure>`, add `--figcaption`: the caption is then a `<figcaption class="eu-ai-label">` instead of a `<p>`. If the `<figure>` already has a `<figcaption>`, add the marker, the `<svg>` and the `<span>` from the snippet to it instead.

**Markdown**: add it below the image reference, with a blank line before and after.

```
uv run <skill folder>/scripts/label_tool.py snippet --format markdown --as caption --wording <generated|modified> --document <document> --icon-path <icon path>
```

It reads, for example:

```markdown
<!-- eu-ai-labelling: generated -->
![AI](assets/ai-basic-black.svg) Image generated with AI
```

## Alt text mention

Also add the text label to the image's existing alt text, after what is already there, in brackets. An alt that already carries an AI mention gets it updated to the settled wording, not a second one. Keep the original description: it is what screen-reader users rely on to enjoy the work. In a collapsed or shortcut reference image (`![cartoon][]`, `![cartoon]`) the alt is also the reference key: write the key out first, as `![cartoon (Image generated with AI)][cartoon]`, so the image still finds its definition. The marker belongs to the caption: don't add a second one here.

```markdown
![A satirical cartoon of the minister asleep on the budget (Image generated with AI)](satire.png)
```

In HTML, do the same to the `alt` attribute of the `<img>`. If the image has no alt text, the text label becomes the alt text; suggest the user add a description too.

## Done

The step is done when each place the image is used either carries the caption (the marker comment, the Basic EU Icon and the text label in the document's language, inserted as `snippet` printed them) and the alt text mention, or is outside the project and the user has the caption and alt text mention to paste there. The image file itself is not changed and no Labelled Copy is written. Report to the user:

- each document edited and where the caption went (below which image reference);
- the text label and wording used;
- for Markdown, the path of the copied SVG;
- any place the image is used that you couldn't label, with the caption and alt text mention to paste there, as not yet placed;
- each Existing Label found, only when you found one: where it is and what it says.
