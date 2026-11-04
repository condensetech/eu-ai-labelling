# 42: Run the fast test suite automatically

**What to build:** The unit, docs and plugin tests keep the skill's text and `label_tool` in step (overrides, snippets, SVG bytes, the hook wiring), but nothing runs them automatically: the repository has no CI and no pre-commit hook.

Fix: run `uv run pytest -m "not model and not claude_cli"` in CI on every push, a pre-commit hook, or both.

**Blocked by:** None

**Status:** resolved

Source: review of the skill for checks that can be made deterministic (2026-11-03).

- [x] The fast suite runs without anyone starting it, and a failing test stops the change

## Comments

- What changed: `.github/workflows/tests.yml` runs `uv run pytest -m "not model and not claude_cli"` on every push and pull request (`actions/checkout@v4`, `astral-sh/setup-uv@v6`, `ubuntu-latest`). The README's Development section says so.
- Decision: CI only, no pre-commit hook. A git hook isn't versioned, so it would need each clone to install it, while CI covers every push.
- How tested: the same command in a Linux container (`ghcr.io/astral-sh/uv:python3.12-bookworm`) on a clean copy of the tracked files: 509 passed, 1 xfailed (existing), 4 skipped. Three site-reference tests skip because that image has no Node and one apply test skips when run as root; GitHub's `ubuntu-latest` runner has Node and runs as a non-root user, so all four should run there. The Python 3.8 hook tests ran (uv downloaded 3.8). The workflow itself takes effect once pushed; it has not run on GitHub yet.
