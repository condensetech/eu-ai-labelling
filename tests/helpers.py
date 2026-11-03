"""Helpers shared by every test folder: paths, test images, measurements and
the commands the skill's references tell the agent to run.

Tests never import label_tool: they run it as a subprocess, exactly as the
skill does (see conftest.py), and use these helpers to build inputs and read
what it wrote.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shlex
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageChops

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "eu-ai-labelling"
ICONS_DIR = SKILL_DIR / "assets" / "icons"
LABEL_TOOL = SKILL_DIR / "scripts" / "label_tool.py"
SKILL_MD = SKILL_DIR / "SKILL.md"
PLUGIN_NAME = "eu-ai-labelling"

CORNERS = ("tl", "tr", "bl", "br")
# A flat, mid-tone blue: the Black Icon Colour reaches about 7:1 on it.
BACKGROUND = (90, 160, 210)
DARK = (20, 20, 30)

# Width / height of the visible pill of each official EU Icon, read from the
# black pill path in assets/icons/ai-<variant>-black.svg (viewBox units). The
# aspect of the burned-in pixels tells the variants apart; the plain "AI"
# Basic icon would be a circle (aspect 1.0).
PILL_ASPECT = {
    "generated": (1591.54 - 207.30) / (410.77 - 144.36),  # "AI GENERATED", about 5.20
    "modified": (1461.67 - 231.11) / (410.77 - 144.36),  # "AI MODIFIED", about 4.62
}

# Luminance quantisation table from ITU-T T.81 Annex K (Table K.1), which
# libjpeg scales by quality: scale = 200 - 2q for q >= 50. A JPEG whose
# luminance steps sum to more than this was saved below quality 95.
ANNEX_K_LUMINANCE = [
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
]
QUALITY_95_LUMINANCE_SUM = sum(max(1, (b * 10 + 50) // 100) for b in ANNEX_K_LUMINANCE)  # 386


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digests(folder: Path) -> dict[Path, str]:
    """The hash of every file under `folder`."""
    return {p: sha256(p) for p in folder.rglob("*") if p.is_file()}


# --- Test images ---------------------------------------------------------------


def noise(size: tuple[int, int], low: int = 0, high: int = 255, seed: int = 1) -> Image.Image:
    """Greyscale noise as RGB: every pixel an independent random level in [low, high].

    Mid-grey noise (40..215) leaves neither a black nor a white icon at 3:1
    against every pixel, so `apply` backs the icon with a plate.
    """
    rng = random.Random(seed)
    img = Image.new("L", size)
    img.putdata([rng.randint(low, high) for _ in range(size[0] * size[1])])
    return img.convert("RGB")


def grey_and_white_stripes(grey: int, size: tuple[int, int] = (1000, 800)) -> Image.Image:
    """Vertical 4 px stripes, alternately `grey` and white.

    A flat grey can't sit near the 3:1 threshold (its best contrast is never
    below about 4.6:1). Half white pixels leave a white icon at 1:1, so the
    best icon is black, judged against the grey stripes: about 2.82:1 for
    grey 85 and 3.29:1 for grey 95.
    """
    img = Image.new("RGB", size, (255, 255, 255))
    for x in range(0, size[0], 8):
        img.paste((grey, grey, grey), (x, 0, x + 4, size[1]))
    return img


def animation(path: Path, pillow_format: str) -> Path:
    frames = [Image.new("RGB", (400, 300), c) for c in [(200, 30, 30), (30, 200, 30), (30, 30, 200)]]
    frames[0].save(path, format=pillow_format, save_all=True, append_images=frames[1:], duration=100, loop=0)
    return path


SVG = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
    '<rect width="400" height="300" fill="#5aa0d2"/></svg>\n'
)


def changed_box(original: Path, labelled: Path, threshold: int = 4) -> tuple[int, int, int, int]:
    """Bounding box (left, top, right, bottom) of the pixels the label changed."""
    with Image.open(original) as before, Image.open(labelled) as after:
        assert after.size == before.size, f"{labelled.name} changed size"
        diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
    box = diff.convert("L").point(lambda v: 255 if v > threshold else 0).getbbox()
    assert box, f"no pixels changed: {labelled.name} carries no icon"
    return box


# The official icon, matched in the pixels: what a Labelled Copy must carry.
ICON_MATCH = 0.9  # a burned-in icon scores about 0.95; the other variant or a plain rectangle about 0.8


def _icon_mask(image: Image.Image, colour: str) -> Image.Image:
    """The pixels of an icon's pill in `colour`: black or white."""
    grey = image.convert("L")
    return grey.point(lambda v: 255 if (v < 100 if colour == "black" else v > 155) else 0)


def _dense_box(mask: Image.Image) -> tuple[int, int, int, int] | None:
    """The mask's bounding box, ignoring sparse rows and columns (such as a
    noisy background showing at a plate's rounded corners)."""
    width, height = mask.size
    px = mask.load()
    rows = [sum(1 for x in range(width) if px[x, y]) for y in range(height)]
    cols = [sum(1 for y in range(height) if px[x, y]) for x in range(width)]
    if not max(rows, default=0):
        return None
    ys = [y for y, n in enumerate(rows) if n >= 0.25 * max(rows)]
    xs = [x for x, n in enumerate(cols) if n >= 0.25 * max(cols)]
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


