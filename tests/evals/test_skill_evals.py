"""Skill evals: scenario prompts run against the installed skill in headless Claude Code.

Each scenario in `scenarios/*.json` names the files to put in a throwaway
project, the prompt to send and the behaviour expected back:

    {
      "description": "...",
      "files": {"speech.png": {"image": [w, h]}, "post.md": {"text": "..."},
                "lamp.png": {"image": [w, h], "pixel_text": "AI generated"},   # text drawn black, bottom-left
                "clip.mp4": {"video": {"seconds": s, "size": "WxH",    # encoded by the local ffmpeg
                                       "notice": "..."}}},   # optional: text on screen throughout
      "prompt": "/eu-ai-labelling ...",
      "expect": {
        "variant": "Fully AI-Generated" | "Partially AI-Modified" | "Basic",
                                          # what the prompt says or names
        "labelled": true | false,
        "asks_origin": true,              # optional: asks how AI was involved
        "asks_placement": true,           # optional: asks caption or burn-in
        "asks_if_required": true,         # optional: points to the official sources
        "reply_matches": ["regex", ...]
      }
    }

An image or a video may carry a Marking, embedded offline when the project is
written (tests/markings.py builds it; nothing is fetched):

        "photo.png": {"image": [w, h],
                      "marking": {"xmp": "trainedAlgorithmicMedia",    # IPTC DigitalSourceType in XMP
                                  "c2pa": "trainedAlgorithmicMedia",   # a C2PA manifest, signed (PNG only)
                                  "png_text": {"parameters": "..."}}}  # generator PNG text chunks
        "clip.mp4": {"video": {...}, "marking": {"xmp": "..."}}         # XMP in the MP4 `uuid` box

The C2PA manifest is signed by a throwaway certificate chain: its signature
validates, though no trust list knows the signer. A scenario without
`marking` carries none, so the `unknown-origin` scenarios ask from no evidence.

A scenario may also expect a document to be labelled in place:

        "text_label": {
          "file": "articolo.md",
          "wording": "generated" | "modified",  # the marker's word
          "label": "regex",                    # the text label, document's language
          "section": "## Outlook",             # optional: only this part is AI-made
          "below": "![...](satire.png)",       # optional: a caption below this line
          "icon_name": "IA"                    # optional: the icon's aria-label / alt text
        }

The document must then carry exactly one marker comment, below its headline
(or below `section`'s heading) and before the body that follows; between the
two, the Basic EU Icon (for HTML an inline SVG with role="img", an
aria-label and the official paths, painted as the Black or White Icon
Colour; for Markdown an image reference to a byte-for-byte copy of an
official Basic SVG inside the project) and the text label. Every line of the original document must still be there.
With `icon_name`, the icon's aria-label (HTML) or alt text (Markdown) is
exactly that name, the icon name in the document's language.
With `below`, the Label is a caption for a Creative Work and sits right below
that line (the image reference) instead.

A scenario may instead expect a label component added to a web project:

        "site_component": {
          "extensions": [".jsx", ".tsx"],      # the component's file type
          "used_in": "src/App.jsx",            # the page the user asked it on
          "label": "regex",                    # the text label passed in there
          "details": true                      # optional: a second layer passed in
        }

The project must then hold exactly one new component file of that type
showing the Basic icon, and byte-for-byte copies of the official Black and
White Basic SVGs, which the component offers by background and loads from
the project, never from the plugin. The component carries an alt attribute on the
icon, the text label as its `label` input, and a second layer opened from a
<button> with aria-expanded and aria-controls and closed by Escape. The
page keeps every original line and uses the component with the text label
(and, with `details`, a second layer).

A scenario may also expect the project's references to an image to follow
its Labelled Copy:

        "references": {
          "image": "static/images/hero.png",          # the labelled original
          "updated": {"content/post.md": "regex"},    # page -> alt text mention
          "not_updated": ["layouts/og.html"]          # left alone, named in the reply
        }

Each updated page must then show the Labelled Copy instead of the original,
through one Markdown image whose path resolves to the copy and whose alt
text keeps its description and gains the mention (the regex, in the page's
language); every other line stays as it was. Each `not_updated` file keeps
its bytes and the reply names it.

`asks_placement: true` means the image is a creative work whose placement the
user hasn't settled: the reply asks whether to add a caption or burn the icon
in, whether or not the prompt names the variant, and labels nothing yet.
`asks_origin: true` means nobody said how AI was involved: the reply asks
whether AI created the content from scratch or edited something real.
`asks_if_required: true` means the user asked whether a Label is required: the
reply points to the Guidelines, the Code of Practice and the AI Act Service
Desk and offers to label.

A file name may hold a folder (`"event/crowd.png"`), so a scenario can label
a batch: a folder of images in one request. `batch_questions` then says which
files the questions may name and which they must not:

        "batch_questions": {
          "about": ["crowd.png", "stage.png"],   # each named in some question
          "not_about": ["team-1.png"]            # named in no question
        }

Questions are asked once for the batch: shared answers are not asked again,
and per-file questions name only the files that differ.

`labelled` says whether a Labelled Copy (`<name>.ai-label.<ext>`) of each
image and each video (other than an existing Labelled Copy) must exist afterwards; when it must, it has to carry the `variant`
icon, judged from its pixels. The files the scenario provides must keep
their bytes either way. No reply may say whether the law requires a Label.

A video's Labelled Copy is judged from frames ffmpeg decodes from it and
from the original at the same times: it keeps the container and the video
codec, and carries the `variant` icon. With `"visibility": "continuous"` the
icon shows at the start, middle and end; with `"periodic"` (the default 5 s
every 60 s, on a video over 61 s) at 1 s and 61 s, and at 30 s the frame is
the original's. No video is written besides the expected Labelled Copies
(and the previews in a `.label-preview` folder): nothing is converted.
`asks_visibility: true` means the user didn't say when the Label shows: the
reply asks continuous or periodic and says what the 60-second default does.
`offers_caption: false` means a Creative Work video: no sentence of the reply
asks about or offers a caption. `asks_how_to_proceed: true` means the video
can't be labelled as it is: the reply asks the user how to go on.

A scenario whose content already has an Existing Label expects

        "existing_label": {
          "says": "regex",    # what it says, quoted in the reply
          "where": "regex",   # where the reply says it is
          "asks": true        # stops and asks whether to add the EU Icon anyway
        }

The reply must then match `says` and `where`, and call no Existing Label
sufficient, adequate or compliant (or the opposite) outside a "whether". With `asks: true` it asks whether
to add the EU Icon anyway or leave the content, and `labelled: false` with no
`text_label` keeps every file's bytes; with `asks: false` the request already
settled it, so the content is labelled and the Existing Label kept (for a
document, `text_label` keeps every original line).

Running the scenarios is opt-in, because it calls the model: set
EU_AI_LABELLING_E2E_DIR to a throwaway directory. The checks on canned
replies at the end of this file always run. Run with
`uv run pytest tests/evals`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from helpers import ICON_MATCH, ICONS_DIR, REPO_ROOT, SKILL_DIR, icon_match, sha256
from label_checks import label_problems
from videos import ffmpeg, needs_ffmpeg

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm"}
TEXT_SUFFIXES = {".md", ".markdown", ".html", ".htm", ".txt"}

# Only the tests that run a scenario call the model; the checks on canned
# replies at the bottom of this file always run.
needs_model = pytest.mark.model


def load_scenarios() -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text())) for p in sorted(SCENARIOS_DIR.glob("*.json"))]


# --- Running a scenario -----------------------------------------------------


def write_file(path: Path, spec: dict) -> None:
    """One scenario file, as its spec says. An image's `pixel_text` is drawn in
    black in its bottom-left corner, 6% of the shorter side tall. A `marking`
    is embedded afterwards (see `embed_marking`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if "image" in spec:
        image = Image.new("RGB", tuple(spec["image"]), (200, 220, 240))
        if "pixel_text" in spec:
            size = round(min(image.size) * 0.06)
            draw = ImageDraw.Draw(image)
            draw.text((size, image.height - size), spec["pixel_text"], fill=(0, 0, 0),
                      font=ImageFont.load_default(size=size), anchor="ls")
        image.save(path, **png_metadata(spec.get("marking", {})))
    elif "video" in spec:
        from videos import flat_mp4

        flat_mp4(path, **spec["video"])
    else:
        path.write_text(spec["text"])
    embed_marking(path, spec.get("marking", {}))


def png_metadata(marking: dict) -> dict:
    """Pillow save options writing a PNG's XMP and generator text chunks."""
    if not ("xmp" in marking or "png_text" in marking):
        return {}
    from PIL.PngImagePlugin import PngInfo

    import markings

    info = PngInfo()
    if "xmp" in marking:
        info.add_itxt("XML:com.adobe.xmp", markings.xmp_packet(marking["xmp"]).decode())
    for key, value in marking.get("png_text", {}).items():
        info.add_text(key, value)
    return {"pnginfo": info}


def embed_marking(path: Path, marking: dict) -> None:
    """A video's XMP box, and a C2PA manifest signed in place, offline, by
    tests/markings.py's throwaway certificate chain."""
    import markings

    if "xmp" in marking and path.suffix.lower() in VIDEO_SUFFIXES:
        markings.with_mp4_xmp(path, markings.xmp_packet(marking["xmp"]))
    if "c2pa" in marking:
        unsigned = path.with_name(f".{path.name}.unsigned")
        path.rename(unsigned)
        try:
            markings.signed(unsigned, path, markings.manifest(marking["c2pa"]))
        finally:
            unsigned.unlink()


def make_project(files: dict[str, dict]) -> Path:
    project = Path(os.environ["EU_AI_LABELLING_E2E_DIR"]) / f"eval-{uuid.uuid4().hex[:8]}"
    project.mkdir(parents=True)
    for name, spec in files.items():
        write_file(project / name, spec)
    return project


def run_claude(project: Path, prompt: str, with_plugin: bool = True) -> list[dict]:
    """Run headless Claude Code on the prompt and return its stream-json events.

    The `Skill` tool is denied, so the skill reaches the model only through
    the slash command in the prompt. With `with_plugin=False` the plugin is
    not loaded and the skill folder is not added, so the model can't find the
    skill and read it by hand either.
    """
    plugin = [
        "--plugin-dir", str(REPO_ROOT),
        # The model reads the skill's references from the plugin folder.
        "--add-dir", str(SKILL_DIR),
    ] if with_plugin else []
    proc = subprocess.run(
        [
            "claude", "-p", prompt,
            "--model", "sonnet",
            *plugin,
            "--allowedTools", "Read", "Glob", "Edit", "Write", "Bash(uv run:*)",
            "--disallowedTools", "Skill",
            "--permission-mode", "acceptEdits",
            "--output-format", "stream-json", "--verbose",
        ],
        cwd=project, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def reply_text(events: list[dict]) -> str:
    """The model's final reply to the user."""
    results = [e for e in events if e.get("type") == "result"]
    assert results, "headless run produced no result event"
    return results[-1].get("result", "")


# --- Reading the reply ------------------------------------------------------


def normalise(text: str) -> str:
    """Lower-case, typographic quotes and dashes made plain, markdown emphasis dropped."""
    text = text.replace("’", "'").replace("‑", "-").replace("‐", "-")
    return re.sub(r"[*_`]", "", text).lower()


# A verdict on whether the law requires a Label, which the skill never gives:
# the old outcome block, or a sentence saying a Label is (not) required. Saying
# that it can't tell "whether a label is required" is no verdict.
VERDICT_RE = re.compile(
    r"disclosure outcome"
    r"|\b(?:(?:a|an|the|no|any)\s+(?:ai\s+)?(?:label|disclosure)|labelling)\s+"
    r"(?:is|isn't|is not|would be|wouldn't be|would not be|seems|looks)\s+"
    r"(?:\w+\s+)?(?:required|mandatory|necessary|obligatory|needed)\b"
    r"|\b(?:you|it)\s+(?:are|is|aren't|isn't|are not|is not)\s+(?:legally\s+)?(?:required|obliged)\s+to\s+(?:label|disclose)\b"
)


def verdicts(text: str) -> list[str]:
    found = []
    for match in VERDICT_RE.finditer(text):
        before = text[max(0, match.start() - 20):match.start()]
        if not re.search(r"\b(?:whether|if)\b", before):
            found.append(match.group(0))
    return found


# The official sources the skill points to when asked whether a Label is required.
GUIDANCE = re.compile(r"guidelines|digital-strategy\.ec\.europa\.eu")
SERVICE_DESK = re.compile(r"service desk|ai-act-service-desk")
OFFER = r"\bcan (?:apply|add)|\bwant me to|would you like|shall i|should i|\boffer|\bi(?:'ll|'d)(?: then)? (?:add|apply)"
# The question about how AI was involved: from scratch, or an edit of something real.
FROM_SCRATCH = r"scratch|fully (?:ai[- ])?generated|generated (?:entirely|completely)|created by ai|made by ai"
AN_EDIT = r"edit|modif|real photo|existing|altered|changed"
# The placement question for a creative work: a caption, or the icon burned in.
CAPTION_OPTION = r"\bcaption\b"
BURN_IN_OPTION = r"\bburn(?:ed|t|ing)?[- ]?in(?:to)?\b|\binto the (?:image|picture|pixels)\b"
# The visibility question for a video: the whole way through, or now and then.
CONTINUOUS_OPTION = r"continuous|the whole (?:video|way)|all the way through|throughout"
PERIODIC_OPTION = r"periodic|at (?:regular )?intervals|every \d+ ?s"
CAPTION_OFFER = OFFER + r"|\b(?:can|could) (?:also )?(?:apply|add|put|write)|\bi'll also add|\bhappy to add"
DEFAULT_LENGTH = r"\b60\s*-?\s*(?:s\b|sec)|\b(?:one|1|a) minute"
# The question about an Existing Label: add the EU Icon anyway, or leave the content.
LABEL_ANYWAY = r"\banyway\b|\bstill\b|\bleave\b|\bas it is\b|\bkeep\b"
# A verdict on an Existing Label's adequacy, which the skill never gives.
ADEQUACY = r"\b(?:in)?sufficient\b|\b(?:in)?adequate\b|\b(?:non-?)?compliant\b|\bsatisf(?:y|ies|actory)\b"

# The wording each image Icon Variant takes, by the name a scenario gives it.
VARIANT_WORDING = {"fully ai-generated": "generated", "partially ai-modified": "modified"}


def check(scenario: dict, project: Path, digests: dict[str, str], reply: str) -> None:
    expect = scenario["expect"]
    files = scenario["files"]
    text = normalise(reply)

    text_label = expect.get("text_label")
    site = expect.get("site_component")
    refs = expect.get("references")
    for name, digest in digests.items():
        if text_label and name == text_label["file"]:
            continue  # labelled in place: judged by check_text_label below
        if site and name == site["used_in"]:
            continue  # the component is used there: judged by check_site_component below
        if refs and name in refs["updated"]:
            continue  # points to the Labelled Copy now: judged by check_references below
        assert sha256(project / name) == digest, f"{name} was changed"
    if text_label:
        check_text_label(project, files[text_label["file"]]["text"], text_label, reply)
    if site:
        check_site_component(project, files, site, reply)
    if refs:
        check_references(project, files, refs, reply)

    check_no_converted_video(project, files, expect, reply)
    for name in files:
        path = Path(name)
        if path.suffix.lower() in VIDEO_SUFFIXES and not path.stem.lower().endswith(".ai-label"):
            # A video's Labelled Copy must exist exactly when the scenario labels.
            copy = (project / path).with_name(f"{path.stem}.ai-label{path.suffix}")
            assert copy.exists() == expect["labelled"], (
                f"Labelled Copy of {name} {'missing' if expect['labelled'] else 'written'}:\n{reply}"
            )
            if expect["labelled"] and expect.get("variant"):
                check_video_copy(project / path, copy, files[name]["video"], expect, reply)
        if path.suffix.lower() in IMAGE_SUFFIXES:
            copy = (project / path).with_name(f"{path.stem}.ai-label{path.suffix}")
            assert copy.exists() == expect["labelled"], (
                f"Labelled Copy of {name} {'missing' if expect['labelled'] else 'written'}:\n{reply}"
            )
            if expect["labelled"] and expect.get("variant"):
                # The expected Icon Variant was burned in, judged against the
                # official icon rendered independently, not by the reply.
                match = icon_match(project / name, copy, VARIANT_WORDING[expect["variant"].lower()])
                assert match >= ICON_MATCH, (
                    f"{copy.name} does not carry the {expect['variant']} icon (match {match:.2f}):\n{reply}"
                )

    # Never a verdict on the law, whatever the scenario.
    assert not verdicts(text), f"the reply says whether a Label is required: {verdicts(text)}\n{reply}"

    if expect.get("asks_if_required"):
        assert GUIDANCE.search(text), f"no pointer to the official Guidelines:\n{reply}"
        assert "code of practice" in text, f"no pointer to the Code of Practice:\n{reply}"
        assert SERVICE_DESK.search(text), f"no pointer to the AI Act Service Desk:\n{reply}"
        assert re.search(OFFER, text), f"no offer to apply a Label:\n{reply}"

    if expect.get("asks_origin"):
        # One question, one per option, or a question over a list of the options.
        asked = " ".join(questions(text) + (list_items(text) if questions(text) else []))
        assert re.search(FROM_SCRATCH, asked) and re.search(AN_EDIT, asked), (
            f"no question whether AI created it from scratch or edited something real:\n{reply}"
        )

    if expect.get("asks_placement"):
        assert questions(text), f"no question asked:\n{reply}"
        assert re.search(CAPTION_OPTION, text), f"no caption offered:\n{reply}"
        assert re.search(BURN_IN_OPTION, text), f"no burn-in offered:\n{reply}"

    if expect.get("asks_visibility"):
        # The options may be listed under the question, as for asks_placement.
        assert questions(text), f"no question asked:\n{reply}"
        assert re.search(CONTINUOUS_OPTION, text), f"continuous display not offered:\n{reply}"
        assert re.search(PERIODIC_OPTION, text), f"periodic display not offered:\n{reply}"
        assert re.search(DEFAULT_LENGTH, text), f"no word on what happens without a preference (60 seconds):\n{reply}"

    if expect.get("offers_caption") is False:
        offered = caption_offers(text)
        assert not offered, f"a caption is offered for a video: {offered}\n{reply}"

    if expect.get("asks_how_to_proceed"):
        # A question, or the options listed with an invitation to pick one.
        offered = len(list_items(text)) >= 2 and re.search(r"\btell me\b|\blet me know\b", text)
        assert questions(text) or offered, f"no question on how to proceed:\n{reply}"

    existing = expect.get("existing_label")
    if existing:
        assert re.search(existing["says"], text), f"the reply doesn't say what the Existing Label says ({existing['says']!r}):\n{reply}"
        assert re.search(existing["where"], text), f"no word on where the Existing Label is ({existing['where']!r}):\n{reply}"
        judged = [
            s for s in sentences(text)
            if re.search(ADEQUACY, s) and re.search(r"label|disclaimer|notice", s)
            and not re.search(r"\b(?:whether|if)\b", s)
        ]
        assert not judged, f"the reply judges the Existing Label: {judged}\n{reply}"
        if existing["asks"]:
            asked = " ".join(questions(text) + (list_items(text) if questions(text) else []))
            assert re.search(LABEL_ANYWAY, asked), f"no question whether to add the EU Icon anyway:\n{reply}"

    if expect.get("batch_questions"):
        check_batch_questions(expect["batch_questions"], text, reply)

    for pattern in expect.get("reply_matches", []):
        assert re.search(pattern, text), f"{pattern!r} not in reply:\n{reply}"


def sentences(text: str) -> list[str]:
    """Each line or sentence of the normalised reply."""
    return [p.strip() for p in re.split(r"\n|(?<=[.!?])\s+", text) if p.strip()]


# A question put over the list of its options: "Should I:", "Do you want me to:".
LIST_QUESTION = re.compile(r"^(?:should|shall|do you want|would you like|which|what)\b.*:$")


def questions(text: str) -> list[str]:
    """The questions in the normalised reply: each line or sentence ending in `?`,
    and each one put over a list of its options."""
    return [p for p in sentences(text) if p.rstrip(" )\"'").endswith("?") or LIST_QUESTION.match(p)]


def list_items(text: str) -> list[str]:
    """The list items of the normalised reply (`- ...`, `1. ...`)."""
    return [line.strip() for line in text.splitlines() if re.match(r"\s*(?:-|\d+[.)])\s", line)]


def caption_offers(text: str) -> list[str]:
    """Sentences that ask about or offer a caption; saying a video gets none is no offer."""
    return [s for s in sentences(text)
            if re.search(CAPTION_OPTION, s) and (s.rstrip(" )\"'").endswith("?") or re.search(CAPTION_OFFER, s))]


# Every file a converted or re-muxed video could be written as.
ANY_VIDEO_SUFFIXES = VIDEO_SUFFIXES | {".mkv", ".avi", ".m4v", ".mpg", ".mpeg", ".ts", ".wmv", ".flv"}


def check_no_converted_video(project: Path, files: dict, expect: dict, reply: str) -> None:
    """No video is written but the Labelled Copies the scenario expects (and
    previews, inside a `.label-preview` folder): nothing is converted."""
    allowed = set()
    if expect["labelled"]:
        allowed = {Path(n).with_name(f"{Path(n).stem}.ai-label{Path(n).suffix}").as_posix() for n in files}
    written = [
        p.relative_to(project).as_posix() for p in project_files(project)
        if p.suffix.lower() in ANY_VIDEO_SUFFIXES
        and not any(part.endswith(".label-preview") for part in p.relative_to(project).parts)
    ]
    extra = [p for p in written if p not in files and p not in allowed]
    assert not extra, f"videos written besides the expected Labelled Copies: {extra}\n{reply}"


def video_frame(video: Path, seconds: float, out: Path) -> Path:
    """The frame shown at `seconds`, decoded by ffmpeg as a PNG."""
    ffmpeg("-i", video, "-ss", f"{seconds:.3f}", "-frames:v", "1", out)
    return out


# When each visibility shows the Label: continuous at the start, middle and
# end; periodic (the default window of 5 s every 60 s) in the first and second
# windows, and not between them.
def label_times(visibility: str | None, seconds: float) -> tuple[list[float], list[float]]:
    if visibility == "continuous":
        return [0.1, seconds / 2, seconds - 0.2], []
    if visibility == "periodic":
        assert seconds > 61, "a periodic scenario needs a video longer than 61 s"
        return [1.0, 61.0], [30.0]
    return [min(1.0, seconds / 2)], []


def check_video_copy(original: Path, copy: Path, spec: dict, expect: dict, reply: str) -> None:
    """The Labelled Copy keeps its container and codec and shows the expected
    icon when it should, judged from decoded frames against the official icon."""
    import tempfile

    from videos import changed, probe, video_stream

    before, after = probe(original), probe(copy)
    assert after["format"]["format_name"] == before["format"]["format_name"], (
        f"{copy.name} is a {after['format']['format_name']}, not a {before['format']['format_name']}:\n{reply}"
    )
    assert video_stream(copy)["codec_name"] == video_stream(original)["codec_name"], (
        f"{copy.name} was converted to {video_stream(copy)['codec_name']}:\n{reply}"
    )
    shown, hidden = label_times(expect.get("visibility"), spec["seconds"])
    variant = VARIANT_WORDING[expect["variant"].lower()]
    with tempfile.TemporaryDirectory() as tmp:
        for t in shown:
            a = video_frame(original, t, Path(tmp) / f"original-{t}.png")
            b = video_frame(copy, t, Path(tmp) / f"copy-{t}.png")
            try:
                match = icon_match(a, b, variant)
            except AssertionError:  # no pixel changed
                match = 0.0
            assert match >= ICON_MATCH, (
                f"{copy.name} does not carry the {expect['variant']} icon at {t} s (match {match:.2f}):\n{reply}"
            )
        for t in hidden:
            a = video_frame(original, t, Path(tmp) / f"original-{t}.png")
            b = video_frame(copy, t, Path(tmp) / f"copy-{t}.png")
            with Image.open(a) as ia, Image.open(b) as ib:
                box = changed(ia.convert("RGB"), ib.convert("RGB"))
            assert box is None, f"{copy.name} shows a Label at {t} s, between appearances ({box}):\n{reply}"


def check_batch_questions(spec: dict, text: str, reply: str) -> None:
    """The batch questions asked only about the files that differ."""
    asked = questions(text)
    assert asked, f"no question asked:\n{reply}"
    # A file may be named in a lead-in on the question's line ("**recap.mp4.** Did AI ...?")
    # or in a heading right above it ("**Question about recap.mp4**").
    lines = [line for line in text.splitlines() if line.strip()]
    asked_lines = []
    for i, line in enumerate(lines):
        if any(q in line for q in asked):
            asked_lines.append(line)
            heading = lines[i - 1].strip() if i else ""
            if heading.startswith("#") or (heading and len(heading) < 80 and not re.search(r"[.?!:,;]$", heading)):
                asked_lines.append(heading)
    for name in spec["about"]:
        assert any(name.lower() in q for q in asked + asked_lines), f"no question names {name}:\n{reply}"
    for name in spec["not_about"]:
        offending = [q for q in asked if name.lower() in q]
        assert not offending, f"{name} is settled but asked about again: {offending}\n{reply}"


MARKER_RE = re.compile(r"<!--\s*eu-ai-labelling:\s*(\S+?)\s*-->")
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(<?([^)\s>]+)>?[^)]*\)")
SVG_NS = "{http://www.w3.org/2000/svg}"


