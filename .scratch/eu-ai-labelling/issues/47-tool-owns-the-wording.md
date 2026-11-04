# 47: Serve the text-label wording from label_tool

**What to build:** The wording lives in four reference tables (`text.md`, `creative-work.md`, `site.md`, `update-references.md`), and `tests/docs/test_wording_tables.py` checks that they agree. The agent copies the phrase from a table and passes it to `snippet --label`. It also decides which language applies, from a precedence that is written only in prose: what the user asked, then `textLabelLanguage`, then the document. No code reads `textLabelLanguage`.

**This reverses the decision in 41.** 41 chose a docs test over a `label_tool` table so that each reference stands alone. It's being reversed for two new reasons: 48 needs the table inside the tool so that `verify` can tell a contradicting label, and the tool now works out the language itself.

Fix:

- **One table in `label_tool`**, for en, it, fr, es and de, with these forms for each language and wording (`generated`, `modified`):
  - the document/site label ("Generated with AI");
  - the image phrasing ("Image generated with AI"), used for captions, the icon's accessible name next to an image, and the alt-text mention;
  - the icon name ("AI", "IA", "KI").
- **`snippet` picks the wording.** It takes `--lang <code>` and `--document <path>`, and works out the language in this order:
  1. `--lang` (what the user asked for);
  2. `textLabelLanguage` from the project config found from the document;
  3. the document's declared language (`<html lang>`, front matter `lang`/`language`);
  4. otherwise it fails and asks for `--lang` or `--label`, so the agent judges the language from the body text.

  `--label` (with `--icon-name`) stays as free text for a language outside the table, and for a partial Label that names the part, such as "This section was generated with AI". The output says which language was used and where it came from.
- **`references --apply`** works out the language the same way for each page it edits. `--alt-mention` stays as the free-text fallback.
- **The references** drop their tables and point to the tool. Each one keeps one example row so it still reads on its own. `site.md` keeps the wording guidance for the component's `label` prop and gets the phrases from the tool. Replace `test_wording_tables.py` with tests of the table (the word for AI per language, the same icon name across forms).

**Blocked by:** None

**Status:** resolved

Source: grilling session on deterministic checks (2026-11-03), Q5 to Q8. Supersedes the decision recorded in 41.

- [x] `snippet --document post.md --wording generated` in a document with `lang: it` front matter prints "Generato con IA" with no `--label`
- [x] `textLabelLanguage` wins over the document's language; `--lang` wins over both
- [x] `references --apply` without `--alt-mention` writes each page's mention in that page's language
- [x] An unlisted language still works through `--label`/`--alt-mention`
- [x] The four reference tables are gone; the docs tests that run the references' commands still pass

## Comments

- What changed: `label_tool` holds `WORDING` (en, it, fr, es, de: `label`, `image`, `icon_name` per wording) and `resolve_language`: `--lang`, then the project's `textLabelLanguage` (config found from the document's folder, or the current folder), then the document's `<html lang>` or front matter `lang`/`language`. Regional codes use their language (`it-IT` is `it`).
- New `wording` subcommand prints the three phrases with `language` and `language_from`; fails with `language_unknown` or `language_not_listed`, each saying what to pass instead.
- `snippet`: `--label` is optional; without it the phrase comes from the table, via `--document`/`--lang`. New `--as caption` (same output as a Label, image phrasing), and `--as icon` takes the image phrasing too. `--label` without `--icon-name` takes the icon name from the table when the language is known (a partial Label in a listed language). Prints `label`, `language`, `language_from`.
- `references --apply --wording [--lang]`: each page's mention in its own language; a page with no known language, or outside the table, keeps its path change and goes to `needs_hand_edit` with the reason. `--alt-mention` (bare or per page) still wins.
- References: the four tables are gone. `text.md` Wording says how the language is settled and when to pass `--lang` or `--label`; `creative-work.md` uses `--as caption` and prints the alt-text phrase with `wording`; `site.md` gets the component's `label`/`iconAlt` from `wording --lang`; `update-references.md` step 2 uses `--wording`, step 3 prints hand mentions with `wording`; `project.md` says the tools read `textLabelLanguage` themselves.
- How tested: `tests/unit/test_wording.py` (the table per language, each phrase using the language's word for AI, the language order, both errors, snippet forms, a free-text partial Label, references per-page language and `--alt-mention` winning). `test_wording_tables.py` is removed; docs tests run every `snippet` command against a document that declares its language and every `wording` command as written, and step 2 of `update-references.md` as written (Italian page from the table, a page without a language left for step 3). Fast suite: 600 passed, 1 xfailed (existing). No headless run yet: the skill text changed, so `italian-article`, `creative-work-caption-italian` and `markdown-site-references` are the evals to run before a release.
- Beyond the ticket, and why: the `wording` subcommand (41 had turned it down; here `site.md` needs the phrases without printing a snippet, and the alt-text option and `update-references.md` step 3 edit alts by hand); `snippet --as caption` (a caption takes the image phrasing, where a document Label takes the plain one, and `--as label` couldn't tell them apart); `references --wording/--lang` (the ticket's "works out the language the same way" needed a wording to look up).
- After review (2026-11-03):
  - **`--apply` requires a mention.** Without `--wording` or `--alt-mention` it changed only paths and left every alt as it was, saying nothing. It now fails with a `usage` error before changing anything. The paths-only run had no documented use: `update-references.md` skips the whole step when the user wants the pages left alone.
  - **The language order is written once**, in `text.md` (**Wording**). `creative-work.md`, `site.md`, `update-references.md` and `project.md` point there. This removes `project.md`'s "Add `--lang` only when the user asks", which contradicted `site.md` passing `--lang` every time. `site.md`'s command now takes `--document <page>`, with `--lang` per language for a site with i18n. `update-references.md` loses "never the language the user writes to you in".
