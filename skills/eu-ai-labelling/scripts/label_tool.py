#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow>=10",
#     "resvg-py>=0.5",
# ]
# ///
"""label_tool: deterministic helpers for the eu-ai-labelling skill.

Run it with `uv run label_tool.py <subcommand> ...` (or `python3 label_tool.py`
when Pillow and resvg-py are installed). Every subcommand prints one JSON
object on stdout. On failure it prints `{"error": {...}}` and exits non-zero.

Subcommands:
  score <image> [--variant generated|modified] [--size PX] [--prefer CORNER]
      Judges each corner as a place for the Label: busyness (edge density),
      the Icon Colour with the best contrast, that contrast ratio and whether it
      reaches 3:1. Also reports the image's dimensions and a corner ranking,
      led by the preferred corner when it is free: the one the user asked for
      (`--prefer`), else the top-right.
  score <folder | image image ...> [--variant ...] [--size PX] [--prefer CORNER]
      Judges a batch: every image in the folder (not its subfolders) or every
      image listed. Prints `images` (each image's report plus its `path`),
      `refused` (files the tool cannot label, each with its `error`, including
      broken links as `not_found` and, in a list, a folder holding no image as
      `no_images`) and `skipped` (existing Labelled Copies, whatever the case
      of `.ai-label`). A path listed twice is judged once. One refused file
      never stops the batch; a folder given alone that holds no image fails
      with `no_images`.
  apply <image> --variant generated|modified [--corner tl|tr|bl|br]
        [--colour auto|black|white] [--size PX] [--plate|--no-plate]
      Writes a Labelled Copy `<name>.ai-label.<ext>` next to the image, with the
      EU Icon burned in. The original file is never modified. Accepts still
      PNG, JPEG (including camera MPO JPEGs, labelled as their main image) and
      WebP; keeps greyscale and CMYK in their colour space, the ICC profile and
      EXIF; re-encodes JPEG at quality 95.

Both subcommands refuse animated images (`animated_image`), SVG
(`svg_image`) and any other format, such as BMP, TIFF or a still GIF
(`unsupported_format`), and a Labelled Copy (`labelled_copy`); a batch
lists a Labelled Copy under `skipped` instead.

  references <image> [--root DIR]
      After `apply`, finds where the project under DIR (default: the current
      folder) uses the original image: in pages, Markdown, styles, templates,
      source and data files. Prints `updatable` (each literal reference that
      resolves to the original: `file`, `line`, `kind`, `reference`, its
      `replacement` pointing to the Labelled Copy, the image's `alt` text
      for a Markdown image or <img>, and `alt_expression`, the raw `{...}`
      when the <img> alt is computed rather than written out) and
      `not_updatable` (references it found but can't safely point to the
      copy, each with a `reason`). It changes no file. Fails with `no_labelled_copy` before `apply`.
  references <image> [--root DIR] --apply [--wording generated|modified [--lang CODE]]
             [--alt-mention [FILE=]TEXT ...]
      Points each updatable Markdown or HTML image reference (not a link, nor
      an `other` reference, which goes to `needs_hand_edit`) to the Labelled Copy and
      adds a mention to its alt text: `--alt-mention` as given, else, with
      `--wording`, the wording table's image phrasing in each page's language
      (see `wording`). Prints `applied`, `alt_updated`, `alt_unchanged` and
      `needs_hand_edit` (each with a `reason`). Edits that would overlap
      fail with `overlapping_edits` and change no page.

  wording --wording generated|modified [--lang CODE] [--document FILE]
      Prints the wording table's `label` (a document or site), `image` (a
      caption, the icon next to an image, the alt-text mention) and
      `icon_name` (the word for AI), with the `language` and `language_from`:
      `lang` (what the user asked for) or `document` (its <html lang> or
      front matter), in that order. Fails with `language_unknown` when
      neither says, and with
      `language_not_listed` for a language outside the table (en, it, fr,
      es, de): the agent then writes the text itself.

  snippet --format html|markdown --wording generated|modified [--document FILE]
          [--lang CODE] [--label TEXT] [--icon-name NAME] [--as label|caption]
          [--dark] [--figcaption] [--icon-path PATH]
      Prints `snippet`: the marker comment and a Label to insert into a
      document, built from the official Basic EU Icon, worded from the
      table in the document's language (as `wording`) unless `--label` gives
      free text. `--as label` (the default) is the icon with a visible text
      label at the top of a document (HTML: a <p>, or a <figcaption>;
      Markdown: an image reference to the copied icon); `--as caption` is the
      same below an image, worded for the image.
      `--dark` gives the White Icon Colour. Also prints the `label` used and
      its `language` and `language_from`.

  copy-icons --to DIR [--colour black|white|both]
      Copies the official Basic EU Icon SVGs into DIR byte for byte. Prints
      `copied`, `kept` (an identical copy already there) and `replaced` (a
      file of that name that was not the official icon).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
import urllib.parse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ICONS_DIR = SKILL_DIR / "assets" / "icons"

LABELLED_INFIX = ".ai-label"

# Placement defaults. These are this plugin's own choices: the Code of Practice
# sets no minimum size or margin. Sizes refer to the visible icon (the pill),
# not the official SVG canvas, which has wide transparent padding.
ICON_HEIGHT_RATIO = 0.06  # of the image's shorter side
ICON_MIN_HEIGHT_PX = 24
ICON_RENDER_MAX_PX = 4096  # cap on the oversampled render height, unless the icon itself is taller
MARGIN_RATIO = 0.02  # of the image's shorter side
JPEG_QUALITY = 95
WEBP_QUALITY = 95  # for lossy WebP; lossless WebP stays lossless

# Contrast. The 3:1 threshold is WCAG's minimum for graphical objects. The
# region under the icon is judged by its worst pixels, not its average, so a
# noisy region cannot pass on a flattering mean: a black icon is judged against
# the darkest pixels (this percentile), a white icon against the lightest.
CONTRAST_THRESHOLD = 3.0
CONTRAST_PERCENTILE = 0.10
CONTRAST_SAMPLE_PIXELS = 40_000  # sampled (nearest-neighbour) to bound the cost

# Busyness: the share of the region's pixels on an edge, i.e. whose edge-filter
# response exceeds EDGE_LEVEL. A corner above BUSY_THRESHOLD is "busy".
EDGE_LEVEL = 32
BUSY_THRESHOLD = 0.10

# Backing plate, used when neither black nor white reaches the threshold: an
# opaque rounded rectangle in the opposite colour, padded around the icon. On a
# small image the padding shrinks to fit, down to PLATE_MIN_PADDING_PX; below
# that no plate fits and the label goes on without one.
PLATE_PADDING_RATIO = 0.2  # of the icon height
PLATE_MIN_PADDING_PX = 2

# Transparency: a pixel shows whatever page it is published on, so it is judged
# against both a white and a black page. A corner is reported `transparent` when
# more than this share of its pixels are not (nearly) opaque.
OPAQUE_ALPHA = 250
TRANSPARENT_SHARE = 0.01
PLATE_COLOURS = {"black": (255, 255, 255, 255), "white": (0, 0, 0, 255)}

VARIANTS = ("generated", "modified")
CORNERS = ("tl", "tr", "bl", "br")
# Order of preference among corners that are equally good: the Code of
# Practice suggests the top-right.
CORNER_PREFERENCE = ("tr", "tl", "br", "bl")
DEFAULT_CORNER = CORNER_PREFERENCE[0]  # the top-right, as the Code of Practice suggests
COLOURS = ("black", "white")  # the opaque Icon Colours; the 50% ones are vendored but not applied
AUTO = "auto"


class LabelToolError(Exception):
    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details  # extra fields of the JSON error, such as `issues`


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")


def labelled_copy_path(original: Path) -> Path:
    return original.with_name(f"{original.stem}{LABELLED_INFIX}{original.suffix}")


def render_icon(variant: str, colour: str, height: int):
    """Render the official SVG and return the visible icon, `height` px tall."""
    import resvg_py
    from PIL import Image

    svg_path = ICONS_DIR / f"ai-{variant}-{colour}.svg"
    # Render well above the target size, crop away the SVG's transparent
    # padding, then downsample, so edges stay crisp at any size. Large icons
    # need less oversampling, so the render is capped near the target size.
    render_height = max(height, min(max(height, 64) * 8, ICON_RENDER_MAX_PX))
    png = resvg_py.svg_to_bytes(svg_path=str(svg_path), height=render_height)
    icon = Image.open(io.BytesIO(bytes(png))).convert("RGBA")
    icon = icon.crop(icon.getchannel("A").getbbox())
    width = max(1, round(icon.width * height / icon.height))
    return icon.resize((width, height), Image.Resampling.LANCZOS)


def icon_size(variant: str, height: int) -> tuple[int, int]:
    """The (width, height) render_icon gives for `height`, without rendering it that large."""
    reference = render_icon(variant, "black", ICON_MIN_HEIGHT_PX)
    return max(1, round(reference.width * height / reference.height)), height


def fitted_icon(variant: str, image_size, icon_height: int, margin: int):
    """Render the black icon for judging, refusing an image too small for it first."""
    check_fits(image_size, icon_size(variant, icon_height), margin)
    icon = render_icon(variant, "black", icon_height)
    check_fits(image_size, icon.size, margin)
    return icon


def icon_position(corner: str, image_size, icon_size, margin: int) -> tuple[int, int]:
    image_w, image_h = image_size
    icon_w, icon_h = icon_size
    x = margin if corner[1] == "l" else image_w - margin - icon_w
    y = margin if corner[0] == "t" else image_h - margin - icon_h
    return x, y


def to_eight_bit(source):
    """Return `source` in a mode that converts to RGBA without losing the picture.

    Pillow's conversion of 16- and 32-bit integer greyscale to RGBA clips every
    value above 255, which turns a 16-bit PNG white. Scale those to 8-bit first.
    """
    if source.mode.startswith("I;16") or source.mode == "I":
        scaled = source.convert("I").point(lambda v: v / 256).convert("L")
        # Keep EXIF (for orientation). A 16-bit transparent grey level has no
        # exact 8-bit equivalent, so it is dropped rather than mis-scaled.
        scaled.info.update({k: v for k, v in source.info.items() if k != "transparency"})
        return scaled
    return source


ORIENTATION_TAG = 0x0112


def kept_metadata(source) -> dict:
    """The original's colour profile and EXIF, as Pillow `save()` options.

    The EXIF Orientation tag is dropped: the Labelled Copy's pixels are already
    upright, so keeping it would make viewers rotate the picture a second time.
    """
    kept = {}
    if source.info.get("icc_profile"):
        kept["icc_profile"] = source.info["icc_profile"]
    from PIL import Image

    # Work on a copy: `getexif()` is cached on the image, and the orientation
    # transpose that follows still needs the original tag.
    exif = Image.Exif()
    exif.load(source.getexif().tobytes())
    exif.pop(ORIENTATION_TAG, None)
    if len(exif):
        kept["exif"] = exif.tobytes()
    return kept


GREY_MODES = ("1", "L", "LA")


def burn_in(source, overlay):
    """Return `source` with the full-size RGBA `overlay` (plate and icon)
    composited on it, in a mode whose colour space matches the original's, so
    its colour profile stays valid.

    Greyscale stays greyscale and CMYK stays CMYK; everything else becomes RGB,
    with an alpha channel only when the original had transparency.
    """
    has_alpha = "A" in source.getbands() or "transparency" in source.info
    if source.mode == "CMYK":
        # Paint the label straight onto the CMYK pixels: every pixel outside it
        # keeps its exact original ink values.
        labelled = source.copy()
        labelled.paste(overlay.convert("RGB").convert("CMYK"), (0, 0), overlay.getchannel("A"))
        return labelled
    canvas = source.convert("RGBA")
    canvas.alpha_composite(overlay)
    if source.mode in GREY_MODES:
        return canvas.convert("LA" if has_alpha else "L")
    return canvas if has_alpha else canvas.convert("RGB")


# ICC header bytes 16:20: the colour space of the data the profile describes.
PROFILE_SPACE = {"L": b"GRAY", "LA": b"GRAY", "RGB": b"RGB ", "RGBA": b"RGB ", "CMYK": b"CMYK"}


def matching_profile_only(metadata: dict, mode: str) -> dict:
    """Drop the ICC profile when it describes a different colour space from the
    Labelled Copy's pixels: such a profile is invalid and viewers reject it."""
    profile = metadata.get("icc_profile")
    if profile and profile[16:20] != PROFILE_SPACE.get(mode):
        return {k: v for k, v in metadata.items() if k != "icc_profile"}
    return metadata


def is_lossless_webp(path: Path) -> bool:
    """True when the WebP file holds a lossless (VP8L) bitstream."""
    with path.open("rb") as handle:
        data = handle.read()
    offset = 12  # past "RIFF", size, "WEBP"
    while offset + 8 <= len(data):
        chunk, size = data[offset:offset + 4], int.from_bytes(data[offset + 4:offset + 8], "little")
        if chunk == b"VP8L":
            return True
        if chunk == b"VP8 ":
            return False
        offset += 8 + size + (size & 1)
    return False


def encoder_options(image_format: str | None, original: Path) -> dict:
    """Encoder settings that keep labelling from visibly degrading the picture."""
    if image_format == "JPEG":
        # High quality and no chroma subsampling.
        return {"quality": JPEG_QUALITY, "subsampling": 0}
    if image_format == "WEBP":
        if is_lossless_webp(original):
            return {"lossless": True}
        return {"quality": WEBP_QUALITY}
    return {}


SVG_SUFFIXES = (".svg", ".svgz")
SUPPORTED_FORMATS = ("PNG", "JPEG", "WEBP")


# XML prolog items that may precede the root element: declaration, processing
# instructions, comments and a DOCTYPE.
_XML_PROLOG_ITEM = re.compile(r"\s*(<\?.*?\?>|<!--.*?-->|<!DOCTYPE[^>]*>)", re.DOTALL | re.IGNORECASE)


def looks_like_svg(path: Path) -> bool:
    """True when the file is XML whose root element is `<svg`."""
    with path.open("rb") as handle:
        head = handle.read(8192).decode("utf-8", errors="ignore").lstrip("\ufeff")
    while match := _XML_PROLOG_ITEM.match(head):
        head = head[match.end():]
    return re.match(r"\s*<(\w+:)?svg[\s>/]", head) is not None


# The refusal of an animated or SVG image, worded as the user should read it:
# the skill relays `error.message` as written, so the wording lives here only.
STILL_ONLY = "{kind} aren't supported yet: a still PNG, JPEG or WebP version can be labelled instead."


