"""End-to-end: after a Labelled Copy, the project's references point to it (ticket 10).

The `apply` command is taken verbatim from `references/image.md` and the
`references` commands of steps 1 and 2 from `references/update-references.md`
(only placeholders filled in), and all run from the user's project, never
from the skill folder. Step 2's `--apply` must point each page to the
Labelled Copy and add the mention to its alt, changing nothing else. Every kind, field and reason the tool reports must have a
rule in the procedure. The headless run of the whole path, alt text
included, is the `markdown-site-references` eval scenario.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import SKILL_DIR, digests, doc_command, run_json, sha256, step

UPDATE_MD = SKILL_DIR / "references" / "update-references.md"


POST = """\
---
title: Five trails for an autumn weekend
---

# Five trails for an autumn weekend

![A trail among yellow larches](../../public/images/hero.png)

From the lakeside loop to the ridge walk.
"""

PAGE = """\
<!DOCTYPE html>
<html lang="it">
<body>
  <img src="/images/hero.png" alt="Un sentiero tra i larici">
</body>
</html>
"""

COMPONENT = """\
const base = import.meta.env.BASE_URL;
export const hero = `${base}/images/hero.png`;
"""


@pytest.fixture
def project(tmp_path) -> Path:
    """A small site: a Markdown post, an Italian HTML page and a component using one image."""
    project = tmp_path / "site"
    (project / "public" / "images").mkdir(parents=True)
    Image.new("RGB", (1200, 800), (200, 220, 240)).save(project / "public" / "images" / "hero.png")
    for name, text in {"content/posts/trails.md": POST, "index.html": PAGE, "src/hero.js": COMPONENT}.items():
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_text(text)
    return project


def labelled(project: Path) -> Path:
    original = project / "public" / "images" / "hero.png"
    code, report = run_json(
        doc_command("image.md", "apply", {
            "<image>": str(original), "<generated|modified>": "generated", "<tl|tr|bl|br>": "tr",
        }),
        project,
    )
    assert code == 0, report
    return original


def test_references_command_run_from_the_users_project_finds_every_use(project):
    original = labelled(project)
    before = digests(project)

    code, report = run_json(
        doc_command("update-references.md", "references", {"<image>": str(original), "<project root>": str(project)},
                    without_flag="--apply"),
        project,
    )

    assert code == 0, report
    assert report["labelled_copy"] == str(project / "public" / "images" / "hero.ai-label.png")
    assert sorted((r["file"], r["kind"], r["alt"]) for r in report["updatable"]) == [
        ("content/posts/trails.md", "markdown-image", "A trail among yellow larches"),
        ("index.html", "html-img", "Un sentiero tra i larici"),
    ]
    assert [(r["file"], r["reason"]) for r in report["not_updatable"]] == [("src/hero.js", "dynamic")]
    # Finding references changes nothing.
    assert digests(project) == before


def test_step_2_run_as_written_points_each_page_to_the_copy_and_adds_the_mention(project):
    """Step 2's command: each page's mention comes from the wording table in
    that page's language; a page that declares none is left for step 3."""
    original = labelled(project)
    original_bytes = sha256(original)
    argv = doc_command(
        "update-references.md", "references",
        {"<image>": str(original), "<project root>": str(project), "<generated|modified>": "generated"},
        with_flag="--apply",
    )

    code, report = run_json(argv, project)

    assert code == 0, report
    post = (project / "content/posts/trails.md").read_text()
    page = (project / "index.html").read_text()
    assert '<img src="/images/hero.ai-label.png" alt="Un sentiero tra i larici (Immagine generata con IA)">' in page
    # The post declares no language: its path changes, its alt is left for step 3.
    assert POST.replace("hero.png", "hero.ai-label.png") == post, "something else on the page changed"
    hand = {(h["file"], h["kind"]) for h in report["needs_hand_edit"]}
    assert ("content/posts/trails.md", "markdown-image") in hand
    assert sorted(r["file"] for r in report["applied"]) == ["content/posts/trails.md", "index.html"]
    assert sha256(original) == original_bytes
    # Run again: nothing left to update, and the copy is never offered as a reference.
    _, again = run_json(
        doc_command("update-references.md", "references", {"<image>": str(original), "<project root>": str(project)},
                    without_flag="--apply"),
        project,
    )
    assert again["updatable"] == []
    assert [r["file"] for r in again["not_updatable"]] == ["src/hero.js"]


def test_every_field_step_2_prints_has_a_rule():
    text = step(UPDATE_MD.read_text(), "Point the references")
    for field in ("`applied`", "`alt_updated`", "`alt_unchanged`", "`needs_hand_edit`"):
        assert field in text, f"the {field} field is never explained"
    assert "--alt-mention <file>=<mention>" in text, "no word on pages in different languages"


# --- The procedure covers everything the tool reports ---------------------------


def test_every_kind_field_and_reason_the_tool_reports_has_a_rule():
    text = UPDATE_MD.read_text()
    find = step(text, "Find the references")
    for kind in ("markdown-image", "markdown-definition", "html-img", "html-source", "link", "other"):
        assert f"`{kind}`" in find, f"no rule for the `{kind}` kind"
    for field in ("`images`", "`alt`", "`alt_expression`", "`replacement`"):
        assert field in text, f"the {field} field is never explained"
    for reason in ("dynamic", "external", "unresolved"):
        assert f"`{reason}`" in find, f"no rule for a `{reason}` reference"
