"""A batch holding videos: discovered through `score`, labelled one by one.

`score` on a folder or a list reports each video under `videos`, with its
`media`, so the agent sends it to `references/video.md`; existing Labelled
Copies of videos are skipped as for images. Each video then goes through its
own `video-apply`: a video that stops leaves the others' Labelled Copies as
they are, and a retry rerenders only the file it names. The copies are
measured by decoding them, independently of what label_tool says.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from helpers import sha256
from videos import changed, flat_mp4, frame_images, needs_ffmpeg, real_tools

pytestmark = needs_ffmpeg


def by_name(entries: list[dict]) -> dict[str, dict]:
    return {Path(e["path"]).name: e for e in entries}


def test_score_on_a_folder_lists_its_videos_beside_its_images(tmp_path, label_tool):
    folder = tmp_path / "shots"
    folder.mkdir()
    Image.new("RGB", (1000, 800), (200, 220, 240)).save(folder / "beach.png")
    flat_mp4(folder / "short.mp4", seconds=1)
    flat_mp4(folder / "Long.MOV", seconds=1)
    flat_mp4(folder / "archive.mkv", seconds=1)  # not a validated path: video-inspect says so, not score
    flat_mp4(folder / "old.ai-label.mp4", seconds=1)
    (folder / "notes.md").write_text("# not media\n")
    (folder / "sub").mkdir()
    flat_mp4(folder / "sub" / "inner.mp4", seconds=1)
    before = {p.name: sha256(p) for p in folder.iterdir() if p.is_file()}

    result = label_tool("score", folder)

    assert result.returncode == 0, result.json
    assert {n: e["media"] for n, e in by_name(result.json["images"]).items()} == {"beach.png": "image"}
    videos = by_name(result.json["videos"])
    assert {n: e["media"] for n, e in videos.items()} == {
        "Long.MOV": "video", "archive.mkv": "video", "short.mp4": "video",
    }
    assert Path(videos["short.mp4"]["path"]).resolve() == (folder / "short.mp4").resolve()
    assert result.json["refused"] == []
    skipped = by_name(result.json["skipped"])
    assert list(skipped) == ["old.ai-label.mp4"]
    assert skipped["old.ai-label.mp4"] == {**skipped["old.ai-label.mp4"], "reason": "labelled_copy", "media": "video"}
    # Discovery reads nothing deeper than the folder and writes nothing.
    assert {p.name: sha256(p) for p in folder.iterdir() if p.is_file()} == before


def test_score_on_a_list_of_videos_only_lists_them(tmp_path, label_tool):
    first = flat_mp4(tmp_path / "a.mp4", seconds=1)
    folder = tmp_path / "clips"
    folder.mkdir()
    flat_mp4(folder / "b.webm", seconds=1, codec="libvpx-vp9")

    result = label_tool("score", first, folder)

    assert result.returncode == 0, result.json
    assert result.json["images"] == []
    assert sorted(by_name(result.json["videos"])) == ["a.mp4", "b.webm"]


def test_one_video_that_stops_leaves_the_others_copies_intact(tmp_path, label_tool):
    """A short and a long video with the default visibility, and one that can't be kept as it is."""
    env = real_tools(tmp_path / "bin")
    good = flat_mp4(tmp_path / "good.mp4", seconds=1, size="640x360")
    other = flat_mp4(tmp_path / "other.mp4", seconds=61, size="160x90", rate=10)
    refused = flat_mp4(tmp_path / "archive.mkv", seconds=1, size="640x360")
    originals = {p.name: sha256(p) for p in (good, other, refused)}

    results = {p.name: label_tool("video-apply", p, "--variant", "generated", env=env) for p in (good, other, refused)}

    assert results["good.mp4"].returncode == 0, results["good.mp4"].json
    assert results["other.mp4"].returncode == 0, results["other.mp4"].json
    assert results["archive.mkv"].returncode != 0
    assert results["archive.mkv"].json["error"]["code"] == "preservation_unsupported"
    good_copy, other_copy = tmp_path / "good.ai-label.mp4", tmp_path / "other.ai-label.mp4"
    kept = sha256(other_copy)
    # Each successful copy decodes with its Label, timed for its own length:
    # the short one shows it to the last frame, the long one hides it between windows.
    source, labelled = frame_images(good), frame_images(good_copy)
    assert changed(source[0], labelled[0]) is not None and changed(source[-1], labelled[-1]) is not None
    source, labelled = frame_images(other), frame_images(other_copy)
    assert changed(source[0], labelled[0]) is not None
    assert changed(source[300], labelled[300]) is None, "the long video's Label is hidden at 30 s"
    assert not (tmp_path / "archive.ai-label.mkv").exists()
    assert {p.name: sha256(p) for p in (good, other, refused)} == originals

    # A retry of one file rerenders it alone.
    retry = label_tool("video-apply", good, "--variant", "generated", "--corner", "bl", env=env)

    assert retry.returncode == 0, retry.json
    left, top, right, bottom = changed(frame_images(good)[0], frame_images(good_copy)[0])
    assert left < 320 and top > 180, "the retried copy has its Label bottom-left"
    assert sha256(other_copy) == kept
    assert {p.name: sha256(p) for p in (good, other, refused)} == originals
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == [
        "archive.mkv", "good.ai-label.mp4", "good.mp4", "other.ai-label.mp4", "other.mp4",
    ]