def svg_refusal(path: Path) -> LabelToolError:
    return LabelToolError(
        "svg_image",
        f"{path.name} is an SVG image. {STILL_ONLY.format(kind='SVG images')}",
    )


def open_image(path: Path):
    """Open a still image in the orientation viewers display, in an 8-bit mode.

    Returns (image, format, metadata), where metadata holds the ICC profile and
    EXIF to carry over. Refuses SVG (`svg_image`), animated images
    (`animated_image`) and any other format than PNG, JPEG and WebP
    (`unsupported_format`), even one Pillow can read.
    """
    from PIL import Image, ImageOps

    if not path.is_file():
        raise LabelToolError("not_found", f"Image not found: {path}")
    if path.suffix.lower() in SVG_SUFFIXES:
        raise svg_refusal(path)
    try:
        source = Image.open(path)
        source.load()
    except Exception as exc:  # Pillow raises several types for unreadable files
        if looks_like_svg(path):
            raise svg_refusal(path)
        raise LabelToolError("unreadable_image", f"Cannot read {path} as an image: {exc}")
    image_format = source.format
    if image_format == "MPO":
        # A camera or phone JPEG carrying a second image (a large preview or an
        # Ultra HDR gain map) via MPF. It is one still photo: label the primary
        # image (frame 0, already loaded) and write an ordinary JPEG.
        image_format = "JPEG"
    elif getattr(source, "is_animated", False):
        raise LabelToolError(
            "animated_image",
            f"{path.name} is an animated {source.format} image ({source.n_frames} frames). "
            + STILL_ONLY.format(kind="Animated images"),
        )
    if image_format not in SUPPORTED_FORMATS:
        raise LabelToolError(
            "unsupported_format",
            f"{path.name} is a {image_format} image. Only PNG, JPEG or WebP images can be labelled: "
            "a copy saved in one of those formats can be labelled instead.",
        )
    metadata = kept_metadata(source)
    source = to_eight_bit(source)
    # Work in the orientation viewers display: a phone JPEG often stores its
    # pixels sideways plus an EXIF Orientation tag. Transposing first puts the
    # icon upright in the corner the user sees, and the copy (saved without that
    # tag) displays the same way as the original.
    source = ImageOps.exif_transpose(source)
    return source, image_format, metadata


def icon_geometry(image_size, size_override: int | None) -> tuple[int, int]:
    """Return (icon height, margin) in pixels for an image of `image_size`."""
    shorter_side = min(image_size)
    if size_override is None:
        icon_height = max(ICON_MIN_HEIGHT_PX, round(shorter_side * ICON_HEIGHT_RATIO))
    elif size_override < ICON_MIN_HEIGHT_PX:
        raise LabelToolError(
            "size_too_small",
            f"Icon height {size_override} px is below the {ICON_MIN_HEIGHT_PX} px minimum.",
        )
    else:
        icon_height = size_override
    return icon_height, round(shorter_side * MARGIN_RATIO)


def plate_padding(image_size, icon_size, margin: int) -> int | None:
    """Padding for a plate around `icon_size`, shrunk to fit; None when none fits."""
    wanted = max(PLATE_MIN_PADDING_PX, round(icon_size[1] * PLATE_PADDING_RATIO))
    room = min(image_size[0] - 2 * margin - icon_size[0],
               image_size[1] - 2 * margin - icon_size[1]) // 2
    pad = min(wanted, room)
    return pad if pad >= PLATE_MIN_PADDING_PX else None


def plated(icon_size, pad: int | None) -> tuple[int, int]:
    """The label's footprint: the icon, plus its plate's padding when there is one."""
    if pad is None:
        return tuple(icon_size)
    return icon_size[0] + 2 * pad, icon_size[1] + 2 * pad


def check_fits(image_size, footprint_size, margin: int) -> None:
    if footprint_size[0] + 2 * margin > image_size[0] or footprint_size[1] + 2 * margin > image_size[1]:
        raise LabelToolError(
            "image_too_small",
            f"Image {image_size[0]}x{image_size[1]} is too small for a "
            f"{footprint_size[0]}x{footprint_size[1]} px label with a {margin} px margin.",
        )


def corner_region(corner: str, image_size, footprint_size, margin: int) -> tuple[int, int, int, int]:
    """The area a label of `footprint_size` covers in `corner`, plus its margin all round."""
    x, y = icon_position(corner, image_size, footprint_size, margin)
    return (
        max(0, x - margin),
        max(0, y - margin),
        min(image_size[0], x + footprint_size[0] + margin),
        min(image_size[1], y + footprint_size[1] + margin),
    )


def _linear(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


_LINEAR = [_linear(v) for v in range(256)]


def judge_contrast(region) -> dict:
    """Worst-case contrast of a black and of a white icon over `region`.

    Returns {"black": ratio, "white": ratio, "transparent": bool}. Transparent
    pixels show the page the image is published on, which may be light or dark,
    so the region is judged composited over both a white and a black page.
    """
    from PIL import Image

    rgba = region.convert("RGBA")
    pixels = rgba.width * rgba.height
    if pixels > CONTRAST_SAMPLE_PIXELS:
        scale = (CONTRAST_SAMPLE_PIXELS / pixels) ** 0.5
        rgba = rgba.resize(
            (max(1, int(rgba.width * scale)), max(1, int(rgba.height * scale))),
            Image.Resampling.NEAREST,
        )
    alpha = rgba.getchannel("A").histogram()
    see_through = sum(alpha[:OPAQUE_ALPHA]) / max(1, sum(alpha))
    if alpha[255] == sum(alpha):
        views = [rgba.convert("RGB")]
    else:
        views = []
        for page in ((255, 255, 255, 255), (0, 0, 0, 255)):
            backdrop = Image.new("RGBA", rgba.size, page)
            backdrop.alpha_composite(rgba)
            views.append(backdrop.convert("RGB"))
    lum = sorted(
        0.2126 * _LINEAR[r] + 0.7152 * _LINEAR[g] + 0.0722 * _LINEAR[b]
        for view in views
        for r, g, b in zip(*[iter(view.tobytes())] * 3)
    )
    k = int(len(lum) * CONTRAST_PERCENTILE)
    darkest, lightest = lum[k], lum[len(lum) - 1 - k]
    return {
        "black": (darkest + 0.05) / 0.05,  # black icon against the darkest pixels
        "white": 1.05 / (lightest + 0.05),  # white icon against the lightest pixels
        "transparent": see_through > TRANSPARENT_SHARE,
    }


def best_colour(judged: dict) -> tuple[str, float]:
    """The opaque Icon Colour (black or white) with the best worst-case contrast."""
    if judged["black"] >= judged["white"]:
        return "black", judged["black"]
    return "white", judged["white"]


def busyness(edges, box) -> float:
    histogram = edges.crop(box).histogram()
    return sum(histogram[EDGE_LEVEL + 1:]) / max(1, sum(histogram))


def judge_corner(image, edges, corner: str, footprint_size, margin: int) -> dict:
    box = corner_region(corner, image.size, footprint_size, margin)
    contrasts = judge_contrast(image.crop(box))
    colour, contrast = best_colour(contrasts)
    busy_share = busyness(edges, box)
    meets = contrast >= CONTRAST_THRESHOLD
    return {
        "busyness": round(busy_share, 4),
        "busy": busy_share > BUSY_THRESHOLD,
        "colour": colour,
        "contrast": round(contrast, 2),
        "meets_threshold": meets,
        "plate": not meets,
        "transparent": contrasts["transparent"],
        "region": dict(zip(("x", "y", "width", "height"),
                           (box[0], box[1], box[2] - box[0], box[3] - box[1]))),
    }


def rank_corners(judged: dict, preferred: str = DEFAULT_CORNER, plate_fits: bool = True) -> list[str]:
    """Free corners (not busy, and with enough contrast or a plate that gives
    it) first, the preferred corner (the top-right unless the user asked for
    another) leading them."""
    order = (preferred, *(c for c in CORNER_PREFERENCE if c != preferred))

    def key(corner: str):
        c = judged[corner]
        free = not c["busy"] and (c["meets_threshold"] or plate_fits)
        preference = order.index(corner)
        if free:
            return (0, corner != preferred, c["busyness"], preference)
        return (1, c["busy"], not c["meets_threshold"], c["busyness"], preference)

    return sorted(CORNERS, key=key)


def find_edges(grey):
    """FIND_EDGES on a greyscale image, without a false frame round its border.

    Pillow's 3x3 filters copy the outermost pixels through unfiltered, so a
    flat light image would report its whole border as edges. Filter a copy
    with the border replicated one pixel outwards, then crop back.
    """
    from PIL import Image, ImageFilter

    w, h = grey.size
    padded = Image.new("L", (w + 2, h + 2))
    padded.paste(grey, (1, 1))
    padded.paste(grey.crop((0, 0, w, 1)), (1, 0))  # top row
    padded.paste(grey.crop((0, h - 1, w, h)), (1, h + 1))  # bottom row
    padded.paste(padded.crop((1, 0, 2, h + 2)), (0, 0))  # left column, corners included
    padded.paste(padded.crop((w, 0, w + 1, h + 2)), (w + 1, 0))  # right column
    return padded.filter(ImageFilter.FIND_EDGES).crop((1, 1, w + 1, h + 1))


def edge_map(image):
    """Edges of what shows, not of the RGB hidden under transparent pixels.

    A transparent image is flattened over a white and over a black page, as
    judge_contrast does, and each pixel keeps the stronger of the two edges.
    """
    from PIL import Image, ImageChops

    if "A" not in image.getbands() and "transparency" not in image.info:
        return find_edges(image.convert("L"))
    rgba = image.convert("RGBA")
    maps = []
    for page in ((255, 255, 255, 255), (0, 0, 0, 255)):
        backdrop = Image.new("RGBA", rgba.size, page)
        backdrop.alpha_composite(rgba)
        maps.append(find_edges(backdrop.convert("L")))
    return ImageChops.lighter(*maps)


def cmd_score(args: argparse.Namespace) -> dict:
    paths = [Path(p) for p in args.images]
    if len(paths) == 1 and not paths[0].is_dir():
        return score_image(paths[0], args.variant, args.size, args.prefer)
    return score_batch(paths, args.variant, args.size, args.prefer)


# Files a folder is searched for: the formats `apply` labels, plus the image
# formats it refuses, so that the batch can say why they were left out.
IMAGE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".jpe", ".webp", ".gif", ".svg", ".svgz",
    ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif",
}


def is_labelled_copy(path: Path) -> bool:
    return path.stem.lower().endswith(LABELLED_INFIX)


def folder_images(folder: Path) -> list[Path]:
    """The images directly inside a folder: not its subfolders, nor hidden files.

    A link whose target is gone is kept, so that the batch reports it as `not_found`.
    """
    return sorted(
        p for p in folder.iterdir()
        if (p.is_file() or (p.is_symlink() and not p.exists()))
        and not p.name.startswith(".")
        and p.suffix.lower() in IMAGE_SUFFIXES
    )


def score_batch(paths: list[Path], variant: str, size: int | None, prefer: str | None = None) -> dict:
    """Score each listed file and each image in a listed folder, each path once."""
    images, refused, skipped = [], [], []
    seen = set()
    for given in paths:
        if given.is_dir():
            found = folder_images(given)
            if not found:
                if len(paths) == 1:
                    raise LabelToolError("no_images", f"No image found in {given}.")
                refused.append({"path": str(given), "error": {"code": "no_images", "message": f"No image found in {given}."}})
            files = found
        else:
            files = [given]
        for path in files:
            key = os.path.abspath(path)
            if key in seen:
                continue
            seen.add(key)
            if is_labelled_copy(path):
                skipped.append({"path": str(path), "reason": "labelled_copy"})
                continue
            try:
                images.append({"path": str(path), **score_image(path, variant, size, prefer)})
            except LabelToolError as exc:
                refused.append({"path": str(path), "error": {"code": exc.code, "message": exc.message}})
    return {"images": images, "refused": refused, "skipped": skipped}


def score_image(path: Path, variant: str, size: int | None, prefer: str | None = None) -> dict:
    if is_labelled_copy(path):
        raise LabelToolError("labelled_copy", f"{path} is a Labelled Copy: pass the original image.")
    image, image_format, _ = open_image(path)
    icon_height, margin = icon_geometry(image.size, size)
    # The region judged is where the label would go: sized for the padded plate,
    # the largest footprint the label can take, or for the icon alone when the
    # image has no room for a plate.
    icon = fitted_icon(variant, image.size, icon_height, margin)
    pad = plate_padding(image.size, icon.size, margin)
    footprint = plated(icon.size, pad)
    edges = edge_map(image)
    judged = {corner: judge_corner(image, edges, corner, footprint, margin) for corner in CORNERS}
    preferred, preferred_from = (prefer, "request") if prefer else (DEFAULT_CORNER, "default")
    ranking = rank_corners(judged, preferred, pad is not None)
    return {
        "image": {
            "width": image.width,
            "height": image.height,
            "format": image_format,
        },
        "icon": {"variant": variant, "width": icon.width, "height": icon.height},
        "margin": margin,
        "plate_fits": pad is not None,
        "contrast_threshold": CONTRAST_THRESHOLD,
        "busy_threshold": BUSY_THRESHOLD,
        "corners": judged,
        "preferred_corner": preferred,
        "preferred_from": preferred_from,
        "ranking": ranking,
        "suggested_corner": ranking[0],
        "all_busy": all(judged[c]["busy"] for c in CORNERS),
    }