def official_basic_paths() -> list[str]:
    import xml.etree.ElementTree as ET

    root = ET.parse(ICONS_DIR / "ai-basic-black.svg").getroot()
    return [p.get("d") for p in root.iter(f"{SVG_NS}path")]


class InlineSvgs(HTMLParser):
    """Each <svg> in an HTML fragment (its attributes and path data) and the
    visible text outside them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.svgs: list[dict] = []
        self.text: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "svg":
            self._depth += 1
            self.svgs.append({"attrs": dict(attrs), "paths": []})
        elif tag == "path" and self._depth:
            self.svgs[-1]["paths"].append(dict(attrs))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "svg":
            self._depth -= 1

    def handle_endtag(self, tag):
        if tag == "svg" and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if not self._depth:
            self.text.append(data)


def heading_line(document: str, html: bool) -> str | None:
    """The document's headline: the first `# ` line or the line holding the first <h1>."""
    for line in document.splitlines():
        if (html and re.search(r"<h1[\s>]", line, re.I)) or (not html and line.startswith("# ")):
            return line
    return None


def first_body_line(original: str, anchor: str) -> str:
    """The first non-empty line of the original after the anchor line."""
    lines = original.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == anchor.strip())
    return next(line for line in lines[start + 1 :] if line.strip())


