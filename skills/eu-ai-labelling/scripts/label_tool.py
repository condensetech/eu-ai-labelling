#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow>=11",
#     "resvg-py>=0.5",
#     "c2pa-python>=0.38,<0.39",
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
      EXIF; re-encodes JPEG at quality 95. Keeps the original's IPTC Marking
      (see `marking_kept` below).

`apply` and `video-apply` (MP4, MOV) write into the copy's XMP the original's
IPTC DigitalSourceType and IPTC AI fields (AISystemUsed, AISystemVersionUsed,
AIPromptInformation, AIPromptWriterName), unchanged, and print them as
`marking_kept`; with no such field the copy gets no XMP and no `marking_kept`.
The DigitalSourceType comes from the original's XMP, or from its active C2PA
manifest when that one settles the Icon Variant (see `marking`). Nothing else
of the original's XMP is kept (no xmpMM:InstanceID, no dcterms:provenance), nor
its C2PA manifest, whose hard binding the copy no longer matches.

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

  marking <image | video>
      Reads the Marking an image or video carries and grades it as evidence for
      the Icon Variant. It never says whether a Label is required. Sources: IPTC
      DigitalSourceType in XMP (PNG, JPEG, WebP, MP4, MOV); C2PA manifests (the
      Provider: claim generator and signer, the actions, their
      digitalSourceType and whether the signature validates, read offline: a
      manifest kept only at a remote URL counts as none); an AI tool named in
      EXIF/XMP Software or CreatorTool; the generator PNG text chunks
      (`parameters`, `prompt`, `workflow`); and, for a video, the container
      tags ffprobe reads (`encoder`, `comment`, `com.apple.quicktime.*`), which
      need ffmpeg and ffprobe as `video-tools` checks. Prints `media`, `c2pa`
      (`checked`; `unavailable` when c2pa-python is not installed, the other
      sources still read; `unreadable`), `signals` (each with its `source`,
      `field`, `value`, `grade` and `quote`, plus `variant` when precise),
      `settled` (generated, modified or null), `settled_by` and `quotes` (what
      the origin question quotes when nothing is settled).
      Grades: `trainedAlgorithmicMedia` is precise for generated,
      `compositeWithTrainedAlgorithmicMedia` for modified, from XMP or from the
      active C2PA manifest when its signature validates. Other AI source types,
      tool names, generator chunks and an invalid C2PA manifest are vague;
      human-origin source types are ignored. A valid active C2PA manifest
      decides a conflict; otherwise precise signals that disagree become vague
      (`conflict`). A file without any Marking gives `settled: null` and no
      signals.

  copy-icons --to DIR [--colour black|white|both]
      Copies the official Basic EU Icon SVGs into DIR byte for byte. Prints
      `copied`, `kept` (an identical copy already there) and `replaced` (a
      file of that name that was not the official icon).
"""

from __future__ import annotations

import argparse
import contextlib
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


@contextlib.contextmanager
def staged_replace(target: Path):
    """A new file next to `target`, uniquely named `.{name}.<random>.tmp`, to write into; moved onto `target`
    once the block completes. A name nobody can predict is never a link planted beforehand, and the move
    replaces whatever `target` is, a link included, without writing through it. On any failure the staged
    file is removed and `target` is left as it was."""
    import tempfile

    handle, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(handle)
    staged = Path(name)
    try:
        yield staged
        os.replace(staged, target)
    finally:
        try:
            staged.unlink(missing_ok=True)  # never leave a partial file behind
        except OSError:
            pass


def rendered(staged: Path) -> bool:
    """Whether a tool wrote anything into the `staged` file, which exists empty from the start."""
    return staged.is_file() and staged.stat().st_size > 0


def stderr_tail(stderr: str | bytes | None, lines: int = 1, fallback: str = "no output") -> str:
    """The last `lines` lines a tool printed, on one line, for an error message."""
    text = stderr.decode(errors="replace") if isinstance(stderr, bytes) else (stderr or "")
    return " ".join(text.strip().splitlines()[-lines:]) or fallback


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


# Images a folder is searched for: the formats `apply` labels, plus the image
# formats it refuses, so that the batch can say why they were left out. A
# folder is searched for videos too (VIDEO_SUFFIXES), listed for video-inspect.
IMAGE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".jpe", ".webp", ".gif", ".svg", ".svgz",
    ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif",
}


def is_labelled_copy(path: Path) -> bool:
    return path.stem.lower().endswith(LABELLED_INFIX)


def media_of(path: Path) -> str:
    """`video` by the file's suffix, else `image`: which commands a file goes to."""
    return "video" if path.suffix.lower() in VIDEO_SUFFIXES else "image"


def folder_media(folder: Path) -> list[Path]:
    """The images and videos directly inside a folder: not its subfolders, nor hidden files.

    A link whose target is gone is kept, so that the batch reports it as `not_found`.
    """
    return sorted(
        p for p in folder.iterdir()
        if (p.is_file() or (p.is_symlink() and not p.exists()))
        and not p.name.startswith(".")
        and p.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES
    )


def score_batch(paths: list[Path], variant: str, size: int | None, prefer: str | None = None) -> dict:
    """Score each listed image and each image in a listed folder, each path once.

    Videos are listed under `videos`, unscored: each goes through `video-inspect`,
    which alone says whether and how it can be labelled.
    """
    images, videos, refused, skipped = [], [], [], []
    seen = set()
    for given in paths:
        if given.is_dir():
            found = folder_media(given)
            if not found:
                message = f"No image or video found in {given}."
                if len(paths) == 1:
                    raise LabelToolError("no_images", message)
                refused.append({"path": str(given), "error": {"code": "no_images", "message": message}})
            files = found
        else:
            files = [given]
        for path in files:
            key = os.path.abspath(path)
            if key in seen:
                continue
            seen.add(key)
            media = media_of(path)
            if is_labelled_copy(path):
                skipped.append({"path": str(path), "media": media, "reason": "labelled_copy"})
            elif media == "video":
                videos.append({"path": str(path), "media": media})
            else:
                try:
                    images.append({"path": str(path), "media": media, **score_image(path, variant, size, prefer)})
                except LabelToolError as exc:
                    refused.append({"path": str(path), "media": media,
                                    "error": {"code": exc.code, "message": exc.message}})
    return {"images": images, "videos": videos, "refused": refused, "skipped": skipped}


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
    kept = kept_marking(original, image_xmp(original))
    if kept:
        metadata.update(xmp_options(image_format, xmp_for_copy(kept)))
    # An existing copy that is a link to the original (or anything else) is
    # replaced, never written through, and a failed write leaves it as it was.
    try:
        with staged_replace(target) as staged:
            labelled.save(staged, format=image_format, **metadata, **encoder_options(image_format, original))
    except OSError as exc:
        raise LabelToolError("write_failed", f"Cannot write {target}: {exc}")

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
    if kept:
        result["marking_kept"] = kept
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
    media = media_of(original)
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
        detail = stderr_tail(proc.stderr or proc.stdout, fallback="no version printed")
        return {"status": "unusable", "path": str(path),
                "message": f"{name} -version failed (exit {proc.returncode}): {detail}"}
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


def video_tools_report() -> tuple[dict, dict | None]:
    """What `video-tools` prints, and every name the ffmpeg build lists by kind (None when not ready)."""
    platform, simulated = current_platform()
    tools = {name: check_tool(name, platform) for name in VIDEO_TOOLS}
    ready = all(t["status"] == "available" for t in tools.values())
    report = {"ready": ready, "platform": platform, "tools": tools}
    found = None
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
    return report, found


def cmd_video_tools(args: argparse.Namespace) -> dict:
    return video_tools_report()[0]


def require_video_tools() -> dict:
    """The tools' paths and, under `listed`, every name the ffmpeg build lists by kind: the build is probed
    once per command. Or `video_tools_missing` with what to do."""
    report, found = video_tools_report()
    tools = report["tools"]
    unavailable = [f"{n} is {t['status']} ({t['message']})" for n, t in tools.items() if t["status"] != "available"]
    if unavailable:
        raise LabelToolError(
            "video_tools_missing",
            "Video labelling needs FFmpeg's ffmpeg and ffprobe: " + "; ".join(unavailable)
            + ". Run `video-tools` for installation steps for this platform, ask the user to install them, "
              "and check again. Images, documents and sites can still be labelled without them.",
        )
    return {n: t["path"] for n, t in tools.items()} | {"listed": found}


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


EBML_MAGIC, EBML_DOCTYPE = b"\x1a\x45\xdf\xa3", 0x4282
EBML_HEADER_MAX_BYTES = 4096  # far more than any EBML header holds


def ebml_doctype(path: Path) -> str | None:
    """`webm` or `matroska`: the DocType element of the file's EBML header, else None (no header, or one
    cut short or malformed)."""
    def vint(at: int, keep_marker: bool = False) -> tuple[int, int] | None:
        """An EBML variable-length integer at `at`: (value, where the next field starts)."""
        if at >= len(head) or not head[at]:
            return None
        length = 9 - head[at].bit_length()  # the leading zero bits, plus the marker bit
        if at + length > len(head):
            return None
        value = head[at] if keep_marker else head[at] & (0xFF >> length)
        for byte in head[at + 1: at + length]:
            value = value << 8 | byte
        return value, at + length

    with path.open("rb") as handle:
        head = handle.read(EBML_HEADER_MAX_BYTES)
    header = vint(len(EBML_MAGIC)) if head.startswith(EBML_MAGIC) else None
    if not header:
        return None
    length, at = header
    end = min(at + length, len(head))
    while at < end:  # the header's elements: ID, size, data
        element = vint(at, keep_marker=True)
        size = element and vint(element[1])
        if not size:
            return None
        (element_id, _), (length, data) = element, size
        if element_id == EBML_DOCTYPE:
            return head[data: data + length].decode("ascii", "ignore").rstrip("\0") or None
        at = data + length
    return None


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


DOLBY_VISION_TAGS = ("dvh1", "dvhe", "dva1", "dvav", "dav1")