def cmd_apply(args: argparse.Namespace) -> dict:
    from PIL import Image, ImageDraw

    original = Path(args.image)
    if is_labelled_copy(original):
        raise LabelToolError("labelled_copy", f"{original} is a Labelled Copy: pass the original image.")
    source, image_format, metadata = open_image(original)
    target = labelled_copy_path(original)
    icon_height, margin = icon_geometry(source.size, args.size)

    # Judge the corner as `score` does, to pick the colour and decide the plate.
    probe = fitted_icon(args.variant, source.size, icon_height, margin)
    pad = plate_padding(source.size, probe.size, margin)
    region = corner_region(args.corner, source.size, plated(probe.size, pad), margin)
    contrasts = judge_contrast(source.crop(region))
    best, best_contrast = best_colour(contrasts)
    if args.colour == AUTO:
        colour = best
        plate = best_contrast < CONTRAST_THRESHOLD if args.plate is None else args.plate
    else:
        colour = args.colour
        plate = bool(args.plate)
    if plate and pad is None:
        if args.plate:  # the user asked for a plate the image has no room for
            raise LabelToolError(
                "image_too_small",
                f"Image {source.width}x{source.height} has no room for a backing plate "
                f"around a {probe.width}x{probe.height} px icon with a {margin} px margin.",
            )
        plate = False  # automatic fallback: label without one, and say contrast is short

    # Contrast the label actually gets: icon against its plate, or against the
    # corner's worst pixels.
    meets_threshold = True if plate else contrasts[colour] >= CONTRAST_THRESHOLD

    icon = render_icon(args.variant, colour, icon_height)
    footprint = plated(icon.size, pad) if plate else icon.size
    fx, fy = icon_position(args.corner, source.size, footprint, margin)

    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    plate_box = None
    if plate:
        ImageDraw.Draw(overlay).rounded_rectangle(
            (fx, fy, fx + footprint[0] - 1, fy + footprint[1] - 1),
            radius=pad, fill=PLATE_COLOURS[colour],
        )
        plate_box = {"x": fx, "y": fy, "width": footprint[0], "height": footprint[1]}
        x, y = fx + pad, fy + pad
    else:
        x, y = fx, fy
    overlay.alpha_composite(icon, (x, y))
    labelled = burn_in(source, overlay)
    metadata = matching_profile_only(metadata, labelled.mode)
    # Write a new file and move it into place: an existing copy that is a link
    # to the original (or anything else) is replaced, never written through,
    # and a failed write leaves the previous copy as it was.
    staged = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        labelled.save(staged, format=image_format, **metadata, **encoder_options(image_format, original))
        os.replace(staged, target)
    except OSError as exc:
        raise LabelToolError("write_failed", f"Cannot write {target}: {exc}")
    finally:
        try:
            staged.unlink(missing_ok=True)  # never leave a partial file behind
        except OSError:
            pass

    result = {
        "labelled_copy": str(target),
        "original": str(original),
        "variant": args.variant,
        "corner": args.corner,
        "colour": colour,
        "plate": plate,
        "meets_threshold": meets_threshold,
        "icon": {"x": x, "y": y, "width": icon.width, "height": icon.height},
        "margin": margin,
        "image": {"width": source.width, "height": source.height, "format": image_format},
    }
    if plate_box:
        result["plate_box"] = plate_box
    return result


# --- The official Basic EU Icon, as `snippet` inlines it ------------------------

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
COLOUR_NAMES = {"black": "#000", "#000000": "#000", "white": "#fff", "#ffffff": "#fff"}


def style_declarations(style: str | None) -> dict:
    return {k.strip(): v.strip() for k, v in (d.split(":", 1) for d in (style or "").split(";") if ":" in d)}


def paint(fill: str | None, fill_rule: str | None) -> tuple:
    """A path's (fill, fill-rule), with SVG's defaults: black, nonzero."""
    fill = (fill or "#000").strip().lower()
    return COLOUR_NAMES.get(fill, fill), (fill_rule or "nonzero").strip().lower()


def official_basic_icons() -> dict:
    """The official Basic EU Icon: its path data, and the per-path paint of
    the Black and the White Icon Colour, read from the vendored SVGs."""
    import xml.etree.ElementTree as ET

    paints = []
    path_data = None
    for name in ("ai-basic-black.svg", "ai-basic-white.svg"):
        root = ET.parse(ICONS_DIR / name).getroot()
        css = "".join(s.text or "" for s in root.iter(SVG_NAMESPACE + "style"))
        rules = {c: style_declarations(body) for c, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", css)}
        paths = list(root.iter(SVG_NAMESPACE + "path"))
        path_data = [x.get("d") for x in paths]
        paints.append([
            paint(rules.get(x.get("class", ""), {}).get("fill"), rules.get(x.get("class", ""), {}).get("fill-rule"))
            for x in paths
        ])
    return {"path_data": path_data, "paints": paints}


def fenced_ranges(text: str) -> list:
    """The spans of Markdown fenced code blocks: what they show is an example."""
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


# --- wording: the text label in each language ----------------------------------

# The text labels the skill writes, per language: `label` for a document or a
# site, `image` for an image (a caption, the icon next to it, the alt-text
# mention), and `icon_name`, the icon's accessible name: the language's word
# for AI. One table, used by `wording`, `snippet` and `references --apply`.
WORDING = {
    "en": {"label": {"generated": "Generated with AI", "modified": "Modified with AI"},
           "image": {"generated": "Image generated with AI", "modified": "Image modified with AI"},
           "icon_name": "AI"},
    "it": {"label": {"generated": "Generato con IA", "modified": "Modificato con IA"},
           "image": {"generated": "Immagine generata con IA", "modified": "Immagine modificata con IA"},
           "icon_name": "IA"},
    "fr": {"label": {"generated": "Généré par IA", "modified": "Modifié par IA"},
           "image": {"generated": "Image générée par IA", "modified": "Image modifiée par IA"},
           "icon_name": "IA"},
    "es": {"label": {"generated": "Generado con IA", "modified": "Modificado con IA"},
           "image": {"generated": "Imagen generada con IA", "modified": "Imagen modificada con IA"},
           "icon_name": "IA"},
    "de": {"label": {"generated": "Mit KI erstellt", "modified": "Mit KI bearbeitet"},
           "image": {"generated": "Bild mit KI erstellt", "modified": "Bild mit KI bearbeitet"},
           "icon_name": "KI"},
}
LANGUAGE_CODE = re.compile(r"\s*([A-Za-z]{2,3})(?:[-_][A-Za-z0-9]{1,8})*\s*\Z")
HTML_LANG = re.compile(r"<html\b[^>]*?\blang\s*=\s*[\"']?([A-Za-z][A-Za-z0-9_-]*)", re.I)
FRONT_MATTER = re.compile(r"\A---[ \t]*\n.*?^---[ \t]*$", re.S | re.M)
FRONT_MATTER_LANG = re.compile(r"^(?:lang|language)\s*:\s*[\"']?([A-Za-z][A-Za-z0-9_-]*)", re.M)
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}


def primary_language(code) -> str | None:
    """`it` for `it`, `it-IT` or `IT_it`; None when it is not a language code."""
    match = LANGUAGE_CODE.match(code) if isinstance(code, str) else None
    return match.group(1).lower() if match else None


def declared_language(document: Path) -> str | None:
    """The language a page declares: `<html lang>`, or `lang`/`language` in a
    Markdown document's front matter."""
    try:
        text = document.read_text(encoding="utf-8", errors="ignore")[:65536]
    except OSError:
        return None
    if document.suffix.lower() in MARKDOWN_SUFFIXES:
        front = FRONT_MATTER.match(text)
        found = FRONT_MATTER_LANG.search(front.group(0)) if front else None
    else:
        found = HTML_LANG.search(text)
    return primary_language(found.group(1)) if found else None


def resolve_language(lang: str | None, document: Path | None) -> tuple[str | None, str | None]:
    """The text label's language and where it comes from: what the user asked
    for (`lang`), else the document's declared language. (None, None) when
    neither says: the agent then judges it from context."""
    if lang:
        code = primary_language(lang)
        if not code:
            raise LabelToolError("usage", f"--lang must be a language code such as `it` or `en`, not {lang!r}.")
        return code, "lang"
    declared = declared_language(document) if document else None
    if declared:
        return declared, "document"
    return None, None


LABEL_INSTEAD = "--label, with --icon-name the language's word for AI"


def phrases(code: str, wording: str, instead: str = LABEL_INSTEAD) -> dict:
    """The table's phrases for a language, or the reason to write them yourself."""
    entry = WORDING.get(code)
    if entry is None:
        raise LabelToolError(
            "language_not_listed",
            f"label_tool has no wording for `{code}` (it has {', '.join(WORDING)}). Translate the text "
            f"label into that language yourself and pass it with {instead}.",
        )
    return {"label": entry["label"][wording], "image": entry["image"][wording], "icon_name": entry["icon_name"]}


LANGUAGE_UNKNOWN = (
    "The document declares no language (no `lang` attribute or front matter). Judge it from the "
    "document's text and the conversation and pass --lang <code>; when they settle no one language, "
    "ask the user and wait."
)


def document_arg(value: str | None) -> Path | None:
    if not value:
        return None
    document = Path(value)
    if not document.is_file():
        raise LabelToolError("not_found", f"File not found: {document}")
    return document


def cmd_wording(args: argparse.Namespace) -> dict:
    """The text label, image phrasing and icon name for one language."""
    code, source = resolve_language(args.lang, document_arg(args.document))
    if code is None:
        raise LabelToolError("language_unknown", LANGUAGE_UNKNOWN)
    return {"language": code, "language_from": source, "wording": args.wording, **phrases(code, args.wording)}


# --- snippet and copy-icons: Labels the agent puts into documents -------------

# The official Basic icon cropped to its round pill: what a Label inlines.
BASIC_VIEWBOX = "89.28 100.72 365.49 365.49"
LABEL_STYLE = "display:flex;align-items:center;gap:0.4em;margin:0.5em 0;font-size:0.9em"
SNIPPET_ICON_PX = 24


def basic_svg(name: str, dark: bool, style: str, indent: str | None = None) -> str:
    """The official Basic EU Icon as an accessible inline SVG named `name`,
    its path data and paint read from the vendored files."""
    icons = official_basic_icons()
    paints = icons["paints"][1 if dark else 0]
    paths = []
    for d, (fill, rule) in zip(icons["path_data"], paints):
        rule_attr = f' fill-rule="{rule}"' if rule != "nonzero" else ""
        paths.append(f'<path fill="{fill}"{rule_attr} d="{d}"/>')
    open_tag = (
        f'<svg role="img" aria-label="{escape_html(name)}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{BASIC_VIEWBOX}" width="{SNIPPET_ICON_PX}" height="{SNIPPET_ICON_PX}" style="{style}">'
    )
    if indent is None:
        return open_tag + "".join(paths) + "</svg>"
    inner = "\n".join(indent + "  " + x for x in paths)
    return f"{indent}{open_tag}\n{inner}\n{indent}</svg>"


def escape_html(text: str) -> str:
    import html

    return html.escape(text, quote=True)


def markdown_destination(path: str) -> str:
    """A Markdown link destination: in `<...>` when the path has a space or a parenthesis."""
    return f"<{path}>" if re.search(r"[\s()]", path) else path


def escape_markdown_alt(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def cmd_snippet(args: argparse.Namespace) -> dict:
    """The marker comment and the Label, ready to insert into a document. The
    text label comes from the wording table in the document's language, or
    is given with --label."""
    code, source = resolve_language(args.lang, document_arg(args.document))
    name = (args.icon_name or "").strip()
    if args.label is not None:
        label = args.label.strip()
        if not label:
            raise LabelToolError("usage", "--label must be the text label, in the document's language.")
        source = "label"
        if not name:
            if code not in WORDING:
                raise LabelToolError(
                    "usage", "--icon-name is required with --label when the language isn't known: "
                             "the icon name (the word for AI) in the document's language.")
            name = WORDING[code]["icon_name"]
    else:
        if code is None:
            raise LabelToolError("language_unknown", LANGUAGE_UNKNOWN)
        table = phrases(code, args.wording)
        label = table["label" if args.form == "label" else "image"]
        name = name or table["icon_name"]
    marker = f"<!-- eu-ai-labelling: {args.wording} -->"
    colour = "white" if args.dark else "black"
    icon_path = args.icon_path or f"assets/ai-basic-{colour}.svg"
    if args.format == "html":
        tag = "figcaption" if args.figcaption else "p"
        svg = basic_svg(name, args.dark, "flex:none", indent="  ")
        snippet = (
            f'{marker}\n<{tag} class="eu-ai-label" style="{LABEL_STYLE}">\n'
            f"{svg}\n  <span>{escape_html(label)}</span>\n</{tag}>"
        )
    else:
        snippet = f"{marker}\n![{escape_markdown_alt(name)}]({markdown_destination(icon_path)}) {label}"
    return {
        "snippet": snippet, "format": args.format, "form": args.form, "wording": args.wording,
        "label": label, "language": code, "language_from": source,
    }


def cmd_copy_icons(args: argparse.Namespace) -> dict:
    """Copy the official Basic SVGs into the project, byte for byte."""
    folder = Path(args.to)
    folder.mkdir(parents=True, exist_ok=True)
    colours = ("black", "white") if args.colour == "both" else (args.colour,)
    copied, kept, replaced = [], [], []
    for colour in colours:
        source = ICONS_DIR / f"ai-basic-{colour}.svg"
        target = folder / source.name
        data = source.read_bytes()
        if target.is_file():
            if target.read_bytes() == data:
                kept.append(str(target))
                continue
            replaced.append(str(target))
        else:
            copied.append(str(target))
        target.write_bytes(data)
    return {"copied": copied, "kept": kept, "replaced": replaced}


# --- references: where the project uses an image ------------------------------

# Files that can reference an image: pages, Markdown, styles, templates,
# source and data files. Dependencies, build output and hidden folders are
# never scanned.
REFERENCE_SUFFIXES = {
    ".html", ".htm", ".md", ".markdown", ".mdx", ".txt",
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".astro",
    ".css", ".scss", ".sass", ".less",
    ".njk", ".liquid", ".hbs", ".ejs", ".erb", ".php", ".twig",
    ".py", ".rb", ".go", ".java", ".rs", ".cs",
    ".json", ".yaml", ".yml", ".toml", ".xml",
}
SKIPPED_DIRS = {"node_modules", "vendor", "dist", "build", "out", "_site", "__pycache__", "venv", "target"}
REFERENCE_MAX_BYTES = 2_000_000
# Folders a site serves at its root, so `/hero.png` may live in `public/hero.png`.
STATIC_DIRS = ("public", "static")

# A path as written in a page or source file: a Markdown `<...>` destination
# whole, spaces included, or else everything up to a quote, bracket, white
# space or separator. An unquoted attribute (`src=hero.png`) keeps its name
# out of the path.
REFERENCE_TOKEN = re.compile(r"""\]\(\s*<([^<>\n]+)>|(?:[\w:-]+=)?([^\s"'`()<>\[\]{}|,;*]+)""")
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*(?:<([^<>\n]+)>|([^)\s>]+))(?:\s+[^)]*)?\)")
# Files of prose, where a bare file name is a mention, not a reference.
PROSE_SUFFIXES = {".txt"}


