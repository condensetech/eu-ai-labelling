"""A real marketplace install of the published plugin into Claude Code.

The install works on what the public repository serves: the files git
tracks (the `published` fixture). It runs the real `claude plugin` commands
against a throwaway CLAUDE_CONFIG_DIR, so the user's own configuration is
never touched; with no credentials there a session stops before reaching the
model, which still shows how the bare `/eu-ai-labelling` command resolves.
The installed skill's own command then labels an image from a user's project.

Codex is not installed here. What a Codex install depends on is checked
statically in test_packaging.py (the marketplace source and Codex manifest).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from helpers import (
    PLUGIN_NAME, changed_box, doc_command, run_json,
)

PLUGIN_ID = f"{PLUGIN_NAME}@{PLUGIN_NAME}"
AUTH_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")

pytestmark = pytest.mark.claude_cli


@pytest.fixture(scope="module")
def claude_install(published, tmp_path_factory) -> tuple[dict, Path]:
    """Install the published plugin from its marketplace into a throwaway Claude Code config."""
    config = tmp_path_factory.mktemp("claude-config")
    env = {k: v for k, v in os.environ.items() if k not in AUTH_ENV}
    env["CLAUDE_CONFIG_DIR"] = str(config)
    cwd = tmp_path_factory.mktemp("cwd")
    for args in (["marketplace", "add", "--json", str(published)], ["install", "--json", PLUGIN_ID]):
        proc = subprocess.run(["claude", "plugin", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    listed = subprocess.run(["claude", "plugin", "list", "--json"], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    plugin = next(p for p in json.loads(listed.stdout) if p["id"] == PLUGIN_ID)
    assert plugin["enabled"] is True
    return env, Path(plugin["installPath"])


def claude_expands(env: dict, project: Path, prompt: str) -> str:
    """The user message a headless session records for `prompt` (no credentials: no model call)."""
    message = json.dumps({"type": "user", "message": {"role": "user", "content": prompt}})
    proc = subprocess.run(
        ["claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json",
         "--verbose", "--replay-user-messages", "--allowedTools", "Read"],
        input=message, cwd=project, env=env, capture_output=True, text=True, timeout=300,
    )
    events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip().startswith("{")]
    users = [e for e in events if e.get("type") == "user"]
    assert users, proc.stdout + proc.stderr
    content = users[0]["message"]["content"]
    return content if isinstance(content, str) else json.dumps(content)


def test_claude_code_bare_command_resolves_to_the_installed_skill(claude_install, tmp_path):
    env, _ = claude_install

    bare = claude_expands(env, tmp_path, "/eu-ai-labelling label photo.png as fully AI-generated")
    unknown = claude_expands(env, tmp_path, "/eu-ai-labelling-nope label photo.png")

    assert "<command-name>/eu-ai-labelling:eu-ai-labelling</command-name>" in bare
    assert "label photo.png as fully AI-generated" in bare
    assert "<command-name>" not in unknown, "an unknown command should not resolve to a skill"


def test_claude_code_installed_skill_labels_an_image_with_its_own_tool_and_icons(claude_install, tmp_path):
    _, install_path = claude_install
    skill = install_path / "skills" / PLUGIN_NAME
    original = tmp_path / "photo.png"
    Image.new("RGB", (1000, 800), (90, 160, 210)).save(original)
    argv = doc_command(
        "image.md", "apply",
        {"<image>": "photo.png", "<generated|modified>": "generated", "<tl|tr|bl|br>": "tr"},
        skill_dir=skill,
    )
    assert str(skill) in " ".join(argv), "the command does not run the installed copy's tool"

    code, report = run_json(argv, tmp_path)

    assert code == 0, report
    assert report["variant"] == "generated"
    changed_box(original, tmp_path / "photo.ai-label.png")
