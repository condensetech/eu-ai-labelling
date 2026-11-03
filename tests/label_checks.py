"""Is a text Label made as the skill says: the tests' definition of a well-made Label.

The evals, the snippet tests and the reference snippet tests hold every Label
to these checks. For each `<!-- eu-ai-labelling: ... -->` marker outside a code
block or backticks:

- the marker word is `generated` or `modified`, and an icon or an image follows it;
- an inline SVG icon has `role="img"`, an `aria-label`, and the official Basic
  path data in the official Black or White paint;
- an icon file (named like an official icon, or an SVG with the text label after
  it on its line) has alt text and is a byte-for-byte copy of an official Basic
  SVG in the project;
- an image labelled in its alt text has alt text.

Wording is judged by each test, where the scenario says what the Label reads.
"""

from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from functools import cache
from html.parser import HTMLParser
from pathlib import Path

from helpers import ICONS_DIR

ANY_MARKER = re.compile(r"<!--\s*eu-ai-labelling:\s*(.*?)\s*-->")
MARKER_WORDS = ("generated", "modified")
LABEL_TARGET = re.compile(r"<svg\b|<img\b|!\[", re.I)
MARKDOWN_IMAGE_AT = re.compile(r"!\[([^\]]*)\]\(\s*(<[^>\n]*>|[^)\s]+)[^)]*\)")
OFFICIAL_ICON_FILE = re.compile(r"(?:^|/)ai-(?:basic|generated|modified)-[a-z0-9-]+\.svg$", re.I)
SVG_NS = "{http://www.w3.org/2000/svg}"
TARGET_LINES = 3  # the target starts on the marker's line or within this many non-empty lines
COLOUR_NAMES = {"black": "#000", "#000000": "#000", "white": "#fff", "#ffffff": "#fff"}
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}


def style_declarations(style: str | None) -> dict:
    return {k.strip(): v.strip() for k, v in (d.split(":", 1) for d in (style or "").split(";") if ":" in d)}


def paint(fill: str | None, fill_rule: str | None) -> tuple:
    fill = (fill or "#000").strip().lower()
    return COLOUR_NAMES.get(fill, fill), (fill_rule or "nonzero").strip().lower()