def project_text_files(root: Path):
    """The project's pages and source files, outside dependencies and build
    output. A link to a file outside the project is not followed: `--apply`
    would edit that file."""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in REFERENCE_SUFFIXES:
            continue
        parts = path.relative_to(root).parts[:-1]
        if any(part in SKIPPED_DIRS or part.startswith(".") for part in parts):
            continue
        if not path.resolve().is_relative_to(root):
            continue
        try:
            if path.stat().st_size > REFERENCE_MAX_BYTES:
                continue
            with path.open(encoding="utf-8", newline="") as handle:  # line endings as they are
                yield path, handle.read()
        except (OSError, UnicodeDecodeError):
            continue


def unsafe_reference(text: str, start: int, token: str) -> str | None:
    """Why a reference can't be pointed to the copy as written, or None.

    `dynamic`: the path is built at run or build time (`${base}/hero.png`,
    `{{ site.url }}/hero.png`, `base + "/hero.png"`), so the tool can't tell
    where it points. `external`: a URL on another host (a CDN or CMS).
    """
    if "://" in token or token.startswith("//"):
        return "external"
    before = text[:start]
    if before.endswith("}"):
        return "dynamic"
    if before[-1:] in ("'", '"', "`") and before[:-1].rstrip().endswith("+"):
        return "dynamic"
    return None


def resolve_reference(path: str, page: Path, root: Path) -> Path | None:
    """The file a literal reference points to, or None when it resolves to none."""
    path = urllib.parse.unquote(path.split("#", 1)[0].split("?", 1)[0])
    if path.startswith("/"):
        # Root-relative: served from the site's root, which is the project
        # root, a folder above the page, or the public/static folder there.
        candidates = []
        for folder in (page.parent, *page.parent.parents):
            for served in ("", *STATIC_DIRS):
                candidates.append(folder / served / path.lstrip("/"))
            if folder == root:
                break
    else:
        candidates = [page.parent / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def braced_expression(text: str, start: int) -> str:
    """The `{...}` expression opening at `start`, braces balanced (to the end if unclosed)."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start: i + 1]
    return text[start:]


def attribute_value_end(text: str, at: int) -> int:
    """Where the attribute value starting at `at` ends: a quoted string, a balanced `{...}` or a bare word."""
    if text.startswith(("\"", "'"), at):
        close = text.find(text[at], at + 1)
        return close + 1 if close >= 0 else len(text)
    if text.startswith("{", at):
        return at + len(braced_expression(text, at))
    bare = re.compile(r"[^\s>]*").match(text, at)
    return bare.end()


def tag_attributes(text: str, tag_start: int) -> tuple[list[tuple[str, int, int]], int]:
    """The attributes of the tag opening at `tag_start` as (name, value start, value end), and the tag's end.

    Quoted values and `{...}` expressions are skipped whole, so a `>` in an
    arrow function (`onLoad={() => go()}`) or an `alt=` inside another value
    is never taken for the tag's end or its alt.
    """
    attributes = []
    name = re.compile(r"[^\s=/>]+")
    i = re.compile(r"<[\w.:-]+").match(text, tag_start).end()
    while i < len(text):
        while i < len(text) and (text[i].isspace() or text[i] == "/"):
            i += 1
        if i >= len(text) or text[i] == ">":
            return attributes, i
        if text[i] == "{":  # a JSX spread, `{...props}`
            i += len(braced_expression(text, i))
            continue
        match = name.match(text, i)
        if not match:
            i += 1
            continue
        i = match.end()
        equals = re.compile(r"\s*=\s*").match(text, i)
        if equals:
            value_end = attribute_value_end(text, equals.end())
            attributes.append((match.group(), equals.end(), value_end))
            i = value_end
        else:
            attributes.append((match.group(), i, i))
    return attributes, len(text)


# The alt bound to an expression in Vue: its value is code, not text.
BOUND_ALT = {":alt", "v-bind:alt"}
# A `{...}` alt that is only a string literal: its text is the alt.
LITERAL_BRACED = re.compile(r"""\{\s*(?:"([^"]*)"|'([^']*)'|`([^`$]*)`)\s*\}""")


# A Markdown link (not an image) and a link reference definition, `[r]: path`.
# A link's text may hold an image, as in a linked image `[![alt](thumb.png)](full.png)`.
MARKDOWN_LINK = re.compile(r"(?<!!)\[(?:[^\]\[]|!\[[^\]]*\]\([^)]*\))*\]\(\s*(?:<([^<>\n]+)>|([^)\s>]+))")
MARKDOWN_DEFINITION = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*(?:<([^<>\n]+)>|(\S+))", re.M)
# A reference-style image: `![alt][label]`, `![alt][]` or `![alt]`.
MARKDOWN_IMAGE_BY_LABEL = re.compile(r"!\[([^\]]*)\](?:\[([^\]]*)\]|(?![(\[:]))")
# Attributes whose value is text for people: a file name in them is not a path.
TEXT_ATTRIBUTES = {"alt", "title", *BOUND_ALT}
# A file name that is written as text, not as a path to the image.
NOT_A_REFERENCE = {"kind": None}
# A reference-style link: `[text][label]`, `[label][]` or `[label]`, not an image or a definition.
MARKDOWN_LINK_BY_LABEL = re.compile(r"(?<![!\]])\[([^\]\[]+)\](?:\[([^\]]*)\]|(?![(:\[]))")
# A definition both an image and a link use: pointing it to the copy would change the link too.
SHARED_DEFINITION = {"kind": None, "reason": "shared"}
# Tags whose attributes can hold an image path, by the kind they give it.
TAG_KINDS = {"img": "html-img", "source": "html-source", "a": "link"}
# The kinds of a video's player references: the `src` of a `<video>`, and of a
# `<source>` inside one. Only they point to a video's Labelled Copy.
VIDEO_KINDS = {"html-video", "html-video-source"}
# Where a `<source>` sits: the last `<video>`, `<picture>` or `<audio>` opened or closed before it.
MEDIA_ELEMENT = re.compile(r"<(/?)(video|picture|audio)(?![\w:.-])", re.I)


def markdown_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def images_using(text: str, label: str) -> list[dict]:
    """Each reference-style image that shows the definition `label`, with its line and alt text."""
    return [
        {"line": text.count("\n", 0, match.start()) + 1, "alt": match.group(1),
         "_alt_span": match.span(1), "_span": match.span(), "_collapsed": not match.group(2)}
        for match in MARKDOWN_IMAGE_BY_LABEL.finditer(text)
        if markdown_label(match.group(2) or match.group(1)) == markdown_label(label)
    ]


def links_using(text: str, label: str) -> bool:
    """Whether a reference-style link (not an image) uses the definition `label`."""
    return any(
        markdown_label(match.group(2) or match.group(1)) == markdown_label(label)
        for match in MARKDOWN_LINK_BY_LABEL.finditer(text)
    )


def path_group(match: re.Match) -> int:
    """The group of `match` that holds the path: the `<...>` form or the bare one."""
    return next(i for i in range(match.re.groups, 0, -1) if match.group(i) is not None)


def markdown_kind(text: str, start: int) -> dict | None:
    """What a Markdown reference at `start` is: an image, a definition images use, or a link."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    line_end = line_end if line_end >= 0 else len(text)
    for match in MARKDOWN_IMAGE.finditer(text, line_start, line_end):
        if match.start(path_group(match)) <= start < match.end(path_group(match)):
            return {"kind": "markdown-image", "alt": match.group(1), "alt_expression": None,
                    "_alt_span": match.span(1)}
        if match.start(1) <= start < match.end(1):
            return NOT_A_REFERENCE
    for match in MARKDOWN_LINK.finditer(text, line_start, line_end):
        if match.start(path_group(match)) <= start < match.end(path_group(match)):
            return {"kind": "link", "alt": None, "alt_expression": None}
    match = MARKDOWN_DEFINITION.match(text, line_start, line_end)
    if match and match.start(path_group(match)) <= start < match.end(path_group(match)):
        images = images_using(text, match.group(1))
        if not images:
            return {"kind": "link", "alt": None, "alt_expression": None}
        if links_using(text, match.group(1)):
            return SHARED_DEFINITION
        return {"kind": "markdown-definition", "alt": None, "alt_expression": None, "images": images}
    return None


def in_video(text: str, tag_start: int) -> bool:
    """Whether the tag at `tag_start` sits inside an open `<video>` element.

    A commented-out tag opens nothing, and a self-closing `<video ... />` (JSX)
    holds no `<source>`.
    """
    comments = [m.span() for m in re.finditer(r"<!--.*?(?:-->|\Z)", text[:tag_start], re.S)]
    last = None
    for match in MEDIA_ELEMENT.finditer(text, 0, tag_start):
        if not any(a <= match.start() < b for a, b in comments):
            last = match
    if not last or last.group(1) or last.group(2).lower() != "video":
        return False
    _, tag_end = tag_attributes(text, last.start())
    return text[tag_end - 1: tag_end] != "/"


def is_html_element(name: str) -> bool:
    """Whether a tag name is an HTML element (`video`, `VIDEO`), not a framework component (`Video`)."""
    return name in (name.lower(), name.upper())


def video_kind(match: re.Match, text: str, holder: str) -> dict | None:
    """The kind of a reference held by a `<video>` or a `<source>` inside one, or None for any other tag."""
    tag = match.group(1)
    if tag.lower() not in ("video", "source"):
        return None
    if tag.lower() == "source" and not in_video(text, match.start()):
        return None
    if is_html_element(tag) and holder.lower() == "src":
        return {"kind": "html-video" if tag.lower() == "video" else "html-video-source"}
    # A `poster`, a `data-src`, a component's prop: the tool can't tell what it does.
    return {"kind": "other"}


def html_kind(text: str, start: int, media: str = "image") -> dict | None:
    """What an HTML or JSX reference at `start` is: an `<img>` (with its alt), a `<source>` or a link;
    for a video, also a `<video src>` or a `<source>` inside a `<video>`."""
    tags = r"<(img|source|a|video)(?![\w:.-])" if media == "video" else r"<(img|source|a)(?![\w:.-])"
    for match in reversed(list(re.finditer(tags, text[:start], re.I))):
        attributes, _ = tag_attributes(text, match.start())
        holder = next((n for n, a, b in attributes if a <= start < b), None)
        if holder is None:
            continue
        if holder.lower() in TEXT_ATTRIBUTES or holder.lower().startswith("aria-"):
            return NOT_A_REFERENCE
        if media == "video":
            found = video_kind(match, text, holder)
            if found:
                return found
        kind = TAG_KINDS[match.group(1).lower()]
        if kind != "html-img":
            return {"kind": kind, "alt": None, "alt_expression": None}
        alt, alt_expression = img_alt(text, attributes)
        value_span = next(((a, b) for n, a, b in attributes if n.lower() == "alt"), None)
        return {"kind": kind, "alt": alt, "alt_expression": alt_expression,
                "_alt_value_span": value_span, "_tag_name_end": match.end()}
    return None


def img_alt(text: str, attributes: list[tuple[str, int, int]]) -> tuple[str | None, str | None]:
    """(alt, alt_expression) of an `<img>`.

    `alt` is the literal alt text; `alt_expression` is the raw computed value
    as written (`{title}` in JSX, `"title"` for a Vue `:alt`), so a computed
    alt is never taken for a missing one.
    """
    for name, value_start, value_end in attributes:
        name = name.lower()
        if name != "alt" and name not in BOUND_ALT:
            continue
        value = text[value_start:value_end]
        if name in BOUND_ALT:
            return None, value
        if value[:1] in ("\"", "'"):
            return value[1:-1], None
        if value.startswith("{"):
            literal = LITERAL_BRACED.fullmatch(value)
            if literal:
                return next(g for g in literal.groups() if g is not None), None
            return None, value
        return value, None
    return None, None


def reference_kind(text: str, start: int, media: str = "image") -> dict:
    """The kind of the reference at `start`, with the alt text an image has (`other` when unknown)."""
    return (markdown_kind(text, start) or html_kind(text, start, media)
            or {"kind": "other", "alt": None, "alt_expression": None})


def cmd_references(args: argparse.Namespace) -> dict:
    root = Path(args.root or Path.cwd()).resolve()
    original = Path(args.image)
    original = (original if original.is_absolute() else Path.cwd() / original).resolve()
    media = "video" if original.suffix.lower() in VIDEO_SUFFIXES else "image"
    if media == "video" and (args.alt_mention or args.wording or args.lang):
        raise LabelToolError(
            "usage", "A video has no alt text: run `references --apply` for it without --wording, "
                     "--alt-mention or --lang.")
    if not original.is_file():
        raise LabelToolError("not_found", f"{media.capitalize()} not found: {original}")
    if is_labelled_copy(original):
        raise LabelToolError("labelled_copy", f"{original} is a Labelled Copy: pass the original {media}.")
    copy = labelled_copy_path(original)
    if not copy.is_file():
        apply = "video-apply" if media == "video" else "apply"
        raise LabelToolError(
            "no_labelled_copy",
            f"{original.name} has no Labelled Copy ({copy.name}) yet: label it with `{apply}` first.",
        )
    try:
        original.relative_to(root)
    except ValueError:
        raise LabelToolError("outside_project", f"{original} is not inside the project {root}.")

    name = original.name
    updatable, not_updatable, positions = [], [], []
    for page, text in project_text_files(root):
        prose = page.suffix.lower() in PROSE_SUFFIXES
        examples = fenced_ranges(text) if page.suffix.lower() in MARKDOWN_SUFFIXES else []
        for match in REFERENCE_TOKEN.finditer(text):
            group = 1 if match.group(1) is not None else 2
            token, start = match.group(group), match.start(group)
            if any(a <= start < b for a, b in examples):
                continue  # an example in a code block shows nothing
            bare = token.split("#", 1)[0].split("?", 1)[0]
            written = bare.rsplit("/", 1)[-1]  # the file name as written, maybe URL-encoded
            if urllib.parse.unquote(written) != name:
                continue
            if prose and "/" not in bare:
                continue  # a file name mentioned in prose
            entry = {
                "file": page.relative_to(root).as_posix(),
                "line": text.count("\n", 0, start) + 1,
                "reference": token,
            }
            reason = unsafe_reference(text, start, token)
            if reason is None:
                resolved = resolve_reference(token, page, root)
                if resolved is None:
                    reason = "unresolved"
                elif resolved != original:
                    continue  # another image with the same name
            if reason:
                not_updatable.append({**entry, "reason": reason})
                continue
            kind = reference_kind(text, start, media)
            if kind is NOT_A_REFERENCE:
                continue
            if kind is SHARED_DEFINITION:
                not_updatable.append({**entry, "reason": "shared"})
                continue
            if media == "video":
                if kind["kind"] not in (*VIDEO_KINDS, "link", "other"):
                    # An `<img>`, a `<source>` in a `<picture>` or `<audio>`, a
                    # Markdown image: it is no video player.
                    not_updatable.append({**entry, "reason": "not_a_player"})
                    continue
                kind = {"kind": kind["kind"]}  # a video has no alt text to report
            # The copy sits next to the original: only the file name changes,
            # keeping its encoding (`my%20hero.png` -> `my%20hero.ai-label.png`).
            stem, dot, suffix = written.rpartition(".")
            new_name = f"{stem}{LABELLED_INFIX}{dot}{suffix}" if dot else copy.name
            replacement = token[: len(bare) - len(written)] + new_name + token[len(bare):]
            private = {k: kind.pop(k) for k in [k for k in kind if k.startswith("_")]}
            for image in kind.get("images", []):
                private.setdefault("_images", []).append({k: image.pop(k) for k in [k for k in image if k.startswith("_")]})
            found = {**entry, "kind": kind.pop("kind"), "replacement": replacement, **kind}
            updatable.append(found)
            positions.append((page, text, start, found, private))
    result = {
        "original": str(original),
        "labelled_copy": str(copy),
        "media": media,
        "root": str(root),
        "updatable": updatable,
        "not_updatable": not_updatable,
    }
    if media == "video":
        if args.apply:
            result.update(apply_references(positions, root, {}, media="video"))
        return result
    if args.apply and not (args.wording or args.alt_mention):
        raise LabelToolError(
            "usage", "--apply also adds the AI mention to each alt text: give --wording generated|modified "
                     "(the mention in each page's language) or --alt-mention TEXT.")
    if args.apply:
        result.update(apply_references(positions, root, alt_mentions(args.alt_mention, root), args.wording, args.lang))
    elif args.alt_mention or args.wording:
        raise LabelToolError("usage", "--alt-mention and --wording edit the pages: use them with --apply.")
    return result


def alt_mentions(given: list | None, root: Path) -> dict:
    """`--alt-mention` values as {page or "": mention}; `FILE=TEXT` names one page."""
    mentions = {}
    for value in given or []:
        page, sep, mention = value.partition("=")
        if sep and (root / page).is_file():
            mentions[Path(page).as_posix()] = mention.strip()
        else:
            mentions[""] = value.strip()
    return mentions


def mentions_ai(alt: str, mention: str) -> bool:
    """Whether an alt already says the image is made with AI."""
    return mention.lower() in alt.lower() or re.search(r"\b(AI|IA|KI)\b", alt) is not None


def with_mention(alt: str, mention: str) -> str:
    return f"{alt.rstrip()} ({mention})" if alt.strip() else mention


def table_mention(page: Path, wording: str, lang: str | None) -> tuple[str | None, str]:
    """A page's alt-text mention from the wording table, in the page's
    language, or None and the reason it can't be chosen."""
    code, _ = resolve_language(lang, page)
    if code is None:
        return None, "the page declares no language: pass --alt-mention FILE=TEXT with the mention in its language"
    try:
        return phrases(code, wording, "--alt-mention FILE=TEXT")["image"], ""
    except LabelToolError as exc:
        return None, exc.message


