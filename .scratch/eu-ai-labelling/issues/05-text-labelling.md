# 05: Text labelling

**What to build:** A writer asks to label a Markdown or HTML document. The agent edits it in place, adding at the top near the headline:
- the Basic EU Icon;
- a plain-language text label in the document's language, saying generated or modified, e.g. "Generato con IA";
- a marker comment of the form `<!-- eu-ai-labelling: generated|modified -->`.

HTML gets an inline SVG with `role="img"` and an `aria-label`. Markdown gets an image reference to an SVG copied into the project's assets folder. Where only part of a document is AI-made, only that part is labelled. The skill loads a dedicated text reference file only when needed.

**Blocked by:** 01

**Status:** resolved

- [x] A text reference file inside the skill folder holds the HTML and Markdown snippets and the rules
- [x] HTML output: inline accessible SVG, text label, marker comment
- [x] Markdown output: SVG copied to the project's assets folder, image reference, text label, marker comment
- [x] The text label is translated to the document's language; the icon stays the official "AI"
- [x] Eval: an Italian article gets the Basic icon, "Generato con IA" and the marker
- [x] Eval: an English HTML page gets the accessible inline SVG and the marker

## Comments

**Built:** The text reference file `skills/eu-ai-labelling/references/text.md` holds the HTML and Markdown snippets and the rules, loaded only when a text label is needed. HTML gets an inline accessible SVG with `role="img"`, the translated text label and the marker comment. Markdown gets the official SVG copied into the project's assets folder, an image reference, the text label and the marker comment. The icon stays the official "AI" in every language. Partly AI-made documents are labelled only where the AI part is.

**Tested:** `tests/e2e/test_text_reference.py` (static checks on the snippets and rules) and the text scenarios in `tests/evals/scenarios/` (`italian-article.json`, `english-html-page.json`, `partly-ai-markdown-report.json`), run headlessly and opt-in. The default `uv run pytest` run passes: 161 passed, 23 skipped (headless tests skipped).

**Follow-ups:** 17 (text label language assertions).
