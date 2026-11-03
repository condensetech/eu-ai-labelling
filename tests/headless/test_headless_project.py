"""Placement preferences said in the request, in headless Claude Code.

Calls the model (`model` marker): set EU_AI_LABELLING_E2E_DIR to a
throwaway directory; each test creates its own project inside it and runs
`claude -p --plugin-dir <repo>` there with a narrow tool allow-list.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from PIL import Image

from checks import result_text
from helpers import REPO_ROOT, changed_box

pytestmark = pytest.mark.model


def new_project() -> Path:
    project = Path(os.environ["EU_AI_LABELLING_E2E_DIR"]) / f"e2e-project-{uuid.uuid4().hex[:8]}"
    project.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)  # a project root
    return project


def run_claude(project: Path, prompt: str, tools: tuple[str, ...]) -> list[dict]:
    proc = subprocess.run(
        [
            "claude", "-p", prompt,
            "--model", "sonnet",
            "--plugin-dir", str(REPO_ROOT),
            "--allowedTools", *tools,
            "--output-format", "stream-json", "--verbose",
        ],
        cwd=project, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def test_skill_uses_the_corner_the_user_prefers_when_it_is_free():
    project = new_project()
    original = project / "public" / "images" / "photo.png"
    original.parent.mkdir(parents=True)
    Image.new("RGB", (1200, 800), (200, 220, 240)).save(original)

    events = run_claude(
        project,
        "/eu-ai-labelling label public/images/photo.png as fully AI-generated, bottom-left if it's free. "
        "I don't need a preview, just write the Labelled Copy.",
        tools=("Read", "Bash(uv run:*)"),
    )

    labelled = project / "public" / "images" / "photo.ai-label.png"
    assert labelled.is_file(), result_text(events)
    left, top, right, bottom = changed_box(original, labelled)
    # Bottom-left, 16 px (2% of 800) from the left and bottom edges, not top-right.
    assert left == pytest.approx(16, abs=1)
    assert 800 - bottom == pytest.approx(16, abs=1)