def apply_references(positions: list, root: Path, mentions: dict, wording: str | None = None,
                     lang: str | None = None, media: str = "image") -> dict:
    """Point each updatable reference (not a link) to the Labelled Copy and,
    with a mention for its page (given, or from the wording table in the
    page's language), add the mention to its alt text. A video's references
    get only the new path: no alt text, no text around the player."""
    edits: dict = {}  # page -> [(start, end, new text)]
    applied, alt_updated, alt_unchanged, hand = [], [], [], []
    from_table: dict = {}

    def alt_edit(page, entry, line, alt, span, new_text):
        edits[page].append((span[0], span[1], new_text))
        alt_updated.append({"file": entry["file"], "line": line, "alt": alt})

    for page, text, start, entry, private in positions:
        edits.setdefault(page, [])
        where = {"file": entry["file"], "line": entry["line"], "kind": entry["kind"]}
        if entry["kind"] == "link":
            continue
        if entry["kind"] == "other":
            # An import, a style, a data field or prose: the tool can't tell
            # whether it shows the image, so it changes nothing there.
            reason = ("not changed: if it plays the video, point it to the Labelled Copy" if media == "video" else
                      "not changed: if it shows the image, point it to the Labelled Copy and "
                      "add the mention to the alt text where the image is shown")
            hand.append({**where, "reference": entry["reference"], "replacement": entry["replacement"],
                         "reason": reason})
            continue
        edits[page].append((start, start + len(entry["reference"]), entry["replacement"]))
        applied.append({**where, "reference": entry["reference"], "replacement": entry["replacement"]})
        if media == "video":
            continue
        mention = mentions.get(entry["file"], mentions.get(""))
        if entry["kind"] == "html-source":
            hand.append({**where, "reason": "its alt text is not on this reference: edit the alt where the image is shown"})
            continue
        why = "no --alt-mention for this page"
        if not mention and wording:
            if page not in from_table:
                from_table[page] = table_mention(page, wording, lang)
            mention, why = from_table[page]
        if not mention:
            if mentions or wording:
                hand.append({**where, "reason": why})
            continue
        if entry["kind"] == "html-img" and entry.get("alt_expression"):
            hand.append({**where, "reason": f"computed alt {entry['alt_expression']}: append the mention by hand"})
            continue
        if entry["kind"] == "markdown-definition":
            for image, spans in zip(entry["images"], private["_images"]):
                alt = image["alt"]
                if mentions_ai(alt, mention):
                    alt_unchanged.append({"file": entry["file"], "line": image["line"], "alt": alt})
                elif spans["_collapsed"]:
                    if not alt.strip():
                        hand.append({**where, "line": image["line"], "reason": "an empty collapsed reference image"})
                        continue
                    new_alt = with_mention(alt, mention)
                    alt_edit(page, entry, image["line"], new_alt, spans["_span"], f"![{new_alt}][{alt}]")
                else:
                    new_alt = with_mention(alt, mention)
                    alt_edit(page, entry, image["line"], new_alt, spans["_alt_span"], new_alt)
            continue
        alt = entry.get("alt") or ""
        if mentions_ai(alt, mention):
            alt_unchanged.append({"file": entry["file"], "line": entry["line"], "alt": alt})
            continue
        new_alt = with_mention(alt, mention)
        if entry["kind"] == "markdown-image":
            alt_edit(page, entry, entry["line"], new_alt, private["_alt_span"], new_alt)
        elif private.get("_alt_value_span"):
            quoted = '"' + new_alt.replace('"', "&quot;") + '"'
            alt_edit(page, entry, entry["line"], new_alt, private["_alt_value_span"], quoted)
        else:
            at = private["_tag_name_end"]
            alt_edit(page, entry, entry["line"], new_alt, (at, at), ' alt="' + new_alt.replace('"', "&quot;") + '"')

    for page, changes in edits.items():
        if not changes:
            continue
        text = next(t for p, t, *_ in positions if p == page)
        ordered = sorted(set(changes), reverse=True)
        for (begin, _, _), (_, earlier_end, _) in zip(ordered, ordered[1:]):
            if earlier_end > begin:
                raise LabelToolError(
                    "overlapping_edits",
                    f"Two edits to {page.relative_to(root).as_posix()} overlap: no page was changed. "
                    "Update its references by hand.")
    for page, changes in edits.items():
        if not changes:
            continue
        text = next(t for p, t, *_ in positions if p == page)
        for begin, end, new_text in sorted(set(changes), reverse=True):
            text = text[:begin] + new_text + text[end:]
        with page.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    return {"applied": applied, "alt_updated": alt_updated, "alt_unchanged": alt_unchanged, "needs_hand_edit": hand}


# --- video: FFmpeg tools, inspection and Labelled Copies -------------------------

# Video work uses an existing FFmpeg installation (ffmpeg and ffprobe), never
# one the plugin installs. Image, text and site work never look for it.
VIDEO_TOOLS = ("ffmpeg", "ffprobe")
VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".wmv", ".flv", ".mpg", ".mpeg", ".ts", ".3gp"}
TOOL_TIMEOUT_S = 30
# Test hook: report and look up tools as on another platform. The lookup is
# then simulated on this machine; the result says so.
PLATFORM_OVERRIDE = "LABEL_TOOL_PLATFORM"

INSTALL_AFTER = (
    "Once installed, reopen the terminal and the application running the skill, check that "
    "`ffmpeg -version` and `ffprobe -version` both work there, then ask again: the tools are checked again "
    "before any video is processed."
)
INSTALL_GUIDANCE = {
    "windows": [
        "Install FFmpeg (it provides ffmpeg and ffprobe) with WinGet, in PowerShell: "
        "`winget install --id Gyan.FFmpeg.Essentials --exact --source winget`.",
        "Without WinGet: download `ffmpeg-release-essentials.zip` from https://www.gyan.dev/ffmpeg/builds/#release-builds, "
        "extract it to a permanent folder and add its `bin` folder to your user Path "
        "(Settings > System > About > Advanced system settings > Environment Variables).",
    ],
    "macos": [
        "Install FFmpeg with Homebrew: `brew install ffmpeg`.",
        "Without Homebrew: download a build linked from https://ffmpeg.org/download.html and put the folder holding "
        "ffmpeg and ffprobe on your PATH.",
    ],
    "linux": [
        "Install FFmpeg from your distribution: `sudo apt install ffmpeg` (Debian, Ubuntu), "
        "`sudo dnf install ffmpeg` (Fedora, with RPM Fusion enabled) or `sudo pacman -S ffmpeg` (Arch).",
        "Or download a static build linked from https://ffmpeg.org/download.html and put the folder holding "
        "ffmpeg and ffprobe on your PATH.",
    ],
}
INSTALL_NOTE = (
    "The plugin never installs or downloads FFmpeg itself. These instructions are not validated on every "
    "platform; follow your platform's own documentation when they differ."
)

# Capabilities a video path may need, reported by `video-tools`. Having one is
# not a validated labelling path: `paths` says which paths are validated.
CAPABILITY_NAMES = {
    "decoders": ("h264", "hevc", "vp8", "vp9", "av1", "prores", "aac", "mp3", "opus", "vorbis", "flac",
                 "pcm_s16le", "pcm_s24le", "mov_text", "webvtt"),
    "encoders": ("libx264", "libx265", "libvpx", "libvpx-vp9", "libsvtav1", "libaom-av1", "prores_ks"),
    "filters": ("overlay", "format", "scale", "select", "showinfo"),
    "pixel_formats": ("yuv420p", "yuv422p", "yuv444p", "yuv420p10le", "yuv422p10le", "yuv444p10le", "rgba"),
    "muxers": ("mp4", "mov", "webm"),
}


def current_platform() -> tuple[str, bool]:
    """('windows' | 'macos' | 'linux', simulated)."""
    override = os.environ.get(PLATFORM_OVERRIDE)
    if override:
        return override, True
    if sys.platform.startswith("win"):
        return "windows", False
    return ("macos" if sys.platform == "darwin" else "linux"), False


def find_executable(name: str, platform: str) -> Path | None:
    """The first `name` on PATH. On Windows, through PATHEXT (`ffmpeg.exe`)."""
    if platform == "windows":
        extensions = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e]
        names = [name + e.lower() for e in extensions] + [name + e.upper() for e in extensions]
    else:
        names = [name]
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        for candidate in names:
            path = Path(folder) / candidate
            if path.is_file() and (platform == "windows" or os.access(path, os.X_OK)):
                return path
    return None


def check_tool(name: str, platform: str) -> dict:
    """`available`, `missing` or `unusable` (found, but `-version` fails)."""
    import subprocess

    path = find_executable(name, platform)
    if path is None:
        return {"status": "missing", "path": None, "message": f"{name} is not on PATH."}
    try:
        proc = subprocess.run([str(path), "-version"], capture_output=True, text=True, timeout=TOOL_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "unusable", "path": str(path), "message": f"{name} cannot run: {exc}"}
    first = (proc.stdout or "").splitlines()[:1]
    if proc.returncode != 0 or not first or not first[0].startswith(f"{name} version"):
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or ["no version printed"]
        return {"status": "unusable", "path": str(path),
                "message": f"{name} -version failed (exit {proc.returncode}): {detail[0]}"}
    return {"status": "available", "path": str(path), "version": first[0].split()[2]}


def listed_names(ffmpeg: str, option: str) -> set:
    """Names listed by `ffmpeg -<option>` (encoders, decoders, filters, pix_fmts, muxers)."""
    import subprocess

    out = subprocess.run([ffmpeg, "-hide_banner", f"-{option}"], capture_output=True, text=True,
                         timeout=TOOL_TIMEOUT_S).stdout
    names = set()
    body = out.split("---", 1)[-1] if "---" in out else out
    for line in body.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if option == "pix_fmts":
            names.add(parts[1])
        elif option == "muxers":
            if "E" in parts[0]:
                names.update(parts[1].split(","))
        else:
            names.add(parts[1])
    return names


def tool_capabilities(ffmpeg: str) -> dict:
    found = {kind: listed_names(ffmpeg, option) for kind, option in
             (("decoders", "decoders"), ("encoders", "encoders"), ("filters", "filters"),
              ("pixel_formats", "pix_fmts"), ("muxers", "muxers"))}
    return {kind: {n: n in found[kind] for n in names} for kind, names in CAPABILITY_NAMES.items()} | {
        "_all": found}


def video_tools_report() -> dict:
    platform, simulated = current_platform()
    tools = {name: check_tool(name, platform) for name in VIDEO_TOOLS}
    ready = all(t["status"] == "available" for t in tools.values())
    report = {"ready": ready, "platform": platform, "tools": tools}
    if simulated:
        report["simulated"] = True
    if ready:
        capabilities = tool_capabilities(tools["ffmpeg"]["path"])
        found = capabilities.pop("_all")
        report["capabilities"] = capabilities
        report["paths"] = [labelling_path_status(p, found) for p in LABELLING_PATHS]
        report["note"] = (
            "`capabilities` lists what this FFmpeg build has: a capability is not a validated labelling path. "
            "`paths` lists the labelling paths this tool has validated, and whether this build has what each needs. "
            "Every output is still checked after rendering."
        )
    else:
        report["install"] = {"platform": platform, "simulated": simulated, "steps": INSTALL_GUIDANCE[platform],
                             "after": INSTALL_AFTER, "note": INSTALL_NOTE}
    return report


