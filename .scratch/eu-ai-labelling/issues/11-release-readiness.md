# 11: Release readiness

**What to build:** The plugin is ready for public release at `condensetech/eu-ai-labelling`. The README covers:
- installation for both Claude Code and Codex;
- usage examples for images, text, sites and project setup;
- links to the official EU icons page, the Code of Practice and the Guidelines;
- the not-legal-advice statement;
- the note that using the icons doesn't signal adherence to the Code;
- the placement defaults, documented as the plugin's own choices.

A manual install check in both tools confirms the plugin works end to end.

**Blocked by:** 02, 03, 04, 05, 06, 07, 08, 09, 10

**Status:** resolved

- [x] The README is complete as described
- [x] Manual check in Claude Code: marketplace install, `/eu-ai-labelling` resolves, skill-relative assets and scripts resolve, hook fires in an opted-in project
- [x] Manual check in Codex: marketplace install, `$eu-ai-labelling` resolves, skill-relative assets and scripts resolve, hook fires in an opted-in project
  - **Done on 2026-11-02 with codex-cli 0.166.0** (see Comments). The original note follows:
  - **Covered statically only.** The Codex CLI is not installed where the release check runs, so `tests/e2e/test_release.py` only simulates the install. The simulation supplies these facts itself, and none of them has been seen in a real Codex:
    - `codex plugin marketplace add condensetech/eu-ai-labelling` reads `.claude-plugin/marketplace.json` (the test parses that file itself);
    - the `hooks` key in `.codex-plugin/plugin.json` is honoured, and Codex exports `PLUGIN_ROOT` to the hook (the test sets `PLUGIN_ROOT` itself);
    - the README's flow exists as written: install from `/plugins`, approve the hook once with `/hooks`.
  - This criterion stays unticked until a human installs the plugin in Codex and confirms each point above, plus `$eu-ai-labelling label photo.png as fully AI-generated` and the reminder after writing a file in a Content Path of an opted-in project. Fix the README or the manifest for any point that turns out wrong.
- [x] The full pytest suite passes (302 passed, 33 skipped: the headless tests and evals are opt-in)
- [ ] The headless evals pass (not run in this release pass; opt-in)

## Comments

**Built:** The README covers installation for Claude Code and Codex, usage for images, text, creative works, batches, sites and projects, the official sources, the not-legal-advice and no-adherence statements, and a Placement defaults section. `tests/e2e/test_release.py` checks the marketplace install, the `/eu-ai-labelling` resolution, the installed hook in an opted-in project, the Codex manifest and skill name statically, the README against the shipped files, and the placement defaults against `label_tool`.

**Tested:** `uv run pytest` (without the headless LLM tests): 302 passed, 33 skipped. The skips are the headless tests and evals, which need `EU_AI_LABELLING_E2E_DIR` and a live `claude` CLI.

**Still open:** The Claude Code hook firing was later confirmed in a real session (ticket 33). The Codex criterion was later checked in a real Codex (comment below). The headless evals were not run.

**Follow-ups:** 33 (real Claude Code hook-firing check), 34 (README Voluntary Label wording).

**Codex manual check (2026-11-02, codex-cli 0.166.0, macOS):** run against a local checkout, in a throwaway git project.
- `codex plugin marketplace add <checkout>` read `.claude-plugin/marketplace.json` with no `policy` field on the plugin entry. `codex plugin add eu-ai-labelling@eu-ai-labelling` installed and enabled the plugin into `~/.codex/plugins/cache/eu-ai-labelling/eu-ai-labelling/0.1.0`.
- `$eu-ai-labelling label public/images/hero.png as fully AI-generated` (`codex exec`) resolved the skill and ran its tool with the bundled icons. It wrote `hero.ai-label.png` with the icon at top right, left the original unchanged, and updated the `<img>` reference and alt text.
- `$eu-ai-labelling set up AI labelling for this project` wrote `.eu-ai-labelling.json` with `contentPaths: ["content/**/*.md"]`.
- Hook: until the hook was trusted, creating `content/second.md` produced no reminder, as expected. With `codex exec --dangerously-bypass-hook-trust`, creating `content/third.md` via `apply_patch` ran `PostToolUse`, and the model quoted the reminder verbatim: "eu-ai-labelling: content/third.md is in a Content Path of this project (.eu-ai-labelling.json) and carries no Label yet. …". So the manifest's `hooks` key is honoured and `PLUGIN_ROOT` reaches the hook command.
- Not exercised: adding the marketplace from GitHub (`condensetech/eu-ai-labelling`), the interactive `/plugins` install and the `/hooks` approval screen (the CLI equivalents and the trust bypass stood in for them), and the reminder going away once the file is labelled.
