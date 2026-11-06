# 01: Installable plugin labels one image (tracer bullet)

**What to build:** A user installs `eu-ai-labelling` from the repository's marketplace in Claude Code or Codex. They invoke `/eu-ai-labelling` (Claude Code) or `$eu-ai-labelling` (Codex) and ask to "label photo.png as fully AI-generated". The single skill runs `label_tool apply`, which writes a Labelled Copy (`photo.ai-label.png`) with the Fully AI-Generated EU Icon burned in at the top-right, at default size, margin and colour. The original is untouched. This ticket sets up the whole path end to end:
- the Claude Code manifest, the Codex manifest and the marketplace file;
- the skill, with its frontmatter `name` set explicitly;
- the official SVGs, vendored with normalised names and a record of their source;
- the `label_tool` CLI, with dependencies declared inline and run via `uv run`;
- the MIT licence and a minimal README with the not-legal-advice statement.

All bundled files are referenced relative to the skill folder (see spec: Packaging, Asset and script paths).

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] The plugin installs via the marketplace in Claude Code; `/eu-ai-labelling` and `/eu-ai-labelling:eu-ai-labelling` resolve
- [x] The Codex manifest is valid and the skill is discoverable as `$eu-ai-labelling`
- [x] All 12 official SVGs are vendored with normalised file names, a mapping to the official names, and the source URL and retrieval date
- [x] `label_tool apply <image> --variant generated|modified --corner tr` writes `<name>.ai-label.<ext>` and outputs JSON with the path and the parameters used
- [x] The original file's bytes are unchanged after `apply`
- [x] Default size (6% of the shorter side, minimum 24 px) and margin (2%) are applied
- [x] pytest covers `apply` through the CLI: file created, original unchanged, icon in the expected corner and size, minimum size enforced on small images
- [x] The skill references the script and icons by paths relative to its own folder, never `${CLAUDE_PLUGIN_ROOT}`
- [x] MIT licence and a minimal README with the disclaimer are present

## Comments

Built the `eu-ai-labelling` plugin end to end: Claude Code manifest (`.claude-plugin/plugin.json`), marketplace file, Codex manifest (`.codex-plugin/`), the single skill `skills/eu-ai-labelling/SKILL.md` (explicit frontmatter `name`, bundled files referenced relative to the skill folder), the 12 official SVGs vendored with normalised names plus a mapping, source URL and retrieval date, and the `label_tool` CLI (PEP 723 inline deps, run via `uv run`). `apply` writes `<name>.ai-label.<ext>` with the EU Icon at the chosen corner, default size 6% of the shorter side (min 24 px) and 2% margin, and prints JSON with the path and parameters. MIT licence and README with the not-legal-advice statement added.

Testing: pytest drives `label_tool apply` as a subprocess (unit seam) — file created, original bytes unchanged, icon in expected corner and size, minimum size on small images, manifest/path checks. E2E: headless `claude -p --plugin-dir` run in a throwaway project confirms the skill resolves and produces a Labelled Copy (skipped when unavailable). Codex validated statically only (CLI not installed). Final run: 37 passed, 3 skipped.
