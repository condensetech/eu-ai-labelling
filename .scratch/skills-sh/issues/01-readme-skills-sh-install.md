# 01: Add a skills.sh install route to the README

**What to build:** A third install section in `README.md`, next to Claude Code and Codex, for any agent through the `skills` CLI. See [spec](../spec.md).

**Blocked by:** none

**Status:** ready-for-agent

- [ ] The section shows `npx skills add condensetech/eu-ai-labelling`, with no `-a <agent>` pin: the CLI asks which agents to install into.
- [ ] It mentions `-g` for a global install instead of the current project, and that the CLI needs Node 22.20 or later.
- [ ] It says how to update (`npx skills update`) and how to pin a release (`condensetech/eu-ai-labelling@v0.1.0`).
- [ ] It names the entry point the same way as the existing **Use** section (`/eu-ai-labelling` in Claude Code, `$eu-ai-labelling` in Codex). Check that this still holds for a skill installed this way, not as a plugin.
- [ ] The Claude Code and Codex plugin sections stay as they are.
- [ ] `tests/docs/test_readme.py` covers the new command.