def dynamic_range(stream: dict, frame_side_data: list) -> str:
    """sdr, hdr10, hlg, or an HDR profile this tool has not validated: hdr10plus, dolby_vision, other_hdr."""
    side = [d for d in (stream.get("side_data_list") or []) if isinstance(d, dict)]
    kinds = [d.get("side_data_type", "") for d in side] + frame_side_data
    # Dolby Vision shows as the stream's configuration record (MP4 dvcC/dvvC: "DOVI configuration record",
    # with dv_* fields), the frames' RPU ("Dolby Vision RPU Data", "Dolby Vision Metadata"), or a sample
    # entry only Dolby Vision uses: any one of them is enough, whichever this ffprobe reports.
    if (any("DOVI" in k or "Dolby Vision" in k for k in kinds) or any("dv_profile" in d for d in side)
            or stream.get("codec_tag_string") in DOLBY_VISION_TAGS):
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
    """The first video frame's side data, each entry with its `side_data_type` and fields."""
    # `frame_side_data` names the entries' fields: `frame=side_data_list` alone lists them empty.
    proc = run_tool([ffprobe, "-v", "error", "-select_streams", "v:0", "-read_intervals", "%+#1",
                     "-show_entries", "frame=side_data_list:frame_side_data", "-of", "json", path],
                    timeout=TOOL_TIMEOUT_S * 4)
    try:
        frames = json.loads(proc.stdout or "{}").get("frames", [])
    except json.JSONDecodeError:
        return []
    return [d for d in (frames[0].get("side_data_list") or [] if frames else []) if isinstance(d, dict)]


def hdr_metadata(side_data: list) -> dict:
    """Mastering display and content light levels of the first frame, as ffprobe reports them."""
    found = {}
    for data in side_data:
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


GENERIC_HANDLER = re.compile(r"handler|^core media ", re.IGNORECASE)  # "SoundHandler", "Core Media Audio", ...


def track_title(tags: dict) -> str | None:
    """A track's title wherever this ffmpeg keeps it in MP4 and MOV: `title`; `name`, the udta box FFmpeg 9
    writes and reads back; or the handler name (hdlr), the only place FFmpeg 8 and earlier write one, unless
    it is a muxer's generic name for the track's kind."""
    handler = tags.get("handler_name")
    return (tags.get("title") or tags.get("name")
            or (handler if handler and not GENERIC_HANDLER.search(handler) else None))


def stream_summary(stream: dict) -> dict:
    tags = stream.get("tags") or {}
    summary = {"index": stream["index"], "codec": stream.get("codec_name"), "codec_tag": stream.get("codec_tag_string"),
               "language": tags.get("language"), "title": track_title(tags),
               "disposition": disposition_of(stream), "start_time": number(stream.get("start_time"))}
    if stream.get("codec_type") == "audio":
        summary.update({"channels": stream.get("channels"), "channel_layout": stream.get("channel_layout"),
                        "sample_rate": stream.get("sample_rate")})
    return summary


def inspect_video(path: Path, tools: dict | None = None, support: bool = True) -> dict:
    """What ffprobe reads from the file: never its name alone. The file is only read. With `support`, also
    whether and how it can be labelled (`labelling`)."""
    if not path.is_file():
        raise LabelToolError("not_found", f"Video not found: {path}")
    tools = tools or require_video_tools()
    proc = run_tool([tools["ffprobe"], "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
                    timeout=TOOL_TIMEOUT_S * 4)
    try:
        probed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        probed = {}
    if proc.returncode != 0 or not probed.get("streams"):
        raise LabelToolError("unreadable_video", f"Cannot read {path.name} as a video: "
                                                 f"{stderr_tail(proc.stderr, fallback='no stream found')}")
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
        "dynamic_range": dynamic_range(main, [d.get("side_data_type", "") for d in side]),
    }
    if colour["dynamic_range"] != "sdr":
        colour["hdr_metadata"] = hdr_metadata(side)
    others = [s for s in probed["streams"] if s is not main]
    info = {
        "path": str(path),
        "container": {
            "format": container_format(path, fmt.get("format_name", ""), fmt.get("tags") or {}),
            "format_name": fmt.get("format_name"), "duration": duration,
            "start_time": number(fmt.get("start_time")), "size": int(fmt.get("size") or path.stat().st_size),
        },
        "video": {
            "index": main["index"], "codec": main.get("codec_name"), "codec_tag": main.get("codec_tag_string"),
            "profile": main.get("profile"),
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
    if support:
        info["labelling"] = labelling_support(info, tools["listed"])
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
# A path's pixel formats, each with the `overlay` format that composites it at its own depth and chroma
# resolution: overlay's default, 8-bit 4:2:0, would subsample 4:2:2 and 4:4:4 chroma and lose its detail.
H264_PIX_FMTS = {"yuv420p": "yuv420", "yuvj420p": "yuv420", "yuv422p": "yuv422", "yuv444p": "yuv444"}
VPX_PIX_FMTS = {"yuv420p": "yuv420"}
HEVC_10BIT_PIX_FMTS = {"yuv420p10le": "yuv420p10"}
X264 = {"codec": "h264", "codec_title": "H.264", "encoder": "libx264", "quality": "CRF 16",
        "encode": ["-preset", "medium", "-crf", "16"]}
# The filters every render uses (render_command): the Label's padding and counter-rotation, and the overlay.
RENDER_FILTERS = ["overlay", "pad", "null", "transpose", "hflip", "vflip", "setparams"]
# What a path has been validated to keep beyond one audio track, an unrotated picture and constant timing:
# `tracks` (several audio and subtitle tracks), `rotation` (by 90, 180 or 270 degrees), `variable_timing`.
EVERY_CHARACTERISTIC = ("tracks", "rotation", "variable_timing")
# HDR10: the Label's white is SDR reference white (ITU-R BT.2408, 203 cd/m2) in the PQ signal, its black stays
# black; it is composited in 10-bit YUV, the video's transfer is never converted. The preview frames' SDR
# rendering (`sdr_view`) also needs `lutrgb` and `colorchannelmixer`.
REFERENCE_WHITE_NITS = 203
HDR10_COLOUR = {"primaries": "bt2020", "transfer": "smpte2084", "matrix": "bt2020nc", "range": "tv"}
# HLG: the Label's white is HDR reference white for HLG (ITU-R BT.2408), 75% of the HLG signal, which a
# 1000 cd/m2 display shows at 203 cd/m2; its black stays black. HLG needs no HDR10 metadata: the copy
# declares only what the source declares, and its transfer stays ARIB STD-B67 in the VUI.
HLG_REFERENCE_WHITE = 0.75
HLG_COLOUR = {"primaries": "bt2020", "transfer": "arib-std-b67", "matrix": "bt2020nc", "range": "tv"}
# ARIB STD-B67 (HLG) OETF: a, b, c; and the system gamma of a 1000 cd/m2 display (ITU-R BT.2100).
HLG_CONSTANTS = (0.17883277, 1 - 4 * 0.17883277, 0.5 - 0.17883277 * math.log(4 * 0.17883277))
HLG_SYSTEM_GAMMA = 1.2
HDR_FILTERS = ["format", "scale", "colorchannelmixer", "lutrgb"]
# SMPTE ST 2084 (PQ): m1, m2, c1, c2, c3.
PQ_CONSTANTS = (2610 / 16384, 2523 / 4096 * 128, 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32)
HDR_PIXEL_FORMATS = ["yuv420p10le", "yuva420p10le", "rgba64le", "rgb48le"]
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
        "dynamic_range": ("sdr",), "pix_fmts": VPX_PIX_FMTS, "muxer": "webm",
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
        "dynamic_range": ("sdr",), "pix_fmts": VPX_PIX_FMTS, "muxer": "webm",
        "audio": WEBM_AUDIO, "subtitles": ("webvtt",),
        "preserves": (),  # not yet validated in WebM: these stop for a decision
        "needs": {"decoders": ["vp8"], "encoders": ["libvpx"], "filters": RENDER_FILTERS, "muxers": ["webm"]},
    },
    {
        "name": "mp4-hevc-hdr10",
        "description": ("MP4 with an HEVC Main 10 video stream in HDR10: 10-bit 4:2:0, BT.2020, PQ, limited range, "
                        "with mastering display metadata"),
        "container": "mp4", "codec": "hevc", "codec_title": "HEVC Main 10", "encoder": "libx265", "quality": "CRF 14",
        "encode": ["-preset", "medium", "-crf", "14"],
        "dynamic_range": ("hdr10",), "pix_fmts": HEVC_10BIT_PIX_FMTS, "colour": HDR10_COLOUR, "signal": "pq",
        "codec_tags": ("hvc1", "hev1"), "muxer": "mp4",
        "audio": MP4_AUDIO, "subtitles": ("mov_text",),
        "preserves": ("tracks",),  # rotation and variable timing are not yet validated in HDR10: they stop
        "needs": {"decoders": ["hevc"], "encoders": ["libx265"], "filters": RENDER_FILTERS + HDR_FILTERS,
                  "pixel_formats": HDR_PIXEL_FORMATS, "muxers": ["mp4"]},
    },
    {
        "name": "mp4-hevc-hlg",
        "description": ("MP4 with an HEVC Main 10 video stream in HLG: 10-bit 4:2:0, BT.2020, HLG (ARIB STD-B67), "
                        "limited range"),
        "container": "mp4", "codec": "hevc", "codec_title": "HEVC Main 10", "encoder": "libx265", "quality": "CRF 14",
        "encode": ["-preset", "medium", "-crf", "14"],
        "dynamic_range": ("hlg",), "pix_fmts": HEVC_10BIT_PIX_FMTS, "colour": HLG_COLOUR, "signal": "hlg",
        "codec_tags": ("hvc1", "hev1"), "muxer": "mp4",
        "audio": MP4_AUDIO, "subtitles": ("mov_text",),
        "preserves": ("tracks",),  # rotation and variable timing are not yet validated in HLG: such videos stop
        "needs": {"decoders": ["hevc"], "encoders": ["libx265"], "filters": RENDER_FILTERS + HDR_FILTERS,
                  "pixel_formats": HDR_PIXEL_FORMATS, "muxers": ["mp4"]},
    },
]

# What a mastering display declares (SMPTE ST 2086), as ffprobe names it: the copy carries every value.
MASTERING_KEYS = tuple(f"{p}_{axis}" for p in ("red", "green", "blue", "white_point") for axis in "xy") + (
    "min_luminance", "max_luminance")
