"""The image procedure's commands, run as `references/image.md` writes them.

Each test takes the command verbatim from the skill folder's
`references/image.md` (only its placeholders filled in) and runs it from the
user's project directory, never from the skill folder, so a broken script
path, program or flag in the skill text fails here. What label_tool does with
each option is tested in tests/unit; the headless runs in tests/headless.
"""

from __future__ import annotations

import re
import subprocess

import pytest
from PIL import Image

from helpers import BACKGROUND, LABEL_TOOL, PILL_ASPECT, SKILL_DIR, changed_box, doc_command, run_json, section, sha256, step


def apply_command(image: str, variant: str = "generated", corner: str = "tr") -> list[str]:
    return doc_command("image.md", "apply", {"<image>": image, "<generated|modified>": variant, "<tl|tr|bl|br>": corner})


@pytest.mark.parametrize("image_arg", ["photo.png", "absolute"])
def test_the_apply_command_run_from_the_users_project_labels_the_image(tmp_path, image_arg):
    project = tmp_path / "project"
    project.mkdir()
    original = project / "photo.png"
    Image.new("RGB", (1000, 800), BACKGROUND).save(original)
    digest = sha256(original)

    code, report = run_json(apply_command(str(original) if image_arg == "absolute" else "photo.png"), project)

    assert code == 0, report
    labelled = project / "photo.ai-label.png"
    assert (project / report["labelled_copy"]).resolve() == labelled.resolve()
    assert sha256(original) == digest, "the original was modified"
    left, top, right, bottom = changed_box(original, labelled)
    # Default placement: 48 px (6% of 800) tall, 16 px (2%) from the top and right.
    assert bottom - top == pytest.approx(48, abs=1)
    assert top == pytest.approx(16, abs=1) and 1000 - right == pytest.approx(16, abs=1)
    assert (right - left) / (bottom - top) == pytest.approx(PILL_ASPECT["generated"], rel=0.03)


def test_the_score_command_run_from_the_users_project_judges_each_corner(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    photo = Image.new("RGB", (1000, 800), (235, 235, 235))
    photo.paste(Image.effect_noise((500, 400), 120).convert("RGB"), (500, 0))
    photo.save(project / "photo.png")
    argv = doc_command("image.md", "score", {"<image>": "photo.png", "<generated|modified>": "generated"})

    code, report = run_json(argv, project)

    assert code == 0, report
    assert report["corners"]["tr"]["busy"] is True
    assert report["suggested_corner"] != "tr"


def test_every_override_the_procedure_documents_is_one_apply_accepts():
    """Each flag under `## Overrides`, with each value it lists, is an
    option (and a choice) of `label_tool apply`."""
    overrides = section((SKILL_DIR / "references" / "image.md").read_text(), "Overrides")
    documented = {
        # `--corner tl|tr|bl|br` lists choices; `--size <px>` a placeholder.
        flag: values.split("|") if "|" in values and "<" not in values else []
        for flag, values in re.findall(r"`(--[a-z-]+)(?: ([^`]+))?`", overrides)
    }
    assert {"--corner", "--size", "--colour", "--plate", "--no-plate"} <= set(documented)
    help_text = subprocess.run(
        ["uv", "run", "--quiet", str(LABEL_TOOL), "apply", "--help"],
        capture_output=True, text=True, timeout=300, check=True,
    ).stdout
    for flag, values in documented.items():
        assert re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", help_text), f"apply has no {flag}"
        if values:
            choices = re.search(rf"{re.escape(flag)} \{{([^}}]*)\}}", help_text)
            assert choices, f"{flag} takes no fixed choices in apply"
            missing = set(values) - set(choices.group(1).split(","))
            assert not missing, f"{flag}: documented values {missing} are not accepted"


def test_every_score_field_the_procedure_names_is_one_score_prints(tmp_path):
    """Step 1 lists the fields the next steps use; each is in the report, so
    the agent never looks for a field the tool doesn't print."""
    listed = step((SKILL_DIR / "references" / "image.md").read_text(), "Score the corners")
    fields = set(re.findall(r"^\s+- `([a-z_]+)`", listed, re.M))
    assert {"corners", "plate_fits", "preferred_corner", "ranking", "all_busy"} <= fields
    Image.new("RGB", (1000, 800), (235, 235, 235)).save(tmp_path / "photo.png")
    argv = doc_command("image.md", "score", {"<image>": "photo.png", "<generated|modified>": "generated"})

    code, report = run_json(argv, tmp_path)

    assert code == 0, report
    assert fields <= set(report), fields - set(report)


def test_choosing_a_corner_starts_from_the_tools_suggestion_not_a_hand_swap():
    """The preferred corner is applied by `score --prefer`; step 3 must not
    ask the agent to swap it in by hand."""
    choose = step((SKILL_DIR / "references" / "image.md").read_text(), "Choose a corner")
    assert "`suggested_corner`" in choose


def test_the_image_is_checked_for_an_existing_label_before_a_labelled_copy_is_written():
    """The rule itself lives in SKILL.md (test_existing_label); image.md says where
    the check happens and what an Existing Label looks like for an image."""
    image_md = (SKILL_DIR / "references" / "image.md").read_text()
    look = step(image_md, "Look at the image yourself")
    check = look.split("**An Existing Label:**", 1)[1]
    for sign in ('"AI generated" text', "AI icon", "caption"):
        assert sign in check, f"the check never names {sign}"
    assert "document or page" in check, "no word on a caption near an image shown in a page"
    # Alt text alone is no Existing Label: it keeps its own handling.
    assert re.search(r"[Aa]lt text that mentions AI is not one", check)
    assert "`references/update-references.md`" in check
    assert "**An Existing Label** in SKILL.md" in check
    assert "no Labelled Copy until the user answers" in check
    # Before step 4 writes the Labelled Copy.
    assert image_md.index("**An Existing Label:**") < image_md.index("4. **Apply the label.**")
