# 39: Let `references` point the project to the Labelled Copy itself

**What to build:** `references/update-references.md` step 2 is mechanical: in `file`, at `line`, replace `reference` with `replacement`, exactly, and change nothing else. The tool already reports all four. In a batch the agent makes many such edits by hand.

Fix: add `--apply` to `label_tool references`, which makes those edits (leaving `link` entries alone), and `--alt-mention "<text>"`, which appends ` (<text>)` to plain-text alts of `markdown-image`, `html-img` and the images of a `markdown-definition`, skipping alts that already carry the mention. Report what it changed, and list computed alts (`alt_expression`) and `other` references as `needs_hand_edit` for the agent. The agent still picks the mention's language.

**Blocked by:** None

**Status:** resolved

Source: review of the skill for checks that can be made deterministic (2026-11-03).

- [x] `--apply` rewrites each updatable reference except links, and nothing else in the file
- [x] `--alt-mention` appends to plain alts, fills an empty alt, and leaves an alt that already carries the mention unchanged
- [x] Computed alts and `other` references come back as `needs_hand_edit`
- [x] `update-references.md` steps 2 and 3 use the flags

## Comments

- What changed: `label_tool references <image> --apply [--alt-mention [FILE=]TEXT ...]` points each updatable reference except links to the Labelled Copy, and with a mention adds ` (TEXT)` after the alt of each `markdown-image`, `html-img` (quoted, unquoted or `{"..."}` literal alt; an `alt="..."` is added when there is none) and each image of a `markdown-definition` (a collapsed `![alt]` / `![alt][]` becomes `![alt (TEXT)][alt]`). An empty alt becomes the mention. `--alt-mention` is repeatable: a bare one for every page, `FILE=TEXT` for one page, since one project can mix languages. It prints `applied`, `alt_updated`, `alt_unchanged` (an alt that already carries the mention or a standalone AI / IA / KI) and `needs_hand_edit` (computed alts, `html-source`, `other`, and pages with no mention when others have one). `--alt-mention` without `--apply` is a usage error.
- Files are now read and written with their line endings as they are (`newline=""`), so `--apply` leaves CRLF files CRLF.
- `update-references.md`: step 2 chooses the mention per page language and runs `--apply`; step 3 covers what `needs_hand_edit` lists. `tests/helpers.doc_command` takes `with_flag` / `without_flag` to pick one of several commands.
- How tested: `tests/unit/test_references.py` (8 alt forms, links left alone, paths only without a mention, a per-page mention, an alt already saying AI, the three hand-edit cases, CRLF, the usage error); `tests/docs/test_project_references.py` runs step 2's command as written and checks nothing else on the pages changed. Fast suite: 483 passed, 1 xfailed (existing).
- Headless `markdown-site-references` with Sonnet, 3 runs: 3/3 before, 3/3 after. A captured run used one `--apply` call with `--alt-mention "Image generated with AI" --alt-mention "content/posts/trails.it.md=Immagine generata con IA"` and edited no page by hand.
