# 43: Catch local edits to the vendored skills

**What to build:** The skills under `.agents/skills/` come from `mattpocock/skills`, pinned in `skills-lock.json` with a `computedHash` each, and `.claude/skills/*` are symlinks to them. A local edit to one of them goes unnoticed until the next update overwrites it.

Fix: if `computedHash` can be recomputed locally, add a check (test or script) that every lock entry has its folder and symlink and that each folder still matches its hash. If it can't, record that and close.

**Blocked by:** None

**Status:** resolved

Source: review of the skill for checks that can be made deterministic (2026-11-03).

- [x] Editing a vendored skill fails the check, or this ticket records why it can't be checked

## Comments

- The hash can be recomputed. It is the `skills` CLI's `computeSkillFolderHash` (read from skills 1.7.0, `dist/cli.mjs`): SHA-256 over each file's path relative to the skill folder followed by its bytes, files sorted with JavaScript's `localeCompare` (case-insensitive, so `agents/…` comes before `SKILL.md`), skipping `.git` and `node_modules`. `agents/openai.yaml` is part of it. Recomputed this way, all 38 entries match.
- What changed: `tests/plugin/test_vendored_skills.py` checks that `.agents/skills` holds exactly the locked skills, that each `.claude/skills/<name>` is a link to it, and that each folder matches its `computedHash`; a copy with a one-line edit to `SKILL.md` must fail. The failure message says to change the skill upstream or update it with the CLI. It runs in the fast suite, so CI (42) runs it.
- Limit: sorting by lower case, then the raw path, matches `localeCompare` for these ASCII names; a file name with accents or symbols could sort differently and give a false failure.
- How tested: 40 passed on macOS and in a Linux container (links survive the checkout). Fast suite: 553 passed, 1 xfailed (existing).
