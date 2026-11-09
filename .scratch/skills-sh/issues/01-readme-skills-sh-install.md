# 01: Add a skills.sh install route to the README

**What to build:** A third install section in `README.md`, next to Claude Code and Codex, for any agent through the `skills` CLI. See [spec](../spec.md).

**Blocked by:** none

**Status:** resolved

- [x] The section shows `npx skills add condensetech/eu-ai-labelling`, with no `-a <agent>` pin: the CLI asks which agents to install into.
- [x] It mentions `-g` for a global install instead of the current project, and that the CLI needs Node 22.20 or later.
- [x] It says how to update (`npx skills update`) and how to pin a release (`condensetech/eu-ai-labelling@v0.1.0`).
- [x] It names the entry point the same way as the existing **Use** section (`/eu-ai-labelling` in Claude Code, `$eu-ai-labelling` in Codex). Check that this still holds for a skill installed this way, not as a plugin.
- [x] The Claude Code and Codex plugin sections stay as they are.
- [x] `tests/docs/test_readme.py` covers the new command.

**Note:** the pin is written `condensetech/eu-ai-labelling#v0.1.0`, not `@v0.1.0`. In `skills` CLI 1.7.0, `owner/repo@name` filters for a skill called `name`; a tag or branch goes after `#` (checked in `parseSource` and with `add ... --list`). The spec's "Pinning and updates" line still says `@<tag>`. The `v0.1.0` tag doesn't exist yet, so the pin example works only once it's pushed.
