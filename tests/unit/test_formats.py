"""`label_tool apply` across image formats and colour spaces: what it keeps.

Refused formats (animated, SVG, floating point) are in test_refusals.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, JpegImagePlugin
from PIL.ExifTags import IFD

from helpers import BACKGROUND, QUALITY_95_LUMINANCE_SUM, changed_box, noise


@pytest.mark.parametrize(
    "name, pillow_format",
    [("photo.png", "PNG"), ("photo.jpg", "JPEG"), ("photo.jpeg", "JPEG"), ("photo.webp", "WEBP")],
)
def test_apply_writes_the_labelled_copy_next_to_the_original_in_its_format(tmp_path, label_tool, name, pillow_format):
    original = tmp_path / name
    Image.new("RGB", (1000, 800), BACKGROUND).save(original, format=pillow_format)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    stem, ext = name.split(".")
    labelled = tmp_path / f"{stem}.ai-label.{ext}"
    assert Path(result.json["labelled_copy"]) == labelled
    assert result.json["original"] == str(original)
    with Image.open(labelled) as img:
        assert img.format == pillow_format
        assert img.size == (1000, 800)


FORMATS = [("photo.png", "PNG"), ("photo.jpg", "JPEG"), ("photo.webp", "WEBP")]

# EXIF tags (base IFD) a photographer cares about, with known-good values.
MAKE, MODEL, ARTIST, DATETIME, ORIENTATION = 0x010F, 0x0110, 0x013B, 0x0132, 0x0112
PROVENANCE = {MAKE: "Fujifilm", MODEL: "X-T5", ARTIST: "Ada Lovelace", DATETIME: "2026:05:17 09:30:00"}
# Capture time (Exif sub-IFD) and location (GPS sub-IFD).
DATETIME_ORIGINAL = 0x9003
GPS_LATITUDE_REF, GPS_LATITUDE = 0x0001, 0x0002
CAPTURED_AT = "2026:05:17 09:30:00"
LATITUDE = (45.0, 30.0, 0.0)


def colour_profile() -> bytes:
    from PIL import ImageCms

    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def provenance_exif(orientation: int | None = None) -> Image.Exif:
    exif = Image.Exif()
    for tag, value in PROVENANCE.items():
        exif[tag] = value
    if orientation is not None:
        exif[ORIENTATION] = orientation
    exif.get_ifd(IFD.Exif)[DATETIME_ORIGINAL] = CAPTURED_AT
    gps = exif.get_ifd(IFD.GPSInfo)
    gps[GPS_LATITUDE_REF] = "N"
    gps[GPS_LATITUDE] = LATITUDE
    return exif


def assert_provenance_kept(exif: Image.Exif) -> None:
    for tag, value in PROVENANCE.items():
        assert exif.get(tag) == value
    assert exif.get_ifd(IFD.Exif).get(DATETIME_ORIGINAL) == CAPTURED_AT
    gps = exif.get_ifd(IFD.GPSInfo)
    assert gps.get(GPS_LATITUDE_REF) == "N"
    assert tuple(gps.get(GPS_LATITUDE, ())) == LATITUDE


@pytest.mark.parametrize("name, pillow_format", FORMATS)
def test_apply_keeps_the_originals_colour_profile(tmp_path, label_tool, name, pillow_format):
    profile = colour_profile()
    original = tmp_path / name
    Image.new("RGB", (1000, 800), BACKGROUND).save(original, format=pillow_format, icc_profile=profile)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as img:
        assert img.info.get("icc_profile") == profile


@pytest.mark.parametrize("name, pillow_format", FORMATS)
def test_apply_keeps_the_originals_exif(tmp_path, label_tool, name, pillow_format):
    original = tmp_path / name
    Image.new("RGB", (1000, 800), BACKGROUND).save(original, format=pillow_format, exif=provenance_exif())

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as img:
        exif = img.getexif()
    assert_provenance_kept(exif)


def test_apply_keeps_exif_but_not_a_stale_orientation_on_a_rotated_jpeg(tmp_path, label_tool):
    # The copy's pixels are already upright, so a kept Orientation 6 would rotate it twice.
    original = tmp_path / "phone.jpg"
    Image.new("RGB", (600, 400), BACKGROUND).save(original, format="JPEG", exif=provenance_exif(orientation=6))

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as img:
        exif = img.getexif()
        assert img.size == (400, 600)
    assert exif.get(ORIENTATION, 1) == 1
    assert_provenance_kept(exif)


def test_apply_reencodes_a_jpeg_at_quality_95_without_chroma_subsampling(tmp_path, label_tool):
    # A low-quality, subsampled original must not drag the Labelled Copy down with it.
    original = tmp_path / "photo.jpg"
    Image.new("RGB", (1000, 800), BACKGROUND).save(original, format="JPEG", quality=60, subsampling=2)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as img:
        # Finer quantisation (smaller steps) means higher quality.
        assert sum(img.quantization[0]) <= QUALITY_95_LUMINANCE_SUM
        assert JpegImagePlugin.get_sampling(img) == 0, "chroma is subsampled (not 4:4:4)"


def webp_bitstream(path: Path) -> str:
    data = path.read_bytes()
    return "lossless" if b"VP8L" in data else "lossy" if b"VP8 " in data else "unknown"


@pytest.mark.parametrize("lossless", [True, False], ids=["lossless", "lossy"])
def test_apply_keeps_a_webp_lossless_or_lossy_as_it_was(tmp_path, label_tool, lossless):
    # A detailed picture, so re-encoding would visibly shift pixel values.
    original = tmp_path / "render.webp"
    picture = Image.effect_mandelbrot((1000, 800), (-2.0, -1.2, 1.0, 1.2), 100).convert("RGB")
    picture.save(original, format="WEBP", **({"lossless": True} if lossless else {"quality": 95}))

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    assert webp_bitstream(copy) == webp_bitstream(original)
    with Image.open(original) as before, Image.open(copy) as after:
        # Shorter side 800 px: the icon sits in the top 16 + 48 px, so the bottom half is untouched.
        untouched = (0, 400, 1000, 800)
        a = before.convert("RGB").crop(untouched).tobytes()
        b = after.convert("RGB").crop(untouched).tobytes()
    if lossless:
        assert a == b
    else:
        # Re-encoded at quality 95: close to the original, not degraded.
        assert sum(abs(x - y) for x, y in zip(a, b)) / len(a) < 2.0


def test_apply_labels_a_camera_jpeg_with_an_embedded_preview_as_a_still_jpeg(tmp_path, label_tool):
    # Phones and cameras append a second image (gain map or large preview) to
    # an ordinary .jpg via MPF. That is one photo, not an animation.
    original = tmp_path / "camera.jpg"
    primary = Image.new("RGB", (800, 600), BACKGROUND)
    preview = Image.new("RGB", (200, 150), (200, 30, 30))
    primary.save(original, format="MPO", save_all=True, append_images=[preview], quality=60)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["image"]["format"] == "JPEG"
    with Image.open(result.json["labelled_copy"]) as img:
        # An ordinary single-image JPEG: the preview is not carried over.
        assert img.format == "JPEG"
        assert getattr(img, "n_frames", 1) == 1
        assert img.size == (800, 600)
        assert sum(img.quantization[0]) <= QUALITY_95_LUMINANCE_SUM
        # The primary image, not the red preview, is what got labelled.
        assert img.convert("RGB").getpixel((10, 590)) == pytest.approx(BACKGROUND, abs=4)


# ICC header bytes 16:20 name the colour space of the data the profile describes.
# A profile only applies to pixel data in that same colour space.
PROFILE_SPACE_FOR_MODE = {"RGB": b"RGB ", "RGBA": b"RGB ", "L": b"GRAY", "LA": b"GRAY", "CMYK": b"CMYK"}


def colour_profile_for(space: bytes) -> bytes:
    """An ICC profile whose header declares `space` (GRAY, CMYK, ...)."""
    profile = bytearray(colour_profile())
    profile[16:20] = space
    return bytes(profile)


@pytest.mark.parametrize("name, pillow_format", [("scan.png", "PNG"), ("scan.jpg", "JPEG")])
def test_apply_keeps_a_greyscale_profile_valid_for_the_labelled_copy(tmp_path, label_tool, name, pillow_format):
    profile = colour_profile_for(b"GRAY")
    original = tmp_path / name
    Image.new("L", (1000, 800), 140).save(original, format=pillow_format, icc_profile=profile)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as img:
        assert img.info.get("icc_profile") == profile
        assert PROFILE_SPACE_FOR_MODE[img.mode] == b"GRAY", f"GRAY profile embedded in {img.mode} data"


def test_apply_keeps_a_cmyk_jpeg_in_cmyk_with_its_profile_and_inks(tmp_path, label_tool):
    profile = colour_profile_for(b"CMYK")
    inks = (20, 60, 0, 30)
    original = tmp_path / "print.jpg"
    Image.new("CMYK", (1000, 800), inks).save(original, format="JPEG", quality=95, icc_profile=profile)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(original) as before, Image.open(result.json["labelled_copy"]) as img:
        assert img.info.get("icc_profile") == profile
        assert PROFILE_SPACE_FOR_MODE[img.mode] == b"CMYK", f"CMYK profile embedded in {img.mode} data"
        # Away from the icon (top right), the ink values are the original's.
        assert img.getpixel((100, 700)) == pytest.approx(before.getpixel((100, 700)), abs=3)


def test_apply_draws_a_plate_on_a_greyscale_image_and_keeps_it_greyscale(tmp_path, label_tool):
    profile = colour_profile_for(b"GRAY")
    original = tmp_path / "scan.png"
    noise((1000, 800), 40, 215).convert("L").save(original, icc_profile=profile)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is True
    box = result.json["plate_box"]
    with Image.open(result.json["labelled_copy"]) as img:
        assert img.mode == "L"
        assert img.info.get("icc_profile") == profile
        # The plate's own pixels, just inside its padded edge, are one flat level.
        plate_edge = img.crop((box["x"] + 3, box["y"] + box["height"] // 2,
                               box["x"] + 5, box["y"] + box["height"] // 2 + 2))
        assert len(set(plate_edge.tobytes())) == 1


def test_apply_draws_a_plate_on_a_cmyk_jpeg_and_keeps_it_cmyk(tmp_path, label_tool):
    profile = colour_profile_for(b"CMYK")
    original = tmp_path / "print.jpg"
    noise((1000, 800), 40, 215).convert("CMYK").save(original, format="JPEG", quality=95, icc_profile=profile)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is True
    with Image.open(original) as before, Image.open(result.json["labelled_copy"]) as img:
        assert img.mode == "CMYK"
        assert img.info.get("icc_profile") == profile
        # Away from the label (top right), the ink values are the original's.
        assert img.getpixel((100, 700)) == pytest.approx(before.getpixel((100, 700)), abs=3)


# --- Palette and greyscale-with-alpha PNGs --------------------------------------


def palette_png(path: Path, transparent_bottom: bool) -> Path:
    """A palette PNG: mid-tone blue on top, a second colour on the bottom half,
    which is the transparent index (tRNS) when `transparent_bottom`."""
    img = Image.new("RGB", (1000, 800), BACKGROUND)
    img.paste((240, 240, 240), (0, 400, 1000, 800))
    palette = img.quantize(colors=2)
    bottom = palette.getpixel((0, 799))
    palette.save(path, **({"transparency": bottom} if transparent_bottom else {}))
    return path


def test_apply_labels_a_palette_png(tmp_path, label_tool):
    original = palette_png(tmp_path / "flat.png", transparent_bottom=False)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    copy = Path(result.json["labelled_copy"])
    left, top, right, bottom = changed_box(original, copy)
    assert top == pytest.approx(16, abs=1) and 1000 - right == pytest.approx(16, abs=1)
    with Image.open(original) as before, Image.open(copy) as after:
        assert after.convert("RGB").getpixel((100, 700)) == before.convert("RGB").getpixel((100, 700))


def test_apply_keeps_the_transparent_index_of_a_palette_png_transparent(tmp_path, label_tool):
    # tRNS transparency, with no alpha channel: the copy must not turn it opaque.
    original = palette_png(tmp_path / "cutout.png", transparent_bottom=True)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    assert result.json["plate"] is False  # the top-right is opaque blue
    with Image.open(result.json["labelled_copy"]) as img:
        rgba = img.convert("RGBA")
    assert rgba.getpixel((100, 700))[3] == 0, "the transparent area became opaque"
    assert rgba.getpixel((100, 100))[3] == 255


def test_score_sees_the_transparent_index_of_a_palette_png(tmp_path, label_tool):
    original = palette_png(tmp_path / "cutout.png", transparent_bottom=True)

    result = label_tool("score", original)

    assert result.returncode == 0, result.json
    corners = result.json["corners"]
    assert corners["tr"]["transparent"] is False and corners["tl"]["transparent"] is False
    assert corners["br"]["transparent"] is True and corners["bl"]["transparent"] is True
    assert corners["br"]["plate"] is True


def test_apply_keeps_greyscale_with_alpha_as_greyscale_with_alpha(tmp_path, label_tool):
    original = tmp_path / "mask.png"
    img = Image.new("LA", (1000, 800), (140, 255))
    img.paste((140, 0), (0, 400, 1000, 800))  # transparent bottom half
    img.save(original)

    result = label_tool("apply", original, "--variant", "generated", "--corner", "tr")

    assert result.returncode == 0, result.json
    with Image.open(result.json["labelled_copy"]) as copy:
        assert copy.mode == "LA"
        assert copy.getpixel((100, 700)) == (140, 0)
        assert copy.getpixel((100, 100)) == (140, 255)
        assert len(copy.crop((800, 0, 1000, 80)).getcolors(1 << 16)) > 1, "the icon was not burned in"
