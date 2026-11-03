"""`label_tool score` on a folder or a list of images: one run judges a whole batch.

Each still image gets the same report a single `score` gives, under its path.
Files the tool refuses (animated, SVG, too small, unreadable) are listed with
their error instead of stopping the batch, and existing Labelled Copies are
skipped so they are never labelled twice.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import CORNERS, SVG, animation


def still(path: Path, size=(1000, 800), colour=(200, 220, 240)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)
    return path


def by_name(entries: list[dict]) -> dict[str, dict]:
    return {Path(e["path"]).name: e for e in entries}


def test_score_on_a_folder_judges_every_still_image_in_it(tmp_path, label_tool):
    folder = tmp_path / "shots"
    still(folder / "beach.png")
    still(folder / "portrait.jpg", size=(800, 1200))
    still(folder / "city.webp", size=(1200, 600))
    (folder / "notes.md").write_text("# not an image\n")

    result = label_tool("score", folder, "--variant", "generated")

    assert result.returncode == 0, result.json
    images = by_name(result.json["images"])
    assert sorted(images) == ["beach.png", "city.webp", "portrait.jpg"]
    portrait = images["portrait.jpg"]
    assert (portrait["image"]["width"], portrait["image"]["height"]) == (800, 1200)
    assert portrait["image"]["format"] == "JPEG"
    assert set(portrait["corners"]) == set(CORNERS)
    # A flat image: every corner free, the top-right first, as for one image.
    assert portrait["suggested_corner"] == "tr"
    assert portrait["all_busy"] is False
    assert Path(portrait["path"]).resolve() == (folder / "portrait.jpg").resolve()
    assert result.json["refused"] == []
    assert result.json["skipped"] == []


def test_score_on_a_folder_lists_refused_files_without_stopping_the_batch(tmp_path, label_tool):
    folder = tmp_path / "shots"
    still(folder / "beach.png")
    animation(folder / "loop.gif", "GIF")
    (folder / "logo.svg").write_text(SVG)
    still(folder / "tiny.png", size=(20, 20))
    before = {p.name: p.read_bytes() for p in folder.iterdir()}

    result = label_tool("score", folder, "--variant", "generated")

    assert result.returncode == 0, result.json
    # Scoring writes and changes nothing.
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert sorted(by_name(result.json["images"])) == ["beach.png"]
    refused = {name: e["error"]["code"] for name, e in by_name(result.json["refused"]).items()}
    assert refused == {"loop.gif": "animated_image", "logo.svg": "svg_image", "tiny.png": "image_too_small"}
    for entry in result.json["refused"]:
        assert entry["error"]["message"]


@pytest.mark.parametrize(
    "copy_name, listed",
    [
        ("beach.ai-label.png", False),  # in the folder
        ("D.AI-LABEL.PNG", False),  # whatever the case of its infix
        ("beach.ai-label.png", True),  # named in a list
    ],
    ids=["in a folder", "uppercase infix", "in a list"],
)
def test_score_skips_an_existing_labelled_copy(tmp_path, label_tool, copy_name, listed):
    folder = tmp_path / "shots"
    beach = still(folder / "beach.png")
    copy = still(folder / copy_name)

    result = label_tool("score", *((beach, copy) if listed else (folder,)))

    assert result.returncode == 0, result.json
    assert sorted(by_name(result.json["images"])) == ["beach.png"]
    skipped = by_name(result.json["skipped"])
    assert list(skipped) == [copy_name]
    assert skipped[copy_name]["reason"] == "labelled_copy"


def test_score_on_a_list_of_images_judges_each_one(tmp_path, label_tool):
    first = still(tmp_path / "a" / "one.png")
    second = still(tmp_path / "b" / "two.png", colour=(20, 20, 20))
    still(tmp_path / "a" / "left-out.png")

    result = label_tool("score", first, second, "--variant", "modified")

    assert result.returncode == 0, result.json
    images = by_name(result.json["images"])
    assert sorted(images) == ["one.png", "two.png"]
    # Each image is judged on its own pixels: a dark image gets the white icon.
    assert images["one.png"]["corners"]["tr"]["colour"] == "black"
    assert images["two.png"]["corners"]["tr"]["colour"] == "white"
    assert images["two.png"]["icon"]["variant"] == "modified"


def test_score_on_a_list_reports_a_missing_image_as_refused(tmp_path, label_tool):
    present = still(tmp_path / "one.png")

    result = label_tool("score", present, tmp_path / "gone.png")

    assert result.returncode == 0, result.json
    assert sorted(by_name(result.json["images"])) == ["one.png"]
    assert by_name(result.json["refused"])["gone.png"]["error"]["code"] == "not_found"


def test_score_on_a_folder_without_images_fails_with_json_error(tmp_path, label_tool):
    folder = tmp_path / "empty"
    folder.mkdir()
    (folder / "readme.txt").write_text("nothing to label\n")

    result = label_tool("score", folder)

    assert result.returncode != 0
    assert result.json["error"]["code"] == "no_images"


def test_score_on_a_folder_covers_only_its_own_visible_images(tmp_path, label_tool):
    folder = tmp_path / "shots"
    still(folder / "beach.png")
    still(folder / "IMG.JPG")
    still(folder / ".hidden.png")
    still(folder / "sub" / "inner.png")

    result = label_tool("score", folder, "--variant", "generated")

    assert result.returncode == 0, result.json
    # An uppercase suffix is still an image; dotfiles and subfolders are left out.
    assert sorted(by_name(result.json["images"])) == ["IMG.JPG", "beach.png"]
    listed = {Path(e["path"]).name for key in ("images", "refused", "skipped") for e in result.json[key]}
    assert ".hidden.png" not in listed
    assert "inner.png" not in listed


def test_score_on_a_folder_and_a_file_judges_both_in_one_batch(tmp_path, label_tool):
    folder = tmp_path / "shots"
    still(folder / "beach.png")
    elsewhere = still(tmp_path / "other" / "city.png")

    result = label_tool("score", folder, elsewhere, "--variant", "generated")

    assert result.returncode == 0, result.json
    assert sorted(by_name(result.json["images"])) == ["beach.png", "city.png"]
    assert result.json["refused"] == []
    assert result.json["skipped"] == []


def test_score_reports_an_image_listed_twice_once(tmp_path, label_tool):
    folder = tmp_path / "shots"
    beach = still(folder / "beach.png")

    result = label_tool("score", beach, beach, folder)

    assert result.returncode == 0, result.json
    assert [Path(e["path"]).name for e in result.json["images"]] == ["beach.png"]


def test_score_on_a_folder_refuses_a_dangling_link_as_not_found(tmp_path, label_tool):
    folder = tmp_path / "shots"
    still(folder / "beach.png")
    (folder / "dangling.png").symlink_to(tmp_path / "gone.png")

    result = label_tool("score", folder)

    assert result.returncode == 0, result.json
    assert sorted(by_name(result.json["images"])) == ["beach.png"]
    assert by_name(result.json["refused"])["dangling.png"]["error"]["code"] == "not_found"


def test_score_on_a_list_refuses_an_empty_folder_in_it(tmp_path, label_tool):
    empty = tmp_path / "empty"
    empty.mkdir()
    beach = still(tmp_path / "beach.png")

    result = label_tool("score", empty, beach)

    assert result.returncode == 0, result.json
    assert sorted(by_name(result.json["images"])) == ["beach.png"]
    refused = by_name(result.json["refused"])["empty"]
    assert refused["error"]["code"] == "no_images"
    assert refused["error"]["message"]