DYNAMIC_RANGE_TITLES = {"sdr": "SDR", "hdr10": "HDR10", "hlg": "HLG", "hdr10plus": "HDR10+",
                        "dolby_vision": "Dolby Vision", "other_hdr": "HDR with an unrecognised transfer"}
DYNAMIC_METADATA = {"hdr10plus": "HDR10+ dynamic metadata (SMPTE ST 2094-40)", "dolby_vision": "Dolby Vision metadata"}


def pq_signal(nits: float) -> float:
    """The PQ (SMPTE ST 2084) signal value, 0 to 1, of `nits` cd/m2."""
    m1, m2, c1, c2, c3 = PQ_CONSTANTS
    y = (nits / 10000) ** m1
    return ((c1 + c2 * y) / (1 + c3 * y)) ** m2


def hlg_display(signal: float, gamma: float = HLG_SYSTEM_GAMMA) -> float:
    """An HLG signal level of a grey as display light, 0 to 1 of the display's peak: the inverse OETF and the
    system `gamma` (sdr_view applies it per channel)."""
    a, b, c = HLG_CONSTANTS
    scene = signal * signal / 3 if signal <= 0.5 else (math.exp((signal - c) / a) + b) / 12
    return scene ** gamma


def label_white_nits(path: dict, metadata: dict) -> float:
    """The luminance, in cd/m2, at which the copy's display shows the Label's white. PQ: 203. HLG is relative
    to the display, so on the mastering display's peak (else BT.2100's 1000 cd/m2 reference), with the
    system gamma BT.2100 gives for that peak: 203 cd/m2 at 1000."""
    if path["signal"] == "pq":
        return REFERENCE_WHITE_NITS
    peak = ratio(str((metadata.get("mastering_display") or {}).get("max_luminance") or 1000)) or 1000
    return peak * hlg_display(HLG_REFERENCE_WHITE, HLG_SYSTEM_GAMMA + 0.42 * math.log10(peak / 1000))


def label_white(path: dict) -> float:
    """The signal level, 0 to 1, of the Label's white on an HDR path: reference white in its transfer."""
    return pq_signal(REFERENCE_WHITE_NITS) if path["signal"] == "pq" else HLG_REFERENCE_WHITE


def limited_code(signal: float) -> float:
    """A 0-1 signal as a 10-bit limited-range luma code value (64 to 940)."""
    return 64 + 876 * signal


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
        title = DYNAMIC_RANGE_TITLES.get(dynamic, dynamic)
        kept = sorted({DYNAMIC_RANGE_TITLES[r] for p in for_codec for r in p["dynamic_range"]})
        if dynamic == "sdr":
            return None, [issue("codec_not_validated",
                                f"Its video codec, {video['codec']}, has a validated labelling path in "
                                f"{container.upper()} only for {', '.join(kept)} video, and it is SDR.")]
        lost = (f" Re-encoding it would lose its {DYNAMIC_METADATA[dynamic]}, which this version can't carry "
                f"into the Labelled Copy and won't drop." if dynamic in DYNAMIC_METADATA else "")
        return None, [issue("hdr_not_validated",
                            f"It is {title} video, and no validated path keeps {title} for {video['codec']} in "
                            f"{container.upper()}.{lost} It won't be converted to SDR.")]
    for path in for_range:
        if video["pix_fmt"] in path["pix_fmts"]:
            break
    else:
        return None, [issue("pixel_format_not_validated",
                            f"Its pixel format, {video['pix_fmt']}, has no validated labelling path "
                            f"(validated: {', '.join(for_range[0]['pix_fmts'])}).")]
    wrong = {k: video["colour"].get(k) for k, v in (path.get("colour") or {}).items() if video["colour"].get(k) != v}
    if wrong:
        return None, [issue("colour_not_validated",
                            f"Its colour tags ({', '.join(f'{k} {v}' for k, v in wrong.items())}) are not those of "
                            f"the validated {DYNAMIC_RANGE_TITLES[dynamic]} path (" + ", ".join(
                                f"{k} {v}" for k, v in path["colour"].items()) + "). They won't be converted.")]
    return path, []


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
    mastering = (video["colour"].get("hdr_metadata") or {}).get("mastering_display")
    if path.get("signal") == "pq" and mastering is None:
        found.append(issue("hdr_metadata_missing",
                           "It carries no mastering display metadata, so the Labelled Copy's HDR10 metadata can't "
                           "be established from the source. This version won't guess it or drop the HDR."))
    elif mastering is not None:
        unreadable = [k for k in MASTERING_KEYS if ratio(str(mastering.get(k))) is None]
        if unreadable:
            found.append(issue("hdr_metadata_missing",
                               f"Its mastering display metadata is incomplete or unreadable ({', '.join(unreadable)}), "
                               "so the Labelled Copy can't declare the source's. This version won't guess it or "
                               "drop the HDR."))
    return found


def capability_issues(path: dict, found: dict) -> list:
    status = labelling_path_status(path, found)
    if status["available"]:
        return []
    return [issue("capability_missing",
                  f"This FFmpeg build lacks what the {path['name']} path needs: {', '.join(status['missing'])}.")]


def labelling_support(info: dict, listed: dict) -> dict:
    """Whether the video can be labelled, given the names the ffmpeg build lists (require_video_tools)."""
    path, issues = matching_path(info)
    if path:
        issues = stream_issues(info, path) + capability_issues(path, listed)
    return {"supported": path is not None and not issues, "path": path["name"] if path else None, "issues": issues}


def path_named(name: str) -> dict:
    return next(p for p in LABELLING_PATHS if p["name"] == name)


# --- rendering ------------------------------------------------------------------

def sdr_view(path: dict) -> str | None:
    """For an HDR path, the filters that render a decoded frame for viewing on an SDR display, else None.

    BT.2020 code values to display light relative to reference white, which shows as SDR white: for PQ the
    EOTF over 203 cd/m2; for HLG the inverse OETF and the system gamma 1.2 of a 1000 cd/m2 display, per
    channel (BT.2100's OOTF applies the gamma to luminance; per channel is exact for greys), over 75% HLG.
    Then highlights above 0.8 of reference white rolled off towards white (Reinhard on the excess), BT.2020
    to BT.709 primaries in linear light, and the sRGB curve. Only these PNGs are tone-mapped; never the copy."""
    if path.get("signal") not in ("pq", "hlg"):
        return None
    knee = 0.8
    if path["signal"] == "pq":
        m1, m2, c1, c2, c3 = PQ_CONSTANTS
        display = (f"st(0,pow(val/maxval,{1 / m2:.8f}));"
                   f"st(1,pow(max(ld(0)-{c1:.8f},0)/({c2:.8f}-{c3:.8f}*ld(0)),{1 / m1:.8f})"
                   f"*{10000 / REFERENCE_WHITE_NITS:.6f});")
    else:
        a, b, c = HLG_CONSTANTS
        display = ("st(0,val/maxval);"
                   f"st(1,pow(if(lte(ld(0),0.5),ld(0)*ld(0)/3,(exp((ld(0)-{c:.8f})/{a:.8f})+{b:.8f})/12),"
                   f"{HLG_SYSTEM_GAMMA})/{hlg_display(HLG_REFERENCE_WHITE):.8f});")
    linear = (display
              + f"st(2,if(lte(ld(1),{knee}),ld(1),{knee}+{1 - knee:.2f}*(ld(1)-{knee})/(ld(1)-{knee}+{1 - knee:.2f})));"
              "clip(ld(2)*maxval,0,maxval)")
    srgb = "st(0,val/maxval);clip(maxval*if(lte(ld(0),0.0031308),12.92*ld(0),1.055*pow(ld(0),1/2.4)-0.055),0,maxval)"
    to_709 = ("rr=1.6605:rg=-0.5876:rb=-0.0728:gr=-0.1246:gg=1.1329:gb=-0.0083:"
              "br=-0.0182:bg=-0.1006:bb=1.1187")
    return (f"scale=in_color_matrix=bt2020:in_range=tv:out_range=pc,format=rgb48le,"
            f"lutrgb=r='{linear}':g='{linear}':b='{linear}',colorchannelmixer={to_709},"
            f"lutrgb=r='{srgb}':g='{srgb}':b='{srgb}',format=rgb24")


def extract_frame(ffmpeg: str, video: Path, at: float, target: Path, view: str | None = None) -> Path:
    """The frame shown at `at` seconds into playback, as displayed (rotation applied), as PNG; rendered
    through the `view` filters when given (sdr_view)."""
    proc = run_tool([ffmpeg, "-nostdin", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", video,
                     "-frames:v", "1", *(["-vf", view] if view else []), "-f", "image2", "-c:v", "png", target],
                    timeout=TOOL_TIMEOUT_S * 4)
    if proc.returncode != 0 or not rendered(target):
        raise frame_failure(at, proc.stderr)
    return target


def frame_failure(at: float, stderr: str | bytes | None) -> LabelToolError:
    return LabelToolError("frame_extraction_failed",
                          f"Cannot decode the frame at {at:.2f} s: {stderr_tail(stderr, fallback='no frame decoded')}")


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


def hdr_label_filters(path: dict) -> str:
    """The Label's RGBA overlay mapped into the path's HDR signal, PQ or HLG: white to reference white
    (label_white), black kept black, in 10-bit limited-range BT.2020 YUV. The Label is achromatic, so its
    grey levels need no gamut conversion."""
    gain = f"{label_white(path):.5f}"
    return (f"format=rgba64le,colorchannelmixer=rr={gain}:gg={gain}:bb={gain},"
            "scale=out_color_matrix=bt2020:out_range=tv,format=yuva420p10le,")


def output_hdr_metadata(info: dict, path: dict, plate_size: tuple, display: tuple) -> dict:
    """The static HDR metadata the Labelled Copy declares. The mastering display is the source's, when it
    has one (HLG needs none): the Label changes no grading. The Label adds pixels at reference white
    (label_white_nits), so MaxCLL becomes at least that; MaxFALL may rise by at most the plate's share of the
    picture at that level, so it is raised by that bound (never above MaxCLL). A level the source leaves
    unknown (0) stays unknown, and a source without content light levels gets none."""
    source = info["video"]["colour"].get("hdr_metadata") or {}
    out = {"mastering_display": source["mastering_display"]} if "mastering_display" in source else {}
    light = source.get("content_light")
    if light:
        white = round(label_white_nits(path, source))
        max_cll, max_fall = int(light.get("max_content") or 0), int(light.get("max_average") or 0)
        if max_cll:
            max_cll = max(max_cll, white)
        if max_fall:
            share = plate_size[0] * plate_size[1] / (display[0] * display[1])
            max_fall = math.ceil(max_fall + share * white)
            max_fall = min(max_fall, max_cll) if max_cll else max_fall
        out["content_light"] = {"max_content": max_cll, "max_average": max_fall}
    return out


