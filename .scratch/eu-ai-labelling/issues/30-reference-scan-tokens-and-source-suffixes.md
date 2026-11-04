# 30: Reference scan tokens, prose mentions and source file types

**What to build:** Follow-up from 10 (Updating references and alt text in a project). The reference scan in `skills/eu-ai-labelling/scripts/label_tool.py` (`REFERENCE_TOKEN`, `REFERENCE_SUFFIXES`, `cmd_references`) gives false or missing results in three ways:

- A Markdown image with a space in its path inside `<...>` is split at the space. `![x](<img/my hero.png>)` in `docs/a.md` reports a spurious `not_updatable` entry `{reference: 'hero.png', reason: 'unresolved'}` for a different image.
- Prose that only mentions a file name is reported as unresolved. The line `Photo credit: see hero.png in docs` in a `.txt` file gives the same spurious entry. This is why `.txt` is scanned at all.
- Source files in other languages are not scanned (`.py`, `.rb`, `.go`, `.java`, `.rs` and similar), so `x = "docs/img/hero.png"` in `src/m.py` appears in neither `updatable` nor `not_updatable`. The ticket says "source files", and step 4 of `update-references.md` does not mention this gap.

Fix: tokenise `<...>` destinations whole. Skip the unresolved entry when the token has no path separator and sits in prose, or drop `.txt` from `REFERENCE_SUFFIXES`. Add common source suffixes, or have step 4 tell the agent to list the unscanned file types the project uses.

**Blocked by:** None

**Status:** resolved

Source: ticket 10 (Updating references and alt text in a project), review findings (minor).

- [x] `![x](<img/my hero.png>)` yields no entry for `hero.png`
- [x] A bare file name in prose in a `.txt` file yields no `not_updatable` entry
- [x] References in at least the common source languages are found, or step 4 names the unscanned types the agent should list

## Triage (2026-11-02)

Decisions: tokenise `<...>` destinations whole. In `.txt` files, report only tokens that contain a path separator. Add `.py`, `.rb`, `.go`, `.java`, `.rs`, `.php` and `.cs` to the scanned suffixes.

## Comments

- What changed: `REFERENCE_TOKEN` matches a Markdown `](<...>)` destination whole, spaces included, and `MARKDOWN_IMAGE` takes the `<...>` form too. `.txt` is a prose suffix (`PROSE_SUFFIXES`): a token with no `/` in it is skipped there. `.py`, `.rb`, `.go`, `.java`, `.rs` and `.cs` are added to `REFERENCE_SUFFIXES` (`.php` was already scanned). `update-references.md` step 1 now names the scanned source languages.
- How tested: `test_an_angle_bracket_destination_is_one_path_even_with_spaces`, `test_a_plain_text_file_reports_only_paths_not_a_file_name_in_prose`, `test_finds_references_in_common_source_languages` (parametrised over `.py`, `.rb`, `.go`, `.java`, `.rs`, `.php`, `.cs`). Also `test_every_kind_the_tool_reports_has_a_rule` in `tests/e2e/test_project_references.py`. `uv run pytest` passes.
- Unaddressed minor review finding (not fixed here): a reference definition with a spaced `<...>` destination, `[r]: <img/my hero.png>`, is still split at the space by `REFERENCE_TOKEN`, which gives a spurious `not_updatable` `hero.png` entry with reason `unresolved`. The `]( <...>)` form is handled, but the definition form is not. Fix: also match `^\s{0,3}\[[^\]]+\]:\s*<([^<>\n]+)>` as a whole-destination token.
