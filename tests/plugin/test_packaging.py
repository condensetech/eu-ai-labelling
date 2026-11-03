"""The repository is an installable plugin for Claude Code and Codex.

These checks read the shipped files the way each tool does: the manifests, the
skill's frontmatter, and every path the skill tells the agent to use, resolved
from the skill folder of the published files (what git tracks, so a file left
untracked fails here). Codex is not installed here, so its manifest is checked
statically. `claude plugin validate` runs when the claude CLI is present.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from helpers import ICONS_DIR, PLUGIN_NAME, REPO_ROOT, SKILL_DIR

VARIANTS = ("basic", "generated", "modified")
COLOURS = ("black", "white", "black-50", "white-50")


def load_json(relative: str) -> dict:
    return json.loads((REPO_ROOT / relative).read_text())


def frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{skill_md} has no YAML frontmatter"
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def skill_text_files(skill_dir: Path) -> list[Path]:
    return [skill_dir / "SKILL.md", *sorted((skill_dir / "references").glob("*.md"))]


def expand(pattern: str) -> list[str]:
    """Expand `a-<x|y>-<p|q>` into every combination the skill text names."""
    parts = re.split(r"<([^<>]*\|[^<>]*)>", pattern)
    choices = [[p] if i % 2 == 0 else p.split("|") for i, p in enumerate(parts)]
    return ["".join(combo) for combo in itertools.product(*choices)]


def code_spans(text: str) -> list[str]:
    """Every line of fenced code blocks, then every inline code span outside them."""
    fence = re.compile(r"^[ \t]*```[^\n]*\n(.*?)^[ \t]*```[^\n]*$", re.S | re.M)
    spans = [line for block in fence.findall(text) for line in block.splitlines()]
    spans += re.findall(r"`([^`\n]+)`", fence.sub("", text))
    return spans


def referenced_paths(skill_dir: Path) -> set[str]:
    """Every skill-relative path in code (inline or fenced) in SKILL.md and its references.

    Placeholders such as `<skill folder>/` are stripped; `<a|b>` alternatives
    are expanded; other `<...>` placeholders (user files) are skipped.
    """
    found: set[str] = set()
    for doc in skill_text_files(skill_dir):
        for token in code_spans(doc.read_text()):
            for word in token.replace("<skill folder>/", "").split():
                if word.startswith("ai-") and word.endswith(".svg"):
                    word = f"assets/icons/{word}"  # the icon naming pattern
                if not re.match(r"(scripts|assets|references)/", word):
                    continue
                for path in expand(word):
                    if "<" not in path:
                        found.add(path)
    return found


# --- Claude Code -----------------------------------------------------------


def test_claude_marketplace_lists_the_plugin_from_this_repository():
    marketplace = load_json(".claude-plugin/marketplace.json")
    plugin = load_json(".claude-plugin/plugin.json")

    assert marketplace["name"] == PLUGIN_NAME
    entries = [p for p in marketplace["plugins"] if p["name"] == PLUGIN_NAME]
    assert len(entries) == 1
    # A source in the same repository is a ./ path, resolved from the
    # marketplace root (the repo). Codex reads this marketplace too, and
    # installs the Codex manifest from the same folder.
    path = entries[0]["source"] if isinstance(entries[0]["source"], str) else entries[0]["source"]["path"]
    assert path.startswith("./")
    source = (REPO_ROOT / path).resolve()
    assert source.is_relative_to(REPO_ROOT)
    assert (source / ".claude-plugin" / "plugin.json").is_file()
    assert (source / ".codex-plugin" / "plugin.json").is_file()
    assert plugin["name"] == PLUGIN_NAME
    assert entries[0].get("version", plugin["version"]) == plugin["version"]
    assert plugin["license"] == entries[0].get("license", "MIT") == "MIT"
    assert (REPO_ROOT / "LICENSE").read_text().startswith("MIT License")


@pytest.mark.claude_cli
@pytest.mark.parametrize("target", ["", ".claude-plugin/marketplace.json", ".claude-plugin/plugin.json"],
                         ids=["the plugin", "marketplace.json", "plugin.json"])
def test_claude_plugin_validate_accepts_the_plugin_and_its_manifests(target):
    proc = subprocess.run(
        ["claude", "plugin", "validate", "--strict", str(REPO_ROOT / target)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# --- Codex (static: codex CLI is not installed) -----------------------------


def test_codex_manifest_points_at_the_shared_skills_folder():
    codex = load_json(".codex-plugin/plugin.json")
    claude = load_json(".claude-plugin/plugin.json")

    assert codex["name"] == PLUGIN_NAME
    assert codex["version"] == claude["version"]
    assert codex["description"]
    assert codex["license"] == "MIT"
    skills_root = (REPO_ROOT / codex["skills"]).resolve()
    assert skills_root == (REPO_ROOT / "skills").resolve()
    assert (skills_root / PLUGIN_NAME / "SKILL.md").is_file()
    interface = codex["interface"]
    for field in ("displayName", "shortDescription", "developerName", "category"):
        assert isinstance(interface[field], str) and interface[field]
    assert isinstance(interface["defaultPrompt"], list) and interface["defaultPrompt"]


# --- The skill -------------------------------------------------------------


def test_skill_frontmatter_names_it_explicitly_for_both_tools():
    fields = frontmatter(SKILL_DIR / "SKILL.md")

    # The bare /eu-ai-labelling (Claude Code) and $eu-ai-labelling (Codex)
    # come from this name, which must also match the folder.
    assert fields["name"] == PLUGIN_NAME == SKILL_DIR.name
    assert fields["description"]
    assert len(fields["description"]) <= 1024


def test_every_path_the_skill_names_is_published_relative_to_the_skill_folder(published):
    skill_dir = published / "skills" / PLUGIN_NAME
    paths = referenced_paths(skill_dir)

    # The paths the image procedure depends on are among those named.
    assert "scripts/label_tool.py" in paths
    assert "references/image.md" in paths
    assert "references/text.md" in paths
    assert "references/creative-work.md" in paths
    assert "references/batch.md" in paths
    assert "references/site.md" in paths
    assert "references/update-references.md" in paths
    assert "assets/icons/SOURCE.md" in paths
    missing = sorted(p for p in paths if not (skill_dir / p).exists())
    assert not missing, f"skill names paths that are not published (missing or untracked): {missing}"


def test_the_skill_never_relies_on_claude_plugin_root():
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in SKILL_DIR.rglob("*")
        if path.is_file() and path.suffix in {".md", ".py", ".json", ".sh"}
        and "CLAUDE_PLUGIN_ROOT" in path.read_text()
    ]
    assert not offenders


def test_label_tool_declares_its_dependencies_inline():
    script = (SKILL_DIR / "scripts" / "label_tool.py").read_text()
    block = re.search(r"^# /// script\n(.*?)^# ///$", script, re.S | re.M)
    assert block, "label_tool.py has no PEP 723 inline metadata block"
    metadata = block.group(1).lower()
    assert "pillow" in metadata
    assert "resvg-py" in metadata


# --- The vendored EU Icons --------------------------------------------------


def test_all_twelve_official_svgs_are_vendored_with_normalised_names():
    expected = {f"ai-{v}-{c}.svg" for v in VARIANTS for c in COLOURS}
    vendored = {p.name for p in ICONS_DIR.glob("*.svg")}

    assert vendored == expected
    for name in expected:
        assert " " not in name
        root = ET.parse(ICONS_DIR / name).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg", name


def test_each_vendored_icon_matches_the_checksum_recorded_from_the_official_archive():
    """The checksums were taken from the Commission's archive, not from the
    vendored files: a redrawn or re-saved icon fails here."""
    source = (ICONS_DIR / "SOURCE.md").read_text()
    recorded = dict(re.findall(r"^- `(ai-[^`]+\.svg)`: `([0-9a-f]{64})`$", source, re.M))

    assert set(recorded) == {p.name for p in ICONS_DIR.glob("*.svg")}
    for name, digest in recorded.items():
        assert hashlib.sha256((ICONS_DIR / name).read_bytes()).hexdigest() == digest, name


def test_source_record_maps_each_icon_to_its_official_name_and_origin():
    source = (ICONS_DIR / "SOURCE.md").read_text()

    assert "https://digital-strategy.ec.europa.eu/" in source
    assert re.search(r"Retrieved:\s*\d{4}-\d{2}-\d{2}", source)
    rows = re.findall(r"^\|\s*`(ai-[^`]+\.svg)`\s*\|.*\|\s*`([^`]+\.svg)`\s*\|\s*$", source, re.M)
    mapping = dict(rows)
    assert set(mapping) == {p.name for p in ICONS_DIR.glob("*.svg")}
    assert len(set(mapping.values())) == 12, "each official file is mapped exactly once"