def resolve_markdown_image(project: Path, document: Path, target: str) -> Path | None:
    if target.startswith("/"):
        candidates = [project / d / target.lstrip("/") for d in ("", "static", "public")]
    else:
        candidates = [document.parent / target]
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.is_file() and candidate.is_relative_to(project.resolve()):
            return candidate
    return None


def check_text_label(project: Path, original: str, spec: dict, reply: str) -> None:
    path = project / spec["file"]
    html = path.suffix.lower() in {".html", ".htm"}
    document = path.read_text()

    markers = list(MARKER_RE.finditer(document))
    assert [m.group(1) for m in markers] == [spec["wording"]], (
        f"want one `eu-ai-labelling: {spec['wording']}` marker in {path.name}:\n{document}\n{reply}"
    )
    marker = markers[0]

    below = spec.get("below")
    if spec.get("alt_mention"):
        # A caption also adds its text label to the image's alt text, after
        # the description; that image line is then the caption's anchor.
        alt, target = MD_IMAGE_RE.search(below).groups()
        shown = [a for a, t in MD_IMAGE_RE.findall(document) if t == target]
        assert len(shown) == 1, f"want {target} shown once in {path.name}:\n{document}"
        assert normalise(alt) in normalise(shown[0]), f"the alt lost its description {alt!r}: {shown[0]!r}"
        assert re.search(spec["alt_mention"], normalise(shown[0])), (
            f"alt text {shown[0]!r} lacks {spec['alt_mention']!r}:\n{reply}"
        )
        new_below = f"![{shown[0]}]({target})"
        original, below = original.replace(below, new_below), new_below

    for line in original.splitlines():
        assert line.strip() in document, f"{path.name} lost the line {line.strip()!r}:\n{document}"

    anchor = below or spec.get("section") or heading_line(original, html)
    assert anchor, "the scenario's document has no headline to label below"
    anchor_at = document.find(anchor.strip())
    body = first_body_line(original, anchor)
    body_at = document.find(body.strip(), anchor_at)
    assert 0 <= anchor_at < marker.start() < body_at, (
        f"the Label in {path.name} is not right below {anchor.strip()!r}:\n{document}"
    )
    block = document[marker.end() : body_at]

    # How a Label is made (the icon's artwork, colours, file, role and
    # accessible name) is judged by the tests' checks of a well-made Label.
    verified = label_problems(path, project)
    assert verified["problems"] == [], f"{verified['problems']}\n{block}"

    if html:
        parsed = InlineSvgs()
        parsed.feed(block)
        assert len(parsed.svgs) == 1, f"want one inline SVG in the Label:\n{block}"
        icon_name = (parsed.svgs[0]["attrs"].get("aria-label") or "").strip()
        label_text = " ".join(parsed.text)
    else:
        images = MD_IMAGE_RE.findall(block)
        assert len(images) == 1, f"want one image reference in the Label:\n{block}"
        icon_name = images[0][0].strip()
        label_text = MD_IMAGE_RE.sub(" ", block)

    label_text = normalise(re.sub(r"\s+", " ", label_text))
    assert re.search(spec["label"], label_text), f"text label {spec['label']!r} not in {label_text!r}"
    if spec.get("icon_name"):
        assert icon_name == spec["icon_name"], (
            f"the icon is named {icon_name!r}, not {spec['icon_name']!r}, in {path.name}:\n{block}"
        )


def check_references(project: Path, files: dict, spec: dict, reply: str) -> None:
    """The pages that used the image now show its Labelled Copy, with the AI
    mention added to the alt text; the references left alone are reported."""
    original = (project / spec["image"]).resolve()
    copy = original.with_name(f"{original.stem}.ai-label{original.suffix}")
    for name, mention in spec["updated"].items():
        page = project / name
        before, after = files[name]["text"], page.read_text()
        old_images = [(alt, t) for alt, t in MD_IMAGE_RE.findall(before)
                      if resolve_markdown_image(project, page, t) == original]
        assert len(old_images) == 1, f"the scenario's {name} must use {spec['image']} once"
        old_alt, old_target = old_images[0]
        images = [(alt, t) for alt, t in MD_IMAGE_RE.findall(after)
                  if resolve_markdown_image(project, page, t) in (original, copy)]
        assert [resolve_markdown_image(project, page, t) for _, t in images] == [copy], (
            f"{name} does not show the Labelled Copy {copy.name} in place of the original:\n{after}\n{reply}"
        )
        alt = normalise(images[0][0])
        assert re.search(mention, alt), f"alt text {images[0][0]!r} in {name} lacks {mention!r}:\n{reply}"
        assert normalise(old_alt) in alt, f"{name} lost the image's description {old_alt!r}: {images[0][0]!r}"
        for line in before.splitlines():
            if old_target not in line:
                assert line.strip() in after, f"{name} lost the line {line.strip()!r}:\n{after}"
    for name in spec["not_updated"]:
        assert Path(name).name.lower() in normalise(reply), f"{name} not reported as a reference left alone:\n{reply}"


SITE_ICONS = ("ai-basic-black.svg", "ai-basic-white.svg")
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".vue", ".astro", ".svelte", ".html", ".css", ".scss", ".json"}
# What a component that depends on the plugin at runtime would name.
PLUGIN_REFERENCES = (str(SKILL_DIR), str(REPO_ROOT), "skills/eu-ai-labelling", "assets/icons/")
ICON_REF_RE = re.compile(r"""["'`(]([^"'`()\s{}]*ai-basic-[a-z0-9-]+\.svg)""")
LABEL_PROP_RE = re.compile(r"""\blabel\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*["'`]([^"'`]*)["'`]\s*\})""")


def project_files(project: Path) -> list[Path]:
    skip = {"node_modules", ".git", ".claude"}
    return [p for p in project.rglob("*") if p.is_file() and not skip & set(p.relative_to(project).parts)]


def check_site_component(project: Path, files: dict, spec: dict, reply: str) -> None:
    """One label component in the project's framework, adapted from references/site.md."""
    added = [p for p in project_files(project) if p.relative_to(project).as_posix() not in files]
    components = [p for p in added if p.suffix in spec["extensions"] and "ai-basic-" in p.read_text()]
    assert len(components) == 1, (
        f"want one new {'/'.join(spec['extensions'])} component showing the Basic icon, got "
        f"{[str(p.relative_to(project)) for p in components]}:\n{reply}"
    )
    component = components[0]
    source = component.read_text()

    # The official Basic SVGs, both colours, copied byte for byte into the project.
    copies = [p for p in project_files(project) if re.fullmatch(r"ai-basic-[a-z0-9-]+\.svg", p.name)]
    for name in SITE_ICONS:
        assert any(p.name == name for p in copies), f"{name} was not copied into the project:\n{reply}"
    for copy in copies:
        assert copy.read_bytes() == (ICONS_DIR / copy.name).read_bytes(), (
            f"{copy.relative_to(project)} is not the official {copy.name}"
        )

    # Icon Colour by background: the Black and the White icon.
    colours = set(re.findall(r"ai-basic-(black|white)\b", source))
    templated = re.search(r"ai-basic-\$\{", source) and '"white"' in source and '"black"' in source
    assert colours == {"black", "white"} or templated, f"the component does not offer both Icon Colours:\n{source}"
    # Every icon it loads is the project's copy, never the plugin's.
    for target in ICON_REF_RE.findall(source):
        rest = target.lstrip("/")
        candidates = [project / "public" / rest, project / rest] if target.startswith("/") else [component.parent / target]
        assert any(c.resolve().is_file() and c.resolve().is_relative_to(project.resolve()) for c in candidates), (
            f"the component loads {target}, which is not a file the project serves"
        )
    for path in [*added, project / spec["used_in"]]:
        if path.suffix in SOURCE_SUFFIXES:
            named = [ref for ref in PLUGIN_REFERENCES if ref in path.read_text()]
            assert not named, f"{path.relative_to(project)} depends on the plugin: {named}"

    # Accessible: alt text, a translatable label, a keyboard disclosure.
    assert re.search(r"<img\b[^>]*\balt=", source, re.S), f"the icon has no alt text:\n{source}"
    assert re.search(r"\{\s*(?:props\.)?label\s*\}", source), f"the text label is not the `label` input:\n{source}"
    assert "<button" in source, f"the second layer does not open from a <button>:\n{source}"
    for attr in ("aria-expanded", "aria-controls"):
        assert attr in source, f"no {attr} on the toggle:\n{source}"
    if component.suffix in (".jsx", ".tsx"):
        check_react_behaviour(component, project / spec["used_in"])
    else:
        assert re.search(r"""["']Escape["']|\.esc\b""", source), f"Escape does not close the second layer:\n{source}"
        assert re.search(r"onMouseEnter|@mouseenter|mouseenter", source), f"hover does not open the second layer:\n{source}"
        assert re.search(r"""(?<![\w-])(?::?hidden|v-show)\s*=""", source), (
            f"the second layer has no `hidden` or `v-show` binding:\n{source}"
        )

    # Used where the user asked, with the text label and the second layer.
    original = files[spec["used_in"]]["text"]
    page = (project / spec["used_in"]).read_text()
    for line in original.splitlines():
        assert line.strip() in page, f"{spec['used_in']} lost the line {line.strip()!r}:\n{page}"
    usage = re.search(rf"<{re.escape(component.stem)}\b([^>]*)>", page)
    assert usage, f"{component.stem} is not used in {spec['used_in']}:\n{page}"
    label = LABEL_PROP_RE.search(usage.group(1))
    label_text = normalise(next((g for g in label.groups() if g), "")) if label else ""
    assert re.search(spec["label"], label_text), f"label {spec['label']!r} not passed in:\n{usage.group(0)}"
    if spec.get("details"):
        assert re.search(r"\bdetails\s*=", usage.group(1)), f"no second layer passed in:\n{usage.group(0)}"


SITE_HARNESS = Path(__file__).resolve().parent / "site"
CLOSED = {"expanded": False, "hidden": True}
OPEN = {"expanded": True, "hidden": False}


