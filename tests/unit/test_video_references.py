"""`label_tool references <video>`: point a project's video players to a video's Labelled Copy.

Each test builds a project on disk with the original video, its Labelled Copy
next to it and pages that use it, runs `references <video> --root <project>`
as a subprocess and reads the JSON and the pages it wrote. `references` only
reads the files' names, not their streams, so the videos here are a few bytes
and FFmpeg is never needed.

Only literal `<video src>` and `<source src>` inside a `<video>` change. An
image use (`<img>`, a `<source>` inside `<picture>`, a Markdown image), a link,
an import, a computed path or a URL is reported, never changed, and no alt
text or other text around the player is ever written.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import run_label_tool
from helpers import digests, sha256


def write(project: Path, relative: str, text: str) -> Path:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def video(project: Path, relative: str, labelled: bool = True) -> Path:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"original video")
    if labelled:
        path.with_name(f"{path.stem}.ai-label{path.suffix}").write_bytes(b"labelled video")
    return path


@pytest.fixture
def project(tmp_path) -> Path:
    root = tmp_path / "site"
    root.mkdir()
    return root


def references(project: Path, original: Path, *extra: str):
    return run_label_tool("references", original, "--root", project, *extra, cwd=project)


def test_a_direct_video_src_points_to_the_labelled_copy(project):
    original = video(project, "media/clip.mp4")
    page = write(project, "index.html", '<video src="media/clip.mp4" controls poster="media/still.png"></video>\n')

    result = references(project, original, "--apply")

    assert result.returncode == 0, result.json
    assert result.json["media"] == "video"
    assert page.read_text() == '<video src="media/clip.ai-label.mp4" controls poster="media/still.png"></video>\n'
    assert result.json["applied"] == [{
        "file": "index.html", "line": 1, "kind": "html-video",
        "reference": "media/clip.mp4", "replacement": "media/clip.ai-label.mp4",
    }]
    assert result.json["alt_updated"] == [] and result.json["needs_hand_edit"] == []
    assert (project / "media" / "clip.mp4").read_bytes() == b"original video"


PLAYER = """\
<figure>
  <video controls poster="/media/still.png" aria-describedby="clip-desc">
    <source src="/media/clip.mp4" type="video/mp4">
    <source src="/media/clip.webm" type="video/webm">
    <track kind="subtitles" src="/media/clip.en.vtt" srclang="en" label="English">
    <track kind="descriptions" src="/media/clip.desc.vtt" srclang="en">
  </video>
  <figcaption id="clip-desc">A walk along the lake at dawn. <a href="/media/clip.mp4">Download the video</a></figcaption>
</figure>
"""


def test_a_source_inside_a_video_changes_and_its_tracks_descriptions_and_links_stay(project):
    original = video(project, "public/media/clip.mp4")
    page = write(project, "index.html", PLAYER)

    result = references(project, original, "--apply")

    assert result.returncode == 0, result.json
    # Only the MP4 source changes: the WebM source is another file, the
    # download link leads to the original, the tracks, poster and caption stay.
    assert page.read_text() == PLAYER.replace(
        '<source src="/media/clip.mp4"', '<source src="/media/clip.ai-label.mp4"')
    assert [(a["line"], a["kind"]) for a in result.json["applied"]] == [(3, "html-video-source")]
    assert [(u["line"], u["kind"]) for u in result.json["updatable"]] == [(3, "html-video-source"), (8, "link")]
    assert all(set(u) == {"file", "line", "reference", "kind", "replacement"} for u in result.json["updatable"])


def test_image_uses_of_the_video_file_and_unrelated_files_stay_untouched(project):
    """A `<source>` inside `<picture>`, an `<img>` and a Markdown image show an
    image: they are reported, never pointed to the video's copy."""
    original = video(project, "media/clip.mp4")
    picture = write(project, "picture.html",
                    '<picture>\n  <source srcset="media/clip.mp4" type="video/mp4">\n'
                    '  <img src="media/clip.mp4" alt="A lake at dawn">\n</picture>\n')
    post = write(project, "post.md", "![A lake at dawn](media/clip.mp4)\n\n[Watch it](media/clip.mp4)\n")
    write(project, "other.html", '<video src="media/other.mp4"></video>\n')
    before = digests(project)

    result = references(project, original, "--apply")

    assert result.returncode == 0, result.json
    assert digests(project) == before
    assert sorted((n["file"], n["line"], n["reason"]) for n in result.json["not_updatable"]) == [
        ("picture.html", 2, "not_a_player"), ("picture.html", 3, "not_a_player"), ("post.md", 1, "not_a_player"),
    ]
    assert result.json["applied"] == [] and result.json["alt_updated"] == []
    assert picture.read_text().count('alt="A lake at dawn"') == 1 and "AI" not in post.read_text()


