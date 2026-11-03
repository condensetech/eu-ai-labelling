"""`label_tool apply`: burns an EU Icon into a Labelled Copy of an image.

Formats, colour spaces and metadata are in test_formats.py; refused inputs,
for `apply` and `score` alike, in test_refusals.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageOps

from helpers import (
    BACKGROUND, CORNERS, DARK, ICON_MATCH, PILL_ASPECT, changed_box, grey_and_white_stripes, icon_match, noise,
)

ORIENTATION_TAG = 0x0112


def make_image(path: Path, size: tuple[int, int], colour=BACKGROUND) -> Path:
    Image.new("RGB", size, colour).save(path)
    return path


def make_noisy(path: Path, size=(1000, 800), low=40, high=215) -> Path:
    """Mid-grey noise: no black or white icon reaches 3:1 against every pixel."""
    noise(size, low, high, seed=7).save(path)
    return path


def apply_and_measure(label_tool, original: Path, *args: str):
    result = label_tool("apply", original, *args)
    assert result.returncode == 0, result.json
    left, top, right, bottom = changed_box(original, Path(result.json["labelled_copy"]))
    return result, left, top, right, bottom


def test_apply_leaves_original_bytes_unchanged(tmp_path, label_tool):
    original = make_image(tmp_path / "photo.png", (1000, 800))
    before = original.read_bytes()

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert original.read_bytes() == before


@pytest.mark.parametrize("link", [os.symlink, os.link], ids=["symlink", "hard link"])
def test_apply_never_writes_through_a_labelled_copy_linked_to_the_original(tmp_path, label_tool, link):
    original = make_image(tmp_path / "photo.png", (1000, 800))
    before = original.read_bytes()
    copy = tmp_path / "photo.ai-label.png"
    link(original, copy)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert original.read_bytes() == before
    assert not copy.is_symlink() and copy.read_bytes() != before


@pytest.mark.parametrize("variant", ["generated", "modified"])
def test_apply_burns_the_variants_icon_top_right_at_default_size_and_margin(tmp_path, label_tool, variant):
    # Shorter side 800 px: icon height 6% = 48 px, margin 2% = 16 px.
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", variant, "--corner", "tr"
    )

    assert result.json["variant"] == variant
    assert result.json["corner"] == "tr"
    assert top == pytest.approx(16, abs=1)
    assert 1000 - right == pytest.approx(16, abs=1)
    assert bottom - top == pytest.approx(48, abs=1)
    # The footprint's shape is that variant's official icon. The two pills
    # differ by about 12%, so a 3% tolerance cannot confuse them.
    assert (right - left) / (bottom - top) == pytest.approx(PILL_ASPECT[variant], rel=0.03)
    # And its pixels are that icon, rendered independently with resvg.
    assert icon_match(original, Path(result.json["labelled_copy"]), variant) >= ICON_MATCH


def test_apply_icon_size_follows_the_shorter_side(tmp_path, label_tool):
    # Portrait image: the shorter side is the width (500 px) -> 30 px icon, 10 px margin.
    original = make_image(tmp_path / "portrait.png", (500, 1500))

    _, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "tr"
    )

    assert bottom - top == pytest.approx(30, abs=1)
    assert top == pytest.approx(10, abs=1)
    assert 500 - right == pytest.approx(10, abs=1)


def test_apply_enforces_minimum_icon_height_on_small_images(tmp_path, label_tool):
    # Shorter side 150 px: 6% would be 9 px, so the 24 px minimum applies; margin 3 px.
    original = make_image(tmp_path / "small.png", (200, 150))

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "tr"
    )

    assert bottom - top == pytest.approx(24, abs=1)
    assert top == pytest.approx(3, abs=1)
    assert 200 - right == pytest.approx(3, abs=1)


def test_apply_picks_the_black_icon_on_a_mid_tone_background(tmp_path, label_tool):
    # Black Icon Colour: a black pill with white lettering. On this mid-tone blue
    # black reaches about 7:1 contrast and white under 3:1.
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "tr"
    )

    assert result.json["colour"] == "black"
    assert result.json["plate"] is False
    assert result.json["meets_threshold"] is True
    with Image.open(result.json["labelled_copy"]) as img:
        histogram = img.convert("L").crop((left, top, right, bottom)).histogram()
    dark, light, total = sum(histogram[:40]), sum(histogram[216:]), sum(histogram)
    assert dark > total * 0.5
    assert light > 0


def test_apply_reports_where_the_icon_was_placed(tmp_path, label_tool):
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "tr"
    )

    icon = result.json["icon"]
    assert icon["x"] == pytest.approx(left, abs=1)
    assert icon["y"] == pytest.approx(top, abs=1)
    assert icon["width"] == pytest.approx(right - left, abs=1)
    assert icon["height"] == pytest.approx(bottom - top, abs=1)
    assert result.json["margin"] == 16


@pytest.mark.parametrize("corner", ["tl", "bl", "br"])  # tr: the default-placement test
def test_apply_places_icon_in_the_requested_corner(tmp_path, label_tool, corner):
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", corner
    )

    assert result.json["corner"] == corner
    vertical_gap = top if corner[0] == "t" else 800 - bottom
    horizontal_gap = left if corner[1] == "l" else 1000 - right
    assert vertical_gap == pytest.approx(16, abs=1)
    assert horizontal_gap == pytest.approx(16, abs=1)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_apply_unwritable_destination_fails_with_json_error(tmp_path, label_tool):
    folder = tmp_path / "read-only"
    folder.mkdir()
    original = make_image(folder / "photo.png", (1000, 800))
    folder.chmod(0o555)
    try:
        result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")
    finally:
        folder.chmod(0o755)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "write_failed"
    assert result.json["error"]["message"]
    assert "Traceback" not in result.stderr
    assert not (folder / "photo.ai-label.png").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--variant", "basic"],  # the image path can't burn in the Basic icon
        [],  # no variant at all
        ["--variant", "generated", "--corner", "middle"],
        ["--variant", "generated", "--plate", "--no-plate"],
        ["--variant", "generated", "--size", "big"],
    ],
    ids=["basic variant", "no variant", "unknown corner", "plate and no-plate", "size not a number"],
)
def test_apply_reports_a_usage_error_as_json(tmp_path, label_tool, args):
    original = make_image(tmp_path / "photo.png", (300, 200))

    result = label_tool("apply", original, *args)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "usage"
    assert result.json["error"]["message"]
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "photo.ai-label.png").exists()


def make_rotated_jpeg(path: Path, stored_size: tuple[int, int], orientation: int) -> Path:
    exif = Image.Exif()
    exif[ORIENTATION_TAG] = orientation
    Image.new("RGB", stored_size, BACKGROUND).save(path, format="JPEG", quality=95, exif=exif)
    return path


def displayed(path: Path) -> Image.Image:
    """The image as a viewer shows it, after applying any EXIF Orientation."""
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img).convert("RGB")


@pytest.mark.parametrize("corner", CORNERS)
def test_apply_places_icon_in_the_displayed_corner_of_an_oriented_jpeg(tmp_path, label_tool, corner):
    # Stored 600x400 with Orientation 6 (rotate 90 CW): viewers show it as 400x600 portrait.
    original = make_rotated_jpeg(tmp_path / "phone.jpg", (600, 400), orientation=6)

    result = label_tool("apply", original, "--variant", "generated", "--corner", corner)

    assert result.returncode == 0, result.json
    before, after = displayed(original), displayed(Path(result.json["labelled_copy"]))
    assert before.size == (400, 600)
    assert after.size == before.size
    # Shorter side 400 px: icon 24 px tall, margin 8 px, in the corner as displayed.
    diff = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v > 40 else 0)
    left, top, right, bottom = diff.getbbox()
    assert right - left > bottom - top, "icon is lying sideways"
    assert bottom - top == pytest.approx(24, abs=2)
    vertical_gap = top if corner[0] == "t" else 600 - bottom
    horizontal_gap = left if corner[1] == "l" else 400 - right
    assert vertical_gap == pytest.approx(8, abs=2)
    assert horizontal_gap == pytest.approx(8, abs=2)


def test_apply_keeps_the_picture_of_a_16_bit_greyscale_png(tmp_path, label_tool):
    # 16-bit grey 20000 of 65535 is about 30% grey: 78 on an 8-bit scale.
    original = tmp_path / "scan.png"
    Image.new("I;16", (400, 300), 20000).save(original)

    result = label_tool("apply", original, "--variant", "modified", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as img:
        labelled = img.convert("RGB")
    # Shorter side 300 px: icon 24 px tall at an 8 px margin, so the bottom half is untouched.
    untouched = labelled.crop((0, 150, 400, 300)).getextrema()
    for low, high in untouched:
        assert low == pytest.approx(78, abs=1)
        assert high == pytest.approx(78, abs=1)
    top_right = labelled.crop((300, 0, 400, 50))
    assert len(top_right.getcolors(1 << 16)) > 1, "the icon was not burned in"


def tone_shares(path, box) -> tuple[float, float]:
    """Shares of near-black and near-white pixels inside `box` of the image at `path`."""
    with Image.open(path) as img:
        histogram = img.convert("L").crop(box).histogram()
    total = sum(histogram)
    return sum(histogram[:40]) / total, sum(histogram[216:]) / total


def test_apply_picks_the_white_icon_on_a_dark_background(tmp_path, label_tool):
    # White Icon Colour: a white pill with dark lettering.
    original = make_image(tmp_path / "night.png", (1000, 800), DARK)

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "tr"
    )

    assert result.json["colour"] == "white"
    assert result.json["plate"] is False
    dark, light = tone_shares(result.json["labelled_copy"], (left, top, right, bottom))
    assert light > 0.5
    assert dark > 0


def test_apply_honours_an_explicit_colour_over_the_automatic_choice(tmp_path, label_tool):
    # On a dark background the automatic choice would be white.
    original = make_image(tmp_path / "night.png", (1000, 800), DARK)

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "tr", "--colour", "black"
    )

    assert result.json["colour"] == "black"
    dark, light = tone_shares(result.json["labelled_copy"], (left, top, right, bottom))
    assert dark > 0.5


@pytest.mark.parametrize("colour", ["black-50", "white-50"])
def test_apply_refuses_the_50_percent_icon_colours(tmp_path, label_tool, colour):
    """They blend into the picture, so their contrast can't be judged (ticket 57)."""
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result = label_tool("apply", original, "--variant", "generated", "--colour", colour)

    assert result.returncode != 0 and result.json["error"]["code"] == "usage"
    assert not (tmp_path / "photo.ai-label.png").exists()


