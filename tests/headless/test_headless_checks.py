"""The headless reply checks themselves, on canned replies (no model call).

Each check in checks.py must accept a compliant reply and reject weakened
ones, so a check too loose to catch a non-compliant reply fails here rather
than passing a broken skill.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from checks import assert_asks_which_corner, assert_relays_refusal, check_batch, make_batch_folder

# --- No clear corner ----------------------------------------------------------------

ASKS = "Every corner is busy. Top-left: a face. Bottom-right: the caption. Which corner should I use?"


def test_asks_which_corner_accepts_a_reply_weighing_the_corners(tmp_path):
    assert_asks_which_corner(tmp_path, ASKS)


def test_asks_which_corner_accepts_a_question_asked_with_a_tool(tmp_path):
    assert_asks_which_corner(tmp_path, "Every corner is busy: top-left has a face, bottom-right a sign.", True)


@pytest.mark.parametrize("labelled, reply", [
    (False, "Every corner is busy. Should I use the top-left?"),
    (True, ASKS),
    (False, "Top-left and bottom-right are busy. I cannot continue."),
], ids=["names one corner", "labelled before the answer", "gives up without asking"])
def test_asks_which_corner_rejects(tmp_path, labelled, reply):
    if labelled:
        (tmp_path / "photo.ai-label.png").write_bytes(b"x")

    with pytest.raises(AssertionError):
        assert_asks_which_corner(tmp_path, reply)


# --- An unsupported image -------------------------------------------------------------

REFUSAL = "Animated images aren't supported yet. Export a still PNG or JPEG frame and I can label that."


def session(reply: str, error: dict | None = {"code": "animated_image", "message": "loop.webp is animated"}) -> list[dict]:
    """A session that ran `score` on loop.webp, got `error` back, and replied `reply`."""
    command = "uv run /skill/scripts/label_tool.py score loop.webp --variant generated"
    output = json.dumps({"error": error} if error else {"corners": {}})
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": command}},
        ]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": output}]}},
        {"type": "result", "result": reply},
    ]


def test_relays_refusal_accepts_the_reason_and_a_still_format():
    assert_relays_refusal(session(REFUSAL), "loop.webp", "animated_image", "animated")


@pytest.mark.parametrize("events", [
    session("Animated images aren't supported yet."),
    session("loop.webp can't be labelled. Try a PNG."),
    session(REFUSAL, error=None),
], ids=["no still format", "reason only in the file name", "label_tool never refused"])
def test_relays_refusal_rejects(events):
    with pytest.raises(AssertionError):
        assert_relays_refusal(events, "loop.webp", "animated_image", "animated")


# --- A batch ----------------------------------------------------------------------------

BATCH_REPLY = """\
Labelled (Fully AI-Generated):
- shots/beach.ai-label.png: top-right
- shots/market.ai-label.png: bottom-left

crowd.png and rain.png have no free corner: every corner is busy.
Which corner should I use for crowd.png and rain.png?

Refused: loop.gif (animated images aren't supported), logo.svg (SVG images aren't supported).
Skipped: old.ai-label.png (already a Labelled Copy).
"""

WEAKENED_BATCH_REPLIES = {
    "a corner missing from its line": ("- shots/market.ai-label.png: bottom-left", "- shots/market.ai-label.png"),
    # The check judges the paragraph that holds the question, so the other
    # image must be named only outside it.
    "the question covers one image": (
        "crowd.png and rain.png have no free corner: every corner is busy.\n"
        "Which corner should I use for crowd.png and rain.png?",
        "rain.png has no free corner and was left unlabelled.\n\n"
        "Which corner should I use for crowd.png?",
    ),
    "a refused file listed as labelled": (
        "- shots/market.ai-label.png: bottom-left",
        "- shots/market.ai-label.png: bottom-left\n- logo.svg: Fully AI-Generated, top-right",
    ),
    "the skipped file left out": ("Skipped: old.ai-label.png (already a Labelled Copy).\n", ""),
    "no variant on the lines or heading": ("Labelled (Fully AI-Generated):", "Done:"),
}


@pytest.fixture
def batch(tmp_path, label_tool) -> tuple[Path, dict[str, str]]:
    """The batch folder, with beach.png labelled top-right and market.png bottom-left."""
    shots = tmp_path / "shots"
    digests = make_batch_folder(shots)
    for name, corner in (("beach.png", "tr"), ("market.png", "bl")):
        assert label_tool("apply", shots / name, "--variant", "generated", "--corner", corner).returncode == 0
    return shots, digests


def test_check_batch_accepts_a_compliant_reply(batch):
    check_batch(*batch, BATCH_REPLY)


def test_check_batch_accepts_the_images_listed_under_a_bold_heading_before_the_question(batch):
    reply = BATCH_REPLY.replace(
        "crowd.png and rain.png have no free corner: every corner is busy.\n"
        "Which corner should I use for crowd.png and rain.png?",
        "**Waiting on your answer**\n"
        "- `crowd.png`: every corner is equally busy.\n"
        "- `rain.png`: every corner is equally busy.\n\n"
        "Which corner for each?",
    )

    check_batch(*batch, reply)


@pytest.mark.parametrize("weakened", sorted(WEAKENED_BATCH_REPLIES))
def test_check_batch_rejects_a_weakened_reply(batch, weakened):
    old, new = WEAKENED_BATCH_REPLIES[weakened]
    assert old in BATCH_REPLY

    with pytest.raises(AssertionError):
        check_batch(*batch, BATCH_REPLY.replace(old, new))


def test_check_batch_rejects_labelling_an_uncertain_image_before_the_answer(batch, label_tool):
    shots, digests = batch
    assert label_tool("apply", shots / "crowd.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check_batch(shots, digests, BATCH_REPLY)
