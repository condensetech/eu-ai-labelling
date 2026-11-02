# Labelling a text document

A Markdown or HTML document gets a **Label** at the top, near its headline, made of three parts:

1. the **Basic** EU Icon (the official "AI" icon);
2. a plain-language **text label** in the document's language, saying the text was generated or modified with AI;
3. a hidden **marker comment**: `<!-- eu-ai-labelling: generated -->` or `<!-- eu-ai-labelling: modified -->`.

The document is edited in place; no copy is written, because version control covers undo. label_tool prints the Label; you insert it into the file.

## Wording

The wording, `generated` or `modified`, is the one SKILL.md step 2 settled. The marker uses the same word, always in English.

The text label is in the **document's language**, not the language the user writes to you in. `snippet` writes it from label_tool's own wording table (English, Italian, French, Spanish and German): in English, "Generated with AI" or "Modified with AI", with the icon name "AI". Pass the document with `--document`: the tool uses the language the document declares (its `lang` attribute or front matter) and prints the `label` and `language` it used.

- **The user named a language:** add `--lang <code>`. It wins over the document.
- **`language_unknown`:** the document declares no language. Settle the language this way before writing a text label yourself too: `--label` alone skips this check. Judge it from the body text and the conversation and run the command again with `--lang <code>`. When neither settles one language, ask the user and wait.
- **`language_not_listed`, or a Label that names a part** (see **Where the Label goes**): write the text label yourself, short and plain, in the document's language. With `snippet`, pass it as `--label "<text label>"`, and when the tool asks for it, `--icon-name "<icon name>"`, the language's word for AI. With `wording`, which takes neither flag, use the text you wrote directly where its output would go.

The icon itself is never translated: it stays the official English "AI" artwork. Only the text label and the icon's accessible name are in the document's language.

## Where the Label goes

- **Whole document:** directly below the headline (the first `# ` heading in Markdown, the first `<h1>` in HTML), before the first paragraph of the body. With no headline, put it at the top of the body: after YAML front matter in Markdown, as the first thing inside `<main>`, `<article>` or `<body>` in HTML.
- **Only part of the document is AI-made** (the user says so, or you wrote only that part): label only that part. Put the Label directly below that section's heading, or just before the AI-made passage when it has no heading, and add no Label at the top. Make the text label name the part, e.g. "This section was generated with AI" / "Questa sezione è generata con IA", and pass it with `--label`.
- **Already labelled:** if the document already contains a `<!-- eu-ai-labelling: ... -->` marker at that spot, don't add a second Label. Tell the user it is already labelled; if the wording differs from the one now chosen, update that Label instead.

Leave every other line of the document as it was.

## HTML

Print the Label with:

```
uv run <skill folder>/scripts/label_tool.py snippet --format html --wording <generated|modified> --document <document>
```

- Add `--lang`, or `--label` and `--icon-name`, only as **Wording** says.
- **Dark page background:** add `--dark`, for the White Icon Colour.

It prints JSON whose `snippet` is the marker comment and a `<p class="eu-ai-label">` holding the official Basic EU Icon, inlined as an accessible SVG, and the text label. Insert `snippet` as printed. If the project has a stylesheet and the user prefers it, the inline `style` attributes may move into a `.eu-ai-label` rule; keep `role`, `aria-label` and the paths as they are.

## Markdown

1. **Copy the icon into the project's assets folder.** Use the folder the project already keeps images or static files in (for example `assets/`, `images/`, `img/`, `static/` or `public/`, often one the document already links to). If there is none, use `assets/` next to the document. Copy the official file with:

   ```
   uv run <skill folder>/scripts/label_tool.py copy-icons --to <assets folder>
   ```

   Add `--colour white` when the site renders Markdown on a dark background. It copies the official SVG byte for byte, keeping its name, and leaves an identical copy already there alone. Done when the SVG is listed under `copied`, `kept` or `replaced`.
2. **Add the Label** below the headline (see **Where the Label goes**), as its own block with a blank line before and after. Print it with:

   ```
   uv run <skill folder>/scripts/label_tool.py snippet --format markdown --wording <generated|modified> --document <document> --icon-path <icon path>
   ```

   `<icon path>` is the copied SVG's path relative to the document. When the folder is served at the site root (Hugo's `static/`, Astro's or Next.js's `public/`), use the path the site serves it at instead, such as `/ai-basic-black.svg`. Insert `snippet` as printed. It reads, for example:

   ```markdown
   <!-- eu-ai-labelling: generated -->
   ![AI](assets/ai-basic-black.svg) Generated with AI
   ```

   The alt text is the icon name; the text after the image is the text label.

## Done

The step is done when the document holds, at the right spot, the marker comment, the Basic EU Icon (inline SVG for HTML; image reference to the copied SVG for Markdown) and the text label in the document's language, inserted as `snippet` printed them. Report to the user:

- the document edited and where the Label went (top, or which section);
- the text label and wording used;
- for Markdown, the path of the copied SVG.
