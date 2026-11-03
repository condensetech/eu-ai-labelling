"""The vendored skills under .agents/skills match skills-lock.json.

They come from upstream (mattpocock/skills) through the `skills` CLI, which
records each folder's hash in skills-lock.json, and .claude/skills links to
them. A local edit would be lost at the next `skills` update, so it fails
here: change the skill upstream, or update the lock with the CLI.

The hash is the CLI's own (skills 1.7.0, `computeSkillFolderHash`): SHA-256
over each file's path relative to the skill folder, then its bytes, files in
case-insensitive path order (JavaScript's `localeCompare`), skipping `.git`
and `node_modules`.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from helpers import REPO_ROOT

LOCK = json.loads((REPO_ROOT / "skills-lock.json").read_text())["skills"]
VENDORED = REPO_ROOT / ".agents" / "skills"
LINKS = REPO_ROOT / ".claude" / "skills"


def folder_hash(folder: Path) -> str:
    files = [
        p for p in folder.rglob("*")
        if p.is_file() and not {".git", "node_modules"} & set(p.relative_to(folder).parts)
    ]
    files.sort(key=lambda p: (p.relative_to(folder).as_posix().lower(), p.relative_to(folder).as_posix()))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(folder).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_every_locked_skill_is_vendored_and_linked_and_nothing_else_is():
    assert sorted(p.name for p in VENDORED.iterdir() if p.is_dir()) == sorted(LOCK)
    for name in LOCK:
        link = LINKS / name
        assert link.is_symlink(), f".claude/skills/{name} is not a link"
        assert link.resolve() == (VENDORED / name).resolve(), f".claude/skills/{name} points elsewhere"


@pytest.mark.parametrize("name", sorted(LOCK))
def test_a_vendored_skill_matches_its_locked_hash(name):
    assert folder_hash(VENDORED / name) == LOCK[name]["computedHash"], (
        f".agents/skills/{name} differs from skills-lock.json: it was edited locally. "
        "Change it upstream, or update it with the skills CLI."
    )


def test_a_local_edit_is_caught(tmp_path):
    name = sorted(LOCK)[0]
    copy = tmp_path / name
    shutil.copytree(VENDORED / name, copy)
    assert folder_hash(copy) == LOCK[name]["computedHash"]

    skill = copy / "SKILL.md"
    skill.write_text(skill.read_text() + "\nA local note.\n")

    assert folder_hash(copy) != LOCK[name]["computedHash"]