def x265_hdr_params(hdr: dict) -> str:
    """x265's SEI settings for the Labelled Copy's `hdr` metadata (output_hdr_metadata): what it declares
    and nothing else, so an HLG source without static metadata gets none."""
    params = ["log-level=error"]
    md = hdr.get("mastering_display")
    if md:
        def units(key, scale):
            return round(ratio(str(md[key])) * scale)
        chroma = "".join(f"{name}({units(p + '_x', 50000)},{units(p + '_y', 50000)})"
                         for name, p in (("G", "green"), ("B", "blue"), ("R", "red"), ("WP", "white_point")))
        params += ["hdr10=1",
                   f"master-display={chroma}L({units('max_luminance', 10000)},{units('min_luminance', 10000)})"]
    light = hdr.get("content_light")
    if light:
        params.append(f"max-cll={light['max_content']},{light['max_average']}")
    return ":".join(params)


def render_command(tools: dict, info: dict, path: dict, overlay: Path, position: tuple, staged: Path,
                   enable: str | None, excerpt: tuple | None = None, hdr: dict | None = None) -> list:
    """The ffmpeg command for the Labelled Copy or, with `excerpt` (start, seconds on the playback
    timeline), a video-only excerpt of it rendered the same way and keeping the source's timestamps.
    `hdr` is what an HDR copy declares and shows (draw_label), for a path with an HDR signal (PQ or HLG)."""
    x, y = position
    turn, at_x, at_y = COUNTER_ROTATIONS[info["video"]["rotation"]]
    timing = f":enable='{enable}'" if enable else ""
    # A decoder may tag frames the source leaves untagged (VP8 frames come out BT.470BG): keep them untagged.
    untagged = [f"{name}=unknown" for key, name in SETPARAMS_NAMES.items()
                if info["video"]["colour"].get(key) in (None, "unknown")]
    tags = f",setparams={':'.join(untagged)}" if untagged else ""
    signal = hdr_label_filters(path) if path.get("signal") else ""
    # overlay converts both pictures to its `format`: the one keeping the source's depth and chroma.
    blend = f":format={path['pix_fmts'][info['video']['pix_fmt']]}"
    # Even sizes and positions: overlay rounds a subsampled picture's x and y down to even, which a
    # counter-rotation would turn into a shift the other way on the displayed picture.
    graph = (f"[1:v]{signal}pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:color=black@0,{turn}null[label];"
             f"[0:{info['video']['index']}][label]overlay=x={at_x.format(x=x, y=y)}:y={at_y.format(x=x, y=y)}:"
             f"eof_action=repeat{blend}{timing}{tags}[labelled]")
    # -copyts keeps every timestamp, a start offset included; -fps_mode passthrough (below) keeps variable frame
    # timing. -noautorotate keeps the stored picture, whose display matrix carries through.
    trim = ["-ss", f"{excerpt[0]:.3f}", "-t", f"{excerpt[1]:.3f}"] if excerpt else []
    argv = [tools["ffmpeg"], "-nostdin", "-v", "error", "-y", "-copyts", "-noautorotate", *trim, "-i", info["path"],
            "-i", overlay,
            "-filter_complex", graph, "-map", "[labelled]"]
    for out, stream in enumerate(info["audio"] + info["subtitles"], start=1):  # each track by name, never by default
        argv += ["-map", f"0:{stream['index']}", f"-map_metadata:s:{out}", f"0:s:{stream['index']}",
                 f"-disposition:{out}", "+".join(k for k, v in stream["disposition"].items() if v) or "0"]
        if stream["title"]:  # set again: a muxer doesn't write the `name` it read back (track_title)
            argv += [f"-metadata:s:{out}", f"title={stream['title']}"]
            if path["muxer"] in ("mp4", "mov"):  # and as the handler name, where FFmpeg 8 keeps a title
                argv += [f"-metadata:s:{out}", f"handler_name={stream['title']}"]
    argv += ["-c:v", path["encoder"], *path["encode"], "-pix_fmt", info["video"]["pix_fmt"]]
    if info["video"].get("codec_tag") in path.get("codec_tags", ()):  # hvc1 or hev1, as the source has it
        argv += ["-tag:v", info["video"]["codec_tag"]]
    if hdr:  # explicit: otherwise libx265 copies the source's levels, which the Label may exceed
        argv += ["-x265-params", x265_hdr_params(hdr["metadata"])]
    for key, option in COLOUR_OPTIONS:
        value = info["video"]["colour"].get(key)
        if value and value != "unknown":
            argv += [option, value]
    argv += ["-c:a", "copy", "-c:s", "copy", "-fps_mode", "passthrough", "-map_metadata", "0",
             *(["-an", "-sn", "-dn"] if excerpt else []), "-f", path["muxer"], staged]
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
# HDR10, in 10-bit code values: the mean change and level shift outside the Label that re-encoding may cause,
# and how far the backing plate may sit from its PQ level (about 5% in luminance at reference white).
HDR_MEAN_CHANGE, HDR_BIAS, LEVEL_TOLERANCE = 3.0, 1.0, 6
# The Label's brightest level is the one this share of its samples reaches, not its single brightest sample:
# libx265 rings next to the Icon's edges, and a handful of samples (measured: under 0.2% of a Label)
# overshoot white by an amount that varies between x265 builds (up to 13 code values seen). The Label's
# white is a fifth to a half of its samples, so a Label left at peak or dimmed still moves this level.
LABEL_BRIGHTEST_SHARE = 0.01


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


def planes_10bit(ffmpeg: str, video: Path, at: float, size: tuple) -> tuple[list, list, list]:
    """The Y, U and V planes of the frame shown at `at` seconds, as decoded 10-bit 4:2:0 code values."""
    from array import array
    import subprocess

    proc = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-noautorotate", "-ss", f"{at:.3f}", "-i", str(video),
                           "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-"],
                          capture_output=True, timeout=TOOL_TIMEOUT_S * 4)
    luma, chroma = size[0] * size[1], size[0] * size[1] // 4
    if proc.returncode != 0 or len(proc.stdout) < 2 * (luma + 2 * chroma):
        raise frame_failure(at, proc.stderr)
    values = array("H")
    values.frombytes(proc.stdout[: 2 * (luma + 2 * chroma)])
    if sys.byteorder != "little":
        values.byteswap()
    return list(values[:luma]), list(values[luma:luma + chroma]), list(values[luma + chroma:])


def light_levels(metadata: dict) -> tuple:
    """(MaxCLL, MaxFALL), 0 for unknown or not declared."""
    light = metadata.get("content_light") or {}
    return int(light.get("max_content") or 0), int(light.get("max_average") or 0)


def mastering_values(metadata: dict) -> dict:
    """The mastering display's chromaticities and luminances as numbers, from ffprobe's fractions."""
    return {k: round(ratio(str(v)) or 0, 5) for k, v in (metadata.get("mastering_display") or {}).items()}


