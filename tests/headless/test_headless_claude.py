"""The installed skill labelling images in headless Claude Code.

Calls the model (`model` marker): set EU_AI_LABELLING_E2E_DIR to a throwaway
directory; each test creates its own project inside it and runs
`claude -p --plugin-dir <repo>` there with a narrow tool allow-list. What
label_tool does with an image (formats, metadata, contrast) is tested without
the model in tests/unit; these tests judge what the agent decides. The reply
checks live in checks.py and are held to canned replies in
test_headless_checks.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from PIL import Image

from checks import (
    assert_asks_which_corner, assert_relays_refusal, check_batch, make_batch_folder, result_text, tool_uses,
)
from helpers import ICON_MATCH, REPO_ROOT, SVG, animation, changed_box, icon_match, sha256

pytestmark = pytest.mark.model


def new_project() -> Path:
    project = Path(os.environ["EU_AI_LABELLING_E2E_DIR"]) / f"e2e-{uuid.uuid4().hex[:8]}"
    project.mkdir(parents=True)
    return project


def run_claude(project: Path, prompt: str, extra_tools: tuple[str, ...] = ()) -> list[dict]:
    """Run headless Claude Code and return its stream-json events.

    The `Skill` tool is denied with --disallowedTools (not merely left off
    --allowedTools, which only pre-approves tools). The model then cannot
    load the skill by its description, so the skill reaches it only if the
    slash command in the prompt resolves and expands.
    """
    proc = subprocess.run(
        [
            "claude", "-p", prompt,
            "--model", "sonnet",
            "--plugin-dir", str(REPO_ROOT),
            "--allowedTools", "Read", "Bash(uv run:*)", *extra_tools,
            "--disallowedTools", "Skill",
            "--output-format", "stream-json", "--verbose",
        ],
        cwd=project, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def new_photo(project: Path) -> Path:
    original = project / "photo.png"
    Image.new("RGB", (1200, 800), (200, 220, 240)).save(original)
    return original


@pytest.mark.parametrize(
    "command, wording, variant",
    [
        ("/eu-ai-labelling", "fully AI-generated", "generated"),
        ("/eu-ai-labelling:eu-ai-labelling", "partially AI-modified", "modified"),
    ],
)
def test_skill_labels_one_image(command, wording, variant):
    project = new_project()
    original = new_photo(project)
    digest = sha256(original)

    events = run_claude(project, f"{command} label photo.png as {wording}")

    # With the Skill tool denied, a Labelled Copy can only come from the
    # slash command resolving and expanding the skill into the prompt.
    assert tool_uses(events, "Skill") == []
    labelled = project / "photo.ai-label.png"
    assert labelled.is_file(), "the skill did not write a Labelled Copy"
    assert sha256(original) == digest
    left, top, right, bottom = changed_box(original, labelled)
    # Default placement, shorter side 800 px: a 48 px icon 16 px from the
    # top and right edges.
    assert bottom - top == pytest.approx(48, abs=1)
    assert top == pytest.approx(16, abs=1)
    assert 1200 - right == pytest.approx(16, abs=1)
    # The wording picked the matching Icon Variant, judged against the
    # official icon rendered independently, not by label_tool's own output.
    assert icon_match(original, labelled, variant) >= ICON_MATCH


def test_unknown_command_does_not_label():
    """Control: the setup above can fail. With the Skill tool denied, a slash
    command that does not resolve leaves the model without the skill, so no
    Labelled Copy is written."""
    project = new_project()
    new_photo(project)

    events = run_claude(project, "/eu-ai-labelling-nope label photo.png as fully AI-generated")

    assert tool_uses(events, "Skill") == []
    assert not (project / "photo.ai-label.png").exists()


UNSUPPORTED = [
    ("loop.gif", lambda p: animation(p, "GIF"), "animated_image", "animated"),
    ("loop.webp", lambda p: animation(p, "WEBP"), "animated_image", "animated"),
    ("diagram.svg", lambda p: p.write_text(SVG), "svg_image", "svg"),
]


@pytest.mark.parametrize("name, make, code, reason", UNSUPPORTED)
def test_skill_relays_the_refusal_of_an_unsupported_image(name, make, code, reason):
    project = new_project()
    original = project / name
    make(original)
    digest = sha256(original)

    events = run_claude(project, f"/eu-ai-labelling label {name} as fully AI-generated")

    assert tool_uses(events, "Skill") == []
    assert sha256(original) == digest
    assert sorted(p.name for p in project.iterdir()) == [name], "nothing may be written"
    assert_relays_refusal(events, name, code, reason)


def test_unknown_command_does_not_relay_a_refusal():
    """Control: without the skill the model may still decline the file in its
    own words, but the refusal assertions above must then fail."""
    name, make, code, reason = UNSUPPORTED[1]
    project = new_project()
    make(project / name)

    events = run_claude(project, f"/eu-ai-labelling-nope label {name} as fully AI-generated")

    with pytest.raises(AssertionError):
        assert_relays_refusal(events, name, code, reason)


def test_skill_moves_the_label_off_a_busy_top_right():
    """A cluttered top-right and clean other corners: the label goes elsewhere."""
    project = new_project()
    original = project / "photo.png"
    photo = Image.new("RGB", (1200, 800), (235, 235, 235))
    photo.paste(Image.effect_noise((600, 400), 120).convert("RGB"), (600, 0))
    photo.save(original)

    events = run_claude(
        project,
        "/eu-ai-labelling label photo.png as fully AI-generated. "
        "I don't need a preview, just write the Labelled Copy.",
    )

    labelled = project / "photo.ai-label.png"
    assert labelled.is_file(), result_text(events)
    left, top, right, bottom = changed_box(original, labelled)
    # The icon sits in one of the clean corners, 16 px (2%) from its two edges,
    # and the busy top-right quarter is untouched.
    assert bottom - top == pytest.approx(48, abs=1)
    assert not (top < 400 and right > 600), "the label was put in the busy top-right"
    assert min(top, 800 - bottom) == pytest.approx(16, abs=1)
    assert min(left, 1200 - right) == pytest.approx(16, abs=1)


def test_skill_asks_before_labelling_when_every_corner_is_busy():
    project = new_project()
    Image.effect_noise((1200, 800), 120).convert("RGB").save(project / "photo.png")

    events = run_claude(project, "/eu-ai-labelling label photo.png as fully AI-generated")

    # With nowhere clearly suitable, the agent asks instead of choosing.
    assert_asks_which_corner(project, result_text(events), bool(tool_uses(events, "AskUserQuestion")))


def make_poster(path: Path) -> None:
    """A plain flat poster, 1200x800. A large face fills the top-right, and
    each other corner holds a line of large text of about the same size.

    `score` sees no busy corner (the face is flat fills with few edges, and
    each text line is under the busy threshold), so `all_busy` is false and
    the top-right ranks first. Only looking at the image shows that the
    top-right covers a face and that no other corner is clearly better."""
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (1200, 800), (225, 232, 240))
    draw = ImageDraw.Draw(img)
    draw.ellipse((780, -120, 1260, 360), fill=(240, 200, 160), outline=(120, 80, 50), width=4)
    draw.ellipse((900, 60, 960, 110), fill=(40, 40, 40))
    draw.ellipse((1080, 60, 1140, 110), fill=(40, 40, 40))
    draw.arc((920, 140, 1120, 280), 20, 160, fill=(150, 40, 40), width=10)
    font = ImageFont.load_default(size=56)
    for xy, words, anchor in [
        ((24, 16), "GRAND OPENING", "la"),
        ((24, 784), "SATURDAY 10AM", "ld"),
        ((1176, 784), "MAIN STREET", "rd"),
    ]:
        draw.text(xy, words, fill=(20, 20, 60), font=font, anchor=anchor)
    img.save(path)


def test_skill_asks_when_the_top_right_covers_a_face_and_no_corner_is_clearly_better():
    """Ticket 15: the top-right is unsuitable and no other corner is clearly
    better, though `score` reports no corner busy. The agent asks."""
    project = new_project()
    original = project / "photo.png"
    make_poster(original)
    digest = sha256(original)

    events = run_claude(project, "/eu-ai-labelling label photo.png as fully AI-generated")

    assert tool_uses(events, "Skill") == []
    assert sha256(original) == digest
    assert sorted(p.name for p in project.iterdir()) == ["photo.png"], "nothing may be written"
    assert_asks_which_corner(project, result_text(events), bool(tool_uses(events, "AskUserQuestion")))


def test_skill_honours_corner_size_and_colour_overrides():
    project = new_project()
    original = new_photo(project)  # 1200x800, light: the automatic colour would be black

    events = run_claude(
        project,
        "/eu-ai-labelling label photo.png as fully AI-generated. Put the icon in the "
        "bottom-left corner, 80 px tall, in white. I don't need a preview.",
    )

    labelled = project / "photo.ai-label.png"
    assert labelled.is_file(), result_text(events)
    left, top, right, bottom = changed_box(original, labelled)
    assert bottom - top == pytest.approx(80, abs=1)
    assert left == pytest.approx(16, abs=1)
    assert 800 - bottom == pytest.approx(16, abs=1)
    with Image.open(labelled) as img:
        histogram = img.convert("L").crop((left, top, right, bottom)).histogram()
    # The White Icon Colour is a white pill: mostly near-white pixels.
    assert sum(histogram[216:]) > sum(histogram) * 0.5


def test_skill_looks_at_the_image_and_previews_the_labelled_copy():
    project = new_project()
    new_photo(project)

    events = run_claude(project, "/eu-ai-labelling label photo.png as fully AI-generated")

    assert (project / "photo.ai-label.png").is_file(), result_text(events)
    read_paths = [Path(call["input"].get("file_path", "")).name for call in tool_uses(events, "Read")]
    assert "photo.png" in read_paths, "the agent never looked at the original"
    assert "photo.ai-label.png" in read_paths, "the agent never looked at the Labelled Copy"
    assert "photo.ai-label.png" in result_text(events), "the preview did not name the Labelled Copy"


def test_skill_labels_a_folder_asking_once_for_uncertain_placements():
    project = new_project()
    shots = project / "shots"
    digests = make_batch_folder(shots)

    events = run_claude(
        project,
        "/eu-ai-labelling label every image in shots/ as fully AI-generated. "
        "I don't need a preview, just write the Labelled Copies.",
        extra_tools=("Glob", "Bash(ls:*)"),
    )

    assert tool_uses(events, "Skill") == []
    check_batch(shots, digests, result_text(events))