def check_react_behaviour(component: Path, page: Path) -> None:
    """Run the component as a visitor would: `site/run.mjs` bundles it with the
    page that uses it, renders both in jsdom and replays hover, click and
    Escape (see that file). Needs `npm ci --prefix tests/evals/site`."""
    if not (SITE_HARNESS / "node_modules").is_dir() or not shutil.which("node"):
        pytest.skip("the site harness is not installed: run `npm ci --prefix tests/evals/site`")
    proc = subprocess.run(["node", str(SITE_HARNESS / "run.mjs"), str(component), str(page)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    seen = json.loads(proc.stdout.strip().splitlines()[-1])
    assert "error" not in seen, f"the component or its page does not build or render: {seen['error']}"
    assert seen["page_shows_a_label"], f"{page.name} renders no label"
    assert seen["has_button"], "no <button aria-controls> opens a second layer"
    assert seen["ids_differ"], "two labels on a page share the second layer's id"
    assert "ai-basic-black" in seen["light_icon"] and "ai-basic-white" in seen["dark_icon"], (
        f"the icon does not follow the background: {seen['light_icon']!r}, {seen['dark_icon']!r}"
    )
    assert seen["starts_closed"] == CLOSED, f"the second layer starts open: {seen['starts_closed']}"
    assert seen["hover"] == [OPEN, CLOSED], f"hover does not open it, or leaving does not close it: {seen['hover']}"
    assert seen["click"] == [OPEN, OPEN, CLOSED], f"a click does not pin it open until the next click: {seen['click']}"
    assert seen["escape_inside"] == {**CLOSED, "focus_on_button": True}, (
        f"Escape with focus inside does not close it and return focus: {seen['escape_inside']}"
    )
    assert seen["escape_outside"] == {**CLOSED, "focus_kept": True}, (
        f"Escape with focus elsewhere does not close it, or moves focus: {seen['escape_outside']}"
    )


def run_scenario(
    scenario: dict, command: str = "/eu-ai-labelling", with_plugin: bool = True
) -> tuple[Path, dict[str, str], str, list[dict]]:
    project = make_project(scenario["files"])
    digests = {name: sha256(project / name) for name in scenario["files"]}
    prompt = scenario["prompt"].replace("/eu-ai-labelling", command, 1)
    events = run_claude(project, prompt, with_plugin=with_plugin)
    return project, digests, reply_text(events), events


def tool_inputs(events: list[dict]) -> list[str]:
    """Every tool_use input in the session, as JSON text."""
    return [
        json.dumps(block.get("input", {}))
        for e in events
        if e.get("type") == "assistant"
        for block in e.get("message", {}).get("content", [])
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]


# --- Tests --------------------------------------------------------------------


@needs_model
@pytest.mark.parametrize("name, scenario", load_scenarios(), ids=[n for n, _ in load_scenarios()])
def test_scenario(name, scenario):
    project, digests, reply, _ = run_scenario(scenario)
    check(scenario, project, digests, reply)


@needs_model
def test_unknown_command_fails_the_deepfake_scenario():
    """Control: the checks above can fail. Without the skill the model answers
    in its own words, and the deepfake scenario's expectations are not met.

    The plugin is not loaded at all: with it loaded, a model whose slash
    command doesn't resolve finds the skill folder and follows SKILL.md by
    hand, and the control proves nothing."""
    scenario = json.loads((SCENARIOS_DIR / "politician-deepfake.json").read_text())
    project, digests, reply, events = run_scenario(scenario, command="/eu-ai-labelling-nope", with_plugin=False)

    leaked = [i for i in tool_inputs(events) if str(SKILL_DIR) in i or "SKILL.md" in i]
    assert not leaked, f"the control reached the skill anyway: {leaked}"
    with pytest.raises(AssertionError):
        check(scenario, project, digests, reply)


# --- The checks themselves (no model call) -------------------------------------
#
# Canned replies run through check(), so a check too loose to catch a
# non-compliant reply fails here rather than passing a broken skill.


def load_scenario(name: str) -> dict:
    return json.loads((SCENARIOS_DIR / f"{name}.json").read_text())


def checked_project(tmp_path: Path, scenario: dict) -> tuple[Path, dict[str, str]]:
    """The scenario's files as make_project writes them, under tmp_path."""
    project = tmp_path / "project"
    project.mkdir()
    for name, spec in scenario["files"].items():
        write_file(project / name, spec)
    return project, {name: sha256(project / name) for name in scenario["files"]}


# --- "Do I need a label?": no verdict, the official sources, an offer ---------------

REQUIRED_SCENARIO = "asks-if-a-label-is-required"

ASKS_IF_REQUIRED_REPLY = """\
I can't tell you whether the law requires a Label for council-budget.md:
that depends on facts and a legal judgement that are yours to make. These are the official sources:

- the Guidelines on Article 50: https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations
- the Code of Practice on transparency of AI-generated content
- the AI Act Service Desk: https://ai-act-service-desk.ec.europa.eu/

Would you like me to add a Label to it anyway?

This is not legal advice.
"""

WEAKENED_REQUIRED_REPLIES = {
    "gives a verdict": (
        "I can't tell you whether the law requires a Label for council-budget.md:\nthat depends on facts and a legal judgement that are yours to make.",
        "a Label is not required for council-budget.md:\nan editor reviewed it.",
    ),
    "no Service Desk": ("- the AI Act Service Desk: https://ai-act-service-desk.ec.europa.eu/\n", ""),
    "no Guidelines": (
        "- the Guidelines on Article 50: https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations\n", "",
    ),
    "no offer to label": ("Would you like me to add a Label to it anyway?", "That's all."),
}


@pytest.mark.parametrize("offer", [
    "Would you like me to add a Label to it anyway?",
    "If you want a Label on it anyway, tell me and I'll add one.",
    "If you want a Label, say so. I'd then apply the Basic EU Icon with a text label.",
])
def test_check_accepts_pointing_to_the_official_sources_without_a_verdict(tmp_path, offer):
    scenario = load_scenario(REQUIRED_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, ASKS_IF_REQUIRED_REPLY.replace("Would you like me to add a Label to it anyway?", offer))


@pytest.mark.parametrize("weakened", sorted(WEAKENED_REQUIRED_REPLIES))
def test_check_rejects_a_verdict_or_a_missing_source(tmp_path, weakened):
    scenario = load_scenario(REQUIRED_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    old, new = WEAKENED_REQUIRED_REPLIES[weakened]
    assert old in ASKS_IF_REQUIRED_REPLY
    reply = ASKS_IF_REQUIRED_REPLY.replace(old, new)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, reply)


def test_check_rejects_labelling_before_the_user_answers(tmp_path):
    scenario = load_scenario(REQUIRED_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    document = project / "council-budget.md"
    document.write_text("<!-- eu-ai-labelling: generated -->\n" + document.read_text())

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_IF_REQUIRED_REPLY)


@pytest.mark.parametrize("reply, accepted", [
    ("Labelled summit.png with the Fully AI-Generated icon: summit.ai-label.png.", True),
    ("I don't decide whether a label is required. Labelled summit.png: summit.ai-label.png.", True),
    ("Labelled summit.png: summit.ai-label.png. For the site component, `label` is required.", True),
    ("A label is required for a deepfake like this. Labelled summit.png: summit.ai-label.png.", False),
    ("- **Disclosure Outcome:** Required\n\nLabelled summit.png: summit.ai-label.png.", False),
    ("You are legally required to label this. Labelled summit.png: summit.ai-label.png.", False),
], ids=["no verdict", "says it doesn't decide", "a required prop", "label is required", "outcome block", "you are required"])
def test_check_never_accepts_a_verdict_on_the_law(tmp_path, label_tool, reply, accepted):
    scenario = load_scenario("politician-deepfake")
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "summit.png", "--variant", "generated").returncode == 0

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


# --- An image whose origin nobody stated: the skill asks -----------------------

ASKS_ORIGIN_REPLY = "Before I label photo.png: did AI create it from scratch, or did it edit a real photo?"


def test_check_accepts_asking_how_ai_was_involved(tmp_path):
    scenario = load_scenario("unknown-origin")
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, ASKS_ORIGIN_REPLY)


ASKS_ORIGIN_OVER_A_LIST_REPLY = """\
Before I label `photo.png`, I need to know how AI was involved:

- **Fully AI-generated:** AI created the image from scratch.
- **Partially AI-modified:** AI edited something that already existed, such as a real photo.

Which one is it?
"""


def test_check_accepts_asking_how_ai_was_involved_over_a_list_of_the_options(tmp_path):
    scenario = load_scenario("unknown-origin")
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, ASKS_ORIGIN_OVER_A_LIST_REPLY)


@pytest.mark.parametrize("reply", [
    "I'll treat photo.png as fully AI-generated.",
    "Is photo.png a photo?",
    ASKS_ORIGIN_OVER_A_LIST_REPLY.replace("Which one is it?", "I'll go with the first."),
], ids=["assumes", "asks something else", "lists the options without asking"])
def test_check_rejects_not_asking_how_ai_was_involved(tmp_path, reply):
    scenario = load_scenario("unknown-origin")
    project, digests = checked_project(tmp_path, scenario)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, reply)


def test_check_rejects_labelling_before_the_origin_is_known(tmp_path, label_tool):
    scenario = load_scenario("unknown-origin")
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "photo.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ORIGIN_REPLY)


@pytest.mark.parametrize("burned_in, accepted", [("modified", True), ("generated", False)])
def test_check_judges_the_named_variant_from_the_labelled_copy(tmp_path, label_tool, burned_in, accepted):
    scenario = load_scenario("named-variant-on-a-photo")
    project, digests = checked_project(tmp_path, scenario)
    result = label_tool("apply", project / "photo.png", "--variant", burned_in)
    assert result.returncode == 0, result.stderr
    reply = "Labelled photo.png with the Partially AI-Modified icon: photo.ai-label.png."

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


def test_check_rejects_a_rectangle_in_place_of_the_icon(tmp_path):
    """A mark of the right size that isn't the official artwork."""
    scenario = load_scenario("named-variant-on-a-photo")
    project, digests = checked_project(tmp_path, scenario)
    with Image.open(project / "photo.png") as img:
        copy = img.copy()
    ImageDraw.Draw(copy).rectangle((copy.width - 16 - 222, 16, copy.width - 16, 16 + 48), fill=(0, 0, 0))
    copy.save(project / "photo.ai-label.png")

    with pytest.raises(AssertionError):
        check(scenario, project, digests, "Done.")


# A named Basic for an image: the image path can't apply it, so the skill asks
# which of the two image variants it is, and labels nothing yet.

BASIC_FOR_AN_IMAGE_REPLY = """\
The Basic icon is for documents and sites; an image is labelled with Fully AI-Generated or
Partially AI-Modified. Is photo.png fully AI-generated, or a real photo that AI modified?
"""


def test_check_accepts_asking_which_variant_when_basic_is_named_for_an_image(tmp_path):
    scenario = load_scenario("named-basic-for-an-image")
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, BASIC_FOR_AN_IMAGE_REPLY)


def test_check_rejects_not_asking_which_variant_when_basic_is_named_for_an_image(tmp_path):
    scenario = load_scenario("named-basic-for-an-image")
    project, digests = checked_project(tmp_path, scenario)
    reply = "photo.png can't be labelled with the Basic icon. Pick another variant."

    with pytest.raises(AssertionError):
        check(scenario, project, digests, reply)


def test_check_rejects_labelling_an_image_named_as_basic_before_the_user_answers(tmp_path, label_tool):
    scenario = load_scenario("named-basic-for-an-image")
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "photo.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, BASIC_FOR_AN_IMAGE_REPLY)


# --- Text labels: canned documents ---------------------------------------------
#
# A document the agent labelled, written by hand from the ticket, runs through
# check(); each broken variant must be rejected.

OFFICIAL_BASIC = ICONS_DIR / "ai-basic-black.svg"

LABELLED_ITALIAN_ARTICLE = """\
# Il nuovo orario dei treni regionali

<!-- eu-ai-labelling: generated -->
![IA](assets/ai-basic-black.svg) Generato con IA

Dal 14 dicembre cambia l'orario dei treni regionali in tutta la provincia. Le corse del mattino partiranno dieci minuti prima.

La regione ha pubblicato le nuove tabelle sul proprio sito.
"""

NAMED_VARIANT_REPLY = "Labelled articolo.md in place with the Basic EU Icon and the text label."


def labelled_document(tmp_path: Path, scenario: dict, document: str, icon: bytes | None = None):
    """The scenario's project after a (canned) labelling: the document
    rewritten in place and, for Markdown, the icon copied to assets/."""
    project, digests = checked_project(tmp_path, scenario)
    name = scenario["expect"]["text_label"]["file"]
    (project / name).write_text(document)
    if name.endswith(".md"):
        (project / "assets").mkdir()
        (project / "assets" / "ai-basic-black.svg").write_bytes(icon or OFFICIAL_BASIC.read_bytes())
    return project, digests


def test_check_accepts_a_labelled_italian_article(tmp_path):
    scenario = load_scenario("italian-article")
    project, digests = labelled_document(tmp_path, scenario, LABELLED_ITALIAN_ARTICLE)

    check(scenario, project, digests, NAMED_VARIANT_REPLY)


BROKEN_ITALIAN_ARTICLES = {
    "no marker": ("<!-- eu-ai-labelling: generated -->\n", ""),
    "modified marker on generated text": ("eu-ai-labelling: generated", "eu-ai-labelling: modified"),
    "English text label on an Italian article": ("Generato con IA", "Generated with AI"),
    "no icon": ("![IA](assets/ai-basic-black.svg) ", ""),
    "English icon name on an Italian article": ("![IA](", "![AI]("),
    "generic icon name": ("![IA](", "![icon]("),
    "icon file missing": ("assets/ai-basic-black.svg", "assets/missing.svg"),
    "label at the bottom": (
        "<!-- eu-ai-labelling: generated -->\n![IA](assets/ai-basic-black.svg) Generato con IA\n\n",
        "",
    ),
    "a body line dropped": ("La regione ha pubblicato le nuove tabelle sul proprio sito.\n", ""),
}


@pytest.mark.parametrize("broken", sorted(BROKEN_ITALIAN_ARTICLES))
def test_check_rejects_a_badly_labelled_italian_article(tmp_path, broken):
    scenario = load_scenario("italian-article")
    old, new = BROKEN_ITALIAN_ARTICLES[broken]
    assert old in LABELLED_ITALIAN_ARTICLE
    document = LABELLED_ITALIAN_ARTICLE.replace(old, new)
    if broken == "label at the bottom":
        document += "\n<!-- eu-ai-labelling: generated -->\n![IA](assets/ai-basic-black.svg) Generato con IA\n"
    project, digests = labelled_document(tmp_path, scenario, document)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, NAMED_VARIANT_REPLY)