def hdr_checks(tools: dict, source: dict, out: dict, staged: Path, box: tuple, at: float, hdr: dict) -> list:
    """HDR checks of the produced file: its declared static metadata, exactly what `hdr` expects (for HLG,
    none unless the source has it), and its decoded 10-bit picture."""
    expected, found = hdr["metadata"], out["video"]["colour"].get("hdr_metadata") or {}
    display = mastering_values(found) == mastering_values(expected)
    want = "the source's" if expected.get("mastering_display") else "none"
    if display:
        got = want
    else:
        got = "a different one" if found.get("mastering_display") else "none"
    checks = [check("hdr_metadata", display and light_levels(found) == light_levels(expected),
                    f"mastering display {got} (expected {want}), "
                    f"MaxCLL/MaxFALL {light_levels(found)} (expected {light_levels(expected)})")]
    width, height = source["video"]["width"], source["video"]["height"]
    before = planes_10bit(tools["ffmpeg"], Path(source["path"]), at, (width, height))
    after = planes_10bit(tools["ffmpeg"], staged, at, (width, height))
    left, top, right, bottom = box
    shifts = []
    for plane, (a, b) in enumerate(zip(before, after)):
        scale = 1 if plane == 0 else 2
        w = width // scale
        outside = [y - x for i, (x, y) in enumerate(zip(a, b))
                   if not (left // scale <= i % w < -(-right // scale) and top // scale <= i // w < -(-bottom // scale))]
        shifts.append((sum(abs(d) for d in outside) / len(outside), sum(outside) / len(outside)))
    mean_change, worst_bias = max(s[0] for s in shifts), max(abs(s[1]) for s in shifts)
    # x265 re-encoding moves a sample by about a code value on average; a transfer or range conversion
    # shifts levels by tens.
    checks.append(check("hdr_picture", mean_change <= HDR_MEAN_CHANGE and worst_bias <= HDR_BIAS,
                        f"outside the Label, 10-bit samples changed by {mean_change:.2f} code values on average, "
                        f"with a level shift of {worst_bias:.2f}, at {at:.2f} s"))
    a, b = before[0], after[0]
    label = [b[row * width + col] for row in range(top, bottom) for col in range(left, right)
             if abs(b[row * width + col] - a[row * width + col]) > 40]  # the plate's rounded corners show the source
    band = sorted(b[row * width + left + hdr["pad"] // 2]
                  for row in range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3))
    plate = band[len(band) // 2] if band else None
    label.sort()
    peak = label[int(len(label) * (1 - LABEL_BRIGHTEST_SHARE))] if label else None
    checks.append(check("label_level", plate is not None and abs(plate - hdr["plate_code"]) <= LEVEL_TOLERANCE
                        and peak is not None  # the plate or the Icon is white: neither dim nor at peak
                        and abs(peak - hdr["white_code"]) <= 2 * LEVEL_TOLERANCE,
                        f"backing plate at code value {plate} (expected {hdr['plate_code']}), brightest "
                        f"{LABEL_BRIGHTEST_SHARE:.0%} of the Label at {peak} or above, its brightest sample "
                        f"{label[-1] if label else None} (reference white {hdr['white_code']})"))
    return checks


def compare_streams(name: str, before: list, after: list, keys: tuple) -> dict:
    left = [{k: s.get(k) for k in keys} for s in before]
    right = [{k: s.get(k) for k in keys} for s in after]
    return check(name, left == right, f"{len(after)} kept" if left == right else f"source {left}, copy {right}")


def validate_output(tools: dict, source: dict, staged: Path, box: tuple, visible_at: float, work: Path,
                    hidden_at: float | None = None, hdr: dict | None = None) -> list:
    """Checks of the produced file itself, independent of the checks before rendering. `hdr` is what an
    HDR10 copy must declare and show (draw_label)."""
    out = inspect_video(staged, tools, support=False)
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
    if hdr:
        checks += hdr_checks(tools, source, out, staged, box, visible_at, hdr)
    return checks


def label_plan(args: argparse.Namespace) -> dict:
    """Everything checked before rendering, shared by `video-apply` and `video-preview`: the video's
    labelling path, the Label's geometry on the video as displayed, and the effective visibility."""
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
    duration = info["container"]["duration"] or 0
    return {"original": original, "tools": tools, "info": info, "path": path_named(support["path"]),
            "display": display, "icon_height": icon_height, "margin": margin, "pad": pad,
            "footprint": plated(probe_icon.size, pad), "duration": duration,
            "visibility": resolve_visibility(args, duration)}


def draw_label(args: argparse.Namespace, plan: dict, work: Path) -> dict:
    """The Label as `video-apply` incorporates it: Icon Colour, overlay PNG and position."""
    tools, original, display, margin = plan["tools"], plan["original"], plan["display"], plan["margin"]
    if args.colour == AUTO:
        # An HDR video's contrast is judged on its SDR rendering, as the preview frames show it.
        frames = [extract_frame(tools["ffmpeg"], original, t, work / f"sample-{i}.png", sdr_view(plan["path"]))
                  for i, t in enumerate(sample_times(plan["duration"]))]
        colour, contrasts = choose_colour(frames, args.corner, display, plan["footprint"], margin)
    else:
        colour, contrasts = args.colour, None
    overlay, plate_size, icon_px = label_overlay(args.variant, colour, plan["icon_height"], plan["pad"],
                                                 work / "label.png")
    x, y = (v - v % 2 for v in icon_position(args.corner, display, plate_size, margin))  # see render_command
    box = (x, y, x + plate_size[0], y + plate_size[1])
    hdr = None
    if plan["path"].get("signal"):
        white = round(limited_code(label_white(plan["path"])), 1)
        hdr = {"metadata": output_hdr_metadata(plan["info"], plan["path"], plate_size, display),
               "pad": plan["pad"],
               "plate_code": white if colour == "black" else 64, "white_code": white}
    return {"colour": colour, "contrast": contrasts, "overlay": overlay, "position": (x, y), "box": box, "hdr": hdr,
            "enable": visibility_enable(plan["visibility"], plan["info"]),
            "settings": {
                "variant": args.variant, "corner": args.corner, "colour": colour, "plate": True,
                "contrast": contrasts,
                "icon": {"x": x + plan["pad"], "y": y + plan["pad"], "width": icon_px[0], "height": icon_px[1]},
                "plate_box": {"x": x, "y": y, "width": plate_size[0], "height": plate_size[1]},
                "margin": margin, "visibility": plan["visibility"],
            }}


UNVERIFIED_HDR = ("The checks measured the decoded 10-bit values; no HDR display was used, so how the copy looks "
                  "in HDR is not verified, nor how a given player or platform shows it.")


def hdr_report(path: dict, metadata: dict) -> dict:
    """`video.hdr` of an HDR Labelled Copy: its profile, the Label's level, the metadata it declares."""
    if path["signal"] == "pq":
        return {"dynamic_range": "hdr10", "label_white_nits": REFERENCE_WHITE_NITS, "metadata": metadata,
                "note": (f"The copy stays HDR10: 10-bit, BT.2020, PQ. The Label's white is at {REFERENCE_WHITE_NITS} "
                         "cd/m2 (SDR reference white), its black at 0. The mastering display metadata is the "
                         "source's; MaxCLL is at least the Label's white and MaxFALL was raised by the most the "
                         "Label can add. " + UNVERIFIED_HDR)}
    declared = ("It declares the source's static metadata, with content light levels raised for the Label."
                if metadata else "Like the source, it declares no mastering display or content light levels.")
    return {"dynamic_range": "hlg", "label_white_signal": HLG_REFERENCE_WHITE, "metadata": metadata,
            "note": (f"The copy stays HLG: 10-bit, BT.2020, the HLG transfer (ARIB STD-B67), never converted to PQ "
                     f"or SDR. The Label's white is at {HLG_REFERENCE_WHITE:.0%} of the HLG signal (HDR reference "
                     f"white, {REFERENCE_WHITE_NITS} cd/m2 on a 1000 cd/m2 display), its black at 0. "
                     f"{declared} " + UNVERIFIED_HDR)}


def cmd_video_apply(args: argparse.Namespace) -> dict:
    import tempfile

    plan = label_plan(args)
    original, tools, info, path = plan["original"], plan["tools"], plan["info"], plan["path"]
    video, display, duration, visibility = info["video"], plan["display"], plan["duration"], plan["visibility"]
    target = labelled_copy_path(original)
    # ffmpeg's -map_metadata carries no XMP (measured with FFmpeg 9): it is written after encoding.
    kept = kept_marking(original, video_xmp(original)) if path["muxer"] in VIDEO_XMP_MUXERS else {}
    with tempfile.TemporaryDirectory(prefix="eu-ai-labelling-") as work:
        work = Path(work)
        label = draw_label(args, plan, work)
        box = label["box"]
        try:
            with staged_replace(target) as staged:
                proc = run_tool(render_command(tools, info, path, label["overlay"], label["position"], staged,
                                               label["enable"], hdr=label["hdr"]))
                if proc.returncode != 0 or not rendered(staged):
                    raise LabelToolError("render_failed",
                                         f"ffmpeg could not render {target.name}: "
                                         f"{stderr_tail(proc.stderr, 3, 'no output')}. "
                                         "The original and any previous Labelled Copy are unchanged.")
                if kept:
                    write_video_xmp(staged, xmp_for_copy(kept), path["muxer"])
                visible_at, hidden_at = label_check_times(visibility, info)
                checks = validate_output(tools, info, staged, box, visible_at, work, hidden_at, hdr=label["hdr"])
                failed = [c for c in checks if not c["passed"]]
                if failed:
                    raise LabelToolError(
                        "output_validation_failed",
                        f"The rendered copy did not keep the source's characteristics: "
                        + "; ".join(f"{c['check']}: {c['detail']}" for c in failed)
                        + ". It was discarded; the original and any previous Labelled Copy are unchanged.",
                        checks=checks)
        except OSError as exc:
            raise LabelToolError("write_failed", f"Cannot write {target}: {exc}")
    return {
        "labelled_copy": str(target),
        "original": str(original),
        **label["settings"],
        "path": path["name"],
        "video": {
            "container": info["container"]["format"], "codec": video["codec"],
            "width": display[0], "height": display[1], "duration": duration,
            "re_encoded": True, "encoder": path["encoder"],
            "note": (f"The video stream was re-encoded as {path['codec_title']} with {path['encoder']} "
                     f"({path['quality']}) to incorporate the Label, so the copy "
                     "is not bit-identical to the original. Audio and subtitle tracks were copied without "
                     "re-encoding."),
            **({"hdr": hdr_report(path, label["hdr"]["metadata"])} if label["hdr"] else {}),
        },
        "validation": {"passed": True, "checks": checks},
        **({"marking_kept": kept} if kept else {}),
    }


# --- previews -------------------------------------------------------------------

PREVIEW_SUFFIX = ".label-preview"
PREVIEW_FRAMES = 5
PREVIEW_SAMPLE = re.compile(r"frame-\d{2,}-\d+\.\d{2}s\.png|excerpt-\d{2,}-\d+\.\d{2}-\d+\.\d{2}s\.[A-Za-z0-9]+")
EXCERPT_S = 3.0  # an excerpt of continuous display
EXCERPT_LEAD_S = 1.0  # hidden time kept either side of a periodic window
EXCERPT_EDGE_S = 2.0  # visible time kept at each end of a long periodic window
SAMPLING_NOTE = (
    "These frames and excerpts are samples: they cannot show that the Label covers no face, text, subtitle "
    "or main subject in every frame of the video. Only watching the full Labelled Copy can."
)
EXCERPT_NOTE = (
    "Each excerpt is rendered as video-apply renders the Labelled Copy with these settings: the same Icon "
    "Variant, Icon Colour, size, position, backing plate and visibility timing, on the source's timestamps. "
    "Excerpts carry the video only, without audio or subtitles."
)

HDR_PREVIEW_NOTES = {
    "pq": (
        "This is HDR10 video. The frames are SDR renderings, tone-mapped for viewing: reference white (203 cd/m2) "
        "shows as near white and brighter highlights are compressed. They show content and layout for choosing a "
        "corner, not how the video looks in HDR. The excerpts are HDR10 like the Labelled Copy, with the Label at "
        "reference white; on an SDR display or player they don't show HDR appearance either. Only an HDR display "
        "can, and the tool has not checked one."
    ),
    "hlg": (
        "This is HLG video. The frames are SDR renderings, tone-mapped for viewing through the HLG curve: "
        "reference white (75% HLG) shows as near white and brighter highlights are compressed. They show "
        "content and layout for choosing a corner, not how the video looks in HDR. The excerpts are HLG like the "
        "Labelled Copy, with the Label at reference white; an SDR display or player shows them with HLG's SDR "
        "compatibility at best, not their HDR appearance. Only an HDR display can, and the tool has not checked "
        "one."
    ),
}


def preview_folder(args: argparse.Namespace, original: Path) -> Path:
    """Where previews go: `--out`, or `<name>.<ext>.label-preview` next to the video. Never a file,
    the original or its Labelled Copy."""
    out = Path(args.out) if args.out else original.with_name(original.name + PREVIEW_SUFFIX)
    if out.resolve() in (original.resolve(), labelled_copy_path(original).resolve()) or is_labelled_copy(out):
        raise LabelToolError("usage", f"--out {out} is the video or a Labelled Copy: choose a folder for previews.")
    if out.exists() and not out.is_dir():
        raise LabelToolError("usage", f"--out {out} is a file: choose a folder for previews.")
    return out


def merged(spans: list) -> list:
    out = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


def excerpt_spans(visibility: dict, duration: float) -> list:
    """Playback spans for the excerpts. Continuous display: the start, middle and end. Periodic display:
    the first, second and last windows, each with hidden time either side, so that every excerpt shows
    the Label and its appearing or disappearing."""
    if visibility["mode"] != "periodic":
        length = min(EXCERPT_S, duration)
        middle = max(0.0, duration / 2 - length / 2)
        spans = [(0.0, length), (middle, middle + length), (duration - length, duration)]
    else:
        window, every = visibility["window"], visibility["every"]
        last = int(max(duration - 1e-3, 0) // every)
        spans = []
        for k in sorted({0, min(1, last), last}):
            start, end = k * every, min(k * every + window, duration)
            before, after = max(0.0, start - EXCERPT_LEAD_S), min(duration, end + EXCERPT_LEAD_S)
            if end - start <= 2 * EXCERPT_EDGE_S:
                spans.append((before, after))
            else:
                spans += [(before, start + EXCERPT_EDGE_S), (end - EXCERPT_EDGE_S, after)]
    return [(round(a, 3), round(b, 3)) for a, b in merged(spans) if b > a]


def visible_spans(visibility: dict, start: float, end: float) -> list:
    """The parts of [start, end] in which the Label shows."""
    if visibility["mode"] != "periodic":
        return [[start, end]]
    window, every = visibility["window"], visibility["every"]
    spans, k = [], int(start // every)
    while k * every < end:
        a, b = max(start, k * every), min(end, k * every + window)
        if b > a:
            spans.append([round(a, 3), round(b, 3)])
        k += 1
    return spans


def render_excerpt(plan: dict, label: dict, span: tuple, target: Path) -> int:
    """Render one excerpt as `video-apply` renders the whole video; return its decoded frame count."""
    info, tools = plan["info"], plan["tools"]
    # `-ss` counts from the container's start, the playback timeline from the first video frame.
    lead = (info["video"]["start_time"] or 0) - (info["container"]["start_time"] or 0)
    with staged_replace(target) as staged:
        proc = run_tool(render_command(tools, info, plan["path"], label["overlay"], label["position"], staged,
                                       label["enable"], excerpt=(span[0] + lead, span[1] - span[0]),
                                       hdr=label["hdr"]),
                        timeout=TOOL_TIMEOUT_S * 10)
        if proc.returncode != 0 or not rendered(staged):
            raise LabelToolError("render_failed", f"ffmpeg could not render the excerpt: {stderr_tail(proc.stderr)}")
        decoded = len(packet_times(tools["ffprobe"], staged, 0))
        if not decoded:
            raise LabelToolError("render_failed", "The rendered excerpt holds no video frame.")
    return decoded


def sample_failure(exc: Exception) -> str:
    return exc.message if isinstance(exc, LabelToolError) else f"Cannot write the sample: {exc}"


def cmd_video_preview(args: argparse.Namespace) -> dict:
    import tempfile

    if args.frames < 1:
        raise LabelToolError("usage", f"--frames must be at least 1, not {args.frames}.")
    plan = label_plan(args)
    original, tools, duration, visibility = plan["original"], plan["tools"], plan["duration"], plan["visibility"]
    out = preview_folder(args, original)
    try:
        out.mkdir(parents=True, exist_ok=True)
        for old in out.iterdir():  # an earlier preview's samples, by the exact names it writes, or links there
            if PREVIEW_SAMPLE.fullmatch(old.name) and (old.is_symlink() or old.is_file()):
                old.unlink()
    except OSError as exc:
        raise LabelToolError("write_failed", f"Cannot write previews to {out}: {exc}")
    frames, excerpts, view = [], [], sdr_view(plan["path"])
    with tempfile.TemporaryDirectory(prefix="eu-ai-labelling-") as work:
        work = Path(work)
        label = draw_label(args, plan, work)
        for i, at in enumerate(sample_times(duration, args.frames), 1):
            target = out / f"frame-{i:02d}-{at:.2f}s.png"
            try:
                with staged_replace(target) as staged:
                    extract_frame(tools["ffmpeg"], original, at, staged, view)
                frames.append({"time": at, "path": str(target), "status": "written"})
            except (LabelToolError, OSError) as exc:
                frames.append({"time": at, "path": None, "status": "failed", "error": sample_failure(exc)})
        for i, (start, end) in enumerate(excerpt_spans(visibility, duration), 1):
            target = out / f"excerpt-{i:02d}-{start:.2f}-{end:.2f}s{original.suffix}"
            entry = {"start": start, "end": end, "label_visible": visible_spans(visibility, start, end)}
            try:
                decoded = render_excerpt(plan, label, (start, end), target)
                entry |= {"path": str(target), "status": "written", "decoded_frames": decoded}
            except (LabelToolError, OSError) as exc:
                entry |= {"path": None, "status": "failed", "error": sample_failure(exc)}
            excerpts.append(entry)
    failed = [e for e in frames + excerpts if e["status"] == "failed"]
    if len(failed) == len(frames) + len(excerpts):
        raise LabelToolError("preview_failed",
                             f"No preview of {original.name} could be made: {failed[0]['error']} "
                             "Nothing was checked; the original and any previous Labelled Copy are unchanged.",
                             frames=frames, excerpts=excerpts)
    return {
        "original": str(original),
        "out": str(out),
        **label["settings"],
        "path": plan["path"]["name"],
        "frames": frames,
        "frame_rendering": "sdr_tone_mapped" if view else "source",
        "excerpts": excerpts,
        "complete": not failed,
        "failed": len(failed),
        "excerpt_note": EXCERPT_NOTE,
        "sampling_note": SAMPLING_NOTE,
        **({"hdr_note": HDR_PREVIEW_NOTES[plan["path"]["signal"]]} if view else {}),
    }


# --- marking: the Marking a Provider embedded, as evidence for the Icon Variant -------

# IPTC DigitalSourceType codes (https://cv.iptc.org/newscodes/digitalsourcetype/). Two say which Icon
# Variant applies; three say AI took part without saying how. Every other code (digitalCapture,
# digitalArt, humanEdits, ...) is a human origin and is ignored, as if no Marking were found.
PRECISE_SOURCE_TYPES = {"trainedAlgorithmicMedia": "generated", "compositeWithTrainedAlgorithmicMedia": "modified"}
VAGUE_SOURCE_TYPES = {"algorithmicallyEnhanced", "compositeSynthetic", "algorithmicMedia"}
VALID_C2PA_STATES = ("Valid", "Trusted")  # the signature validates; whether the signer is trusted is not judged
# c2pa-python's Reader settings: never fetch a remote manifest or an OCSP response.
C2PA_OFFLINE = {"verify": {"remote_manifest_fetch": False, "ocsp_fetch": False}}
C2PA_ACTIONS_LABEL = re.compile(r"c2pa\.actions(?:\.v\d+)?(?:__\d+)?\Z")  # c2pa.actions.v2, c2pa.actions__1, ...

# AI tools named in Software, CreatorTool, a C2PA claim generator or a container tag, the first match
# winning. A name alone never says which Icon Variant applies, so a match is only ever vague.
AI_TOOLS = {
    "Stable Diffusion": r"stable[ -]?diffusion|\bsdxl\b",
    "AUTOMATIC1111": r"automatic1111|\bA1111\b",
    "ComfyUI": r"comfyui",
    "InvokeAI": r"invoke[ -]?ai",
    "Fooocus": r"fooocus",
    "Midjourney": r"midjourney",
    "DALL-E": r"\bdall[-·. ]?e(?![a-z])",
    "ChatGPT": r"chatgpt|\bgpt[- ]?(?:4o|image)",
    "Sora": r"\bsora\b",
    "Adobe Firefly": r"firefly",
    "Imagen": r"\bimagen\b",
    "Gemini": r"\bgemini\b",
    "Veo": r"\bveo\b",
    "Runway": r"\brunway(?:ml)?\b",
    "Pika": r"\bpika\b",
    "Kling": r"\bkling\b",
    "Luma Dream Machine": r"dream machine|\bluma ai\b",
    "Leonardo.Ai": r"leonardo\.?ai",
    "Ideogram": r"ideogram",
    "FLUX": r"\bflux\.1\b|black forest labs",
    "NovelAI": r"novelai",
    "Krea": r"\bkrea\b",
    "Synthesia": r"synthesia",
    "HeyGen": r"heygen",
    "Grok": r"\bgrok\b",
    "OpenAI": r"\bopenai\b",  # after its products, so that "OpenAI Sora" names Sora
}
GENERATOR_CHUNKS = ("parameters", "prompt", "workflow")  # PNG text chunks of AUTOMATIC1111 and ComfyUI
VIDEO_TAGS = ("encoder", "comment")  # plus every com.apple.quicktime.* tag
QUOTED_CHARS = 200  # a value is cut to this length in the report and in the quote
XMP_START = re.compile(rb"<x:x[ma]pmeta\b")
XMP_END = re.compile(rb"</x:x[ma]pmeta\s*>")
XMP_MAX_BYTES = 4_000_000
NS_IPTC_EXT = "{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}"
NS_RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
XMP_TOOL_FIELDS = {"{http://ns.adobe.com/xap/1.0/}CreatorTool": "XMP CreatorTool",
                   "{http://ns.adobe.com/tiff/1.0/}Software": "XMP Software"}
EXIF_SOFTWARE = 0x0131
MP4_XMP_UUID = bytes.fromhex("BE7ACFCB97A942E89C71999491E3AFAC")  # Adobe XMP specification, part 3
BOX_READ_MAX_BYTES = 64_000_000  # the most of a `moov` box read to find its XMP


def shortened(value: str) -> str:
    value = " ".join(str(value).split())
    return value if len(value) <= QUOTED_CHARS else value[:QUOTED_CHARS - 1] + "…"


def ai_tool(value: str) -> str | None:
    """The AI tool `value` names, if any."""
    for name, pattern in AI_TOOLS.items():
        if re.search(pattern, value, re.IGNORECASE):
            return name
    return None


def source_type_code(value: str) -> str:
    """`trainedAlgorithmicMedia` from the full IPTC URI or from the bare code."""
    return value.strip().rstrip("/").rsplit("/", 1)[-1]


def graded_source_type(code: str, trusted: bool = True) -> dict | None:
    """`grade` (and `variant` when precise) of an IPTC code, or None for a human origin. A precise code is
    precise only when `trusted`: from XMP, or from a C2PA manifest whose signature validates."""
    if code in PRECISE_SOURCE_TYPES:
        return {"grade": "precise", "variant": PRECISE_SOURCE_TYPES[code]} if trusted else {"grade": "vague"}
    if code in VAGUE_SOURCE_TYPES:
        return {"grade": "vague"}
    return None


def tool_signal(source: str, field: str, value, label: str | None = None) -> dict | None:
    """A vague signal when `value` names an AI tool."""
    if not isinstance(value, str):
        return None
    tool = ai_tool(value)
    if tool is None:
        return None
    value = shortened(value)
    return {"source": source, "field": field, "value": value, "tool": tool, "grade": "vague",
            "quote": f"{label or field}: {value}"}


def xmp_packets(blob: bytes) -> list[bytes]:
    """Each `<x:xmpmeta>` packet in `blob`."""
    packets, at = [], 0
    while (start := XMP_START.search(blob, at)) is not None:
        end = XMP_END.search(blob, start.end())
        if end is None:
            break
        packets.append(blob[start.start():end.end()])
        at = end.end()
    return packets


def parse_xmp(packet: bytes):
    """The packet's XML tree, or None. A packet declaring a DTD is refused, so no entity is ever expanded."""
    import xml.etree.ElementTree as ET

    if b"<!DOCTYPE" in packet or b"<!ENTITY" in packet or len(packet) > XMP_MAX_BYTES:
        return None
    try:
        return ET.fromstring(packet)
    except ET.ParseError:
        return None


def xmp_signals(blobs: list[bytes]) -> list[dict]:
    """IPTC DigitalSourceType (source `xmp`) and AI tools in CreatorTool or tiff:Software (`software`)."""
    signals, seen = [], set()
    for blob in blobs:
        for packet in xmp_packets(blob):
            tree = parse_xmp(packet)
            if tree is None:
                continue
            for element in tree.iter():
                values = list(element.attrib.items())
                text = (element.text or "").strip()
                if text:
                    values.append((element.tag, text))
                if element.tag == NS_IPTC_EXT + "DigitalSourceType" and element.get(NS_RDF + "resource"):
                    values.append((element.tag, element.get(NS_RDF + "resource")))
                for name, value in values:
                    if (name, value) in seen:
                        continue
                    seen.add((name, value))
                    if name == NS_IPTC_EXT + "DigitalSourceType":
                        code = source_type_code(value)
                        graded = graded_source_type(code)
                        if graded:
                            signals.append({"source": "xmp", "field": "DigitalSourceType", "value": code, **graded,
                                            "quote": f"XMP DigitalSourceType: {code}"})
                    elif name in XMP_TOOL_FIELDS:
                        signal = tool_signal("software", XMP_TOOL_FIELDS[name], value)
                        if signal:
                            signals.append(signal)
    return signals


def as_text(value) -> str:
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)


def xmp_blobs(image) -> list[bytes]:
    """The blobs of an opened (and, for a PNG, loaded) image that may hold its XMP."""
    blobs = [v if isinstance(v, bytes) else as_text(v).encode()
             for k, v in image.info.items() if k in ("xmp", "XML:com.adobe.xmp")]
    return blobs + [data for marker, data in getattr(image, "applist", []) if marker == "APP1"]


def image_marking(path: Path) -> list[dict]:
    """XMP, EXIF Software and the generator PNG text chunks of an image."""
    from PIL import Image

    try:
        image = Image.open(path)
    except Exception as exc:  # Pillow raises several types for unreadable files
        if path.suffix.lower() in SVG_SUFFIXES or looks_like_svg(path):
            raise svg_refusal(path)
        raise LabelToolError("unreadable_image", f"Cannot read {path} as an image: {exc}")
    with image:
        if image.format == "PNG":
            try:
                image.load()  # Pillow reads the text and XMP chunks after IDAT only once the image is loaded
            except Exception:  # truncated image data: keep the chunks read before it
                pass
        info = dict(image.info)
        signals = xmp_signals(xmp_blobs(image))
        try:
            software = image.getexif().get(EXIF_SOFTWARE)
        except Exception:  # a broken EXIF block is no Marking
            software = None
        if (signal := tool_signal("software", "EXIF Software", software)) is not None:
            signals.append(signal)
        if image.format == "PNG":
            for key, value in info.items():
                if not isinstance(key, str) or key in ("xmp", "XML:com.adobe.xmp"):
                    continue
                if key.lower() in GENERATOR_CHUNKS and as_text(value).strip():
                    value = shortened(as_text(value))
                    signals.append({"source": "png_text", "field": key, "value": value, "grade": "vague",
                                    "quote": f'PNG text chunk "{key}": {value}'})
                elif key.lower() == "software":
                    if (signal := tool_signal("software", "PNG Software", as_text(value))) is not None:
                        signals.append(signal)
    return signals


def iso_boxes(read, start: int, end: int):
    """(type, payload start, payload end) of each ISO BMFF box between `start` and `end`."""
    at = start
    while at + 8 <= end:
        header = read(at, 16)
        if len(header) < 8:
            return
        size, kind = int.from_bytes(header[:4], "big"), header[4:8]
        offset = 8
        if size == 1:
            if len(header) < 16:
                return
            size, offset = int.from_bytes(header[8:16], "big"), 16
        elif size == 0:
            size = end - at
        if size < offset:
            return
        yield kind, at + offset, min(at + size, end)
        at += size


def video_xmp(path: Path) -> list[bytes]:
    """The XMP packets of an MP4 (a top-level `uuid` box) or a QuickTime file (`moov/udta/XMP_`)."""
    blobs = []
    size = path.stat().st_size
    with path.open("rb") as handle:
        def read(at: int, length: int) -> bytes:
            handle.seek(at)
            return handle.read(length)

        for kind, start, end in iso_boxes(read, 0, size):
            if kind == b"uuid" and read(start, 16) == MP4_XMP_UUID and end - start <= XMP_MAX_BYTES:
                blobs.append(read(start + 16, end - start - 16))
            elif kind == b"moov" and end - start <= BOX_READ_MAX_BYTES:
                moov = read(start, end - start)
                inside = lambda at, length: moov[at:at + length]  # noqa: E731
                for child, child_start, child_end in iso_boxes(inside, 0, len(moov)):
                    if child == b"udta":
                        for item, item_start, item_end in iso_boxes(inside, child_start, child_end):
                            if item == b"XMP_":
                                blobs.append(moov[item_start:item_end])
                    elif child == b"uuid" and moov[child_start:child_start + 16] == MP4_XMP_UUID:
                        blobs.append(moov[child_start + 16:child_end])
    return blobs


def video_marking(path: Path) -> list[dict]:
    """The XMP and the container tags ffprobe reads (`encoder`, `comment`, `com.apple.quicktime.*`)."""
    tools = require_video_tools()
    proc = run_tool([tools["ffprobe"], "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json",
                     path], timeout=TOOL_TIMEOUT_S * 4)
    try:
        probed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        probed = {}
    if proc.returncode != 0:
        raise LabelToolError("unreadable_video", f"Cannot read {path.name} as a video: "
                                                 f"{stderr_tail(proc.stderr, fallback='no stream found')}")
    signals = xmp_signals(video_xmp(path))
    tag_sets = [probed.get("format", {}).get("tags") or {}] + [s.get("tags") or {} for s in probed.get("streams", [])]
    seen = set()
    for tags in tag_sets:
        for key, value in tags.items():
            name = key.lower()
            if name in VIDEO_TAGS or name.startswith("com.apple.quicktime."):
                signal = tool_signal("container_tags", name, value, label=f"container tag {name}")
                if signal and (name, signal["value"]) not in seen:
                    seen.add((name, signal["value"]))
                    signals.append(signal)
    return signals


def c2pa_provider(manifest: dict) -> str | None:
    info = manifest.get("claim_generator_info") or []
    names = [i.get("name") for i in info if isinstance(i, dict) and i.get("name")]
    return names[0] if names else manifest.get("claim_generator")


def c2pa_signer(manifest: dict) -> str | None:
    signature = manifest.get("signature_info") or {}
    return signature.get("issuer") or signature.get("common_name")


def c2pa_actions(manifest: dict) -> list[dict]:
    actions = []
    for assertion in manifest.get("assertions") or []:
        if C2PA_ACTIONS_LABEL.match(str(assertion.get("label", ""))):
            actions += [a for a in (assertion.get("data") or {}).get("actions") or [] if isinstance(a, dict)]
    return actions


def c2pa_marking(path: Path) -> tuple[str, list[dict]]:
    """(`checked` | `unavailable` | `unreadable`, signals) from the file's embedded C2PA manifests, read
    offline. A manifest kept only at a remote URL counts as none."""
    try:
        import c2pa
    except Exception:  # not installed under the python3 fallback, or its native library won't load
        return "unavailable", []
    try:
        with c2pa.Context(c2pa.Settings.from_dict(C2PA_OFFLINE)) as context, \
                c2pa.Reader(str(path), context=context) as reader:
            store = json.loads(reader.json())
    except (c2pa.C2paError.ManifestNotFound, c2pa.C2paError.NotSupported, c2pa.C2paError.RemoteManifest):
        return "checked", []
    except c2pa.C2paError as exc:
        if str(exc).startswith("Remote"):  # a remote-only manifest, never fetched
            return "checked", []
        return "unreadable", []
    state = store.get("validation_state")
    valid = state in VALID_C2PA_STATES
    active_label = store.get("active_manifest")
    signals = []
    for label, manifest in (store.get("manifests") or {}).items():
        active = label == active_label
        provider, signer = c2pa_provider(manifest), c2pa_signer(manifest)
        validity = "signature valid" if valid else f"signature {str(state or 'not validated').lower()}"
        who = f"C2PA {'manifest' if active else 'ingredient manifest'} by {provider or 'an unnamed generator'}" + (
            f", signed by {signer}" if signer else "") + f" ({validity})"
        details = {"active": active, "provider": provider, "signer": signer, "validation_state": state}
        found = False
        for action in c2pa_actions(manifest):
            if not action.get("digitalSourceType"):
                continue
            code = source_type_code(str(action["digitalSourceType"]))
            # An ingredient's origin is not the origin of this file: it never settles the variant.
            graded = graded_source_type(code, trusted=valid and active)
            if graded:
                found = True
                signals.append({"source": "c2pa", "field": "digitalSourceType", "value": code,
                                "action": action.get("action"), **details, **graded,
                                "quote": f"{who}: {action.get('action')} with digitalSourceType {code}"})
        if not found and active:
            for field, value in (("claim generator", provider), ("signer", signer)):
                tool = ai_tool(value) if isinstance(value, str) else None
                if tool:
                    signals.append({"source": "c2pa", "field": field, "value": shortened(value), "tool": tool,
                                    **details, "grade": "vague", "quote": who})
                    break
    return "checked", signals


def settle(signals: list[dict]) -> tuple[str | None, list[dict]]:
    """The Icon Variant the signals settle, and the signals that settle it, after the conflict rules:
    a valid active C2PA manifest decides; otherwise precise signals that disagree all become vague."""
    precise = [s for s in signals if s["grade"] == "precise"]
    deciding = [s for s in precise if s["source"] == "c2pa"]  # only the active manifest, when valid, is precise
    if deciding and len({s["variant"] for s in deciding}) == 1:
        variant = deciding[0]["variant"]
        for signal in precise:
            if signal["variant"] != variant:
                signal["overridden"] = True
        return variant, [s for s in precise if s["variant"] == variant]
    if len({s["variant"] for s in precise}) == 1:
        return precise[0]["variant"], precise
    for signal in precise:
        signal.update(grade="vague", conflict=True)
        del signal["variant"]
    return None, []


def cmd_marking(args: argparse.Namespace) -> dict:
    path = Path(args.file)
    if not path.is_file():
        raise LabelToolError("not_found", f"File not found: {path}")
    media = media_of(path)
    signals = video_marking(path) if media == "video" else image_marking(path)
    c2pa_status, c2pa_signals = c2pa_marking(path)
    signals = c2pa_signals + signals
    settled, settled_by = settle(signals)
    return {
        "path": str(path),
        "media": media,
        "c2pa": c2pa_status,
        "signals": signals,
        "settled": settled,
        "settled_by": [s["quote"] for s in settled_by],
        "quotes": [] if settled else [s["quote"] for s in signals if s["grade"] == "vague"],
    }


# --- The Marking a Labelled Copy keeps ----------------------------------------------

# The original's IPTC DigitalSourceType and the IPTC AI fields (IPTC Photo Metadata 2025.1), kept unchanged:
# adding a Label doesn't change what the content is. Nothing else of its XMP is kept: its xmpMM:InstanceID
# would misidentify the copy, and its dcterms:provenance points at a manifest whose hard binding the copy fails.
KEPT_IPTC_FIELDS = ("DigitalSourceType", "AISystemUsed", "AISystemVersionUsed", "AIPromptInformation",
                    "AIPromptWriterName")
IPTC_SOURCE_URI = "http://cv.iptc.org/newscodes/digitalsourcetype/"
VIDEO_XMP_MUXERS = ("mp4", "mov")


def iptc_fields(blobs: list[bytes]) -> dict:
    """The first plain value of each KEPT_IPTC_FIELDS in the XMP packets of `blobs`, as written."""
    found = {}
    for blob in blobs:
        for packet in xmp_packets(blob):
            tree = parse_xmp(packet)
            if tree is None:
                continue
            for element in tree.iter():
                values = list(element.attrib.items())
                if len(element) == 0:  # a structure (rdf:Alt, rdf:Bag) is not a plain value
                    values.append((element.tag, element.get(NS_RDF + "resource") or element.text or ""))
                for name, value in values:
                    field = name[len(NS_IPTC_EXT):] if name.startswith(NS_IPTC_EXT) else None
                    if field in KEPT_IPTC_FIELDS and value.strip():
                        found.setdefault(field, value.strip())
    return found


def image_xmp(path: Path) -> list[bytes]:
    from PIL import Image

    with Image.open(path) as image:
        image.load()  # a PNG's chunks after IDAT are read only once the image is loaded
        return xmp_blobs(image)


def kept_marking(original: Path, blobs: list[bytes]) -> dict:
    """The IPTC fields the Labelled Copy of `original` keeps. The DigitalSourceType is the XMP's, unless the
    active C2PA manifest settles the Icon Variant with another one: then it is the manifest's, so that the
    copy settles the variant the original settles."""
    kept = iptc_fields(blobs)
    _, signals = c2pa_marking(original)
    deciding = {s["value"] for s in signals if s["grade"] == "precise"}
    if len(deciding) == 1:
        code = deciding.pop()
        if source_type_code(kept.get("DigitalSourceType", "")) != code:
            kept["DigitalSourceType"] = IPTC_SOURCE_URI + code
    return {field: kept[field] for field in KEPT_IPTC_FIELDS if field in kept}


def xmp_for_copy(kept: dict) -> bytes:
    """A fresh XMP packet holding only the `kept` IPTC fields."""
    from xml.sax.saxutils import escape

    fields = "".join(f"<Iptc4xmpExt:{name}>{escape(value)}</Iptc4xmpExt:{name}>" for name, value in kept.items())
    return ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            f'<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="{NS_IPTC_EXT[1:-1]}">{fields}</rdf:Description>'
            '</rdf:RDF></x:xmpmeta><?xpacket end="w"?>').encode()


def xmp_options(image_format: str, packet: bytes) -> dict:
    """Pillow `save()` options writing `packet` as the image's XMP."""
    if image_format == "PNG":
        from PIL.PngImagePlugin import PngInfo

        info = PngInfo()
        info.add_itxt("XML:com.adobe.xmp", packet.decode())
        return {"pnginfo": info}
    return {"xmp": packet}  # JPEG (Pillow 11 and later) and WebP


def iso_box(kind: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + kind + payload


def write_video_xmp(path: Path, packet: bytes, muxer: str) -> None:
    """Write `packet` as the video's XMP where Adobe's XMP specification (part 3) puts it: `moov/udta/XMP_`
    for QuickTime, a top-level `uuid` box for MP4. ffmpeg writes `moov` last, so growing it moves no sample;
    a QuickTime file laid out otherwise gets the `uuid` box too, which `marking` also reads."""
    size = path.stat().st_size
    with path.open("r+b") as handle:
        def read(at: int, length: int) -> bytes:
            handle.seek(at)
            return handle.read(length)

        last = None
        for last in iso_boxes(read, 0, size):
            pass
        if muxer == "mov" and last and last[0] == b"moov" and last[2] == size \
                and int.from_bytes(read(last[1] - 8, 4), "big") == size - last[1] + 8 \
                and size - last[1] <= BOX_READ_MAX_BYTES:
            start = last[1]
            moov = read(start, size - start)
            inside = lambda at, length: moov[at:at + length]  # noqa: E731
            udta = next(((s, e) for kind, s, e in iso_boxes(inside, 0, len(moov)) if kind == b"udta"), None)
            item = iso_box(b"XMP_", packet)
            if udta and int.from_bytes(moov[udta[0] - 8:udta[0] - 4], "big") == udta[1] - udta[0] + 8:
                moov = moov[:udta[0] - 8] + iso_box(b"udta", moov[udta[0]:udta[1]] + item) + moov[udta[1]:]
            else:
                moov += iso_box(b"udta", item)
            handle.seek(start - 8)
            handle.write(iso_box(b"moov", moov))
            handle.truncate()
            return
        handle.seek(size)
        handle.write(iso_box(b"uuid", MP4_XMP_UUID + packet))


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # report usage errors as JSON too
        raise LabelToolError("usage", message)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="label_tool", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=JsonArgumentParser)

    score = sub.add_parser("score", help="Judge each corner as a place for the Label.")
    score.add_argument("images", nargs="+", metavar="image",
                       help="an image; or a folder, or several files, to judge as a batch (videos are listed, not judged)")
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

    def label_options(command):  # the same Label settings for video-apply and video-preview
        command.add_argument("video")
        command.add_argument("--variant", required=True, choices=VARIANTS)
        command.add_argument("--corner", default="tr", choices=CORNERS)
        command.add_argument("--colour", default=AUTO, choices=(AUTO, *COLOURS),
                             help="the Icon Colour; the backing plate is the opposite colour (default: the better "
                                  "contrast over sampled frames)")
        command.add_argument("--size", type=int,
                             help="icon height in px (default: 6%% of the shorter side as displayed)")
        command.add_argument("--visibility", default=AUTO, choices=VISIBILITY_MODES,
                             help="when the Label shows: continuous, periodic, or auto: continuous up to "
                                  "--threshold seconds, periodic beyond it (default: auto)")
        command.add_argument("--window", type=float, default=DEFAULT_WINDOW_S,
                             help="periodic: seconds the Label shows each time (default: %(default)g)")
        command.add_argument("--every", type=float, default=DEFAULT_EVERY_S,
                             help="periodic: seconds between the starts of two windows (default: %(default)g)")
        command.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD_S,
                             help="auto: the longest video, in seconds, shown continuously (default: %(default)g)")

    vapply = sub.add_parser("video-apply", help="Write a Labelled Copy of a video.")
    label_options(vapply)
    vapply.set_defaults(handler=cmd_video_apply)

    vpreview = sub.add_parser("video-preview", help="Write source frames and labelled excerpts of a video, to "
                                                    "choose the Label's corner before video-apply.")
    label_options(vpreview)
    vpreview.add_argument("--out", help="the folder for the previews (default: <video>.label-preview next to it)")
    vpreview.add_argument("--frames", type=int, default=PREVIEW_FRAMES,
                          help="source frames to write, spread over the video (default: %(default)s)")
    vpreview.set_defaults(handler=cmd_video_preview)

    marking_help = ("Read and grade the Marking (C2PA, XMP, generator metadata) an image or video carries, "
                    "as evidence for the Icon Variant.")
    mark = sub.add_parser("marking", help=marking_help, description=marking_help)
    mark.add_argument("file", help="an image or a video")
    mark.set_defaults(handler=cmd_marking)

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
