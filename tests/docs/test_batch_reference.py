"""A folder of images labelled with the commands the skill tells the agent to run.

The batch `score` command is taken verbatim from `references/batch.md` and the
per-image `apply` command from `references/image.md` (only placeholders filled
in), and both run from the user's project, never from the skill folder. So
does the listing command that discovers a batch's images and videos. How the
agent asks about the batch and reports it is judged by the headless runs
(tests/evals `mixed-event-folder`, `mixed-media-folder`, tests/headless); the
wording those runs rely on is checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import (
    PILL_ASPECT, REPO_ROOT, SKILL_DIR, SKILL_MD, SVG, animation, changed_box, doc_command, run_json, section, sha256, step,
)
from videos import flat_mp4, needs_ffmpeg

BATCH_MD = SKILL_DIR / "references" / "batch.md"


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
    argv = doc_command("batch.md", "score", {"<images>": SELECTION, "<generated|modified>": "generated"},
                       with_flag="--variant")

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
        doc_command("batch.md", "score", {"<images>": SELECTION, "<generated|modified>": "modified"},
                    with_flag="--variant"),
        project,
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


@needs_ffmpeg
def test_the_listing_command_discovers_images_and_videos_and_skips_labelled_copies(project):
    shots = project / "shots"
    flat_mp4(shots / "intro.mp4", seconds=1)
    flat_mp4(shots / "archive.mkv", seconds=1)
    flat_mp4(shots / "teaser.ai-label.mp4", seconds=1)
    (shots / "notes.md").write_text("# not media\n")
    before = {p.name: sha256(p) for p in shots.iterdir()}
    argv = doc_command("batch.md", "score", {"<files>": "shots"}, without_flag="--variant")

    code, report = run_json(argv, project)

    assert code == 0, report
    assert sorted(Path(e["path"]).name for e in report["images"]) == ["beach.png", "crowd.png", "market.png", "night.jpg"]
    assert {Path(e["path"]).name: e["media"] for e in report["videos"]} == {"archive.mkv": "video", "intro.mp4": "video"}
    assert {Path(e["path"]).name: e["media"] for e in report["skipped"]} == {
        "old.ai-label.png": "image", "teaser.ai-label.mp4": "video",
    }
    assert {p.name: sha256(p) for p in shots.iterdir()} == before


def test_the_skill_lists_a_batch_with_the_listing_command():
    identify = step(SKILL_MD.read_text(), "Identify the content")
    assert "**Listing a batch**" in identify and "`references/batch.md`" in identify
    listing = section(BATCH_MD.read_text(), "Listing a batch")
    assert "glob" in listing and "directly inside" in listing
    assert "`videos`" in listing and "`skipped`" in listing and "`media`" in listing


def test_a_batchs_questions_cover_visibility_and_placement_in_one_message():
    batch = section(SKILL_MD.read_text(), "A batch of files")
    assert "Icon Variant" in batch and "visibility" in batch and "corner" in batch
    assert "**Shared answers.**" in batch and "**Per-file exceptions.**" in batch
    assert "Never ask again about a file whose answer is settled" in batch
    assert "per video" in batch and "`auto`" in batch


def test_each_video_in_a_batch_follows_its_own_reference_with_independent_outcomes():
    videos = section(BATCH_MD.read_text(), "Videos in a batch")
    assert "`references/video.md`" in videos
    assert "its own `video-preview`" in videos and "its own corner" in videos
    assert "never reuse one video's corner" in videos
    assert "no caption" in videos  # a Creative Work video keeps an incorporated Label
    # Support comes from each file's own inspection, never from a list kept for the batch.
    assert "`video-inspect`" in videos and "never from its extension" in videos
    assert "does not stop the batch" in videos and "never discards" in videos
    assert "`preservation_unsupported`" in videos
    assert "Rerender only the files the user names" in videos
    assert "final" in videos and "step 8 of `references/video.md`" in videos


def test_the_batch_report_lists_each_videos_settings_and_every_failure():
    report = step(BATCH_MD.read_text(), "Report the batch")
    assert "visibility" in report and "corner" in report
    assert "**Failed:**" in report and "**Waiting:**" in report
    assert "**Refused:**" in report and "**Skipped:**" in report
    assert "retry" in report


def test_the_readme_describes_batches_of_videos():
    batches = section((REPO_ROOT / "README.md").read_text(), "Batches")
    assert "video" in batches and "visibility" in batches
    assert "the others" in batches and "retry" in batches


def test_a_batchs_existing_labels_are_asked_about_in_its_one_message():
    """Images are looked at before the one message, so the "label anyway?"
    question joins it; a video's shows only in its preview frames, so it joins
    the later placement question instead. The rule itself is in SKILL.md
    (test_existing_label)."""
    batch = section(SKILL_MD.read_text(), "A batch of files")
    existing = batch.split("**Existing Labels.**", 1)[1].split("\n- ", 1)[0]
    assert "**An Existing Label**" in existing and "step 2 of `references/image.md`" in existing
    assert "before" in existing and "one message" in existing
    assert "group" in existing, "files sharing the question are not grouped by name"
    assert "step 5 of `references/batch.md`" in existing and "`video-preview`" in existing
    assert "Never ask again" in existing
    steps = BATCH_MD.read_text()
    assert "Existing Label" in step(steps, "Look at every image yourself")
    assert "Existing Label" in step(steps, "Ask about every uncertain placement")
    assert "Existing Label" in step(section(steps, "Videos in a batch"), "Preview each video")


def test_a_file_whose_existing_label_is_kept_is_skipped_in_the_report():
    report = step(BATCH_MD.read_text(), "Report the batch")
    skipped = report.split("**Skipped:**", 1)[1].split("\n   - ", 1)[0]
    assert "Existing Label kept, no EU Icon added" in skipped
    assert "Existing Label" in report.split("**Labelled:**", 1)[1].split("\n   - ", 1)[0], (
        "a file labelled anyway never names its Existing Label"
    )
