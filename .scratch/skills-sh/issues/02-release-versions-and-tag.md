# 02: Keep the manifest versions in step, and tag v0.1.0

**What to build:** A test that the plugin's three manifest versions agree, and the first release tag, so users can pin `condensetech/eu-ai-labelling@v0.1.0`. See [spec](../spec.md).

**Blocked by:** none

**Status:** ready-for-agent

- [ ] A fast test fails unless `version` in `.claude-plugin/plugin.json`, the plugin entry of `.claude-plugin/marketplace.json` and `.codex-plugin/plugin.json` are equal. `pyproject.toml` is left out.
- [ ] The README's **Tests** or release notes (wherever release steps fit best) say that a release bumps all three and is tagged `v<version>`.
- [ ] Tagging `v0.1.0` and pushing it is the maintainer's step, after this ticket and 01 and 03 are merged: the agent doesn't push tags.
