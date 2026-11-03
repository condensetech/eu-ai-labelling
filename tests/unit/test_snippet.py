"""`label_tool snippet` and `copy-icons`: the Labels the agent inserts into
documents, built from the official Basic EU Icon rather than copied by hand.

The snippet's icon is checked against the vendored SVG files (path data and
per-path paint), and every form is put into a page and held to the tests'
checks of a well-made Label (`label_checks.py`).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import pytest

from helpers import ICONS_DIR
from label_checks import label_problems

SVG_NS = "{http://www.w3.org/2000/svg}"
COLOUR_NAMES = {"black": "#000", "#000000": "#000", "white": "#fff", "#ffffff": "#fff"}


def paint(fill, rule):
    fill = (fill or "#000").strip().lower()
    return COLOUR_NAMES.get(fill, fill), (rule or "nonzero").strip().lower()


def official(name: str) -> tuple[list[str], list[tuple[str, str]]]:
    """The path data and per-path paint of a vendored icon file."""
    root = ET.parse(ICONS_DIR / name).getroot()
    css = "".join(s.text or "" for s in root.iter(f"{SVG_NS}style"))
    rules = {c: dict((k.strip(), v.strip()) for k, v in (d.split(":", 1) for d in b.split(";") if ":" in d))
             for c, b in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", css)}
    paths = list(root.iter(f"{SVG_NS}path"))
    return [p.get("d") for p in paths], [
        paint(rules.get(p.get("class", ""), {}).get("fill"), rules.get(p.get("class", ""), {}).get("fill-rule"))
        for p in paths
    ]


class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.paths, self.text, self.titles = [], [], [], []
        self._svg = self._title = False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self._svg |= tag == "svg"
        self._title = tag == "title"
        if tag == "path":
            self.paths.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == "svg":
            self._svg = False
        self._title = False

    def handle_data(self, data):
        if self._title:
            self.titles.append(data)
        elif not self._svg and data.strip():
            self.text.append(data.strip())


def snippet(label_tool, *args: str) -> str:
    result = label_tool("snippet", *args)
    assert result.returncode == 0, result.json
    return result.json["snippet"]


@pytest.mark.parametrize("dark, icon_file", [(False, "ai-basic-black.svg"), (True, "ai-basic-white.svg")])
def test_html_label_inlines_the_official_icon_in_its_icon_colour(label_tool, dark, icon_file):
    text = snippet(label_tool, "--format", "html", "--wording", "modified", "--label", "Modificato con IA",
                   "--icon-name", "IA", *(["--dark"] if dark else []))

    assert text.startswith("<!-- eu-ai-labelling: modified -->\n<p class=\"eu-ai-label\"")
    reader = Reader()
    reader.feed(text)
    svg = next(attrs for tag, attrs in reader.tags if tag == "svg")
    assert svg["role"] == "img" and svg["aria-label"] == "IA"
    data, paints = official(icon_file)
    assert [p["d"] for p in reader.paths] == data
    assert [paint(p.get("fill"), p.get("fill-rule")) for p in reader.paths] == paints
    assert reader.text == ["Modificato con IA"]


def test_html_label_can_be_a_figcaption(label_tool):
    text = snippet(label_tool, "--format", "html", "--wording", "generated", "--label", "Image generated with AI",
                   "--icon-name", "AI", "--figcaption")

    assert '<figcaption class="eu-ai-label"' in text and text.rstrip().endswith("</figcaption>")


def test_markdown_label_references_the_copied_icon(label_tool):
    text = snippet(label_tool, "--format", "markdown", "--wording", "generated", "--label", "Generato con IA",
                   "--icon-name", "IA", "--icon-path", "../img/ai-basic-black.svg")

    assert text == "<!-- eu-ai-labelling: generated -->\n![IA](../img/ai-basic-black.svg) Generato con IA"


def test_html_text_is_escaped(label_tool):
    text = snippet(label_tool, "--format", "html", "--wording", "generated", "--label", 'Made with "AI" <beta> & co',
                   "--icon-name", "AI")

    assert "<span>Made with &quot;AI&quot; &lt;beta&gt; &amp; co</span>" in text


def test_a_label_needs_an_icon_name(label_tool):
    result = label_tool("snippet", "--format", "html", "--wording", "generated", "--label", "Generated with AI")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "usage"
    assert "--icon-name" in result.json["error"]["message"]


FORMS = [
    (fmt, form, dark, figcaption)
    for fmt in ("html", "markdown") for form in ("label", "caption") for dark in (False, True)
    for figcaption in ((False, True) if fmt == "html" else (False,))
]


@pytest.mark.parametrize("fmt, form, dark, figcaption", FORMS)
def test_every_form_is_a_well_made_label_in_a_page(tmp_path, label_tool, fmt, form, dark, figcaption):
    project = tmp_path / "site"
    project.mkdir()
    colour = "white" if dark else "black"
    assert label_tool("copy-icons", "--to", project / "assets", "--colour", colour).returncode == 0
    args = ["--format", fmt, "--as", form, "--wording", "generated", "--label", "Image generated with AI"]
    args += ["--icon-name", "AI"]
    args += ["--dark"] if dark else []
    args += ["--figcaption"] if figcaption else []
    text = snippet(label_tool, *args)
    if fmt == "html":
        page = project / "page.html"
        image = '<img src="satire.png" alt="A cartoon">\n' if form == "caption" else ""
        page.write_text(f"<html><body>\n<h1>Satire</h1>\n{image}{text}\n<p>Body.</p>\n</body></html>\n")
    else:
        page = project / "post.md"
        body = f"![A cartoon](satire.png)\n\n{text}\n" if form == "caption" else f"{text}\n"
        page.write_text(f"# Satire\n\n{body}\nBody.\n")

    result = label_problems(page, project)

    assert result["labels"] == 1
    assert result["problems"] == []


def test_copy_icons_copies_byte_for_byte_and_keeps_identical_copies(tmp_path, label_tool):
    folder = tmp_path / "site" / "public"

    first = label_tool("copy-icons", "--to", folder, "--colour", "both")
    again = label_tool("copy-icons", "--to", folder, "--colour", "both")

    names = ["ai-basic-black.svg", "ai-basic-white.svg"]
    assert [Path(p).name for p in first.json["copied"]] == names
    assert [Path(p).name for p in again.json["kept"]] == names and again.json["copied"] == []
    for name in names:
        assert (folder / name).read_bytes() == (ICONS_DIR / name).read_bytes()


def test_copy_icons_replaces_a_redrawn_icon(tmp_path, label_tool):
    folder = tmp_path / "assets"
    folder.mkdir()
    (folder / "ai-basic-black.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'><circle r='5'/></svg>")

    result = label_tool("copy-icons", "--to", folder)

    assert [Path(p).name for p in result.json["replaced"]] == ["ai-basic-black.svg"]
    assert (folder / "ai-basic-black.svg").read_bytes() == (ICONS_DIR / "ai-basic-black.svg").read_bytes()
    assert not (folder / "ai-basic-white.svg").exists()


def test_a_markdown_icon_path_with_spaces_is_a_well_made_label(tmp_path, label_tool):
    project = tmp_path / "site"
    assert label_tool("copy-icons", "--to", project / "my assets").returncode == 0
    text = snippet(label_tool, "--format", "markdown", "--wording", "generated", "--label", "Generated with AI",
                   "--icon-name", "AI", "--icon-path", "my assets/ai-basic-black.svg")
    page = project / "post.md"
    page.write_text(f"# Satire\n\n{text}\n\nBody.\n")

    result = label_problems(page, project)

    assert result["problems"] == []