def cmd_video_tools(args: argparse.Namespace) -> dict:
    return video_tools_report()


def require_video_tools() -> dict:
    """The tools' paths, or `video_tools_missing` with what to do."""
    platform, _ = current_platform()
    tools = {name: check_tool(name, platform) for name in VIDEO_TOOLS}
    unavailable = [f"{n} is {t['status']} ({t['message']})" for n, t in tools.items() if t["status"] != "available"]
    if unavailable:
        raise LabelToolError(
            "video_tools_missing",
            "Video labelling needs FFmpeg's ffmpeg and ffprobe: " + "; ".join(unavailable)
            + ". Run `video-tools` for installation steps for this platform, ask the user to install them, "
              "and check again. Images, documents and sites can still be labelled without them.",
        )
    return {n: t["path"] for n, t in tools.items()}


# --- inspection -----------------------------------------------------------------

def run_tool(argv: list, timeout: int | None = None):
    import subprocess

    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, timeout=timeout)


def ratio(value: str | None) -> float | None:
    if not value or value in ("0/0", "N/A"):
        return None
    num, _, den = value.partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return None


def number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ebml_doctype(path: Path) -> str | None:
    """`webm` or `matroska`, read from the file's EBML header, else None."""
    with path.open("rb") as handle:
        head = handle.read(64)
    if not head.startswith(b"\x1a\x45\xdf\xa3"):
        return None
    at = head.find(b"\x42\x82")
    if at < 0:
        return None
    size = head[at + 2] & 0x7F  # a one-byte EBML size: 0x80 | length
    return head[at + 3: at + 3 + size].decode("ascii", "ignore")


def container_format(path: Path, format_name: str, tags: dict) -> str:
    """mp4, mov, webm, matroska or what ffprobe calls it: from the file, not its name."""
    names = format_name.split(",")
    if "mov" in names or "mp4" in names:
        brand = (tags.get("major_brand") or "").strip()
        return "mov" if brand == "qt" else "mp4"
    if "matroska" in names or "webm" in names:
        return "webm" if ebml_doctype(path) == "webm" else "matroska"
    return names[0]


PIX_FMT_DEPTH = re.compile(r"p(\d{2})(?:le|be)$")


def bit_depth(pix_fmt: str | None) -> int | None:
    if not pix_fmt:
        return None
    match = PIX_FMT_DEPTH.search(pix_fmt)
    return int(match.group(1)) if match else 8


def rotation_of(stream: dict) -> int:
    for data in stream.get("side_data_list", []) or []:
        if "rotation" in data:
            return int(round(float(data["rotation"]))) % 360
    rotate = (stream.get("tags") or {}).get("rotate")
    return int(rotate) % 360 if rotate else 0


def is_mirrored(stream: dict) -> bool:
    """Whether the display matrix flips the picture: ffprobe reports a flip as a rotation too."""
    for data in stream.get("side_data_list", []) or []:
        rows = [line.split(":", 1)[1].split() for line in (data.get("displaymatrix") or "").strip().splitlines()]
        if len(rows) >= 2:
            (a, b, *_), (c, d, *_) = rows[:2]
            return int(a) * int(d) - int(b) * int(c) < 0
    return False


def dynamic_range(stream: dict, frame_side_data: list) -> str:
    """sdr, hdr10, hlg, or an HDR profile this tool has not validated: hdr10plus, dolby_vision, other_hdr."""
    kinds = [d.get("side_data_type", "") for d in (stream.get("side_data_list") or [])] + frame_side_data
    if any("DOVI" in k or "Dolby Vision" in k for k in kinds):
        return "dolby_vision"
    transfer = stream.get("color_transfer")
    if any("SMPTE2094-40" in k or "HDR10+" in k for k in kinds):
        return "hdr10plus"
    if transfer == "smpte2084":
        return "hdr10"
    if transfer == "arib-std-b67":
        return "hlg"
    if (stream.get("color_primaries") == "bt2020" or (bit_depth(stream.get("pix_fmt")) or 8) > 8) and transfer not in (
            None, "bt709", "bt601", "smpte170m", "bt470bg", "iec61966-2-1", "bt2020-10", "bt2020-12"):
        return "other_hdr"
    return "sdr"


def first_frame_side_data(ffprobe: str, path: Path) -> list:
    proc = run_tool([ffprobe, "-v", "error", "-select_streams", "v:0", "-read_intervals", "%+#1",
                     "-show_entries", "frame=side_data_list", "-of", "json", path], timeout=TOOL_TIMEOUT_S * 4)
    try:
        frames = json.loads(proc.stdout or "{}").get("frames", [])
    except json.JSONDecodeError:
        return []
    found = []
    for frame in frames[:1]:
        for data in frame.get("side_data_list", []) or []:
            found.append(data.get("side_data_type", ""))
    return found


def hdr_metadata(ffprobe: str, path: Path) -> dict:
    """Mastering display and content light levels of the first frame, as ffprobe reports them."""
    proc = run_tool([ffprobe, "-v", "error", "-select_streams", "v:0", "-read_intervals", "%+#1",
                     "-show_entries", "frame=side_data_list", "-of", "json", path], timeout=TOOL_TIMEOUT_S * 4)
    try:
        frames = json.loads(proc.stdout or "{}").get("frames", [])
    except json.JSONDecodeError:
        return {}
    found = {}
    for data in (frames[0].get("side_data_list", []) if frames else []) or []:
        kind = data.get("side_data_type", "")
        if kind == "Mastering display metadata":
            found["mastering_display"] = {k: v for k, v in data.items() if k != "side_data_type"}
        elif kind == "Content light level metadata":
            found["content_light"] = {"max_content": data.get("max_content"), "max_average": data.get("max_average")}
    return found


def packet_times(ffprobe: str, path: Path, index: int) -> list:
    """The presentation times of a stream's packets, in order."""
    proc = run_tool([ffprobe, "-v", "error", "-select_streams", str(index), "-show_entries", "packet=pts_time",
                     "-of", "csv=p=0", path], timeout=TOOL_TIMEOUT_S * 20)
    times = sorted(t for t in (number(line.strip().strip(",")) for line in proc.stdout.splitlines()) if t is not None)
    return times


