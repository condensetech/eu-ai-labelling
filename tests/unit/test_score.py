"""`label_tool score`: judges each corner of an image as a place for the Label."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import CORNERS, grey_and_white_stripes, noise


def test_score_ranks_a_clean_bottom_left_above_a_busy_top_right(tmp_path, label_tool):
    # 1000x800, flat light grey, with a busy top-right quarter. The other
    # quarters are flat, so the bottom-left is as clean as an image gets.
    image = Image.new("RGB", (1000, 800), (200, 200, 200))
    image.paste(noise((500, 400)), (500, 0))
    path = tmp_path / "photo.png"
    image.save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    corners = result.json["corners"]
    assert set(corners) == set(CORNERS)
    assert corners["tr"]["busyness"] > corners["bl"]["busyness"]
    assert corners["tr"]["busy"] is True
    assert corners["bl"]["busy"] is False
    ranking = result.json["ranking"]
    assert sorted(ranking) == sorted(CORNERS)
    assert ranking[-1] == "tr"
    assert ranking.index("bl") < ranking.index("tr")
    # Only one corner is busy, so the label moves rather than the user being asked.
    assert result.json["all_busy"] is False
    assert result.json["suggested_corner"] == ranking[0]
    assert result.json["suggested_corner"] != "tr"


def flat(tmp_path: Path, colour, size=(1000, 800), name="flat.png") -> Path:
    path = tmp_path / name
    Image.new("RGB", size, colour).save(path)
    return path


def test_score_reports_the_image_dimensions_and_format(tmp_path, label_tool):
    path = flat(tmp_path, (90, 160, 210), size=(1200, 700))

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    assert result.json["image"]["width"] == 1200
    assert result.json["image"]["height"] == 700
    assert result.json["image"]["format"] == "PNG"


@pytest.mark.parametrize(
    "background, colour",
    [
        ((0, 0, 0), "white"),
        ((20, 30, 70), "white"),  # dark navy
        ((255, 255, 255), "black"),
        ((250, 240, 180), "black"),  # pale yellow
    ],
)
def test_score_picks_the_icon_colour_that_contrasts_with_the_background(
    tmp_path, label_tool, background, colour
):
    result = label_tool("score", flat(tmp_path, background))

    assert result.returncode == 0, result.json
    for corner in CORNERS:
        judged = result.json["corners"][corner]
        assert judged["colour"] == colour
        assert judged["contrast"] >= 3.0
        assert judged["meets_threshold"] is True
        assert judged["plate"] is False
        assert judged["transparent"] is False


@pytest.mark.parametrize("background", [(0, 0, 0), (255, 255, 255)])
def test_score_contrast_is_the_wcag_ratio(tmp_path, label_tool, background):
    # Black against white is the largest WCAG contrast ratio there is: 21:1.
    result = label_tool("score", flat(tmp_path, background))

    assert result.json["corners"]["tr"]["contrast"] == pytest.approx(21.0, abs=0.05)


def test_score_reports_a_mid_grey_noisy_region_as_below_the_threshold(tmp_path, label_tool):
    # Mid-grey noise: pixels spread from dark to light grey, so neither a black
    # nor a white icon stands out against all of them.
    image = Image.new("RGB", (1000, 800), (255, 255, 255))
    image.paste(noise((500, 400), low=40, high=215), (500, 0))
    path = tmp_path / "noisy.png"
    image.save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    top_right = result.json["corners"]["tr"]
    assert top_right["contrast"] < 3.0
    assert top_right["meets_threshold"] is False
    assert top_right["plate"] is True
    # The clean white corners are unaffected.
    assert result.json["corners"]["bl"]["meets_threshold"] is True


def test_score_prefers_the_top_right_when_every_corner_is_free(tmp_path, label_tool):
    result = label_tool("score", flat(tmp_path, (90, 160, 210)))

    assert result.returncode == 0, result.json
    assert result.json["ranking"][0] == "tr"
    assert result.json["suggested_corner"] == "tr"
    assert result.json["all_busy"] is False


def test_score_prefers_the_top_right_over_a_slightly_cleaner_free_corner(tmp_path, label_tool):
    # A few scattered dots keep the top-right free but make it marginally busier
    # than the spotless bottom-left: a free top-right still wins.
    image = Image.new("RGB", (1000, 800), (200, 200, 200))
    for x in range(700, 990, 40):
        image.putpixel((x, 30), (0, 0, 0))
    path = tmp_path / "dots.png"
    image.save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    corners = result.json["corners"]
    assert corners["tr"]["busyness"] > corners["bl"]["busyness"]
    assert corners["tr"]["busy"] is False
    assert result.json["suggested_corner"] == "tr"


def test_score_flags_when_every_corner_is_busy(tmp_path, label_tool):
    path = tmp_path / "busy.png"
    noise((600, 400)).save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    assert all(result.json["corners"][c]["busy"] for c in CORNERS)
    assert result.json["all_busy"] is True


def transparent(tmp_path: Path, hidden_rgb, size=(1000, 800), name="clear.png") -> Path:
    """A fully transparent PNG whose invisible pixels hold `hidden_rgb`."""
    path = tmp_path / name
    Image.new("RGBA", size, (*hidden_rgb, 0)).save(path)
    return path


def test_score_judges_a_transparent_image_by_what_shows_not_by_hidden_rgb(tmp_path, label_tool):
    # Both images look the same: fully transparent. Where they are published the
    # page behind them could be light or dark, so neither black nor white can be
    # promised 3:1, whatever RGB values hide under the transparent pixels.
    black_under = label_tool("score", transparent(tmp_path, (0, 0, 0), name="a.png"))
    white_under = label_tool("score", transparent(tmp_path, (255, 255, 255), name="b.png"))

    assert black_under.returncode == 0, black_under.json
    assert white_under.returncode == 0, white_under.json
    for corner in CORNERS:
        a = black_under.json["corners"][corner]
        b = white_under.json["corners"][corner]
        assert (a["colour"], a["contrast"]) == (b["colour"], b["contrast"])
        for judged in (a, b):
            assert judged["transparent"] is True
            assert judged["contrast"] < 3.0
            assert judged["meets_threshold"] is False
            assert judged["plate"] is True


def cutout(tmp_path: Path, hidden: Image.Image, name: str, size=(800, 600)) -> Path:
    """A background-removed cutout: an opaque red square in the centre, every
    other pixel fully transparent with `hidden` RGB left underneath."""
    rgba = hidden.convert("RGB").resize(size).convert("RGBA")
    rgba.putalpha(0)
    rgba.paste((220, 30, 30, 255), (300, 200, 500, 400))
    path = tmp_path / name
    rgba.save(path)
    return path


def test_score_judges_busyness_by_what_shows_not_by_hidden_rgb(tmp_path, label_tool):
    # Both cutouts look the same: a red square on nothing. One left noise under
    # its transparent pixels (as naive background removal does), the other flat
    # black. Every corner is visually empty, so none is busy.
    flat_under = label_tool(
        "score", cutout(tmp_path, Image.new("RGB", (800, 600), (0, 0, 0)), "flat.png"))
    noise_under = label_tool("score", cutout(tmp_path, noise((800, 600)), "noise.png"))

    assert flat_under.returncode == 0, flat_under.json
    assert noise_under.returncode == 0, noise_under.json
    for corner in CORNERS:
        a = flat_under.json["corners"][corner]
        b = noise_under.json["corners"][corner]
        assert (a["busyness"], a["busy"]) == (b["busyness"], b["busy"])
        assert b["busy"] is False
    for result in (flat_under, noise_under):
        assert result.json["all_busy"] is False


def test_score_judges_a_small_image_the_icon_fits_even_when_a_plate_would_not(tmp_path, label_tool):
    # Shorter side 26 px: the 24 px icon fits within the 1 px margin, but a
    # padded backing plate around it does not. The image can still be labelled.
    result = label_tool("score", flat(tmp_path, (255, 255, 255), size=(300, 26)))

    assert result.returncode == 0, result.json
    assert result.json["plate_fits"] is False
    assert result.json["corners"]["tr"]["colour"] == "black"
    assert result.json["corners"]["tr"]["meets_threshold"] is True


def test_score_reports_that_a_plate_fits_on_a_roomy_image(tmp_path, label_tool):
    result = label_tool("score", flat(tmp_path, (255, 255, 255), size=(140, 140)))

    assert result.returncode == 0, result.json
    assert result.json["plate_fits"] is True


def test_score_refuses_an_image_too_small_for_the_icon_itself(tmp_path, label_tool):
    # Shorter side 23 px: shorter than the 24 px minimum icon height.
    result = label_tool("score", flat(tmp_path, (255, 255, 255), size=(300, 23)))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "image_too_small"


@pytest.mark.parametrize(
    "colour", [(255, 255, 255), (200, 200, 200), (90, 160, 210), (0, 0, 0)]
)
@pytest.mark.parametrize("size", [(1000, 800), (300, 26)])
def test_score_finds_no_edges_in_a_flat_image(tmp_path, label_tool, colour, size):
    # A flat image has no detail anywhere, right up to its outermost pixels.
    # Corner regions touch the image border, so the image's own edge must not
    # be mistaken for detail, whatever the colour.
    result = label_tool("score", flat(tmp_path, colour, size=size))

    assert result.returncode == 0, result.json
    for corner in CORNERS:
        assert result.json["corners"][corner]["busyness"] == 0


def test_score_finds_no_edges_in_a_fully_transparent_image(tmp_path, label_tool):
    result = label_tool("score", transparent(tmp_path, (0, 0, 0)))

    assert result.returncode == 0, result.json
    for corner in CORNERS:
        assert result.json["corners"][corner]["busyness"] == 0


def test_score_still_sees_detail_that_reaches_the_image_border(tmp_path, label_tool):
    # Vertical stripes running off the top edge: the outermost row is detail
    # too, so the top corners are as busy at the border as inside.
    image = Image.new("RGB", (1000, 800), (255, 255, 255))
    for x in range(0, 1000, 4):
        image.paste((0, 0, 0), (x, 0, x + 2, 120))
    path = tmp_path / "stripes.png"
    image.save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    corners = result.json["corners"]
    assert corners["tr"]["busy"] is True and corners["tl"]["busy"] is True
    assert corners["br"]["busyness"] == 0 and corners["bl"]["busyness"] == 0


def test_score_refuses_an_icon_size_larger_than_the_image(tmp_path, label_tool):
    result = label_tool("score", flat(tmp_path, (255, 255, 255)), "--size", "99999")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "image_too_small"


# Black icon against grey 85 is about 2.82:1 (WCAG), against grey 95 about 3.29:1.
@pytest.mark.parametrize(
    "grey, contrast, meets",
    [(85, 2.82, False), (95, 3.29, True)],
)
def test_score_judges_contrast_just_either_side_of_the_3_to_1_threshold(
    tmp_path, label_tool, grey, contrast, meets
):
    path = tmp_path / "stripes.png"
    grey_and_white_stripes(grey).save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    for corner in CORNERS:
        judged = result.json["corners"][corner]
        assert judged["colour"] == "black"
        assert judged["contrast"] == pytest.approx(contrast, abs=0.03)
        assert judged["meets_threshold"] is meets
        assert judged["plate"] is (not meets)


def test_score_without_a_preference_prefers_the_top_right(tmp_path, label_tool):
    result = label_tool("score", flat(tmp_path, (90, 160, 210)))

    assert result.json["preferred_corner"] == "tr"
    assert result.json["preferred_from"] == "default"


def test_score_ranks_the_corner_the_user_prefers_first_when_it_is_free(tmp_path, label_tool):
    result = label_tool("score", flat(tmp_path, (90, 160, 210)), "--prefer", "bl")

    assert result.returncode == 0, result.json
    assert result.json["preferred_corner"] == "bl"
    assert result.json["preferred_from"] == "request"
    assert result.json["ranking"][0] == "bl"
    assert result.json["suggested_corner"] == "bl"


def test_score_falls_back_to_the_first_free_corner_when_the_preferred_one_is_busy(tmp_path, label_tool):
    image = Image.new("RGB", (1000, 800), (200, 200, 200))
    image.paste(noise((500, 400)), (0, 400))
    path = tmp_path / "busy-bottom-left.png"
    image.save(path)

    result = label_tool("score", path, "--prefer", "bl")

    assert result.json["corners"]["bl"]["busy"] is True
    assert result.json["ranking"][-1] == "bl"
    # The default order takes over among the free corners: the top-right first.
    assert result.json["suggested_corner"] == "tr"


def test_score_refuses_a_preference_that_is_not_a_corner(tmp_path, label_tool):
    result = label_tool("score", flat(tmp_path, (90, 160, 210)), "--prefer", "middle")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "usage"


def test_score_batch_applies_the_preference_to_every_image(tmp_path, label_tool):
    one = flat(tmp_path, (90, 160, 210), name="one.png")
    two = flat(tmp_path, (90, 160, 210), name="two.png")

    result = label_tool("score", one, two, "--prefer", "tl")

    corners = {Path(e["path"]).name: e["suggested_corner"] for e in result.json["images"]}
    assert corners == {"one.png": "tl", "two.png": "tl"}


def test_score_counts_a_clean_corner_that_needs_a_plate_as_free(tmp_path, label_tool):
    """A see-through top-right needs a plate, which fits: it is free, so the
    default corner still comes first (image.md, step 3)."""
    path = tmp_path / "cutout.png"
    image = Image.new("RGBA", (1000, 800), (240, 240, 240, 255))
    image.paste((0, 0, 0, 0), (500, 0, 1000, 400))
    image.save(path)

    result = label_tool("score", path)

    assert result.returncode == 0, result.json
    top_right = result.json["corners"]["tr"]
    assert result.json["plate_fits"] and top_right["plate"] and not top_right["busy"]
    assert result.json["suggested_corner"] == "tr"
