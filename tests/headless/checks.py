"""Checks on what a headless Claude Code session did and replied.

Shared by the model runs (test_headless_claude.py) and the canned-reply tests
(test_headless_checks.py), which hold each check to a compliant reply and to
weakened ones, so a check too loose to fail is caught without calling the model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

from helpers import ICON_MATCH, SVG, animation, changed_box, icon_match, sha256


# --- Reading the session ---------------------------------------------------------


def result_text(events: list[dict]) -> str:
    """The model's final reply to the user."""
    results = [e for e in events if e.get("type") == "result"]
    assert results, "headless run produced no result event"
    return results[-1].get("result", "")


def tool_uses(events: list[dict], name: str) -> list[dict]:
    """Every tool_use of the tool `name` the model made in the session."""
    return [
        block
        for e in events
        if e.get("type") == "assistant"
        for block in e.get("message", {}).get("content", [])
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == name
    ]


def label_tool_errors(events: list[dict], name: str) -> list[str]:
    """Error codes label_tool reported for `score` or `apply` runs on `name`.

    Pairs each Bash tool_use whose command runs `label_tool.py score` or
    `label_tool.py apply` on the file with its tool_result, and reads the
    `{"error": {"code": ...}}` JSON the tool printed there.
    """
    runs = {
        block["id"] for block in tool_uses(events, "Bash")
        if "label_tool.py" in (command := block.get("input", {}).get("command", ""))
        and re.search(r"\s(score|apply)\s", command) and name in command
    }
    codes = []
    for e in events:
        if e.get("type") != "user":
            continue
        for block in e.get("message", {}).get("content", []):
            if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                continue
            if block.get("tool_use_id") not in runs:
                continue
            content = block.get("content", "")
            if isinstance(content, list):
                content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
            start = content.find("{")
            try:
                payload = json.loads(content[start:]) if start >= 0 else {}
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
                codes.append(payload["error"].get("code"))
    return codes


# --- An unsupported image: the refusal relayed ------------------------------------

# "isn't supported", "unsupported", "doesn't support", "only labels still images", ...
NOT_SUPPORTED = re.compile(r"(not|n't|un)[ -]?support|only (labels|supports|handles|works with) still")
STILL_FORMATS = ("png", "jpeg", "jpg")


def assert_relays_refusal(events: list[dict], name: str, code: str, reason: str) -> None:
    """The skill ran label_tool, it refused with `code`, and the reply says
    so as image.md asks: the reason, that the format is not supported, and
    that a still PNG/JPEG/WebP version can be labelled instead. The reason and
    the suggestion must come from outside the file name."""
    assert code in label_tool_errors(events, name), "label_tool did not refuse the file in this session"
    reply = result_text(events).lower().replace("’", "'")
    reply_without_name = reply.replace(name, "")
    assert reason in reply_without_name, reply
    assert NOT_SUPPORTED.search(reply), reply
    assert any(fmt in reply_without_name for fmt in STILL_FORMATS), reply


# --- No clear corner: the agent asks ----------------------------------------------

# "top-right", "top right", "Top Right", ...
NAMED_CORNER = re.compile(r"\b(top|bottom)[- ]?(left|right)\b")


def named_corners(text: str) -> set[str]:
    """The distinct corners a reply names, as "top-left", "bottom-right", ..."""
    return {f"{v}-{h}" for v, h in NAMED_CORNER.findall(text.lower().replace("*", ""))}


def assert_asks_which_corner(project: Path, reply: str, asked_with_tool: bool = False) -> None:
    """No Labelled Copy was written, the reply weighs the corners (it names at
    least two of them, as image.md step 3 asks: "top-left: sky, clean; ...")
    and it asks the user which to use, in the reply or with a question tool,
    rather than giving up."""
    assert not (project / "photo.ai-label.png").exists(), reply
    assert len(named_corners(reply)) >= 2, f"the reply does not name the corners it weighs:\n{reply}"
    assert asked_with_tool or "?" in reply, f"the reply does not ask which corner to use:\n{reply}"


# --- A batch: a folder labelled in one request -------------------------------------

CORNER_WORDS = {"tl": "top-left", "tr": "top-right", "bl": "bottom-left", "br": "bottom-right"}
# The Fully AI-Generated Icon Variant, as a summary line names it.
GENERATED_VARIANT = re.compile(r"fully ai-generated|ai[- ]generated|\bgenerated\b")
# A corner, spelled out or as label_tool's code.
CORNER_NAME = re.compile(rf"{NAMED_CORNER.pattern}|\b(tl|tr|bl|br)\b")
LIST_ITEM = re.compile(r"^\s*(?:[-+]|\d+[.)])\s")
# beach.png and market.png have a free corner; crowd.png and rain.png none.
FREE = ("beach.png", "market.png")
UNCERTAIN = ("crowd.png", "rain.png")
REFUSED_OR_SKIPPED = ("loop.gif", "logo.svg", "old.ai-label.png")


def make_batch_folder(shots: Path) -> dict[str, str]:
    """A folder of mixed images, as a creator would have it; return each file's hash."""
    shots.mkdir(parents=True)
    Image.new("RGB", (1200, 800), (200, 220, 240)).save(shots / "beach.png")
    busy_top_right = Image.new("RGB", (1200, 800), (235, 235, 235))
    busy_top_right.paste(Image.effect_noise((600, 400), 120).convert("RGB"), (600, 0))
    busy_top_right.save(shots / "market.png")
    Image.effect_noise((1200, 800), 120).convert("RGB").save(shots / "crowd.png")
    Image.effect_noise((1000, 1000), 120).convert("RGB").save(shots / "rain.png")
    animation(shots / "loop.gif", "GIF")
    (shots / "logo.svg").write_text(SVG)
    Image.new("RGB", (600, 400), (240, 240, 240)).save(shots / "old.ai-label.png")
    return {p.name: sha256(p) for p in shots.iterdir()}


