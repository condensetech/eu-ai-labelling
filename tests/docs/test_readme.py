"""The README against the shipped files and against what label_tool does.

Its install commands name the published plugin, its examples work in both
tools, it says no settings are stored, its disclaimers are
present word for word, and its placement defaults are what `apply` applies,
measured in the pixels of a copy labelled with the skill's own command.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from PIL import Image

from helpers import PLUGIN_NAME, REPO_ROOT, changed_box, doc_command, fenced, run_json, section

README = REPO_ROOT / "README.md"
PLUGIN_ID = f"{PLUGIN_NAME}@{PLUGIN_NAME}"
REPOSITORY = "condensetech/eu-ai-labelling"

EU_ICONS_PAGE = "https://digital-strategy.ec.europa.eu/en/policies/eu-icons-labelling-ai-generated-content"
CODE_OF_PRACTICE = "https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content"
GUIDELINES = "https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations"


def readme() -> str:
    return README.read_text()


def fenced_lines(text: str) -> list[str]:
    return [line.strip() for block in fenced(text) for line in block.splitlines() if line.strip()]


def test_readme_installs_the_published_plugin_in_both_tools():
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["repository"] == f"https://github.com/{REPOSITORY}"
    assert f"{plugin['name']}@{marketplace['name']}" == PLUGIN_ID
    install = section(readme(), "Install")
    lines = fenced_lines(install)

    assert f"/plugin marketplace add {REPOSITORY}" in lines
    assert f"/plugin install {PLUGIN_ID}" in lines
    assert f"codex plugin marketplace add {REPOSITORY}" in lines
    # Codex installs the plugin from its plugin browser.
    assert "/plugins" in install


@pytest.mark.parametrize("example", [
    "label photo.png as fully AI-generated",  # an image
    "label article.md as fully AI-generated",  # a text document
    "add AI labels to my site",  # a site
])
def test_readme_shows_a_usage_example_in_both_tools(example):
    text = readme()

    assert f"/eu-ai-labelling {example}" in text
    assert f"$eu-ai-labelling {example}" in text


def test_readme_projects_store_no_settings():
    projects = section(readme(), "Projects")

    assert "stores no settings" in projects
    assert ".eu-ai-labelling.json" not in readme() and "set up AI labelling" not in readme()
    assert "doesn't watch for unlabelled content" in projects


def test_readme_links_the_official_sources():
    sources = section(readme(), "Sources")

    for url in (EU_ICONS_PAGE, CODE_OF_PRACTICE, GUIDELINES):
        assert url in sources


def test_readme_states_non_affiliation_not_legal_advice_and_no_adherence_signal():
    text = re.sub(r"\s+", " ", readme())

    assert "not affiliated with" in text
    assert "European Commission" in text
    assert "Not legal advice" in text
    assert "doesn't signal adherence to the Code of Practice" in text


# --- Placement defaults ----------------------------------------------------------


def placement_defaults() -> dict[str, str]:
    """The README's placement-defaults table, as {setting: default}."""
    rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", section(readme(), "Placement defaults"), re.M)
    return {k: v for k, v in rows if not set(k) <= set("-: ") and k != "Setting"}


def label_photo(project: Path, size: tuple[int, int], background=(90, 160, 210)) -> tuple[dict, tuple[int, int, int, int]]:
    """Label project/photo.png with the skill's own apply command; return the report and the icon's box."""
    project.mkdir()
    original = project / "photo.png"
    Image.new("RGB", size, background).save(original)
    argv = doc_command("image.md", "apply", {"<image>": "photo.png", "<generated|modified>": "generated", "<tl|tr|bl|br>": "tr"})
    code, report = run_json(argv, project)
    assert code == 0, report
    return report, changed_box(original, project / "photo.ai-label.png")


def test_readme_documents_the_placement_defaults_as_the_plugins_own_choices():
    placement = re.sub(r"\s+", " ", section(readme(), "Placement defaults"))
    defaults = placement_defaults()

    assert "this plugin's own choices" in placement
    assert "The Code of Practice sets no minimum size, colour or margin" in placement
    assert set(defaults) == {"Corner", "Icon height", "Margin", "Icon Colour", "Fallback"}
    assert "top-right" in defaults["Corner"]
    assert "plate" in defaults["Fallback"]


@pytest.mark.parametrize("size", [(1500, 1000), (300, 200)], ids=["percentage", "minimum height"])
def test_readme_icon_height_and_margin_are_what_apply_applies(tmp_path, size):
    defaults = placement_defaults()
    height_pct, min_px = map(int, re.match(r"(\d+)% of the image's shorter side, at least (\d+) px", defaults["Icon height"]).groups())
    margin_pct = int(re.match(r"(\d+)% of the image's shorter side", defaults["Margin"]).group(1))
    shorter = min(size)

    report, (left, top, right, bottom) = label_photo(tmp_path / "project", size)

    # Top-right, at the documented size and margin, measured in the pixels.
    assert report["corner"] == "tr"
    assert bottom - top == pytest.approx(max(shorter * height_pct / 100, min_px), abs=1)
    assert top == pytest.approx(shorter * margin_pct / 100, abs=1)
    assert size[0] - right == pytest.approx(shorter * margin_pct / 100, abs=1)


def test_readme_contrast_threshold_is_the_one_label_tool_judges_by(tmp_path):
    ratio = float(re.search(r"at least (\d+(?:\.\d+)?):1 contrast", placement_defaults()["Icon Colour"]).group(1))
    project = tmp_path / "project"

    dark, _ = label_photo(project, (1000, 800), background=(20, 20, 30))
    score = doc_command("image.md", "score", {"<image>": "photo.png", "<generated|modified>": "generated"})
    _, scored = run_json(score, project)

    assert dark["colour"] == "white" and dark["plate"] is False
    assert scored["contrast_threshold"] == ratio
    assert scored["corners"]["tr"]["contrast"] >= ratio