def test_check_rejects_a_redrawn_icon(tmp_path):
    """The copied SVG must be the official file, not a look-alike."""
    scenario = load_scenario("italian-article")
    redrawn = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="5"/></svg>'
    project, digests = labelled_document(tmp_path, scenario, LABELLED_ITALIAN_ARTICLE, icon=redrawn)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, NAMED_VARIANT_REPLY)


BLACK_FILLS = ['fill="#000" fill-rule="evenodd"', 'fill="#fff"', 'fill="#fff"']
WHITE_FILLS = ['fill="#fff" fill-rule="evenodd"', 'fill="#1d1d1b"', 'fill="#1d1d1b"']


def official_svg_inline(
    role: str = ' role="img"', label: str = ' aria-label="AI"', fills: list[str] = BLACK_FILLS
) -> str:
    paths = official_basic_paths()
    body = "".join(f'<path {f} d="{d}"/>' for f, d in zip(fills, paths))
    return f'<svg{role}{label} xmlns="http://www.w3.org/2000/svg" viewBox="89.28 100.72 365.49 365.49" width="24" height="24">{body}</svg>'


def labelled_english_page(svg: str) -> str:
    page = load_scenario("english-html-page")["files"]["page.html"]["text"]
    label = (
        "<h1>Our spring opening hours</h1>\n"
        "    <!-- eu-ai-labelling: modified -->\n"
        f'    <p class="eu-ai-label">{svg} <span>Modified with AI</span></p>\n'
    )
    return page.replace("<h1>Our spring opening hours</h1>\n", label)


@pytest.mark.parametrize(
    "svg, accepted",
    [
        (official_svg_inline(), True),
        (official_svg_inline(role=""), False),
        (official_svg_inline(label=""), False),
        (official_svg_inline().replace("M328.11", "M300.11"), False),
        (official_svg_inline(fills=WHITE_FILLS), True),
        (official_svg_inline(fills=['fill="#fff" fill-rule="evenodd"', 'fill="#fff"', 'fill="#fff"']), False),
        (official_svg_inline(fills=['fill="#000" fill-rule="evenodd"', 'fill="#1d1d1b"', 'fill="#fff"']), False),
        (official_svg_inline(fills=['fill="#000"', 'fill="#fff"', 'fill="#fff"']), False),
    ],
    ids=[
        "accessible official svg",
        "no role",
        "no aria-label",
        "not the official artwork",
        "white icon colour",
        "white pill on white letters",
        "mixed colours",
        "no evenodd fill-rule",
    ],
)
def test_check_judges_the_inline_svg_of_an_html_page(tmp_path, svg, accepted):
    scenario = load_scenario("english-html-page")
    project, digests = labelled_document(tmp_path, scenario, labelled_english_page(svg))
    reply = "Labelled page.html in place."

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


LABELLED_REPORT = load_scenario("partly-ai-markdown-report")["files"]["report.md"]["text"].replace(
    "## Outlook\n\n",
    "## Outlook\n\n<!-- eu-ai-labelling: generated -->\n"
    "![AI](assets/ai-basic-black.svg) This section was generated with AI\n\n",
)


@pytest.mark.parametrize("extra_at_top, accepted", [(False, True), (True, False)], ids=["section only", "also at the top"])
def test_check_wants_only_the_ai_made_section_labelled(tmp_path, extra_at_top, accepted):
    scenario = load_scenario("partly-ai-markdown-report")
    document = LABELLED_REPORT
    if extra_at_top:
        document = document.replace(
            "# Quarterly sales report\n\n",
            "# Quarterly sales report\n\n<!-- eu-ai-labelling: generated -->\n"
            "![AI](assets/ai-basic-black.svg) Generated with AI\n\n",
        )
    project, digests = labelled_document(tmp_path, scenario, document)
    reply = "Labelled the Outlook section of report.md."

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


# --- An Existing Label: asked about, kept, named --------------------------------

ASKS_ABOUT_EXISTING_LABEL_REPLY = """\
post.md already has a Label this plugin didn't add: the last line, below the rule, reads
"This article was generated by AI." Its wording matches the fully AI-generated wording you chose.

Should I add the EU Icon anyway, or leave post.md as it is?
"""

WEAKENED_EXISTING_LABEL_REPLIES = {
    "doesn't say what it says": ('reads\n"This article was generated by AI."', "is a disclaimer."),
    "doesn't say where": ("the last line, below the rule, reads", "it reads"),
    "asks only where to add the Label": (
        "Should I add the EU Icon anyway, or leave post.md as it is?", "Should I add the Label below the headline?",
    ),
    "doesn't ask": ("Should I add the EU Icon anyway, or leave post.md as it is?", "I left post.md as it is."),
    "asks something else": (
        "Should I add the EU Icon anyway, or leave post.md as it is?", "Is the post in English?",
    ),
    "calls it sufficient": (
        "Its wording matches the fully AI-generated wording you chose.",
        "That disclaimer is sufficient on its own.",
    ),
    "calls it inadequate": (
        "Its wording matches the fully AI-generated wording you chose.",
        "The existing label is not adequate.",
    ),
}


@pytest.mark.parametrize("extra", ["", "\nI can't say whether the disclaimer is sufficient under the law."],
                         ids=["plain", "declines to judge it"])
def test_check_accepts_asking_about_an_existing_label(tmp_path, extra):
    scenario = load_scenario("existing-label-markdown-disclaimer")
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, ASKS_ABOUT_EXISTING_LABEL_REPLY + extra)


def test_check_accepts_an_existing_label_question_put_over_a_list(tmp_path):
    scenario = load_scenario("existing-label-markdown-disclaimer")
    project, digests = checked_project(tmp_path, scenario)
    reply = ASKS_ABOUT_EXISTING_LABEL_REPLY.replace(
        "Should I add the EU Icon anyway, or leave post.md as it is?",
        "Should I:\n1. **Add the EU Icon anyway.**\n2. **Leave the document as it is.**",
    )

    check(scenario, project, digests, reply)


@pytest.mark.parametrize("weakened", sorted(WEAKENED_EXISTING_LABEL_REPLIES))
def test_check_rejects_a_weak_reply_on_an_existing_label(tmp_path, weakened):
    scenario = load_scenario("existing-label-markdown-disclaimer")
    project, digests = checked_project(tmp_path, scenario)
    old, new = WEAKENED_EXISTING_LABEL_REPLIES[weakened]
    assert old in ASKS_ABOUT_EXISTING_LABEL_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_EXISTING_LABEL_REPLY.replace(old, new))


def test_check_rejects_labelling_before_the_user_answers_about_an_existing_label(tmp_path):
    scenario = load_scenario("existing-label-markdown-disclaimer")
    project, digests = labelled_document(
        tmp_path, {**scenario, "expect": load_scenario("existing-label-label-anyway")["expect"]}, LABELLED_POST_WITH_DISCLAIMER,
    )

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_EXISTING_LABEL_REPLY)


LABELLED_POST_WITH_DISCLAIMER = load_scenario("existing-label-label-anyway")["files"]["post.md"]["text"].replace(
    "# Five tips for winter cycling\n\n",
    "# Five tips for winter cycling\n\n<!-- eu-ai-labelling: generated -->\n"
    "![AI](assets/ai-basic-black.svg) Generated with AI\n\n",
)

LABELLED_ANYWAY_REPLY = (
    "Labelled post.md in place below its headline with the Basic EU Icon and \"Generated with AI\". "
    "Your own disclaimer at the end (\"This article was generated by AI.\") is kept as it was."
)


@pytest.mark.parametrize("document, reply, accepted", [
    (LABELLED_POST_WITH_DISCLAIMER, LABELLED_ANYWAY_REPLY, True),
    (LABELLED_POST_WITH_DISCLAIMER.replace("_This article was generated by AI._\n", ""), LABELLED_ANYWAY_REPLY, False),
    (LABELLED_POST_WITH_DISCLAIMER, "Labelled post.md in place below its headline.", False),
], ids=["labelled, disclaimer kept and named", "disclaimer removed", "disclaimer not named"])
def test_check_judges_labelling_anyway(tmp_path, document, reply, accepted):
    scenario = load_scenario("existing-label-label-anyway")
    project, digests = labelled_document(tmp_path, scenario, document)

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


# An image with "AI generated" in its pixels: the skill writes no Labelled Copy
# until the user says whether to add the EU Icon anyway.

IMAGE_EXISTING_LABEL_SCENARIO = "existing-label-image-pixels"

ASKS_ABOUT_IMAGE_EXISTING_LABEL_REPLY = """\
lamp.png already shows "AI generated" in its bottom-left corner. That wording matches the fully AI-generated wording you chose.

Should I add the EU Icon anyway, or leave the image as it is?
"""


def test_the_image_fixture_has_its_text_in_the_pixels(tmp_path):
    """Drawn, not a flat colour: the Existing Label is there to be read."""
    project, _ = checked_project(tmp_path, load_scenario(IMAGE_EXISTING_LABEL_SCENARIO))
    with Image.open(project / "lamp.png") as image:
        grey = image.convert("L")
    width, height = grey.size
    dark = grey.point(lambda v: 255 if v < 100 else 0)
    # Text 48 px tall (6% of 800) along the bottom-left, nothing anywhere else.
    left, top, right, bottom = dark.getbbox()
    assert left < width // 10 and bottom > height * 0.9, "the text is not in the bottom-left corner"
    assert 30 <= bottom - top <= 70 and right - left > 150, f"not a line of text: {(left, top, right, bottom)}"


def test_check_accepts_asking_about_an_existing_label_in_an_image(tmp_path):
    scenario = load_scenario(IMAGE_EXISTING_LABEL_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, ASKS_ABOUT_IMAGE_EXISTING_LABEL_REPLY)


@pytest.mark.parametrize("old, new", [
    ("in its bottom-left corner", "in its top-left corner"),
    ('"AI generated"', "a disclaimer"),
    ("Should I add the EU Icon anyway, or leave the image as it is?", "I'll wait."),
], ids=["wrong corner", "doesn't say what it says", "no question"])
def test_check_rejects_a_weak_reply_on_an_existing_label_in_an_image(tmp_path, old, new):
    scenario = load_scenario(IMAGE_EXISTING_LABEL_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    assert old in ASKS_ABOUT_IMAGE_EXISTING_LABEL_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_IMAGE_EXISTING_LABEL_REPLY.replace(old, new))