@cache
def official_basic_icons() -> dict:
    paints, path_data = [], None
    for name in ("ai-basic-black.svg", "ai-basic-white.svg"):
        root = ET.parse(ICONS_DIR / name).getroot()
        css = "".join(s.text or "" for s in root.iter(SVG_NS + "style"))
        rules = {c: style_declarations(body) for c, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", css)}
        paths = list(root.iter(SVG_NS + "path"))
        path_data = [x.get("d") for x in paths]
        paints.append([paint(rules.get(x.get("class", ""), {}).get("fill"),
                             rules.get(x.get("class", ""), {}).get("fill-rule")) for x in paths])
    return {
        "basic_files": {x.read_bytes() for x in ICONS_DIR.glob("ai-basic-*.svg")},
        "all_files": {x.read_bytes(): x.name for x in ICONS_DIR.glob("ai-*.svg")},
        "path_data": path_data,
        "paints": paints,
    }


class FirstTags(HTMLParser):
    """The start tags of an HTML fragment, and the <path>s inside its first <svg>."""

    def __init__(self, fragment: str) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list = []
        self.paths: list = []
        self._in_svg = 0
        self.feed(fragment)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "svg":
            self._in_svg += 1
        elif tag == "path" and self._in_svg:
            self.paths.append(dict(attrs))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "svg":
            self._in_svg -= 1

    def handle_endtag(self, tag):
        if tag == "svg" and self._in_svg:
            self._in_svg -= 1


def fenced_ranges(text: str) -> list:
    ranges, start, fence, offset = [], 0, None, 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        opening = re.match(r"(`{3,}|~{3,})", stripped)
        if fence is None:
            if opening and len(line) - len(stripped) <= 3:
                fence, start = opening.group(1), offset
        elif stripped.startswith(fence) and not stripped.strip().strip(fence[0]):
            ranges.append((start, offset + len(line)))
            fence = None
        offset += len(line)
    if fence is not None:
        ranges.append((start, offset))
    return ranges


def local_file(target: str, document: Path, root: Path) -> Path | None:
    target = urllib.parse.unquote(target)
    if target.startswith("/"):
        candidates = [root / folder / target.lstrip("/") for folder in ("", "static", "public")]
    else:
        candidates = [document.parent / target]
    return next((c for c in candidates if c.is_file()), None)


def clean_path(target: str) -> str:
    return target.strip().strip("<>").split("#")[0].split("?")[0]


def captioned_after(text: str, at: int) -> bool:
    """Whether visible text follows on the same line: a caption's text label."""
    end = text.find("\n", at)
    return bool(re.sub(r"<[^>]*>", "", text[at:end if end >= 0 else len(text)]).strip())


def is_icon_file(path: str, captioned: bool) -> bool:
    return bool(OFFICIAL_ICON_FILE.search(path)) or (captioned and path.lower().endswith((".svg", ".svgz")))


def judge_inline_svg(text: str, at: int) -> list:
    end = text.lower().find("</svg>", at)
    if end < 0:
        return ["the inline SVG icon is never closed with </svg>"]
    parsed = FirstTags(text[at:end + len("</svg>")])
    attrs = parsed.tags[0][1] if parsed.tags else {}
    icons = official_basic_icons()
    problems = []
    if (attrs.get("role") or "").strip() != "img":
        problems.append('the inline SVG icon has no role="img"')
    if not (attrs.get("aria-label") or "").strip():
        problems.append("the inline SVG icon has no aria-label")
    if [x.get("d") for x in parsed.paths] != icons["path_data"]:
        problems.append("the inline SVG is not the official Basic EU Icon")
    else:
        painted = []
        for x in parsed.paths:
            props = {"fill": x.get("fill"), "fill-rule": x.get("fill-rule")}
            props.update({k: v for k, v in style_declarations(x.get("style")).items() if k in props})
            painted.append(paint(props["fill"], props["fill-rule"]))
        if painted not in icons["paints"]:
            problems.append("the inline SVG is not painted as the official Black or White Icon Colour")
    return problems


def judge_image(alt: str | None, target: str, captioned: bool, document: Path, root: Path) -> list:
    path = clean_path(target)
    if not is_icon_file(path, captioned):
        return [] if (alt or "").strip() else ["the image after the marker has no alt text to carry the Label"]
    problems = [] if (alt or "").strip() else [f"the icon {path} has no alt text"]
    if re.match(r"[a-z][a-z0-9+.-]*:|//", path, re.I):
        return problems  # served from elsewhere: nothing here to compare
    found = local_file(path, document, root)
    if found is None:
        return [*problems, f"the icon {path} is not a file in the project"]
    icons = official_basic_icons()
    data = found.read_bytes()
    if data not in icons["basic_files"]:
        name = icons["all_files"].get(data)
        problems.append(f"the icon {path} is {name}, not the Basic EU Icon" if name else
                        f"the icon {path} is not a byte-for-byte copy of an official Basic EU Icon")
    return problems


def judge_target(text: str, at: int, document: Path, root: Path) -> list:
    head = text[at:at + 4].lower()
    if head.startswith("<svg"):
        return judge_inline_svg(text, at)
    if head.startswith("<img"):
        tags = FirstTags(text[at:at + 4000]).tags
        attrs = tags[0][1] if tags else {}
        tag_end = text.find(">", at)
        after = tag_end + 1 if tag_end >= 0 else len(text)
        return judge_image(attrs.get("alt"), attrs.get("src") or "", captioned_after(text, after), document, root)
    image = MARKDOWN_IMAGE_AT.match(text, at)
    if image is None:
        return []
    return judge_image(image.group(1), image.group(2), captioned_after(text, image.end()), document, root)


def target_window_end(text: str, after: int) -> int:
    end = text.find("\n", after)
    if end < 0:
        return len(text)
    seen = 0
    while seen < TARGET_LINES:
        nxt = text.find("\n", end + 1)
        line = text[end + 1:nxt if nxt >= 0 else len(text)]
        end = nxt if nxt >= 0 else len(text)
        if line.strip():
            seen += 1
        if nxt < 0:
            break
    return end


def label_problems(document: Path, root: Path) -> dict:
    """{"labels": count, "problems": [{"line", "message"}]} for the Labels in `document`."""
    text = document.read_text(encoding="utf-8", errors="ignore")
    fences = fenced_ranges(text) if document.suffix.lower() in MARKDOWN_SUFFIXES else []
    markers = [
        m for m in ANY_MARKER.finditer(text)
        if not any(a <= m.start() < b for a, b in fences) and not (m.start() > 0 and text[m.start() - 1] == "`")
    ]
    problems = []
    for i, marker in enumerate(markers):
        line = text.count("\n", 0, marker.start()) + 1
        if marker.group(1) not in MARKER_WORDS:
            problems.append({"line": line, "message": f"the marker says {marker.group(1)!r}"})
        limit = target_window_end(text, marker.end())
        if i + 1 < len(markers):
            limit = min(limit, markers[i + 1].start())
        target = LABEL_TARGET.search(text, marker.end(), limit)
        if target is None:
            problems.append({"line": line, "message": "nothing follows the marker: no EU Icon and no image"})
            continue
        problems += [{"line": line, "message": m} for m in judge_target(text, target.start(), document, root)]
    return {"labels": len(markers), "problems": problems}