def test_dynamic_imported_component_and_external_uses_are_reported_not_changed(project):
    original = video(project, "src/assets/clip.mp4")
    write(project, "src/Hero.jsx",
          'import clip from "./assets/clip.mp4";\n'
          'export const Hero = () => <video src={clip} controls />;\n'
          'export const Promo = () => <Video src="/src/assets/clip.mp4" />;\n')
    write(project, "src/page.vue", '<template><video :src="`${base}/assets/clip.mp4`"></video></template>\n')
    write(project, "index.html", '<video src="https://cdn.example.com/clip.mp4"></video>\n')
    write(project, "data/videos.json", '{"hero": "/src/assets/clip.mp4"}\n')
    before = digests(project)

    result = references(project, original, "--apply")

    assert result.returncode == 0, result.json
    assert digests(project) == before
    assert result.json["applied"] == []
    assert sorted((h["file"], h["line"], h["kind"]) for h in result.json["needs_hand_edit"]) == [
        ("data/videos.json", 1, "other"), ("src/Hero.jsx", 1, "other"), ("src/Hero.jsx", 3, "other"),
    ]
    assert all("alt" not in h["reason"] for h in result.json["needs_hand_edit"])
    assert sorted((n["file"], n["reason"]) for n in result.json["not_updatable"]) == [
        ("index.html", "external"), ("src/page.vue", "dynamic"),
    ]


def test_a_repeat_run_changes_nothing_and_finds_nothing_left(project):
    original = video(project, "media/clip.mp4")
    page = write(project, "index.html", '<video src="media/clip.mp4"></video>\n')
    first = references(project, original, "--apply")
    assert first.returncode == 0, first.json
    after_first = digests(project)

    again = references(project, original, "--apply")

    assert again.returncode == 0, again.json
    assert again.json["updatable"] == [] and again.json["applied"] == []
    assert digests(project) == after_first
    assert page.read_text() == '<video src="media/clip.ai-label.mp4"></video>\n'
    assert sorted(p.name for p in (project / "media").iterdir()) == ["clip.ai-label.mp4", "clip.mp4"]


def test_without_apply_nothing_changes(project):
    original = video(project, "media/clip.mp4")
    write(project, "index.html", '<video src="media/clip.mp4"></video>\n')
    before = digests(project)

    result = references(project, original)

    assert result.returncode == 0, result.json
    assert digests(project) == before
    assert result.json["updatable"] == [{"file": "index.html", "line": 1, "kind": "html-video",
                                         "reference": "media/clip.mp4", "replacement": "media/clip.ai-label.mp4"}]
    assert "applied" not in result.json


@pytest.mark.parametrize("flag", [["--wording", "generated"], ["--alt-mention", "Video generated with AI"]])
def test_a_video_takes_no_alt_text_mention(project, flag):
    original = video(project, "media/clip.mp4")
    write(project, "index.html", '<video src="media/clip.mp4"></video>\n')
    before = digests(project)

    result = references(project, original, "--apply", *flag)

    assert result.returncode != 0 and result.json["error"]["code"] == "usage"
    assert digests(project) == before


def test_a_video_without_a_labelled_copy_updates_nothing(project):
    """A failed, refused or skipped video leaves no Labelled Copy: no page changes."""
    original = video(project, "media/clip.mp4", labelled=False)
    write(project, "index.html", '<video src="media/clip.mp4"></video>\n')
    before = digests(project)

    result = references(project, original, "--apply")

    assert result.returncode != 0 and result.json["error"]["code"] == "no_labelled_copy"
    assert "video-apply" in result.json["error"]["message"]
    assert digests(project) == before


@pytest.mark.parametrize("suffix", [".mov", ".webm"])
def test_other_containers_go_through_the_same_rule(project, suffix):
    original = video(project, f"media/clip{suffix}")
    page = write(project, "index.html", f'<video controls>\n  <source src="media/clip{suffix}">\n</video>\n')

    result = references(project, original, "--apply")

    assert result.returncode == 0, result.json
    assert f'<source src="media/clip.ai-label{suffix}">' in page.read_text()


def test_a_source_outside_any_open_video_is_never_taken_for_a_player(project):
    """A self-closing JSX `<video />`, a commented-out `<video>` and an
    `<audio>` hold no video source: the `<source>` after them is reported."""
    original = video(project, "media/clip.mp4")
    write(project, "src/Clip.jsx",
          'export const A = () => <video src={other} />;\n'
          'export const B = () => <div><source src="/media/clip.mp4" /></div>;\n')
    write(project, "page.html", '<!-- <video> -->\n<div><source src="media/clip.mp4"></div>\n')
    write(project, "audio.html", '<audio controls>\n  <source src="media/clip.mp4">\n</audio>\n')
    before = digests(project)

    result = references(project, original, "--apply")

    assert result.returncode == 0, result.json
    assert digests(project) == before
    assert sorted((n["file"], n["reason"]) for n in result.json["not_updatable"]) == [
        ("audio.html", "not_a_player"), ("page.html", "not_a_player"), ("src/Clip.jsx", "not_a_player"),
    ]