def test_check_rejects_a_labelled_copy_written_before_the_user_answers_about_an_existing_label(tmp_path, label_tool):
    scenario = load_scenario(IMAGE_EXISTING_LABEL_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "lamp.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_IMAGE_EXISTING_LABEL_REPLY)


# A batch where one image has "AI generated" in its pixels: the batch's one
# message asks, naming that image, whether to add the EU Icon anyway, and no
# file of the batch is labelled until the user answers.

BATCH_EXISTING_LABEL_SCENARIO = "existing-label-batch"

ASKS_ABOUT_BATCH_EXISTING_LABEL_REPLY = """\
All three images were generated from scratch, so each gets the Fully AI-Generated icon.
One question before I label the batch:

1. stage.png already shows "AI generated" in its bottom-left corner. Should I add the EU Icon to stage.png anyway, or leave it as it is?
"""


def test_check_accepts_a_batch_asking_about_the_image_with_an_existing_label(tmp_path):
    scenario = load_scenario(BATCH_EXISTING_LABEL_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, ASKS_ABOUT_BATCH_EXISTING_LABEL_REPLY)


@pytest.mark.parametrize("old, new", [
    ("1. stage.png already shows \"AI generated\" in its bottom-left corner. Should I add the EU Icon to stage.png anyway",
     "1. One image already shows \"AI generated\" in its bottom-left corner. Should I add the EU Icon to it anyway"),
    ("Should I add the EU Icon to stage.png anyway, or leave it as it is?", "I'll label the others first."),
], ids=["question doesn't name the file", "no question"])
def test_check_rejects_a_batch_reply_not_asking_about_the_existing_label_by_name(tmp_path, old, new):
    scenario = load_scenario(BATCH_EXISTING_LABEL_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    assert old in ASKS_ABOUT_BATCH_EXISTING_LABEL_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_BATCH_EXISTING_LABEL_REPLY.replace(old, new))


def test_check_rejects_labelling_the_rest_of_the_batch_before_the_user_answers(tmp_path, label_tool):
    scenario = load_scenario(BATCH_EXISTING_LABEL_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "event" / "team-1.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_BATCH_EXISTING_LABEL_REPLY)


# --- Creative Work: where the Label goes -----------------------------------------
#
# A satirical image, with or without a named variant: the skill asks whether to
# add a caption or burn the icon in, and labels nothing yet.

PLACEMENT_SCENARIOS = ("satirical-ai-art", "named-variant-on-a-creative-work")

PLACEMENT_REPLY = """\
minister-satire.png is satire, so an icon inside the picture may get in the way. How would you like it labelled?

1. **Caption**: the Basic EU Icon and "Image generated with AI" below the image, where it is published.
2. **Burn-in**: the Fully AI-Generated icon burned into a Labelled Copy.
"""

WEAKENED_PLACEMENT_REPLIES = {
    "no caption offered": ('1. **Caption**: the Basic EU Icon and "Image generated with AI" below the image, where it is published.\n', ""),
    "no burn-in offered": ("2. **Burn-in**: the Fully AI-Generated icon burned into a Labelled Copy.\n", ""),
    "no question": ("How would you like it labelled?", "I'll add a caption."),
}


@pytest.mark.parametrize("name", PLACEMENT_SCENARIOS)
def test_check_accepts_asking_for_a_caption_or_burn_in(tmp_path, name):
    scenario = load_scenario(name)
    project, digests = checked_project(tmp_path, scenario)

    check(scenario, project, digests, PLACEMENT_REPLY)


@pytest.mark.parametrize("weakened", sorted(WEAKENED_PLACEMENT_REPLIES))
def test_check_rejects_a_placement_question_missing_an_option(tmp_path, weakened):
    scenario = load_scenario("satirical-ai-art")
    project, digests = checked_project(tmp_path, scenario)
    old, new = WEAKENED_PLACEMENT_REPLIES[weakened]
    assert old in PLACEMENT_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, PLACEMENT_REPLY.replace(old, new))


@pytest.mark.parametrize("name", PLACEMENT_SCENARIOS)
def test_check_rejects_burning_in_before_the_user_picks(tmp_path, label_tool, name):
    scenario = load_scenario(name)
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "minister-satire.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, PLACEMENT_REPLY)


# A caption the user chose for a Creative Work: in the Italian article, right
# below the image reference, with the Basic icon, Italian text label and marker.

CAPTION_SCENARIO = "creative-work-caption-italian"
CAPTION = (
    "<!-- eu-ai-labelling: generated -->\n"
    "![IA](assets/ai-basic-black.svg) Immagine generata con IA\n\n"
)


def captioned_article(caption: str = CAPTION, below_image: bool = True, alt_mention: bool = True) -> str:
    scenario = load_scenario(CAPTION_SCENARIO)
    article = scenario["files"][scenario["expect"]["text_label"]["file"]]["text"]
    anchor = scenario["expect"]["text_label"]["below"]
    if alt_mention:
        mentioned = anchor.replace("](", " (Immagine generata con IA)](", 1)
        article, anchor = article.replace(anchor, mentioned), mentioned
    if below_image:
        return article.replace(f"{anchor}\n\n", f"{anchor}\n\n{caption}", 1)
    headline = article.splitlines()[0]
    return article.replace(f"{headline}\n\n", f"{headline}\n\n{caption}", 1)


CAPTION_REPLY = "Added a caption below satira.png in articolo.md: Immagine generata con IA."


def test_check_accepts_a_caption_below_the_image(tmp_path):
    scenario = load_scenario(CAPTION_SCENARIO)
    project, digests = labelled_document(tmp_path, scenario, captioned_article())

    check(scenario, project, digests, CAPTION_REPLY)


BROKEN_CAPTIONS = {
    "caption under the headline": dict(below_image=False),
    "English text label in an Italian article": dict(caption=CAPTION.replace("Immagine generata con IA", "Image generated with AI")),
    "no marker": dict(caption=CAPTION.replace("<!-- eu-ai-labelling: generated -->\n", "")),
    "no alt text mention": dict(alt_mention=False),
    "no icon": dict(caption=CAPTION.replace("![IA](assets/ai-basic-black.svg) ", "")),
    "English icon name in an Italian article": dict(caption=CAPTION.replace("![IA](", "![AI](")),
}


@pytest.mark.parametrize("broken", sorted(BROKEN_CAPTIONS))
def test_check_rejects_a_bad_caption(tmp_path, broken):
    scenario = load_scenario(CAPTION_SCENARIO)
    project, digests = labelled_document(tmp_path, scenario, captioned_article(**BROKEN_CAPTIONS[broken]))

    with pytest.raises(AssertionError):
        check(scenario, project, digests, CAPTION_REPLY)


def test_check_rejects_a_caption_plus_a_burned_in_copy(tmp_path, label_tool):
    """The user chose a caption: the work itself stays without an icon."""
    scenario = load_scenario(CAPTION_SCENARIO)
    project, digests = labelled_document(tmp_path, scenario, captioned_article())
    assert label_tool("apply", project / "satira.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, CAPTION_REPLY)


# --- Batch: questions asked once, about the files that differ ---------------------
#
# A mixed folder: the reply asks only about the files context doesn't settle,
# and labels nothing until they are answered.

BATCH_SCENARIO = "mixed-event-folder"

COMPLIANT_BATCH_REPLY = """\
team-1.png and team-2.png were generated from scratch, so they get the Fully AI-Generated icon.
One question before I label the batch:

1. Were crowd.png and stage.png generated from scratch, or are they real photos that AI edited?
"""

WEAKENED_BATCH_REPLIES = {
    "asks the shared question per file": (
        "1. Were crowd.png and stage.png generated from scratch, or are they real photos that AI edited?",
        "1. Were crowd.png and stage.png generated from scratch, or are they real photos that AI edited?\n"
        "2. Does team-1.png show real people?",
    ),
    "asks about every file": (
        "1. Were crowd.png and stage.png generated",
        "1. Were team-1.png, team-2.png, crowd.png and stage.png generated",
    ),
    "leaves a differing file out": ("Were crowd.png and stage.png generated", "Was crowd.png generated"),
    "asks nothing": (
        "1. Were crowd.png and stage.png generated from scratch, or are they real photos that AI edited?",
        "I assumed crowd.png and stage.png were generated from scratch.",
    ),
}


@pytest.mark.parametrize("old, new", [
    ("", ""),
    ("1. Were crowd.png and stage.png generated from scratch",
     "**Question: crowd.png and stage.png.** Were they generated from scratch"),
    ("1. Were crowd.png and stage.png generated from scratch",
     "**Question about crowd.png and stage.png**\n\nWere they generated from scratch"),
], ids=["named in the question", "named in the question's lead-in", "named in a heading above the question"])
def test_check_accepts_a_batch_reply_asking_only_about_the_differing_files(tmp_path, old, new):
    scenario = load_scenario(BATCH_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    assert old in COMPLIANT_BATCH_REPLY

    check(scenario, project, digests, COMPLIANT_BATCH_REPLY.replace(old, new) if old else COMPLIANT_BATCH_REPLY)


@pytest.mark.parametrize("weakened", sorted(WEAKENED_BATCH_REPLIES))
def test_check_rejects_a_batch_reply_that_asks_the_wrong_files(tmp_path, weakened):
    scenario = load_scenario(BATCH_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    old, new = WEAKENED_BATCH_REPLIES[weakened]
    assert old in COMPLIANT_BATCH_REPLY
    reply = COMPLIANT_BATCH_REPLY.replace(old, new)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, reply)


def test_check_rejects_a_batch_labelled_before_the_questions_are_answered(tmp_path, label_tool):
    scenario = load_scenario(BATCH_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "event" / "team-1.png", "--variant", "generated").returncode == 0

    with pytest.raises(AssertionError):
        check(scenario, project, digests, COMPLIANT_BATCH_REPLY)


# --- Site integration: a canned React project ------------------------------------
#
# The component and page the agent would write, adapted by hand from
# references/site.md; each broken variant must be rejected.

SITE_SCENARIO = "react-site-component"

REACT_COMPONENT = """\
import { useEffect, useId, useRef, useState } from "react";
import "./AiLabel.css";

export default function AiLabel({ label, background = "light", details }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const pinned = useRef(false);
  const toggle = useRef(null);
  const src = background === "dark" ? "/ai-basic-white.svg" : "/ai-basic-black.svg";
  const icon = <img className="eu-ai-label__icon" src={src} alt="" width="32" height="32" />;
  const wrapper = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key !== "Escape") return;
      const focusInside = wrapper.current.contains(document.activeElement);
      pinned.current = false;
      setOpen(false);
      if (focusInside) toggle.current.focus();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  if (!details) {
    return (
      <span className="eu-ai-label">
        {icon}
        <span className="eu-ai-label__text">{label}</span>
      </span>
    );
  }
  return (
    <span
      ref={wrapper}
      className="eu-ai-label"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => { if (!pinned.current) setOpen(false); }}
    >
      <button
        ref={toggle}
        type="button"
        className="eu-ai-label__toggle"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => { pinned.current = !pinned.current; setOpen(pinned.current); }}
      >
        {icon}
        <span className="eu-ai-label__text">{label}</span>
      </button>
      <span className="eu-ai-label__details" id={id} hidden={!open}>{details}</span>
    </span>
  );
}
"""

REACT_PAGE = """\
import "./App.css";
import AiLabel from "./components/AiLabel.jsx";

export default function App() {
  return (
    <main className="post">
      <h1>Five trails for an autumn weekend</h1>
      <img className="hero" src="/hero.png" alt="A mountain trail among yellow larches" />
      <AiLabel label="Generated with AI" details="The hero image of this post was generated with AI." />
      <p>From the lakeside loop to the ridge walk, here are five routes for every pace.</p>
    </main>
  );
}
"""

SITE_REPLY = (
    "Added src/components/AiLabel.jsx and copied the official icons to public/ai-basic-black.svg "
    "and public/ai-basic-white.svg. It is used below the hero image in src/App.jsx."
)


def site_project(tmp_path: Path, component: str = REACT_COMPONENT, page: str = REACT_PAGE, icons: dict | None = None):
    """The React scenario's project after a (canned) site integration."""
    scenario = load_scenario(SITE_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    (project / "src" / "components").mkdir()
    (project / "src" / "components" / "AiLabel.jsx").write_text(component)
    (project / "src" / "components" / "AiLabel.css").write_text(".eu-ai-label { display: inline-flex; }\n")
    (project / "src" / "App.jsx").write_text(page)
    for name, data in (icons or {n: (ICONS_DIR / n).read_bytes() for n in ("ai-basic-black.svg", "ai-basic-white.svg")}).items():
        (project / "public" / name).write_bytes(data)
    return scenario, project, digests


def test_check_accepts_a_react_label_component(tmp_path):
    scenario, project, digests = site_project(tmp_path)

    check(scenario, project, digests, SITE_REPLY)


BROKEN_REACT_COMPONENTS = {
    "no aria-expanded": ("        aria-expanded={open}\n", ""),
    "no aria-controls": ("        aria-controls={id}\n", ""),
    "second layer not on a button": ("<button\n", "<span\n"),
    "Escape does not close it": ('event.key !== "Escape"', 'event.key !== "Enter"'),
    "hard-coded text label": ('<span className="eu-ai-label__text">{label}</span>', '<span className="eu-ai-label__text">Generated with AI</span>'),
    "icon without alt text": (' alt=""', ""),
    "no White Icon Colour for dark backgrounds": ('background === "dark" ? "/ai-basic-white.svg" : ', ""),
    "icon loaded from the plugin": ('"/ai-basic-black.svg"', f'"{ICONS_DIR}/ai-basic-black.svg"'),
    "hover does not open it": ("      onMouseEnter={() => setOpen(true)}\n", ""),
    "second layer never hidden": (" hidden={!open}", ""),
    "a click does nothing": ("onClick={() => { pinned.current = !pinned.current; setOpen(pinned.current); }}", "onClick={() => {}}"),
    "not valid JavaScript": ("export default function AiLabel", "THIS IS NOT VALID JAVASCRIPT !!!!\nexport default function AiLabel"),
    "Escape only with focus inside": ("document.addEventListener", "wrapper.current.addEventListener"),
}


@pytest.mark.parametrize("broken", sorted(BROKEN_REACT_COMPONENTS))
def test_check_rejects_a_broken_react_label_component(tmp_path, broken):
    old, new = BROKEN_REACT_COMPONENTS[broken]
    assert old in REACT_COMPONENT
    scenario, project, digests = site_project(tmp_path, component=REACT_COMPONENT.replace(old, new))

    with pytest.raises(AssertionError):
        check(scenario, project, digests, SITE_REPLY)


BROKEN_REACT_PAGES = {
    "component not used": ('      <AiLabel label="Generated with AI" details="The hero image of this post was generated with AI." />\n', ""),
    "no second layer": (' details="The hero image of this post was generated with AI."', ""),
    "no text label": ('label="Generated with AI"', 'label=""'),
    "a page line lost": ("      <h1>Five trails for an autumn weekend</h1>\n", ""),
    "component not imported": ('import AiLabel from "./components/AiLabel.jsx";\n', ""),
}


@pytest.mark.parametrize("broken", sorted(BROKEN_REACT_PAGES))
def test_check_rejects_a_react_page_not_using_the_component_as_asked(tmp_path, broken):
    old, new = BROKEN_REACT_PAGES[broken]
    assert old in REACT_PAGE
    scenario, project, digests = site_project(tmp_path, page=REACT_PAGE.replace(old, new))

    with pytest.raises(AssertionError):
        check(scenario, project, digests, SITE_REPLY)


@pytest.mark.parametrize(
    "icons",
    [
        pytest.param({"ai-basic-black.svg": (ICONS_DIR / "ai-basic-black.svg").read_bytes()}, id="white icon not copied"),
        pytest.param(
            {
                "ai-basic-black.svg": b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="9"/></svg>',
                "ai-basic-white.svg": (ICONS_DIR / "ai-basic-white.svg").read_bytes(),
            },
            id="black icon redrawn",
        ),
    ],
)
def test_check_rejects_icons_not_copied_from_the_official_set(tmp_path, icons):
    scenario, project, digests = site_project(tmp_path, icons=icons)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, SITE_REPLY)


def test_check_rejects_a_site_integration_that_gives_a_verdict(tmp_path):
    scenario, project, digests = site_project(tmp_path)
    reply = SITE_REPLY + "\n\nDisclosure Outcome: Required\nIcon Variant: Basic\n"

    with pytest.raises(AssertionError):
        check(scenario, project, digests, reply)


# --- References after a Labelled Copy: canned projects --------------------------------
#
# The project as the agent leaves it after labelling the hero image of the
# Markdown site, written by hand from ticket 10; each broken variant must be
# rejected.

REFERENCES_SCENARIO = "markdown-site-references"
UPDATED_POSTS = {
    "content/posts/trails.md": (
        "![A trail among yellow larches](/images/hero.png)",
        "![A trail among yellow larches (Image generated with AI)](/images/hero.ai-label.png)",
    ),
    "content/posts/trails.it.md": (
        "![Un sentiero tra i larici gialli](/images/hero.png)",
        "![Un sentiero tra i larici gialli (Immagine generata con IA)](/images/hero.ai-label.png)",
    ),
}
REFERENCES_REPLY = (
    "Labelled static/images/hero.png: static/images/hero.ai-label.png (Fully AI-Generated, top-right).\n"
    "References updated: content/posts/trails.md line 7 and content/posts/trails.it.md line 7.\n"
    "References not updated: layouts/partials/og-image.html line 1 builds the path from "
    "{{ .Site.BaseURL }}; change hero.png to hero.ai-label.png there by hand."
)


def referenced_project(tmp_path: Path, label_tool, edits: dict[str, tuple[str, str]] = UPDATED_POSTS):
    scenario = load_scenario(REFERENCES_SCENARIO)
    project, digests = checked_project(tmp_path, scenario)
    result = label_tool("apply", project / "static/images/hero.png", "--variant", "generated")
    assert result.returncode == 0, result.json
    for name, (old, new) in edits.items():
        page = project / name
        assert old in page.read_text()
        page.write_text(page.read_text().replace(old, new))
    return scenario, project, digests


def test_check_accepts_references_pointed_to_the_labelled_copy(tmp_path, label_tool):
    scenario, project, digests = referenced_project(tmp_path, label_tool)

    check(scenario, project, digests, REFERENCES_REPLY)


BROKEN_REFERENCES = {
    "path not updated": {"content/posts/trails.md": (
        "![A trail among yellow larches](/images/hero.png)",
        "![A trail among yellow larches (Image generated with AI)](/images/hero.png)",
    )},
    "no AI mention in the alt text": {"content/posts/trails.md": (
        "![A trail among yellow larches](/images/hero.png)",
        "![A trail among yellow larches](/images/hero.ai-label.png)",
    )},
    "English mention in the Italian post": {"content/posts/trails.it.md": (
        "![Un sentiero tra i larici gialli](/images/hero.png)",
        "![Un sentiero tra i larici gialli (Image generated with AI)](/images/hero.ai-label.png)",
    )},
    "description dropped": {"content/posts/trails.md": (
        "![A trail among yellow larches](/images/hero.png)",
        "![Image generated with AI](/images/hero.ai-label.png)",
    )},
    "path to no file": {"content/posts/trails.md": (
        "![A trail among yellow larches](/images/hero.png)",
        "![A trail among yellow larches (Image generated with AI)](/hero.ai-label.png)",
    )},
    "a body line dropped": {"content/posts/trails.md": (
        "From the lakeside loop to the ridge walk, here are five routes for every pace.\n", "",
    )},
}


@pytest.mark.parametrize("broken", sorted(BROKEN_REFERENCES))
def test_check_rejects_badly_updated_references(tmp_path, label_tool, broken):
    scenario, project, digests = referenced_project(tmp_path, label_tool, {**UPDATED_POSTS, **BROKEN_REFERENCES[broken]})
    if broken == "a body line dropped":  # on top of a correct update
        page = project / "content/posts/trails.md"
        page.write_text(page.read_text().replace(*UPDATED_POSTS["content/posts/trails.md"]))

    with pytest.raises(AssertionError):
        check(scenario, project, digests, REFERENCES_REPLY)


def test_check_rejects_an_unreported_or_edited_dynamic_reference(tmp_path, label_tool):
    scenario, project, digests = referenced_project(tmp_path, label_tool)
    with pytest.raises(AssertionError):
        check(scenario, project, digests, REFERENCES_REPLY.split("\nReferences not updated")[0])

    og = project / "layouts/partials/og-image.html"
    og.write_text(og.read_text().replace("hero.png", "hero.ai-label.png"))
    with pytest.raises(AssertionError):
        check(scenario, project, digests, REFERENCES_REPLY)


# --- Videos: canned Labelled Copies and replies ------------------------------------
#
# The scenarios' videos encoded as make_project encodes them, labelled (or
# not) by label_tool or by hand; each broken variant must be rejected.

VIDEO_REPLY = (
    "Labelled clip.mp4: clip.ai-label.mp4, Fully AI-Generated, top-right, shown continuously. "
    "The video stream was re-encoded to incorporate the Label."
)


def video_project(tmp_path: Path, name: str) -> tuple[dict, Path, dict[str, str], Path]:
    scenario = load_scenario(name)
    project, digests = checked_project(tmp_path, scenario)
    return scenario, project, digests, project / next(iter(scenario["files"]))


def video_copy(video: Path) -> Path:
    return video.with_name(f"{video.stem}.ai-label{video.suffix}")


def apply_video(label_tool, video: Path, *args: str) -> None:
    result = label_tool("video-apply", video, "--variant", "generated", "--corner", "tr", *args)
    assert result.returncode == 0, result.json


@needs_ffmpeg
def test_check_accepts_a_labelled_video(tmp_path, label_tool):
    scenario, project, digests, video = video_project(tmp_path, "video-fully-generated")
    apply_video(label_tool, video)

    check(scenario, project, digests, VIDEO_REPLY)


@needs_ffmpeg
@pytest.mark.parametrize("args", [
    pytest.param(("--variant", "modified"), id="other variant"),
    pytest.param(("--visibility", "periodic", "--window", "0.5", "--every", "1"), id="periodic, not continuous"),
    pytest.param(None, id="no labelled copy"),
])
def test_check_rejects_a_video_not_labelled_as_asked(tmp_path, label_tool, args):
    scenario, project, digests, video = video_project(tmp_path, "video-fully-generated")
    if args is not None:
        apply_video(label_tool, video, *args)  # a later --variant overrides the first

    with pytest.raises(AssertionError):
        check(scenario, project, digests, VIDEO_REPLY)


@needs_ffmpeg
def test_check_rejects_a_rectangle_in_place_of_the_video_icon(tmp_path):
    scenario, project, digests, video = video_project(tmp_path, "video-fully-generated")
    ffmpeg("-i", video, "-vf", "drawbox=x=440:y=12:w=180:h=36:color=black:t=fill",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", video_copy(video))

    with pytest.raises(AssertionError):
        check(scenario, project, digests, VIDEO_REPLY)


@needs_ffmpeg
def test_check_rejects_a_labelled_video_converted_to_another_codec(tmp_path, label_tool):
    scenario, project, digests, video = video_project(tmp_path, "video-fully-generated")
    apply_video(label_tool, video)
    converted = tmp_path / "converted.mp4"
    ffmpeg("-i", video_copy(video), "-c:v", "mpeg4", "-q:v", "1", converted)
    shutil.move(converted, video_copy(video))

    with pytest.raises(AssertionError):
        check(scenario, project, digests, VIDEO_REPLY)


PERIODIC_REPLY = (
    "Labelled keynote.mp4: keynote.ai-label.mp4, Fully AI-Generated, top-right. It is 65 s long, so the "
    "Label shows periodically: for 5 seconds from the start, then for 5 seconds every 60 seconds."
)


@needs_ffmpeg
@pytest.mark.parametrize("visibility, accepted", [("auto", True), ("continuous", False)])
def test_check_judges_when_a_long_video_shows_the_label(tmp_path, label_tool, visibility, accepted):
    scenario, project, digests, video = video_project(tmp_path, "video-long-periodic")
    apply_video(label_tool, video, "--visibility", visibility)

    if accepted:
        check(scenario, project, digests, PERIODIC_REPLY)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, PERIODIC_REPLY)


# A Creative Work video: the Label is incorporated all the same, and no caption is offered.

SATIRE_VIDEO_REPLY = (
    "satire-short.mp4 is a satirical work, but a video has no caption: the Label is part of its picture. "
    "Labelled it: satire-short.ai-label.mp4, Fully AI-Generated, top-right, shown continuously."
)


@needs_ffmpeg
@pytest.mark.parametrize("extra, accepted", [
    ("", True),
    ("\n\nWould you like a caption below it on your channel page as well?", False),
    ("\n\nI can also add a caption with the Basic icon below the video.", False),
], ids=["no caption offered", "asks about a caption", "offers a caption"])
def test_check_wants_no_caption_offered_for_a_creative_work_video(tmp_path, label_tool, extra, accepted):
    scenario, project, digests, video = video_project(tmp_path, "video-satirical-short-film")
    apply_video(label_tool, video)

    if accepted:
        check(scenario, project, digests, SATIRE_VIDEO_REPLY + extra)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, SATIRE_VIDEO_REPLY + extra)


# A video on no validated path: nothing written, the reason given, a question back.

UNSUPPORTED_VIDEO_REPLY = """\
old-clip.mp4 can't be labelled as it is: its video codec, MPEG-4 Part 2 (mpeg4), has no validated
labelling path in MP4, which supports H.264 and HEVC. Nothing was written or converted.

How would you like to proceed? You could convert it to H.264 yourself and I'll label the result.
"""

UNSUPPORTED_OPTIONS = (
    "Options:\n"
    "1. Convert it to H.264 yourself first. Tell me when that's done and I'll label the converted file.\n"
    "2. Keep it unlabelled for now.\n"
)

WEAKENED_UNSUPPORTED_REPLIES = {
    "no question": ("How would you like to proceed? You could", "You could"),
    "options without an invitation": (
        "How would you like to proceed? You could convert it to H.264 yourself and I'll label the result.\n",
        UNSUPPORTED_OPTIONS.replace(" Tell me when that's done and I'll label the converted file.", ""),
    ),
    "no reason given": ("its video codec, MPEG-4 Part 2 (mpeg4), has", "it has"),
}


@needs_ffmpeg
@pytest.mark.parametrize("options", [False, True], ids=["a question", "options to pick from"])
def test_check_accepts_explaining_an_unsupported_video(tmp_path, options):
    scenario, project, digests, _ = video_project(tmp_path, "video-unsupported-codec")
    reply = UNSUPPORTED_VIDEO_REPLY
    if options:
        reply = reply.replace(
            "How would you like to proceed? You could convert it to H.264 yourself and I'll label the result.\n",
            UNSUPPORTED_OPTIONS,
        )

    check(scenario, project, digests, reply)


@needs_ffmpeg
@pytest.mark.parametrize("weakened", sorted(WEAKENED_UNSUPPORTED_REPLIES))
def test_check_rejects_a_weak_reply_on_an_unsupported_video(tmp_path, weakened):
    scenario, project, digests, _ = video_project(tmp_path, "video-unsupported-codec")
    old, new = WEAKENED_UNSUPPORTED_REPLIES[weakened]
    assert old in UNSUPPORTED_VIDEO_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, UNSUPPORTED_VIDEO_REPLY.replace(old, new))


@needs_ffmpeg
@pytest.mark.parametrize("written", ["old-clip.ai-label.mp4", "old-clip.h264.mp4", "old-clip.mkv"])
def test_check_rejects_converting_an_unsupported_video(tmp_path, written):
    scenario, project, digests, video = video_project(tmp_path, "video-unsupported-codec")
    ffmpeg("-i", video, "-c:v", "libx264", "-pix_fmt", "yuv420p", project / written)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, UNSUPPORTED_VIDEO_REPLY)


