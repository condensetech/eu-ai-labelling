# Distribution through skills.sh

The user confirmed this design on 2026-11-09, at the end of a grill-with-docs interview. It records what was agreed. Nothing has been implemented yet.

## Problem

The skill can be installed only as a Claude Code plugin or a Codex plugin. [skills.sh](https://www.skills.sh/) and its `skills` CLI (`npx skills add <owner/repo>`) install skills into any agent (Claude Code, Codex, Cursor, Gemini CLI, Copilot and others) and list them on a public leaderboard.

## Facts checked

- **Listing:** there is nothing to submit. A skill appears on skills.sh through the CLI's anonymous install telemetry, for public GitHub repos only, ranked by install count. `condensetech/eu-ai-labelling` is public.
- **The skill is already portable.** `skills/eu-ai-labelling/SKILL.md` has `name` and `description`, and it resolves `scripts/`, `assets/` and `references/` relative to its own folder, not through a plugin root.
- **Discovery:** on 2026-11-09, `npx -y skills add . --list` found exactly one skill, `eu-ai-labelling`. It did not offer the development skills under `.claude/skills/` and `.agents/skills/` (installed from `mattpocock/skills`, recorded in `skills-lock.json`).
- **What carries over:** only skill folders. Hooks, MCP servers and other plugin-only parts are not installed. The plugin has none since issue 54, so nothing is lost.
- **Pinning and updates:** users can pin `condensetech/eu-ai-labelling@<tag>`. `npx skills update` and `npx skills check` handle updates. The CLI needs Node 22.20 or later.

## Confirmed decisions

- **Only `eu-ai-labelling` is installable.** The development skills are the maintainers' tooling, not part of the product. No change is needed today. A CI check keeps it true.
- **skills.sh is an extra route.** The Claude Code marketplace and Codex plugin installs stay in the README.
- **README install command** is agent-neutral: `npx skills add condensetech/eu-ai-labelling`, with a note on `-g` for a global install and the Node 22.20+ requirement. No `-a <agent>` pin.
- **Release tags:** releases are tagged `v<version>`, matching the `version` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `.codex-plugin/plugin.json`. A test keeps those three equal. The first tag is `v0.1.0`. (`pyproject.toml`'s `0.0.0` is the test project's version, not the plugin's, and stays out of it.)
- **Discovery check runs the real CLI:** a separate CI job sets up Node 22, runs a pinned `skills` CLI version with `add . --list`, and fails unless the only skill listed is `eu-ai-labelling`. Copying the CLI's discovery rules into Python was rejected because it would go stale when the CLI changes.
- **If the discovery check ever fails** because development skills show up, the planned fix is: first declare `"skills": ["./skills/eu-ai-labelling"]` in `marketplace.json`; if that isn't enough, stop committing `.claude/skills/` and `.agents/skills/` and restore them from `skills-lock.json`. Editing their frontmatter (`metadata.internal`) is ruled out, because `npx skills update` would overwrite it.