def test_apply_honours_an_explicit_icon_size(tmp_path, label_tool):
    # Default would be 48 px on this 800 px shorter side; the margin stays 2% (16 px).
    original = make_image(tmp_path / "photo.png", (1000, 800))

    _, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", "bl", "--size", "80"
    )

    assert bottom - top == pytest.approx(80, abs=1)
    assert 800 - bottom == pytest.approx(16, abs=1)
    assert left == pytest.approx(16, abs=1)
    assert (right - left) / (bottom - top) == pytest.approx(PILL_ASPECT["generated"], rel=0.03)


def test_apply_refuses_an_icon_size_below_the_minimum(tmp_path, label_tool):
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result = label_tool("apply", original, "--variant", "generated", "--size", "12")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "size_too_small"
    assert not (tmp_path / "photo.ai-label.png").exists()


@pytest.mark.parametrize("size", ["1000", "5000", "99999"])
def test_apply_refuses_an_icon_size_larger_than_the_image(tmp_path, label_tool, size):
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result = label_tool("apply", original, "--variant", "modified", "--size", size)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "image_too_small"
    assert not (tmp_path / "photo.ai-label.png").exists()


def plate_strip(path: Path, image_width: int, margin: int) -> set:
    """Colours along the two rows just inside the label's top edge, away from its rounded ends."""
    with Image.open(path) as img:
        strip = img.convert("RGB").crop((image_width - margin - 200, margin, image_width - margin - 40, margin + 2))
    return {colour for _, colour in strip.getcolors(1 << 16)}