# A video whose origin nobody stated: the skill asks.

ASKS_VIDEO_ORIGIN_REPLY = "Before I label clip.mp4: did AI generate it from scratch, or did it edit real footage?"


@needs_ffmpeg
def test_check_accepts_asking_how_ai_was_involved_in_a_video(tmp_path):
    scenario, project, digests, _ = video_project(tmp_path, "video-unknown-origin")

    check(scenario, project, digests, ASKS_VIDEO_ORIGIN_REPLY)


@needs_ffmpeg
def test_check_rejects_labelling_a_video_before_the_origin_is_known(tmp_path, label_tool):
    scenario, project, digests, video = video_project(tmp_path, "video-unknown-origin")
    apply_video(label_tool, video)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_VIDEO_ORIGIN_REPLY)


# When the Label shows, unsaid: the skill asks, and says what the default does.

ASKS_VISIBILITY_REPLY = """\
One question before I label clip.mp4: should the Label show continuously, for the whole video,
or periodically, for a few seconds at regular intervals? Without a preference, videos up to 60
seconds show it continuously and longer ones periodically, so clip.mp4 would show it throughout.
"""

VISIBILITY_QUESTION = (
    "should the Label show continuously, for the whole video,\n"
    "or periodically, for a few seconds at regular intervals?"
)
WEAKENED_VISIBILITY_REPLIES = {
    "no periodic option": (
        VISIBILITY_QUESTION + " Without a preference, videos up to 60\nseconds show it continuously and longer ones periodically,",
        "should the Label show continuously, for the whole video? Without a preference, videos up to 60 seconds show it continuously,",
    ),
    "no default given": (
        "Without a preference, videos up to 60\nseconds show it continuously and longer ones periodically, so", "So",
    ),
    "no question": (VISIBILITY_QUESTION, "the Label can show continuously or periodically."),
}