def icon_match(original: Path, labelled: Path, variant: str) -> float:
    """How closely what the Labelled Copy adds matches the official `variant`
    icon (`generated` or `modified`), rendered independently with resvg: the
    intersection over union of the pill's pixels, at the size found, in black
    or white, whichever matches better. A backing plate around it is fine."""
    import io

    import resvg_py

    box = changed_box(original, labelled)
    with Image.open(labelled) as img:
        region = img.convert("RGB").crop(box)
    best = 0.0
    for colour in ("black", "white"):
        mask = _icon_mask(region, colour)
        found = _dense_box(mask)
        if found is None or found[2] - found[0] < 8 or found[3] - found[1] < 8:
            continue
        mask = mask.crop(found)
        png = resvg_py.svg_to_bytes(svg_path=str(ICONS_DIR / f"ai-{variant}-{colour}.svg"), height=mask.height * 8)
        icon = Image.open(io.BytesIO(bytes(png))).convert("RGBA")
        icon = icon.crop(icon.getchannel("A").getbbox())
        flat = Image.new("RGBA", icon.size, (128, 128, 128, 255))
        flat.alpha_composite(icon)
        reference = _icon_mask(flat, colour)
        reference = reference.crop(reference.getbbox()).resize(mask.size, Image.Resampling.BILINEAR)
        reference = reference.point(lambda v: 255 if v > 127 else 0)
        both = ImageChops.multiply(mask, reference).histogram()[255]
        either = ImageChops.lighter(mask, reference).histogram()[255]
        best = max(best, both / either if either else 0.0)
    return best


# --- Reading the skill's Markdown ---------------------------------------------


def fenced(text: str, lang: str = "") -> list[str]:
    """Bodies of the fenced blocks tagged `lang` (any tag when empty), dedented:
    a fence may sit inside a list item."""
    tag = re.escape(lang) if lang else r"[^\n]*"
    blocks = re.findall(rf"^([ \t]*)```{tag}\n(.*?)^[ \t]*```[ \t]*$", text, re.S | re.M)
    return [textwrap.dedent(body) if indent else body for indent, body in blocks]


def section(text: str, heading: str) -> str:
    """The body of the Markdown section titled `heading`, at any level, up to
    the next heading of the same level or above (its subsections included)."""
    match = re.search(rf"^(#+) {re.escape(heading)}\n", text, re.M)
    assert match, f"no `{heading}` section"
    level = len(match.group(1))
    # A `# ...` line inside a fenced block (a snippet, a shell comment) is no heading.
    fences = [m.span() for m in re.finditer(r"^[ \t]*```.*?^[ \t]*```[ \t]*$", text, re.S | re.M)]
    for end in re.finditer(rf"^#{{1,{level}}} ", text[match.end():], re.M):
        at = match.end() + end.start()
        if not any(start <= at < stop for start, stop in fences):
            return text[match.end(): at]
    return text[match.end():]


def step(text: str, title: str) -> str:
    """The numbered step whose bold title starts with `title`."""
    match = re.search(rf"^\d\. \*\*{re.escape(title)}.*?(?=^\d\. |^## |\Z)", text, re.S | re.M)
    assert match, f"no step **{title}...**"
    return match.group(0)


def table(text: str) -> dict[str, list[str]]:
    """A Markdown table as {first cell: other cells}, header and rule rows included."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.startswith("|")]
    return {row[0]: row[1:] for row in rows}


# --- Running the skill's own commands -------------------------------------------


def doc_command(reference: str, subcommand: str, fill: dict[str, str | list[str]], skill_dir: Path = SKILL_DIR,
                with_flag: str | None = None, without_flag: str | None = None) -> list[str]:
    """The one `label_tool.py <subcommand>` command `references/<reference>` tells
    the agent to run, with only its placeholders filled in. When the reference
    has several, `with_flag` / `without_flag` pick the one carrying a flag or not.

    The program, script path and every other argument come from the skill
    text, so a broken path or flag there fails the test that runs it. A
    list value fills one placeholder with several arguments.
    """
    procedure = (skill_dir / "references" / reference).read_text()
    commands = [
        line.strip() for block in fenced(procedure) for line in block.splitlines()
        if "label_tool.py" in line and f" {subcommand} " in line
        and (with_flag is None or with_flag in line) and (without_flag is None or without_flag not in line)
    ]
    assert len(commands) == 1, f"expected one {subcommand} command in {reference}, found {commands}"
    command = commands[0].replace("<skill folder>", "SKILL_FOLDER")
    for placeholder in [k for k in fill if " " in k]:  # e.g. `<project root>`
        command = command.replace(placeholder, shlex.quote(fill[placeholder]))
    argv = []
    for token in shlex.split(command):
        value = fill.get(token, token)
        for token in value if isinstance(value, list) else [value]:
            token = token.replace("SKILL_FOLDER", str(skill_dir))
            assert "<" not in token, f"unfilled placeholder {token!r} in {commands[0]!r}"
            argv.append(token)
    return argv


def run_json(argv: list[str], cwd: Path) -> tuple[int, dict]:
    """Run a label_tool command from `cwd`; return its exit code and JSON."""
    assert shutil.which(argv[0]), f"{argv[0]} must be installed"
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"no JSON on stdout:\n{proc.stdout}\n{proc.stderr}")
