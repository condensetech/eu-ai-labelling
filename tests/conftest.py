"""Shared fixtures for driving label_tool through its CLI seam, and the test markers.

Tests never import label_tool: they run it as a subprocess, exactly as the
skill does, and observe only its JSON output and the files it writes.

Folders:
  unit/     label_tool's subcommands, one behaviour per test.
  docs/     the skill's references and the README: the snippets and commands
            the agent copies, run or parsed as written.
  plugin/   manifests, packaging, and
            a real marketplace install (`claude_cli`).
  headless/ and evals/  the skill in headless Claude Code (`model`).

Markers:
  claude_cli  needs the claude CLI; skipped when it is not installed.
  model       calls the model; skipped unless EU_AI_LABELLING_E2E_DIR points
              at a throwaway directory and the claude CLI is installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from helpers import LABEL_TOOL, PLUGIN_NAME, REPO_ROOT


def pytest_collection_modifyitems(config, items):
    has_claude = shutil.which("claude") is not None
    has_scratch = bool(os.environ.get("EU_AI_LABELLING_E2E_DIR"))
    no_claude = pytest.mark.skip(reason="claude CLI not installed")
    no_model = pytest.mark.skip(
        reason="set EU_AI_LABELLING_E2E_DIR and install the claude CLI to run tests that call the model"
    )
    for item in items:
        if "model" in item.keywords and not (has_claude and has_scratch):
            item.add_marker(no_model)
        elif "claude_cli" in item.keywords and not has_claude:
            item.add_marker(no_claude)


@dataclass
class Result:
    returncode: int
    json: dict
    stderr: str


def run_label_tool(*args: str | Path, cwd: Path | None = None, env: dict | None = None) -> Result:
    """Run label_tool. `env` replaces variables in the environment it gets,
    such as PATH to hide or fake ffmpeg and ffprobe."""
    uv = shutil.which("uv")
    assert uv, "uv must be installed to run label_tool"
    proc = subprocess.run(
        [uv, "run", "--quiet", str(LABEL_TOOL), *map(str, args)],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=600,
        env={**os.environ, **env} if env else None,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"label_tool did not print JSON on stdout.\n"
            f"exit={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr}"
        )
    return Result(proc.returncode, payload, proc.stderr)


@pytest.fixture
def label_tool():
    return run_label_tool


@pytest.fixture(scope="session")
def published(tmp_path_factory) -> Path:
    """A copy of the files git tracks: what cloning the public repository gives.

    A file left untracked never reaches users, so it is left out here too.
    """
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True,
    ).stdout.decode().split("\0")
    root = tmp_path_factory.mktemp("published") / PLUGIN_NAME
    for relative in filter(None, listed):
        source = REPO_ROOT / relative
        if not source.is_symlink() and not source.exists():
            continue  # deleted in the working tree, so not published either
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
    return root