@needs_ffmpeg
def test_check_accepts_asking_when_a_video_shows_the_label(tmp_path):
    scenario, project, digests, _ = video_project(tmp_path, "video-asks-visibility")

    check(scenario, project, digests, ASKS_VISIBILITY_REPLY)


@needs_ffmpeg
@pytest.mark.parametrize("weakened", sorted(WEAKENED_VISIBILITY_REPLIES))
def test_check_rejects_a_weak_visibility_question(tmp_path, weakened):
    scenario, project, digests, _ = video_project(tmp_path, "video-asks-visibility")
    old, new = WEAKENED_VISIBILITY_REPLIES[weakened]
    assert old in ASKS_VISIBILITY_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_VISIBILITY_REPLY.replace(old, new))


@needs_ffmpeg
def test_check_rejects_labelling_a_video_before_the_visibility_is_settled(tmp_path, label_tool):
    scenario, project, digests, video = video_project(tmp_path, "video-asks-visibility")
    apply_video(label_tool, video)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_VISIBILITY_REPLY)


# --- An Existing Label in a video: an on-screen notice ------------------------------

ASKS_ABOUT_ON_SCREEN_NOTICE_REPLY = """\
clip.mp4 already shows a Label this plugin didn't add: "Generated with AI", at the bottom centre
of the picture, in every frame I looked at (0.2 s, 0.6 s, 1.0 s, 1.4 s and 1.8 s). Its wording
matches the fully AI-generated wording you chose. Frames I didn't look at may differ.

Should I add the EU Icon at the top-right anyway, or leave clip.mp4 as it is?
"""

WEAKENED_ON_SCREEN_NOTICE_REPLIES = {
    "doesn't say what it says": ('"Generated with AI", at', "a notice, at"),
    "no place on the picture": ("at the bottom centre\nof the picture, ", ""),
    "no frame times": (
        "in every frame I looked at (0.2 s, 0.6 s, 1.0 s, 1.4 s and 1.8 s)", "in the frames I looked at",
    ),
    "doesn't ask": (
        "Should I add the EU Icon at the top-right anyway, or leave clip.mp4 as it is?", "I left clip.mp4 as it is.",
    ),
}


@needs_ffmpeg
def test_the_on_screen_notice_fixture_shows_its_notice(tmp_path):
    from videos import frame_images

    _, _, _, video = video_project(tmp_path, "existing-label-video-notice")
    frame = frame_images(video)[0]
    width, height = frame.size
    bottom, top = frame.crop((0, height * 3 // 4, width, height)), frame.crop((0, 0, width, height // 4))
    # Antialiased white text with a black outline takes many colours; flat colour, a few after encoding.
    assert len(bottom.getcolors(1 << 16)) > 10, "no notice at the bottom of the picture"
    assert len(top.getcolors(1 << 16)) <= 3, "the top of the picture is not flat"


@needs_ffmpeg
def test_check_accepts_asking_about_an_on_screen_notice(tmp_path):
    scenario, project, digests, _ = video_project(tmp_path, "existing-label-video-notice")

    check(scenario, project, digests, ASKS_ABOUT_ON_SCREEN_NOTICE_REPLY)


@needs_ffmpeg
@pytest.mark.parametrize("weakened", sorted(WEAKENED_ON_SCREEN_NOTICE_REPLIES))
def test_check_rejects_a_weak_reply_on_an_on_screen_notice(tmp_path, weakened):
    scenario, project, digests, _ = video_project(tmp_path, "existing-label-video-notice")
    old, new = WEAKENED_ON_SCREEN_NOTICE_REPLIES[weakened]
    assert old in ASKS_ABOUT_ON_SCREEN_NOTICE_REPLY

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_ON_SCREEN_NOTICE_REPLY.replace(old, new))


@needs_ffmpeg
def test_check_rejects_labelling_a_video_before_the_user_answers_about_its_notice(tmp_path, label_tool):
    scenario, project, digests, video = video_project(tmp_path, "existing-label-video-notice")
    apply_video(label_tool, video)

    with pytest.raises(AssertionError):
        check(scenario, project, digests, ASKS_ABOUT_ON_SCREEN_NOTICE_REPLY)




# --- An Existing Label in an answer on whether a Label is required ---------------

REQUIRED_WITH_EXISTING_LABEL_REPLY = """\
I can't tell you whether the law requires a Label for post.md: that depends on facts and a legal
judgement that are yours to make. The official sources are:

- the Guidelines on Article 50: https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations
- the Code of Practice on transparency of AI-generated content: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
- the AI Act Service Desk: https://ai-act-service-desk.ec.europa.eu/

post.md already ends with its own disclaimer: the last line, below the rule, reads
"This article was generated by AI."

Would you like me to add the EU Icon to it?

This is not legal advice.
"""


@pytest.mark.parametrize("old, new, accepted", [
    ("", "", True),
    ('reads\n"This article was generated by AI."', "is a disclaimer.", False),
    ("Would you like me to add the EU Icon to it?", "The disclaimer is enough on its own, so no Label is needed.", False),
], ids=["names it", "doesn't say what it says", "judges it"])
def test_check_wants_the_existing_label_named_when_asked_if_a_label_is_required(tmp_path, old, new, accepted):
    scenario = load_scenario("existing-label-asks-if-required")
    project, digests = checked_project(tmp_path, scenario)
    reply = REQUIRED_WITH_EXISTING_LABEL_REPLY.replace(old, new) if old else REQUIRED_WITH_EXISTING_LABEL_REPLY

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


# --- A Marking: evidence for the Icon Variant, embedded offline ---------------------
#
# The marking scenarios embed their Marking when the project is written; the
# unknown-origin ones carry none, so they still test asking from no evidence.

MARKING_SCENARIOS = sorted(n for n, _ in load_scenarios() if n.startswith("marking-"))
PRECISE_CODES = {"trainedAlgorithmicMedia": "generated", "compositeWithTrainedAlgorithmicMedia": "modified"}


def test_there_are_six_marking_scenarios():
    assert len(MARKING_SCENARIOS) == 6, MARKING_SCENARIOS


@pytest.mark.parametrize("name", MARKING_SCENARIOS + ["unknown-origin", "video-unknown-origin"])
def test_each_scenario_file_carries_the_marking_it_names(tmp_path, label_tool, name):
    scenario = load_scenario(name)
    if any("video" in spec for spec in scenario["files"].values()) and not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are not installed")
    project, _ = checked_project(tmp_path, scenario)
    for file, spec in scenario["files"].items():
        marking = spec.get("marking", {})
        result = label_tool("marking", project / file)
        assert result.returncode == 0, result.json
        report = result.json
        code = marking.get("c2pa") or marking.get("xmp")
        assert report["settled"] == PRECISE_CODES.get(code), (file, report)
        if "c2pa" in marking:
            assert [s["source"] for s in report["signals"]] == ["c2pa"], report
            assert report["signals"][0]["validation_state"] in ("Valid", "Trusted"), report
        if "xmp" in marking:
            assert [s["source"] for s in report["signals"]] == ["xmp"], report
        if "png_text" in marking:
            assert report["settled"] is None and report["quotes"], report
            for key in marking["png_text"]:
                assert any(key in quote for quote in report["quotes"]), report
        if not marking:
            assert report["signals"] == [], f"{file} carries a Marking it doesn't name: {report}"


VAGUE_MARKING_REPLY = """\
render.png's metadata holds a "parameters" text chunk, as Stable Diffusion writes it:
"a lighthouse at dusk Steps: 30, Sampler: Euler a, Model: sd_xl_base_1.0".

That names a generator but not how it was used: did AI create render.png from scratch, or edit a real photo?
"""


@pytest.mark.parametrize("old, new, accepted", [
    ("", "", True),
    ('holds a "parameters" text chunk, as Stable Diffusion writes it:\n'
     '"a lighthouse at dusk Steps: 30, Sampler: Euler a, Model: sd_xl_base_1.0"', "says nothing useful", False),
    ("did AI create render.png from scratch, or edit a real photo?", "I'll wait.", False),
], ids=["quotes and asks", "doesn't quote", "doesn't ask"])
def test_check_wants_a_vague_marking_quoted_in_the_origin_question(tmp_path, old, new, accepted):
    scenario = load_scenario("marking-vague-png-parameters")
    project, digests = checked_project(tmp_path, scenario)
    reply = VAGUE_MARKING_REPLY.replace(old, new) if old else VAGUE_MARKING_REPLY

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


MARKED_BATCH_REPLY = """\
hero-1.png and hero-2.png carry a Marking that says they were generated from scratch, so they get the
Fully AI-Generated icon. One question before I label the batch:

Were crowd.png and stage.png generated from scratch, or are they real photos edited with AI?
"""


@pytest.mark.parametrize("old, new, accepted", [
    ("", "", True),
    ("Were crowd.png and stage.png generated", "Were hero-1.png, crowd.png and stage.png generated", False),
    ("Were crowd.png and stage.png generated", "Were the other two generated", False),
], ids=["asks only the unmarked", "asks a marked file", "names no file"])
def test_check_wants_a_marked_batch_to_ask_only_about_the_unmarked_files(tmp_path, old, new, accepted):
    scenario = load_scenario("marking-mixed-batch")
    project, digests = checked_project(tmp_path, scenario)
    reply = MARKED_BATCH_REPLY.replace(old, new) if old else MARKED_BATCH_REPLY

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)


MISMATCH_REPLY = """\
Labelled photo.png as Partially AI-Modified, as you said: photo.ai-label.png, top-right, black icon, no plate.
The file's XMP says trainedAlgorithmicMedia, which is Fully AI-Generated; I labelled it as you said.
"""


@pytest.mark.parametrize("old, new, accepted", [
    ("", "", True),
    ("The file's XMP says trainedAlgorithmicMedia, which is Fully AI-Generated; I labelled it as you said.\n", "", False),
    ("The file's XMP says trainedAlgorithmicMedia, which is Fully AI-Generated; I labelled it as you said.\n",
     "I didn't look at its metadata. The Labelled Copy no longer carries the original's Marking.\n", False),
    ("The file's XMP says trainedAlgorithmicMedia, which is Fully AI-Generated; I labelled it as you said.\n",
     "The file's XMP Marking agrees. The Labelled Copy no longer carries the original's Marking.\n", False),
], ids=["states the mismatch", "keeps quiet about it", "mentions only metadata", "calls it agreement"])
def test_check_wants_a_mismatch_with_the_users_word_stated(tmp_path, label_tool, old, new, accepted):
    scenario = load_scenario("marking-user-contradicts")
    project, digests = checked_project(tmp_path, scenario)
    assert label_tool("apply", project / "photo.png", "--variant", "modified").returncode == 0
    reply = MISMATCH_REPLY.replace(old, new) if old else MISMATCH_REPLY

    if accepted:
        check(scenario, project, digests, reply)
    else:
        with pytest.raises(AssertionError):
            check(scenario, project, digests, reply)
