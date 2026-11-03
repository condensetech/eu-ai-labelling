"""A folder of images labelled with the commands the skill tells the agent to run.

The batch `score` command is taken verbatim from `references/batch.md` and the
per-image `apply` command from `references/image.md` (only placeholders filled
in), and both run from the user's project, never from the skill folder. How
the agent asks about the batch and reports it is judged by the headless runs
(tests/evals `mixed-event-folder`, tests/headless).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import PILL_ASPECT, SVG, animation, changed_box, doc_command, run_json, sha256


def noise(size: tuple[int, int]) -> Image.Image:
    return Image.effect_noise(size, 120).convert("RGB")


@pytest.fixture
def project(tmp_path) -> Path:
    """A project with a folder of mixed images, as a creator would have it."""
    project = tmp_path / "project"
    shots = project / "shots"
    shots.mkdir(parents=True)
    Image.new("RGB", (1200, 800), (200, 220, 240)).save(shots / "beach.png")
    Image.new("RGB", (800, 1200), (30, 30, 40)).save(shots / "night.jpg", quality=90)
    busy_top_right = Image.new("RGB", (1000, 800), (235, 235, 235))
    busy_top_right.paste(noise((500, 400)), (500, 0))
    busy_top_right.save(shots / "market.png")
    noise((1000, 800)).save(shots / "crowd.png")
    animation(shots / "loop.gif", "GIF")
    (shots / "logo.svg").write_text(SVG)
    Image.new("RGB", (600, 400), (240, 240, 240)).save(shots / "old.ai-label.png")
    return project


# The batch's files as SKILL.md step 1 lists them, passed by path.
SELECTION = [f"shots/{name}" for name in (
    "beach.png", "night.jpg", "market.png", "crowd.png", "loop.gif", "logo.svg", "old.ai-label.png",
)]


def test_batch_score_command_run_from_the_users_project_judges_each_image(project):
    digests = {p.name: sha256(p) for p in (project / "shots").iterdir()}
    argv = doc_command("batch.md", "score", {"<images>": SELECTION, "<generated|modified>": "generated"})

    code, report = run_json(argv, project)

    assert code == 0, report
    images = {Path(e["path"]).name: e for e in report["images"]}
    assert sorted(images) == ["beach.png", "crowd.png", "market.png", "night.jpg"]
    # Placement is judged per image: each gets its own corners and ranking.
    assert images["beach.png"]["suggested_corner"] == "tr"
    assert images["market.png"]["corners"]["tr"]["busy"] is True
    assert images["market.png"]["suggested_corner"] != "tr"
    assert images["crowd.png"]["all_busy"] is True
    assert images["night.jpg"]["corners"]["tr"]["colour"] == "white"
    refused = {Path(e["path"]).name: e["error"]["code"] for e in report["refused"]}
    assert refused == {"loop.gif": "animated_image", "logo.svg": "svg_image"}
    assert [Path(e["path"]).name for e in report["skipped"]] == ["old.ai-label.png"]
    # Scoring writes nothing.
    assert {p.name: sha256(p) for p in (project / "shots").iterdir()} == digests


def test_batch_path_labels_each_image_in_its_own_corner(project):
    """Score the images as batch.md says, then apply each image whose corner is
    free, as image.md says: every image gets its own Labelled Copy."""
    shots = project / "shots"
    digests = {p.name: sha256(p) for p in shots.iterdir()}
    _, report = run_json(
        doc_command("batch.md", "score", {"<images>": SELECTION, "<generated|modified>": "modified"}), project
    )

    placed = {}
    for entry in report["images"]:
        if entry["all_busy"]:
            continue  # uncertain: gathered into the one question for the user
        name = Path(entry["path"]).name
        corner = entry["suggested_corner"]
        argv = doc_command(
            "image.md", "apply",
            {"<image>": f"shots/{name}", "<generated|modified>": "modified", "<tl|tr|bl|br>": corner},
        )
        code, applied = run_json(argv, project)
        assert code == 0, applied
        placed[name] = (corner, applied)

    assert sorted(placed) == ["beach.png", "market.png", "night.jpg"]
    assert placed["beach.png"][0] == "tr" and placed["market.png"][0] != "tr"
    for name, (corner, applied) in placed.items():
        original = shots / name
        copy = shots / f"{original.stem}.ai-label{original.suffix}"
        assert (project / applied["labelled_copy"]).resolve() == copy.resolve()
        assert applied["corner"] == corner and applied["variant"] == "modified"
        left, top, right, bottom = changed_box(original, copy, threshold=24)
        assert (right - left) / (bottom - top) == pytest.approx(PILL_ASPECT["modified"], rel=0.05), name
        with Image.open(original) as img:
            width = img.width
        if corner in ("tr", "br"):
            assert right > width / 2, f"{name}: icon not on the right"
        else:
            assert left < width / 2, f"{name}: icon not on the left"
    # The originals, the refused files and the old Labelled Copy are untouched,
    # and nothing was written for the uncertain or refused ones.
    assert {n: sha256(shots / n) for n in digests} == digests
    assert sorted(p.name for p in shots.iterdir() if p.name not in digests) == [
        "beach.ai-label.png", "market.ai-label.png", "night.ai-label.jpg",
    ]