def is_constant_rate(times: list) -> bool:
    if len(times) < 3:
        return True
    steps = [b - a for a, b in zip(times, times[1:])]
    typical = sorted(steps)[len(steps) // 2]
    return all(abs(s - typical) <= max(0.002, typical * 0.02) for s in steps)


def disposition_of(stream: dict) -> dict:
    """Every disposition flag ffprobe reports: all are mapped onto the copy and compared after rendering."""
    return {k: bool(v) for k, v in (stream.get("disposition") or {}).items()}


def stream_summary(stream: dict) -> dict:
    tags = stream.get("tags") or {}
    summary = {"index": stream["index"], "codec": stream.get("codec_name"), "codec_tag": stream.get("codec_tag_string"),
               "language": tags.get("language"), "title": tags.get("title") or tags.get("name"),  # MP4: `name`
               "disposition": disposition_of(stream), "start_time": number(stream.get("start_time"))}
    if stream.get("codec_type") == "audio":
        summary.update({"channels": stream.get("channels"), "channel_layout": stream.get("channel_layout"),
                        "sample_rate": stream.get("sample_rate")})
    return summary


def inspect_video(path: Path, tools: dict | None = None) -> dict:
    """What ffprobe reads from the file: never its name alone. The file is only read."""
    if not path.is_file():
        raise LabelToolError("not_found", f"Video not found: {path}")
    tools = tools or require_video_tools()
    proc = run_tool([tools["ffprobe"], "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
                    timeout=TOOL_TIMEOUT_S * 4)
    try:
        probed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        probed = {}
    message = (proc.stderr or "").strip().splitlines()[-1:] or ["no stream found"]
    if proc.returncode != 0 or not probed.get("streams"):
        raise LabelToolError("unreadable_video", f"Cannot read {path.name} as a video: {message[0]}")
    fmt = probed.get("format", {})
    videos = [s for s in probed["streams"] if s.get("codec_type") == "video"
              and not (s.get("disposition") or {}).get("attached_pic")]
    if not videos:
        raise LabelToolError("unreadable_video", f"{path.name} holds no video stream.")
    main = videos[0]
    times = packet_times(tools["ffprobe"], path, main["index"])
    rotation = rotation_of(main)
    width, height = main.get("width"), main.get("height")
    display = (height, width) if rotation in (90, 270) else (width, height)
    side = first_frame_side_data(tools["ffprobe"], path)
    duration = number(fmt.get("duration")) or number(main.get("duration"))
    colour = {
        "primaries": main.get("color_primaries"), "transfer": main.get("color_transfer"),
        "matrix": main.get("color_space"), "range": main.get("color_range"),
        "dynamic_range": dynamic_range(main, side),
    }
    if colour["dynamic_range"] != "sdr":
        colour["hdr_metadata"] = hdr_metadata(tools["ffprobe"], path)
    others = [s for s in probed["streams"] if s is not main]
    info = {
        "path": str(path),
        "container": {
            "format": container_format(path, fmt.get("format_name", ""), fmt.get("tags") or {}),
            "format_name": fmt.get("format_name"), "duration": duration,
            "start_time": number(fmt.get("start_time")), "size": int(fmt.get("size") or path.stat().st_size),
        },
        "video": {
            "index": main["index"], "codec": main.get("codec_name"), "profile": main.get("profile"),
            "width": width, "height": height, "display_width": display[0], "display_height": display[1],
            "rotation": rotation, "mirrored": is_mirrored(main), "pix_fmt": main.get("pix_fmt"), "bit_depth": bit_depth(main.get("pix_fmt")),
            "frame_rate": main.get("r_frame_rate"), "average_frame_rate": main.get("avg_frame_rate"),
            "constant_frame_rate": is_constant_rate(times), "frames": len(times),
            "start_time": number(main.get("start_time")), "colour": colour,
        },
        "audio": [stream_summary(s) for s in others if s.get("codec_type") == "audio"],
        "subtitles": [stream_summary(s) for s in others if s.get("codec_type") == "subtitle"],
        "other_streams": [{**stream_summary(s), "type": s.get("codec_type")} for s in others
                          if s.get("codec_type") not in ("audio", "subtitle")],
    }
    info["labelling"] = labelling_support(info, tools)
    return info


def cmd_video_inspect(args: argparse.Namespace) -> dict:
    return inspect_video(Path(args.video))


# --- labelling paths --------------------------------------------------------------

# The labelling paths this tool has validated end to end, each with a real
# input and decoded-output test. A video outside them stops for a user
# decision; it is never converted silently. Audio and subtitles are copied,
# never re-encoded, so a path lists the codecs its container carries.
MP4_AUDIO = ("aac", "mp3", "alac", "ac3", "eac3", "opus", "flac")
MOV_AUDIO = ("aac", "mp3", "alac", "ac3", "pcm_s16le", "pcm_s24le")
WEBM_AUDIO = ("opus", "vorbis")
H264_PIX_FMTS = ("yuv420p", "yuvj420p", "yuv422p", "yuv444p")
X264 = {"codec": "h264", "codec_title": "H.264", "encoder": "libx264", "quality": "CRF 16",
        "encode": ["-preset", "medium", "-crf", "16"]}
# The filters every render uses (render_command): the Label's padding and counter-rotation, and the overlay.
RENDER_FILTERS = ["overlay", "pad", "null", "transpose", "hflip", "vflip", "setparams"]
# What a path has been validated to keep beyond one audio track, an unrotated picture and constant timing:
# `tracks` (several audio and subtitle tracks), `rotation` (by 90, 180 or 270 degrees), `variable_timing`.
EVERY_CHARACTERISTIC = ("tracks", "rotation", "variable_timing")
LABELLING_PATHS = [
    {
        "name": "mp4-h264-sdr",
        "description": "MP4 with an H.264 video stream in SDR, 8-bit 4:2:0, 4:2:2 or 4:4:4",
        "container": "mp4", **X264, "dynamic_range": ("sdr",), "pix_fmts": H264_PIX_FMTS, "muxer": "mp4",
        "audio": MP4_AUDIO, "subtitles": ("mov_text",),
        "preserves": EVERY_CHARACTERISTIC,
        "needs": {"decoders": ["h264"], "encoders": ["libx264"], "filters": RENDER_FILTERS, "muxers": ["mp4"]},
    },
    {
        "name": "mov-h264-sdr",
        "description": "MOV (QuickTime) with an H.264 video stream in SDR, 8-bit 4:2:0, 4:2:2 or 4:4:4",
        "container": "mov", **X264, "dynamic_range": ("sdr",), "pix_fmts": H264_PIX_FMTS, "muxer": "mov",
        "audio": MOV_AUDIO, "subtitles": ("mov_text",),
        "preserves": EVERY_CHARACTERISTIC,
        "needs": {"decoders": ["h264"], "encoders": ["libx264"], "filters": RENDER_FILTERS, "muxers": ["mov"]},
    },
    {
        "name": "webm-vp9-sdr",
        "description": "WebM with a VP9 video stream in SDR, 8-bit 4:2:0",
        "container": "webm", "codec": "vp9", "codec_title": "VP9", "encoder": "libvpx-vp9", "quality": "CRF 20",
        "encode": ["-crf", "20", "-b:v", "0", "-deadline", "good", "-cpu-used", "4", "-row-mt", "1"],
        "dynamic_range": ("sdr",), "pix_fmts": ("yuv420p",), "muxer": "webm",
        "audio": WEBM_AUDIO, "subtitles": ("webvtt",),
        "preserves": (),  # not yet validated in WebM: these stop for a decision
        "needs": {"decoders": ["vp9"], "encoders": ["libvpx-vp9"], "filters": RENDER_FILTERS, "muxers": ["webm"]},
    },
    {
        "name": "webm-vp8-sdr",
        "description": "WebM with a VP8 video stream in SDR, 8-bit 4:2:0",
        # VP8's CRF is constrained quality: it needs a bitrate ceiling, set high enough not to bind.
        "container": "webm", "codec": "vp8", "codec_title": "VP8", "encoder": "libvpx", "quality": "CRF 10",
        "encode": ["-crf", "10", "-b:v", "50M", "-deadline", "good", "-cpu-used", "4"],
        "dynamic_range": ("sdr",), "pix_fmts": ("yuv420p",), "muxer": "webm",
        "audio": WEBM_AUDIO, "subtitles": ("webvtt",),
        "preserves": (),  # not yet validated in WebM: these stop for a decision
        "needs": {"decoders": ["vp8"], "encoders": ["libvpx"], "filters": RENDER_FILTERS, "muxers": ["webm"]},
    },
]


def labelling_path_status(path: dict, found: dict) -> dict:
    missing = [f"{kind[:-1]} {name}" for kind, names in path["needs"].items() for name in names
               if name not in found.get(kind, set())]
    return {"name": path["name"], "description": path["description"], "validated": True,
            "available": not missing, "missing": missing}


def issue(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def matching_path(info: dict) -> tuple[dict | None, list]:
    """The validated path for this video, or None and why there is none."""
    container, video = info["container"]["format"], info["video"]
    for_container = [p for p in LABELLING_PATHS if p["container"] == container]
    if not for_container:
        known = sorted({p["container"].upper() for p in LABELLING_PATHS})
        return None, [issue("container_not_validated",
                            f"{container.upper()} files have no validated labelling path (validated: "
                            f"{', '.join(known)}).")]
    for_codec = [p for p in for_container if p["codec"] == video["codec"]]
    if not for_codec:
        codecs = sorted({p["codec"] for p in for_container})
        return None, [issue("codec_not_validated",
                            f"Its video codec, {video['codec']}, has no validated labelling path in "
                            f"{container.upper()} (validated: {', '.join(codecs)}). Labelling it would mean "
                            f"converting the video to another codec.")]
    dynamic = video["colour"]["dynamic_range"]
    for_range = [p for p in for_codec if dynamic in p["dynamic_range"]]
    if not for_range:
        return None, [issue("hdr_not_validated",
                            f"It is {dynamic.upper()} video, and no validated path keeps {dynamic.upper()} for "
                            f"{video['codec']} in {container.upper()}. It won't be converted to SDR.")]
    for path in for_range:
        if video["pix_fmt"] in path["pix_fmts"]:
            return path, []
    return None, [issue("pixel_format_not_validated",
                        f"Its pixel format, {video['pix_fmt']}, has no validated labelling path "
                        f"(validated: {', '.join(for_range[0]['pix_fmts'])}).")]


def stream_issues(info: dict, path: dict) -> list:
    """Streams and characteristics the path can't carry through unchanged."""
    found = []
    if info["other_streams"]:
        kinds = ", ".join(f"{s['type']} ({s['codec'] or s['codec_tag'] or 'unknown'})" for s in info["other_streams"])
        found.append(issue("additional_tracks",
                           f"Besides its video, audio and subtitles it has other streams: {kinds}. This version "
                           f"can't carry them into the Labelled Copy, and won't drop them."))
    for kind, code in (("audio", "audio_not_validated"), ("subtitles", "subtitles_not_validated")):
        codecs = [t["codec"] for t in info[kind] if t["codec"] not in path[kind]]
        if codecs:
            found.append(issue(code, f"Its {kind} tracks ({', '.join(codecs)}) can't be copied into "
                                     f"{path['container'].upper()} unchanged: they would have to be converted or "
                                     f"dropped (copied unchanged: {', '.join(path[kind])})."))
    container, preserves = path["container"].upper(), path["preserves"]
    if "tracks" not in preserves and (len(info["audio"]) > 1 or info["subtitles"]):
        found.append(issue("additional_tracks",
                           f"It has more than one audio track, or subtitles: this version labels {container} videos "
                           f"with at most one audio track and no subtitles, and won't drop the others."))
    video = info["video"]
    if video["mirrored"] or video["rotation"] not in COUNTER_ROTATIONS:
        turned = "mirrored" if video["mirrored"] else f"rotated by {video['rotation']} degrees"
        found.append(issue("rotation_not_validated",
                           f"It is displayed {turned}, which this version doesn't label: it keeps a rotation by a "
                           f"multiple of 90 degrees, and won't turn the stored picture."))
    elif video["rotation"] and "rotation" not in preserves:
        found.append(issue("rotation_not_validated",
                           f"It is displayed rotated by {video['rotation']} degrees, which this version doesn't "
                           f"label in {container}, and won't turn the stored picture."))
    if not video["constant_frame_rate"] and "variable_timing" not in preserves:
        found.append(issue("variable_frame_rate_not_validated",
                           f"Its frames are not evenly spaced (variable frame rate), which this version doesn't "
                           f"label in {container} without normalising the timing."))
    return found


def capability_issues(path: dict, found: dict) -> list:
    status = labelling_path_status(path, found)
    if status["available"]:
        return []
    return [issue("capability_missing",
                  f"This FFmpeg build lacks what the {path['name']} path needs: {', '.join(status['missing'])}.")]


def labelling_support(info: dict, tools: dict) -> dict:
    path, issues = matching_path(info)
    if path:
        issues = stream_issues(info, path) + capability_issues(path, tool_capabilities(tools["ffmpeg"])["_all"])
    return {"supported": path is not None and not issues, "path": path["name"] if path else None, "issues": issues}


def path_named(name: str) -> dict:
    return next(p for p in LABELLING_PATHS if p["name"] == name)


# --- rendering ------------------------------------------------------------------

def extract_frame(ffmpeg: str, video: Path, at: float, target: Path) -> Path:
    """The frame shown at `at` seconds into playback, as displayed (rotation applied), as PNG."""
    proc = run_tool([ffmpeg, "-nostdin", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", video,
                     "-frames:v", "1", "-f", "image2", "-c:v", "png", target], timeout=TOOL_TIMEOUT_S * 4)
    if proc.returncode != 0 or not target.is_file():
        detail = (proc.stderr or "").strip().splitlines()[-1:] or ["no frame decoded"]
        raise LabelToolError("frame_extraction_failed", f"Cannot decode the frame at {at:.2f} s: {detail[0]}")
    return target


def sample_times(duration: float, count: int = 5) -> list:
    """Evenly spread times inside the video, away from its very end."""
    duration = max(duration, 0.04)
    return [round(duration * (i + 0.5) / count, 3) for i in range(count)]


def choose_colour(frames: list, corner: str, display: tuple, footprint: tuple, margin: int) -> tuple[str, dict]:
    """The Icon Colour whose worst contrast over the sampled frames is the higher."""
    from PIL import Image

    worst = {"black": float("inf"), "white": float("inf")}
    region = corner_region(corner, display, footprint, margin)
    for frame in frames:
        with Image.open(frame) as image:
            judged = judge_contrast(image.convert("RGB").crop(region))
        for colour in worst:
            worst[colour] = min(worst[colour], judged[colour])
    colour = "black" if worst["black"] >= worst["white"] else "white"
    return colour, {c: round(v, 2) for c, v in worst.items()}


def label_overlay(variant: str, colour: str, icon_height: int, pad: int, target: Path) -> tuple[Path, tuple, tuple]:
    """The Label as one RGBA PNG: the icon on its opaque rounded backing plate.

    Returns the PNG, the plate's size and the icon's size."""
    from PIL import Image, ImageDraw

    icon = render_icon(variant, colour, icon_height)
    size = plated(icon.size, pad)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=pad,
                                              fill=PLATE_COLOURS[colour])
    overlay.alpha_composite(icon, (pad, pad))
    overlay.save(target)
    return target, size, icon.size


COLOUR_OPTIONS = (("primaries", "-color_primaries"), ("transfer", "-color_trc"),
                  ("matrix", "-colorspace"), ("range", "-color_range"))
SETPARAMS_NAMES = {"primaries": "color_primaries", "transfer": "color_trc", "matrix": "colorspace", "range": "range"}


# A rotated video keeps its stored pixels and display matrix: it is decoded
# without autorotation, so the Label, placed on the picture as displayed, is
# turned back the other way (filters) and placed where that corner is stored
# (x, y from the displayed x, y, the stored main_w/main_h and the turned
# Label's overlay_w/overlay_h). Keys are ffprobe rotations (counterclockwise).
COUNTER_ROTATIONS = {
    0: ("", "{x}", "{y}"),
    90: ("transpose=clock,", "main_w-{y}-overlay_w", "{x}"),
    180: ("hflip,vflip,", "main_w-{x}-overlay_w", "main_h-{y}-overlay_h"),
    270: ("transpose=cclock,", "{y}", "main_h-{x}-overlay_h"),
}


def render_command(tools: dict, info: dict, path: dict, overlay: Path, position: tuple, staged: Path,
                   enable: str | None) -> list:
    x, y = position
    turn, at_x, at_y = COUNTER_ROTATIONS[info["video"]["rotation"]]
    timing = f":enable='{enable}'" if enable else ""
    # A decoder may tag frames the source leaves untagged (VP8 frames come out BT.470BG): keep them untagged.
    untagged = [f"{name}=unknown" for key, name in SETPARAMS_NAMES.items()
                if info["video"]["colour"].get(key) in (None, "unknown")]
    tags = f",setparams={':'.join(untagged)}" if untagged else ""
    # Even sizes and positions: overlay rounds a subsampled picture's x and y down to even, which a
    # counter-rotation would turn into a shift the other way on the displayed picture.
    graph = (f"[1:v]pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:color=black@0,{turn}null[label];"
             f"[0:{info['video']['index']}][label]overlay=x={at_x.format(x=x, y=y)}:y={at_y.format(x=x, y=y)}:"
             f"eof_action=repeat{timing}{tags}[labelled]")
    # -copyts keeps every timestamp, a start offset included; -fps_mode passthrough (below) keeps variable frame
    # timing. -noautorotate keeps the stored picture, whose display matrix carries through.
    argv = [tools["ffmpeg"], "-nostdin", "-v", "error", "-y", "-copyts", "-noautorotate", "-i", info["path"],
            "-i", overlay,
            "-filter_complex", graph, "-map", "[labelled]"]
    for out, stream in enumerate(info["audio"] + info["subtitles"], start=1):  # each track by name, never by default
        argv += ["-map", f"0:{stream['index']}", f"-map_metadata:s:{out}", f"0:s:{stream['index']}",
                 f"-disposition:{out}", "+".join(k for k, v in stream["disposition"].items() if v) or "0"]
        if stream["title"]:  # MP4 reads a title back as `name`, which its muxer doesn't write again
            argv += [f"-metadata:s:{out}", f"title={stream['title']}"]
    argv += ["-c:v", path["encoder"], *path["encode"], "-pix_fmt", info["video"]["pix_fmt"]]
    for key, option in COLOUR_OPTIONS:
        value = info["video"]["colour"].get(key)
        if value and value != "unknown":
            argv += [option, value]
    argv += ["-c:a", "copy", "-c:s", "copy", "-fps_mode", "passthrough", "-map_metadata", "0",
             "-f", path["muxer"], staged]
    return argv


# --- visibility -----------------------------------------------------------------

# Product defaults, not legal thresholds: continuous display up to and
# including DEFAULT_THRESHOLD_S, otherwise a DEFAULT_WINDOW_S window starting
# every DEFAULT_EVERY_S from the first frame.
VISIBILITY_MODES = (AUTO, "continuous", "periodic")
DEFAULT_WINDOW_S, DEFAULT_EVERY_S, DEFAULT_THRESHOLD_S = 5.0, 60.0, 60.0


def resolve_visibility(args: argparse.Namespace, duration: float) -> dict:
    """The effective visibility settings, or `usage` for settings that can't be rendered.

    Only the settings the requested mode uses are checked."""
    def seconds(name: str) -> float:
        value = getattr(args, name)
        if not (math.isfinite(value) and value > 0):
            raise LabelToolError("usage", f"--{name} must be a positive number of seconds, not {value:g}.")
        return value

    mode = args.visibility
    settings = {"requested": mode}
    if mode == AUTO:
        settings["threshold"] = seconds("threshold")
        mode = "continuous" if duration <= args.threshold else "periodic"
    settings["mode"] = mode
    if mode == "periodic":
        settings |= {"window": seconds("window"), "every": seconds("every")}
        if args.window >= args.every:
            raise LabelToolError("usage", f"--window ({args.window:g} s) must be shorter than --every "
                                          f"({args.every:g} s): otherwise the Label never hides.")
    return settings


def visibility_enable(visibility: dict, info: dict) -> str | None:
    """The overlay's `enable` expression on the playback timeline (from the first frame), or None: always."""
    if visibility["mode"] != "periodic":
        return None
    start = info["video"]["start_time"] or 0
    # Rendering keeps the source timestamps (-copyts), so `t` starts at the first frame's time. The
    # 0.1 ms nudge keeps a frame exactly on a window's start inside it despite float rounding.
    return f"lt(mod(t-{start:.6f}+1e-4,{visibility['every']:g}),{visibility['window']:g})"


def label_check_times(visibility: dict, info: dict) -> tuple[float, float | None]:
    """A playback time when the Label shows, and one when it is hidden (None: no frame is)."""
    duration = info["container"]["duration"] or 0
    if visibility["mode"] != "periodic":
        return min(0.5, duration / 2), None
    window, every = visibility["window"], visibility["every"]
    last_frame = duration - 1 / (ratio(info["video"]["average_frame_rate"]) or 25)
    hidden_at = (window + min(every, last_frame)) / 2 if last_frame >= window else None
    return min(0.5, window / 2, duration / 2), hidden_at


# --- output validation ----------------------------------------------------------

TIME_TOLERANCE_S = 0.002


def check(name: str, passed: bool, detail: str) -> dict:
    return {"check": name, "passed": bool(passed), "detail": detail}


def label_region_check(tools: dict, source: Path, labelled: Path, at: float, box: tuple, work: Path,
                       hidden: bool = False) -> dict:
    """Decode the same frame of both files: the Label region must change (stay unchanged when `hidden`),
    the rest only by re-encoding noise."""
    from PIL import Image, ImageChops, ImageStat

    before = extract_frame(tools["ffmpeg"], source, at, work / "check-source.png")
    after = extract_frame(tools["ffmpeg"], labelled, at, work / "check-labelled.png")
    with Image.open(before) as a, Image.open(after) as b:
        a, b = a.convert("RGB"), b.convert("RGB")
        if a.size != b.size:
            return check("label_region", False, f"frame sizes differ: {a.size} and {b.size}")
        diff = ImageChops.difference(a, b).convert("L")
        inside = ImageStat.Stat(diff.crop(box)).mean[0]
        mask = Image.new("L", diff.size, 255)
        mask.paste(0, box)
        outside = ImageStat.Stat(diff, mask).mean[0]
    detail = f"mean change {inside:.1f} inside the Label, {outside:.2f} outside it, at {at:.2f} s"
    if hidden:
        return check("label_hidden", inside < 4 and outside < 4, detail)
    return check("label_region", inside > 20 and outside < 4, detail)


def compare_streams(name: str, before: list, after: list, keys: tuple) -> dict:
    left = [{k: s.get(k) for k in keys} for s in before]
    right = [{k: s.get(k) for k in keys} for s in after]
    return check(name, left == right, f"{len(after)} kept" if left == right else f"source {left}, copy {right}")


def validate_output(tools: dict, source: dict, staged: Path, box: tuple, visible_at: float, work: Path,
                    hidden_at: float | None = None) -> list:
    """Checks of the produced file itself, independent of the checks before rendering."""
    out = inspect_video(staged, tools)
    src_v, out_v = source["video"], out["video"]
    checks = [
        check("container", out["container"]["format"] == source["container"]["format"],
              f"{out['container']['format']}"),
        check("video_codec", out_v["codec"] == src_v["codec"], f"{out_v['codec']}"),
        check("dimensions", (out_v["display_width"], out_v["display_height"])
              == (src_v["display_width"], src_v["display_height"]),
              f"{out_v['display_width']}x{out_v['display_height']} as displayed"),
        check("orientation", all(out_v[k] == src_v[k] for k in ("width", "height", "rotation", "mirrored")),
              f"{out_v['width']}x{out_v['height']} stored, rotated by {out_v['rotation']} degrees"
              + (", mirrored" if out_v["mirrored"] else "")),
        check("pixel_format", out_v["pix_fmt"] == src_v["pix_fmt"], f"{out_v['pix_fmt']}"),
        check("colour", all(out_v["colour"].get(k) == src_v["colour"].get(k)
                            for k in ("primaries", "transfer", "matrix", "range", "dynamic_range")),
              f"{ {k: out_v['colour'].get(k) for k in ('primaries', 'transfer', 'matrix', 'range')} }"),
        check("frame_count", out_v["frames"] == src_v["frames"], f"{out_v['frames']} frames"),
    ]
    src_times = packet_times(tools["ffprobe"], Path(source["path"]), src_v["index"])
    out_times = packet_times(tools["ffprobe"], staged, out_v["index"])
    if src_times and out_times and len(src_times) == len(out_times):  # absolute times: a start offset counts
        drift = max(abs(round(b - a, 6)) for a, b in zip(src_times, out_times))
        checks.append(check("frame_timing", drift <= TIME_TOLERANCE_S, f"largest frame time shift {drift * 1000:.2f} ms"))
    else:
        checks.append(check("frame_timing", False, "frame times could not be compared"))
    start = abs((out_v["start_time"] or 0) - (src_v["start_time"] or 0))
    checks.append(check("start_time", start <= TIME_TOLERANCE_S, f"video starts at {out_v['start_time'] or 0:.3f} s"))
    src_d, out_d = source["container"]["duration"] or 0, out["container"]["duration"] or 0
    frame_s = 1 / (ratio(src_v["average_frame_rate"]) or 25)
    checks.append(check("duration", abs(out_d - src_d) <= max(0.05, frame_s), f"{out_d:.3f} s (source {src_d:.3f} s)"))
    keys = ("codec", "channels", "sample_rate", "language", "title", "disposition")
    checks.append(compare_streams("audio_tracks", source["audio"], out["audio"], keys))
    checks.append(compare_streams("subtitle_tracks", source["subtitles"], out["subtitles"],
                                  ("codec", "language", "disposition", "title")))

    def offset(info, stream):  # a track's start relative to the video's: audio/video sync
        return (stream.get("start_time") or 0) - (info["video"]["start_time"] or 0)
    tracks = list(zip(source["audio"], out["audio"])) + list(zip(source["subtitles"], out["subtitles"]))
    sync = [abs(offset(out, b) - offset(source, a)) for a, b in tracks]
    if sync:
        checks.append(check("track_sync", max(sync) <= TIME_TOLERANCE_S,
                            f"largest shift of an audio or subtitle track {max(sync) * 1000:.2f} ms"))
    checks.append(label_region_check(tools, Path(source["path"]), staged, visible_at, box, work))
    if hidden_at is not None:
        checks.append(label_region_check(tools, Path(source["path"]), staged, hidden_at, box, work, hidden=True))
    return checks


def cmd_video_apply(args: argparse.Namespace) -> dict:
    import tempfile

    original = Path(args.video)
    if is_labelled_copy(original):
        raise LabelToolError("labelled_copy", f"{original} is a Labelled Copy: pass the original video.")
    tools = require_video_tools()
    info = inspect_video(original, tools)
    support = info["labelling"]
    if not support["supported"]:
        raise LabelToolError(
            "preservation_unsupported",
            f"{original.name} can't be labelled without losing or converting something: "
            + " ".join(i["message"] for i in support["issues"])
            + " Nothing was written. Ask the user how to proceed.",
            issues=support["issues"],
        )
    path = path_named(support["path"])
    video = info["video"]
    display = (video["display_width"], video["display_height"])
    icon_height, margin = icon_geometry(display, args.size)
    probe_icon = fitted_icon(args.variant, display, icon_height, margin)
    pad = plate_padding(display, probe_icon.size, margin)
    if pad is None:
        raise LabelToolError(
            "image_too_small",
            f"The video is {display[0]}x{display[1]}: too small for a {probe_icon.width}x{probe_icon.height} px "
            f"icon on its backing plate with a {margin} px margin.")
    footprint = plated(probe_icon.size, pad)
    target = labelled_copy_path(original)
    staged = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    duration = info["container"]["duration"] or 0
    visibility = resolve_visibility(args, duration)
    with tempfile.TemporaryDirectory(prefix="eu-ai-labelling-") as work:
        work = Path(work)
        if args.colour == AUTO:
            frames = [extract_frame(tools["ffmpeg"], original, t, work / f"sample-{i}.png")
                      for i, t in enumerate(sample_times(duration))]
            colour, contrasts = choose_colour(frames, args.corner, display, footprint, margin)
        else:
            colour, contrasts = args.colour, None
        overlay, plate_size, icon_px = label_overlay(args.variant, colour, icon_height, pad, work / "label.png")
        x, y = (v - v % 2 for v in icon_position(args.corner, display, plate_size, margin))  # see render_command
        box = (x, y, x + plate_size[0], y + plate_size[1])
        try:
            proc = run_tool(render_command(tools, info, path, overlay, (x, y), staged, visibility_enable(visibility, info)))
            if proc.returncode != 0 or not staged.is_file():
                detail = (proc.stderr or "").strip().splitlines()[-3:]
                raise LabelToolError("render_failed",
                                     f"ffmpeg could not render {target.name}: {' '.join(detail) or 'no output'}. "
                                     "The original and any previous Labelled Copy are unchanged.")
            visible_at, hidden_at = label_check_times(visibility, info)
            checks = validate_output(tools, info, staged, box, visible_at, work, hidden_at)
            failed = [c for c in checks if not c["passed"]]
            if failed:
                raise LabelToolError(
                    "output_validation_failed",
                    f"The rendered copy did not keep the source's characteristics: "
                    + "; ".join(f"{c['check']}: {c['detail']}" for c in failed)
                    + ". It was discarded; the original and any previous Labelled Copy are unchanged.",
                    checks=checks)
            os.replace(staged, target)
        except OSError as exc:
            raise LabelToolError("write_failed", f"Cannot write {target}: {exc}")
        finally:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                pass
    return {
        "labelled_copy": str(target),
        "original": str(original),
        "variant": args.variant,
        "corner": args.corner,
        "colour": colour,
        "plate": True,
        "contrast": contrasts,
        "icon": {"x": x + pad, "y": y + pad, "width": icon_px[0], "height": icon_px[1]},
        "plate_box": {"x": x, "y": y, "width": plate_size[0], "height": plate_size[1]},
        "margin": margin,
        "visibility": visibility,
        "path": path["name"],
        "video": {
            "container": info["container"]["format"], "codec": video["codec"],
            "width": display[0], "height": display[1], "duration": duration,
            "re_encoded": True, "encoder": path["encoder"],
            "note": (f"The video stream was re-encoded as {path['codec_title']} with {path['encoder']} "
                     f"({path['quality']}) to incorporate the Label, so the copy "
                     "is not bit-identical to the original. Audio and subtitle tracks were copied without "
                     "re-encoding."),
        },
        "validation": {"passed": True, "checks": checks},
    }


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # report usage errors as JSON too
        raise LabelToolError("usage", message)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="label_tool", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=JsonArgumentParser)

    score = sub.add_parser("score", help="Judge each corner as a place for the Label.")
    score.add_argument("images", nargs="+", metavar="image",
                       help="an image; or a folder, or several images, to judge as a batch")
    score.add_argument("--variant", default="generated", choices=VARIANTS)
    score.add_argument("--size", type=int, help="icon height in px (default: 6%% of the shorter side)")
    score.add_argument("--prefer", choices=CORNERS,
                       help="the corner the user prefers, ranked first when free (default: the top-right)")
    score.set_defaults(handler=cmd_score)

    apply = sub.add_parser("apply", help="Write a Labelled Copy with the EU Icon burned in.")
    apply.add_argument("image")
    apply.add_argument("--variant", required=True, choices=VARIANTS)
    apply.add_argument("--corner", default="tr", choices=CORNERS)
    apply.add_argument("--colour", default=AUTO, choices=(AUTO, *COLOURS))
    apply.add_argument("--size", type=int, help="icon height in px (default: 6%% of the shorter side)")
    plate = apply.add_mutually_exclusive_group()
    plate.add_argument("--plate", dest="plate", action="store_const", const=True, default=None,
                       help="force the backing plate on (default: on only when "
                            "auto colour cannot reach 3:1)")
    plate.add_argument("--no-plate", dest="plate", action="store_const", const=False,
                       help="force the backing plate off")
    apply.set_defaults(handler=cmd_apply)

    refs = sub.add_parser("references", help="Find where the project uses an image that has a Labelled Copy.")
    refs.add_argument("image", help="the original image (its Labelled Copy must exist)")
    refs.add_argument("--root", help="the project root to search (default: the current folder)")
    refs.add_argument("--apply", action="store_true",
                      help="point each updatable reference (not a link) to the Labelled Copy")
    refs.add_argument("--alt-mention", action="append", metavar="[FILE=]TEXT",
                      help="with --apply, add TEXT to the alt text of each image now showing the copy; "
                           "FILE= limits it to that page (repeatable); wins over --wording")
    refs.add_argument("--wording", choices=VARIANTS,
                      help="with --apply, add the wording table's mention to each alt, in its page's language")
    refs.add_argument("--lang", help="with --wording: the language of every page (default: each page's declared language)")
    refs.set_defaults(handler=cmd_references)

    words = sub.add_parser("wording", help="Print the text label, image phrasing and icon name in one language.")
    words.add_argument("--wording", required=True, choices=VARIANTS)
    words.add_argument("--lang", help="the language code the user asked for (wins over the document)")
    words.add_argument("--document", help="the document the Label goes into, for its declared language")
    words.set_defaults(handler=cmd_wording)


    snippet = sub.add_parser("snippet", help="Print a Label (marker comment and Basic EU Icon) to insert into a document.")
    snippet.add_argument("--format", required=True, choices=("html", "markdown"))
    snippet.add_argument("--wording", required=True, choices=VARIANTS)
    snippet.add_argument("--lang", help="the language code the user asked for (wins over the document)")
    snippet.add_argument("--document", help="the document the Label goes into, for its declared language")
    snippet.add_argument("--label", help="free text in place of the table's text label: another language, a partial Label")
    snippet.add_argument("--icon-name", help="the icon's accessible name, with --label in a language outside the table")
    snippet.add_argument("--as", dest="form", default="label", choices=("label", "caption"),
                         help="label: icon and visible text label; caption: the same below an image, worded "
                              "for the image")
    snippet.add_argument("--dark", action="store_true", help="the White Icon Colour, for a dark background")
    snippet.add_argument("--figcaption", action="store_true", help="HTML: a <figcaption> instead of a <p>")
    snippet.add_argument("--icon-path", help="Markdown: the copied icon's path or URL (default: assets/ai-basic-<colour>.svg)")
    snippet.set_defaults(handler=cmd_snippet)

    copy_icons = sub.add_parser("copy-icons", help="Copy the official Basic EU Icon SVGs into a project folder.")
    copy_icons.add_argument("--to", required=True, help="the project folder to copy them into")
    copy_icons.add_argument("--colour", default="black", choices=("black", "white", "both"))
    copy_icons.set_defaults(handler=cmd_copy_icons)

    tools = sub.add_parser("video-tools", help="Check ffmpeg and ffprobe, and what this build can do.")
    tools.set_defaults(handler=cmd_video_tools)

    inspect = sub.add_parser("video-inspect", help="Read a video's streams, timing, orientation and colour.")
    inspect.add_argument("video")
    inspect.set_defaults(handler=cmd_video_inspect)

    vapply = sub.add_parser("video-apply", help="Write a Labelled Copy of a video.")
    vapply.add_argument("video")
    vapply.add_argument("--variant", required=True, choices=VARIANTS)
    vapply.add_argument("--corner", default="tr", choices=CORNERS)
    vapply.add_argument("--colour", default=AUTO, choices=(AUTO, *COLOURS),
                        help="the Icon Colour; the backing plate is the opposite colour (default: the better "
                             "contrast over sampled frames)")
    vapply.add_argument("--size", type=int, help="icon height in px (default: 6%% of the shorter side as displayed)")
    vapply.add_argument("--visibility", default=AUTO, choices=VISIBILITY_MODES,
                        help="when the Label shows: continuous, periodic, or auto: continuous up to --threshold "
                             "seconds, periodic beyond it (default: auto)")
    vapply.add_argument("--window", type=float, default=DEFAULT_WINDOW_S,
                        help="periodic: seconds the Label shows each time (default: %(default)g)")
    vapply.add_argument("--every", type=float, default=DEFAULT_EVERY_S,
                        help="periodic: seconds between the starts of two windows (default: %(default)g)")
    vapply.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD_S,
                        help="auto: the longest video, in seconds, shown continuously (default: %(default)g)")
    vapply.set_defaults(handler=cmd_video_apply)

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        emit(args.handler(args))
        return 0
    except LabelToolError as exc:
        emit({"error": {"code": exc.code, "message": exc.message, **exc.details}})
        return 1
    except Exception as exc:  # any other failure still honours the JSON contract
        emit({"error": {"code": "internal", "message": f"{type(exc).__name__}: {exc}"}})
        return 1


if __name__ == "__main__":
    sys.exit(main())
