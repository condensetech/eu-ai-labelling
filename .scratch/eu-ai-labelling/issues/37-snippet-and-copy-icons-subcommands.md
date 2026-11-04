# 37: Generate the Label snippets and copy the icons with label_tool

**What to build:** The agent builds each text Label, caption and nearby icon by filling in snippets from `references/text.md` and `references/creative-work.md`, including the long official SVG path data. It copies icons with `cat <skill folder>/assets/icons/... > <folder>/...` in three places (`text.md`, `creative-work.md`, `site.md`).

Fix: add `label_tool snippet --format html|markdown --wording generated|modified --label "<text label>" --icon-name <name> [--dark] [--as label|caption|icon] [--icon-path <path>]`, which prints the exact block, and `label_tool copy-icons --to <folder> [--colour black|white|both]`, which copies the official Basic SVGs byte for byte, leaves existing identical copies alone and prints the paths. The references then tell the agent to run them and to decide only where the block goes.

**Blocked by:** None

**Status:** resolved

Source: review of the skill for checks that can be made deterministic (2026-11-03).

- [x] `snippet` prints the HTML and Markdown blocks the references show today, for both wordings and both icon colours
- [x] `copy-icons` writes byte-identical copies and is idempotent
- [x] `text.md`, `creative-work.md` and `site.md` use the subcommands instead of hand-copied path data and `cat`
- [x] The docs tests that run the snippets as written still pass

## Comments

- What changed: `label_tool snippet --format html|markdown --wording ... --label ... [--icon-name ...] [--as label|icon] [--dark] [--figcaption] [--icon-path ...]` prints the marker and the Label, building the inline SVG from the vendored `ai-basic-black.svg` / `ai-basic-white.svg` (path data and per-path paint), so nothing is copied by hand. `--as label` is the text Label and the caption (`<p>` or `<figcaption>`; Markdown image reference + text label); `--as icon` is the icon next to an image (HTML inline SVG with `<title>`; Markdown inline `<img>`). Text is HTML-escaped. `label_tool copy-icons --to DIR [--colour black|white|both]` copies byte for byte and reports `copied`, `kept` (identical copy already there) and `replaced` (a file of that name that was not the official icon).
- `text.md`, `creative-work.md` and `site.md` use the two commands; the long inline-SVG snippets, the "copy the three `d` attributes exactly" rule and the `cat` redirect (with its protected-file explanation) are gone. Short Markdown examples of each Label stay.
- The evals no longer pre-approve `Bash(mkdir:*)` and `Bash(cat:*)`: the skill needs only `uv run` for icons now, which also means fewer permission prompts for users.
- How tested: `tests/unit/test_snippet.py` (official paths and paint in both colours, role, names, escaping, figcaption, the icon form, a missing `--icon-name`, all 10 forms put in a page pass `verify`, copy-icons copied/kept/replaced). `tests/docs/test_label_snippets_verify.py` now runs every `snippet` and `copy-icons` command in the references as written (placeholders filled) and verifies the result, plus each Markdown example. The docs tests that parsed the old snippets are replaced by checks of the options the references name. Fast suite: 431 passed, 1 xfailed (existing). Plugin tests: 22 passed.
- Headless with Sonnet, 3 runs: `creative-work-caption-italian`, `english-html-page`, `italian-article`, `partly-ai-markdown-report` and `react-site-component` all 15/15 after, without `mkdir`/`cat` permissions; `react-site-component` 3/3 before.
