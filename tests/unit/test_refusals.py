"""What `apply` and `score` refuse: the same files, with the same error codes.

Each refusal is a JSON error on stdout and a non-zero exit, never a
traceback, and the file is left as it was with nothing written next to it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import SVG, animation


def missing(path: Path) -> None:
    pass


def float_tiff(path: Path) -> None:
    Image.new("F", (400, 300), 0.5).save(path)


def still(image_format: str):
    def make(path: Path) -> None:
        Image.new("RGB", (400, 300), (90, 160, 210)).save(path, format=image_format)
    return make


def not_an_image(path: Path) -> None:
    path.write_text("# Notes\n\nThis is not a picture.\n")


# The skill relays these refusals as written, so the tool owns the wording.
STILL_ONLY = "aren't supported yet: a still png, jpeg or webp version can be labelled instead."

REFUSED = [
    # name, make, code, words the message must carry
    ("gone.png", missing, "not_found", ()),
    ("loop.gif", lambda p: animation(p, "GIF"), "animated_image", ("animated images " + STILL_ONLY,)),
    ("loop.webp", lambda p: animation(p, "WEBP"), "animated_image", ("animated images " + STILL_ONLY,)),
    ("diagram.svg", lambda p: p.write_text(SVG), "svg_image", ("svg images " + STILL_ONLY,)),
    # Refused by content too, so a mislabelled extension does not slip through.
    ("diagram.png", lambda p: p.write_text(SVG), "svg_image", ("svg images " + STILL_ONLY,)),
    # Formats Pillow reads but the skill doesn't support: refused, not labelled by accident.
    ("depth.tiff", float_tiff, "unsupported_format", ()),
    ("scan.tiff", still("TIFF"), "unsupported_format", ("png, jpeg or webp",)),
    ("scan.bmp", still("BMP"), "unsupported_format", ("png, jpeg or webp",)),
    ("still.gif", still("GIF"), "unsupported_format", ("png, jpeg or webp",)),
    ("notes.png", not_an_image, "unreadable_image", ()),
]


@pytest.mark.parametrize("subcommand", ["apply", "score"])
@pytest.mark.parametrize("name, make, code, words", REFUSED, ids=[r[0] for r in REFUSED])
def test_refuses_with_a_json_error_and_writes_nothing(tmp_path, label_tool, subcommand, name, make, code, words):
    original = tmp_path / name
    make(original)
    before = original.read_bytes() if original.exists() else None
    args = ["--variant", "generated", "--corner", "tr"] if subcommand == "apply" else []

    result = label_tool(subcommand, original, *args)

    assert result.returncode != 0
    error = result.json["error"]
    assert error["code"] == code
    assert error["message"]
    for word in words:
        assert word in error["message"].lower()
    assert "Traceback" not in result.stderr
    if before is not None:
        assert original.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ([name] if before is not None else [])


def test_score_refuses_a_labelled_copy_named_alone(tmp_path, label_tool):
    """A batch skips it; alone, `score` refuses it as `apply` would."""
    copy = tmp_path / "photo.ai-label.png"
    Image.new("RGB", (400, 300), (90, 160, 210)).save(copy)

    result = label_tool("score", copy, "--variant", "generated")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "labelled_copy"


def test_apply_refuses_a_labelled_copy_and_writes_nothing(tmp_path, label_tool):
    """Labelling `photo.ai-label.png` again would write `photo.ai-label.ai-label.png`."""
    copy = tmp_path / "photo.ai-label.png"
    Image.new("RGB", (400, 300), (90, 160, 210)).save(copy)

    result = label_tool("apply", copy, "--variant", "generated", "--corner", "tr")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "labelled_copy"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["photo.ai-label.png"]