@pytest.mark.parametrize(
    "low, high, icon, plate_rgb",
    [
        # Noise from mid-dark to white: black is the better icon but stays
        # under 3:1 against the darkest pixels, so it goes on a white plate.
        (60, 255, "black", (255, 255, 255)),
        # Noise from black to light grey: white is the better icon but stays
        # under 3:1 against the lightest pixels, so it goes on a black plate.
        (0, 180, "white", (0, 0, 0)),
    ],
)
def test_apply_falls_back_to_an_opaque_backing_plate_in_the_contrasting_colour(
    tmp_path, label_tool, low, high, icon, plate_rgb
):
    original = make_noisy(tmp_path / "noisy.png", low=low, high=high)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is True
    assert result.json["colour"] == icon
    assert result.json["meets_threshold"] is True
    labelled = Path(result.json["labelled_copy"])
    left, top, right, bottom = changed_box(original, labelled)
    # The plate sits at the usual 16 px margin and is taller than the 48 px icon on it.
    assert top == pytest.approx(16, abs=1)
    assert 1000 - right == pytest.approx(16, abs=1)
    assert bottom - top > 48
    # Its edge is one flat, opaque colour where the noise used to be...
    assert plate_strip(labelled, 1000, 16) == {plate_rgb}
    # ...and the icon's pill on it is the opposite colour, so it stands out.
    icon_box = result.json["icon"]
    pill_row = icon_box["y"] + icon_box["height"] // 2
    with Image.open(labelled) as img:
        pill_edge = img.convert("RGB").crop(
            (icon_box["x"] + 2, pill_row - 1, icon_box["x"] + 6, pill_row + 1)
        )
    opposite = (0, 0, 0) if plate_rgb == (255, 255, 255) else (255, 255, 255)
    for colour in {c for _, c in pill_edge.getcolors(1 << 16)}:
        assert all(abs(a - b) <= 40 for a, b in zip(colour, opposite)), colour