def list_heading(lines: list[str], index: int | None) -> str:
    """The non-empty line just above the list that holds `lines[index]`:
    its heading or lead-in, such as "Labelled (Fully AI-Generated):"."""
    if index is None:
        return ""
    for line in reversed(lines[:index]):
        if line.strip() and not LIST_ITEM.match(line):
            return line
    return ""


def placed_corners(shots: Path, reply: str) -> dict[str, str]:
    """The corner each image with a free corner was labelled in, read from its pixels."""
    placed = {}
    for name in FREE:
        copy = shots / name.replace(".png", ".ai-label.png")
        assert copy.is_file(), f"no Labelled Copy of {name}:\n{reply}"
        left, top, right, bottom = changed_box(shots / name, copy)
        assert icon_match(shots / name, copy, "generated") >= ICON_MATCH, f"{copy.name} carries no Fully AI-Generated icon"
        with Image.open(shots / name) as img:
            width, height = img.size
        placed[name] = ("t" if top < height / 2 else "b") + ("l" if left < width / 2 else "r")
    assert placed["beach.png"] == "tr"
    assert placed["market.png"] != "tr", "the label was put in market.png's busy top-right"
    return placed


def check_files(shots: Path, digests: dict[str, str], reply: str) -> list[str]:
    """Originals untouched, and Labelled Copies written only for the free images."""
    assert {n: sha256(shots / n) for n in digests} == digests, "a file of the batch was changed"
    written = sorted(p.name for p in shots.iterdir() if p.name not in digests)
    assert written == ["beach.ai-label.png", "market.ai-label.png"], f"{written}\n{reply}"
    return written


def check_one_question(text: str, reply: str) -> None:
    """The images with no free corner are asked about together. A headless run
    has one reply, so what counts is that the question covers both images,
    not how many question marks it uses."""
    # The question, and a list right before it of the images it then asks
    # about ("Which corner do you want for each?"). Prose before it is not
    # part of the question ("rain.png was left unlabelled.").
    blocks = re.split(r"\n\s*\n", text)

    def a_list(block: str) -> bool:
        # List items under a lead-in: a line ending in ":" or a heading, which
        # (its `**` already stripped) ends in no sentence punctuation.
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        items = [line for line in lines if re.match(r"(?:[-*]|\d+\.)\s", line)]
        return bool(items) and all(line in items or line.endswith(":") or not re.search(r"[.!?]$", line)
                                   for line in lines)

    asking = "\n\n".join(
        block for i, block in enumerate(blocks)
        if "?" in block or (i + 1 < len(blocks) and "?" in blocks[i + 1] and a_list(block))
    )
    assert asking, f"no question asked:\n{reply}"
    for name in UNCERTAIN:
        assert name in asking, f"the question doesn't cover {name}:\n{reply}"


def check_summary(text: str, placed: dict[str, str], written: list[str], reply: str) -> None:
    """Each Labelled Copy with its corner on its own line and its Icon Variant
    on that line or in its list's heading; refused and skipped files named, and
    never listed as labelled."""
    lines = text.splitlines()
    for name, corner in placed.items():
        copy = name.replace(".png", ".ai-label.png")
        index = next((i for i, l in enumerate(lines) if copy in l), None)
        line = lines[index] if index is not None else ""
        assert CORNER_WORDS[corner] in line or re.search(rf"\b{corner}\b", line), (
            f"{copy}'s corner ({CORNER_WORDS[corner]}) not on its summary line:\n{reply}"
        )
        # The prompt says "fully AI-generated", so the variant elsewhere proves nothing.
        assert GENERATED_VARIANT.search(line) or GENERATED_VARIANT.search(list_heading(lines, index)), (
            f"{copy}'s Icon Variant (Fully AI-Generated) not on its summary line or its list's heading:\n{reply}"
        )
    assert NOT_SUPPORTED.search(text), reply
    for name in REFUSED_OR_SKIPPED:
        assert name in text, f"{name} missing from the summary:\n{reply}"
        stem, ext = name.rsplit(".", 1)
        assert f"{stem}.ai-label.{ext}" not in text, f"{name} listed as labelled:\n{reply}"
        for line in (l for l in lines if name in l):
            if any(copy in line for copy in written):
                continue  # one line naming a real Labelled Copy too, as prose may
            assert not (GENERATED_VARIANT.search(line) and CORNER_NAME.search(line)), f"{name} listed as labelled:\n{reply}"


def check_batch(shots: Path, digests: dict[str, str], reply: str) -> None:
    """Ticket 07: every image placed on its own, the two with no free corner
    gathered into one question, unsupported files refused, the old Labelled
    Copy skipped, and a summary listing each Labelled Copy with its variant
    and corner."""
    text = reply.lower().replace("’", "'").replace("*", "").replace("`", "")
    written = check_files(shots, digests, reply)
    placed = placed_corners(shots, reply)
    check_one_question(text, reply)
    check_summary(text, placed, written, reply)