def make_split(path: Path, size=(1000, 800)) -> Path:
    """A light image whose bottom-left quarter is near-black."""
    img = Image.new("RGB", size, (235, 235, 235))
    img.paste(DARK, (0, size[1] // 2, size[0] // 2, size[1]))
    img.save(path)
    return path


@pytest.mark.parametrize("corner, icon", [("bl", "white"), ("tr", "black")])
def test_apply_picks_the_icon_colour_for_the_corner_it_labels(tmp_path, label_tool, corner, icon):
    original = make_split(tmp_path / "split.png")

    result, left, top, right, bottom = apply_and_measure(
        label_tool, original, "--variant", "generated", "--corner", corner
    )

    assert result.json["corner"] == corner
    assert result.json["colour"] == icon
    assert result.json["plate"] is False
    dark, light = tone_shares(result.json["labelled_copy"], (left, top, right, bottom))
    assert (light if icon == "white" else dark) > 0.5


@pytest.mark.parametrize("hidden_rgb", [(0, 0, 0), (255, 255, 255)])
def test_apply_backs_the_icon_with_a_plate_on_a_transparent_image(tmp_path, label_tool, hidden_rgb):
    # Fully transparent: the page behind it may be light or dark, so only an
    # opaque plate guarantees contrast, whatever RGB hides under the pixels.
    original = tmp_path / "clear.png"
    Image.new("RGBA", (1000, 800), (*hidden_rgb, 0)).save(original)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is True
    assert result.json["colour"] == "black"
    with Image.open(result.json["labelled_copy"]) as img:
        strip = img.convert("RGBA").crop((1000 - 16 - 200, 16, 1000 - 16 - 40, 18))
    assert {c for _, c in strip.getcolors(1 << 16)} == {(255, 255, 255, 255)}


def test_apply_fits_the_plate_on_a_small_busy_image(tmp_path, label_tool):
    # 140x140: 24 px icon, 3 px margin. The full plate padding would not fit,
    # so the plate is drawn with less padding instead of the image being refused.
    original = make_noisy(tmp_path / "noisy.png", size=(140, 140))

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is True
    assert result.json["meets_threshold"] is True
    box = result.json["plate_box"]
    assert box["x"] >= 3 and box["y"] >= 3
    assert box["x"] + box["width"] <= 140 - 3
    assert box["y"] + box["height"] <= 140 - 3
    icon = result.json["icon"]
    assert box["x"] < icon["x"] and box["y"] < icon["y"]
    assert icon["x"] + icon["width"] < box["x"] + box["width"]
    assert icon["y"] + icon["height"] < box["y"] + box["height"]


def test_apply_labels_without_a_plate_when_none_fits_and_says_contrast_is_short(tmp_path, label_tool):
    # Shorter side 26 px: the 24 px icon fits within its 1 px margin, a plate does not.
    original = make_noisy(tmp_path / "noisy.png", size=(300, 26))

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is False
    assert result.json["meets_threshold"] is False
    assert "plate_box" not in result.json
    assert Path(result.json["labelled_copy"]).is_file()


def test_apply_refuses_a_requested_plate_the_image_has_no_room_for(tmp_path, label_tool):
    # The same 26 px tall image: the automatic plate quietly falls back to
    # none, but a plate the user asked for is refused rather than dropped.
    original = make_noisy(tmp_path / "noisy.png", size=(300, 26))

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr", "--plate")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "image_too_small"
    assert "plate" in result.json["error"]["message"]
    assert not (tmp_path / "noisy.ai-label.png").exists()


def test_apply_without_plate_when_the_user_turns_it_off(tmp_path, label_tool):
    original = make_noisy(tmp_path / "noisy.png")

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr", "--no-plate")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is False
    labelled = Path(result.json["labelled_copy"])
    left, top, right, bottom = changed_box(original, labelled)
    assert bottom - top == pytest.approx(48, abs=1)
    assert len(plate_strip(labelled, 1000, 16)) > 1, "a plate was drawn anyway"


def test_apply_draws_a_plate_when_the_user_asks_for_one(tmp_path, label_tool):
    # A clean background would not need a plate.
    original = make_image(tmp_path / "photo.png", (1000, 800))

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr", "--plate")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is True
    labelled = Path(result.json["labelled_copy"])
    left, top, right, bottom = changed_box(original, labelled)
    assert bottom - top > 48
    assert plate_strip(labelled, 1000, 16) == {(255, 255, 255)}  # black icon, white plate
    # The icon on the plate keeps its 48 px size: its black pill spans 48 rows.
    with Image.open(labelled) as img:
        pill = img.convert("L").crop((left, top, right, bottom)).point(lambda v: 255 if v < 40 else 0)
    pill_box = pill.getbbox()
    assert pill_box[3] - pill_box[1] == pytest.approx(48, abs=1)


@pytest.mark.parametrize("colour", ["black", "white"])
def test_apply_gives_an_explicit_colour_no_automatic_plate(tmp_path, label_tool, colour):
    # Busy mid-grey noise would get an automatic plate, but an explicit colour does not.
    original = make_noisy(tmp_path / "noisy.png")

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr", "--colour", colour)

    assert result.returncode == 0, result.json
    assert result.json["colour"] == colour
    assert result.json["plate"] is False
    assert "plate_box" not in result.json
    assert len(plate_strip(Path(result.json["labelled_copy"]), 1000, 16)) > 1, "a plate was drawn anyway"


# Black icon against grey 85 is about 2.82:1 (WCAG): short of 3:1, so a plate.
# Against grey 95 it is about 3.29:1: enough, so no plate.
@pytest.mark.parametrize("grey, plate", [(85, True), (95, False)])
def test_apply_backs_the_icon_with_a_plate_only_below_the_3_to_1_threshold(
    tmp_path, label_tool, grey, plate
):
    original = tmp_path / "stripes.png"
    grey_and_white_stripes(grey).save(original)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["colour"] == "black"
    assert result.json["plate"] is plate
    assert result.json["meets_threshold"] is True
    labelled = Path(result.json["labelled_copy"])
    if plate:
        assert "plate_box" in result.json
        assert plate_strip(labelled, 1000, 16) == {(255, 255, 255)}
    else:
        assert "plate_box" not in result.json
        assert len(plate_strip(labelled, 1000, 16)) > 1, "a plate was drawn anyway"
