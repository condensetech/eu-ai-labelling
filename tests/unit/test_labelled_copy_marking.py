"""The Labelled Copy keeps the original's IPTC Marking, and nothing that would misidentify it.

`apply` and `video-apply` write the IPTC DigitalSourceType (and the IPTC AI
fields) of the original into the copy's XMP, unchanged: a non-AI Label doesn't
change what the content is. The copy gets no xmpMM:InstanceID nor
dcterms:provenance of the original, and no C2PA manifest: its hard binding no
longer matches. Each copy is read back with `marking`, as the skill reads it.
"""

from __future__ import annotations

import json
import shutil
import struct
import subprocess

import pytest

from helpers import LABEL_TOOL
from markings import (
    IPTC_SOURCE, XMP_UUID, jpeg, manifest, png, signed, tampered, webp, with_mp4_xmp, with_quicktime_xmp,
    xmp_packet,
)
from videos import flat_mp4, needs_ffmpeg, real_tools

SIZE = (640, 480)
AI_FIELDS = {"AISystemUsed": "Example Image Generator", "AISystemVersionUsed": "2.1",
             "AIPromptInformation": "a lighthouse at dusk &amp; gulls", "AIPromptWriterName": "Jane Doe"}
INSTANCE_ID = "xmp.iid:0f1e2d3c-original-instance"
PROVENANCE = "https://manifests.example.com/original.c2pa"

IMAGES = {"png": png, "jpg": jpeg, "webp": webp}


def marking(label_tool, path, env=None) -> dict:
    result = label_tool("marking", path, env=env)
    assert result.returncode == 0, result.json
    return result.json


def apply(label_tool, image) -> tuple[dict, object]:
    result = label_tool("apply", image, "--variant", "generated")
    assert result.returncode == 0, result.json
    return result.json, type(image)(result.json["labelled_copy"])


def full_xmp(code: str) -> bytes:
    return xmp_packet(code, ai=AI_FIELDS, instance_id=INSTANCE_ID, provenance=PROVENANCE)


# --- Images ------------------------------------------------------------------------


@pytest.mark.parametrize("suffix", IMAGES)
@pytest.mark.parametrize("code, variant", [("trainedAlgorithmicMedia", "generated"),
                                           ("compositeWithTrainedAlgorithmicMedia", "modified")])
def test_the_copy_keeps_the_digital_source_type_and_settles_the_same_variant(tmp_path, label_tool, suffix, code,
                                                                             variant):
    original = IMAGES[suffix](tmp_path / f"photo.{suffix}", xmp=full_xmp(code), size=SIZE)

    report, copy = apply(label_tool, original)

    assert marking(label_tool, original)["settled"] == variant
    read = marking(label_tool, copy)
    assert read["settled"] == variant
    assert [(s["source"], s["value"]) for s in read["signals"]] == [("xmp", code)], "the value stays as it is"
    assert report["marking_kept"]["DigitalSourceType"] == IPTC_SOURCE + code


@pytest.mark.parametrize("suffix", IMAGES)
def test_the_copy_keeps_the_iptc_ai_fields(tmp_path, label_tool, suffix):
    original = IMAGES[suffix](tmp_path / f"photo.{suffix}", xmp=full_xmp("trainedAlgorithmicMedia"), size=SIZE)

    report, copy = apply(label_tool, original)

    data = copy.read_bytes()
    for name, value in AI_FIELDS.items():
        assert f"<Iptc4xmpExt:{name}>{value}</Iptc4xmpExt:{name}>".encode() in data, name
    assert {k: report["marking_kept"][k] for k in AI_FIELDS} == {
        **AI_FIELDS, "AIPromptInformation": "a lighthouse at dusk & gulls"}


@pytest.mark.parametrize("suffix", IMAGES)
def test_the_copy_gets_no_instance_id_and_no_provenance(tmp_path, label_tool, suffix):
    original = IMAGES[suffix](tmp_path / f"photo.{suffix}", xmp=full_xmp("trainedAlgorithmicMedia"), size=SIZE)

    _, copy = apply(label_tool, original)

    data = copy.read_bytes()
    assert b"Iptc4xmpExt:DigitalSourceType" in data
    for left_out in (b"InstanceID", INSTANCE_ID.encode(), b"provenance", PROVENANCE.encode()):
        assert left_out not in data, left_out


@pytest.mark.parametrize("suffix, mime", [("png", "image/png"), ("jpg", "image/jpeg")])
def test_a_c2pa_marking_becomes_the_copys_digital_source_type_and_the_manifest_is_dropped(tmp_path, label_tool,
                                                                                         suffix, mime):
    unsigned = IMAGES[suffix](tmp_path / f"unsigned.{suffix}", size=SIZE)
    original = signed(unsigned, tmp_path / f"photo.{suffix}", manifest("compositeWithTrainedAlgorithmicMedia"), mime)
    assert marking(label_tool, original)["settled"] == "modified"

    report, copy = apply(label_tool, original)

    read = marking(label_tool, copy)
    assert read["settled"] == "modified"
    assert [s["source"] for s in read["signals"]] == ["xmp"], "the original's C2PA manifest is not carried over"
    assert b"c2pa" not in copy.read_bytes()
    assert report["marking_kept"] == {"DigitalSourceType": IPTC_SOURCE + "compositeWithTrainedAlgorithmicMedia"}


def test_when_a_valid_c2pa_manifest_overrides_the_xmp_the_copy_keeps_the_manifests_source_type(tmp_path,
                                                                                                label_tool):
    unsigned = png(tmp_path / "unsigned.png", xmp=xmp_packet("trainedAlgorithmicMedia", ai=AI_FIELDS), size=SIZE)
    original = signed(unsigned, tmp_path / "photo.png", manifest("compositeWithTrainedAlgorithmicMedia"))
    assert marking(label_tool, original)["settled"] == "modified"

    report, copy = apply(label_tool, original)

    assert marking(label_tool, copy)["settled"] == "modified"
    assert report["marking_kept"]["DigitalSourceType"] == IPTC_SOURCE + "compositeWithTrainedAlgorithmicMedia"
    assert report["marking_kept"]["AISystemUsed"] == AI_FIELDS["AISystemUsed"]


@pytest.mark.parametrize("suffix", IMAGES)
def test_an_unmarked_original_gives_an_unmarked_copy(tmp_path, label_tool, suffix):
    original = IMAGES[suffix](tmp_path / f"photo.{suffix}", size=SIZE)

    report, copy = apply(label_tool, original)

    assert "marking_kept" not in report
    assert b"xmpmeta" not in copy.read_bytes()
    assert marking(label_tool, copy)["signals"] == []


def test_an_xmp_without_iptc_fields_is_not_carried(tmp_path, label_tool):
    original = png(tmp_path / "photo.png", xmp=xmp_packet(creator_tool="Midjourney", instance_id=INSTANCE_ID),
                   size=SIZE)

    report, copy = apply(label_tool, original)

    assert "marking_kept" not in report
    assert b"xmpmeta" not in copy.read_bytes()


def test_an_original_whose_xmp_contradicts_itself_gives_a_copy_that_settles_nothing(tmp_path, label_tool):
    xmp = xmp_packet("trainedAlgorithmicMedia", ai=AI_FIELDS) + xmp_packet("compositeWithTrainedAlgorithmicMedia")
    original = png(tmp_path / "photo.png", xmp=xmp, size=SIZE)
    assert marking(label_tool, original)["settled"] is None

    report, copy = apply(label_tool, original)

    assert marking(label_tool, copy)["settled"] is None
    assert "DigitalSourceType" not in report["marking_kept"]
    assert report["marking_kept"]["AISystemUsed"] == AI_FIELDS["AISystemUsed"]
    assert b"DigitalSourceType" not in copy.read_bytes()


def test_a_c2pa_manifest_that_contradicts_itself_gives_a_copy_that_settles_nothing(tmp_path, label_tool):
    unsigned = png(tmp_path / "unsigned.png", xmp=xmp_packet("trainedAlgorithmicMedia"), size=SIZE)
    original = signed(unsigned, tmp_path / "photo.png",
                      manifest("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia"))
    assert marking(label_tool, original)["settled"] is None

    report, copy = apply(label_tool, original)

    assert marking(label_tool, copy)["settled"] is None
    assert "marking_kept" not in report
    assert report["c2pa_left_behind"] is True


def test_the_copy_keeps_the_digital_source_type_that_settles_not_the_first_one_written(tmp_path, label_tool):
    xmp = xmp_packet("algorithmicMedia") + xmp_packet("trainedAlgorithmicMedia")
    original = png(tmp_path / "photo.png", xmp=xmp, size=SIZE)
    assert marking(label_tool, original)["settled"] == "generated"

    report, copy = apply(label_tool, original)

    assert marking(label_tool, copy)["settled"] == "generated"
    assert report["marking_kept"]["DigitalSourceType"] == IPTC_SOURCE + "trainedAlgorithmicMedia"


@pytest.mark.parametrize("make", [
    lambda base, to: signed(base, to, manifest("trainedAlgorithmicMedia")),
    lambda base, to: tampered(signed(base, to, manifest("trainedAlgorithmicMedia"))),
], ids=["precise", "invalid signature"])
def test_the_report_says_when_a_c2pa_marking_is_left_behind(tmp_path, label_tool, make):
    original = make(png(tmp_path / "unsigned.png", size=SIZE), tmp_path / "photo.png")
    assert marking(label_tool, original)["signals"]

    report, copy = apply(label_tool, original)

    assert report["c2pa_left_behind"] is True
    assert b"c2pa" not in copy.read_bytes()


def test_an_original_without_c2pa_leaves_none_behind(tmp_path, label_tool):
    original = png(tmp_path / "photo.png", xmp=xmp_packet("trainedAlgorithmicMedia"), size=SIZE)

    report, _ = apply(label_tool, original)

    assert "c2pa_left_behind" not in report


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
def test_marking_kept_is_what_the_copy_carries_even_where_pillow_cannot_write_it(tmp_path):
    """Pillow 10, which the python3 fallback may have, ignores the `xmp` option of a JPEG save."""
    if shutil.which("uv") is None:
        pytest.skip("needs uv to run label_tool under Pillow 10")
    original = jpeg(tmp_path / "photo.jpg", xmp=full_xmp("trainedAlgorithmicMedia"), size=SIZE)
    # Python 3.12: Pillow 10.4.0 ships wheels up to 3.13 only, and building it from source needs libjpeg headers.
    proc = subprocess.run(["uv", "run", "--quiet", "--no-project", "--python", "3.12",
                           "--with", "pillow==10.4.0", "--with", "resvg-py",
                           "python", str(LABEL_TOOL), "apply", str(original), "--variant", "generated"],
                          capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr
    copy = tmp_path / "photo.ai-label.jpg"

    assert b"xmpmeta" not in copy.read_bytes(), "Pillow 10 wrote no XMP"
    assert "marking_kept" not in json.loads(proc.stdout)


# --- Videos ------------------------------------------------------------------------


def top_level_boxes(data: bytes) -> list[bytes]:
    kinds, at = [], 0
    while at + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[at:at + 8])
        kinds.append(kind)
        at += size
    assert at == len(data), "the boxes cover the file exactly"
    return kinds


def children(data: bytes, kind: bytes, nested: bool = False) -> list[bytes] | bytes:
    """The payload of each `kind` box among the boxes laid out in `data`; the only one unless `nested`."""
    found, at = [], 0
    while at + 8 <= len(data):
        size, box = struct.unpack(">I4s", data[at:at + 8])
        if box == kind:
            found.append(data[at + 8:at + size])
        at += size
    if nested:
        return found
    assert len(found) == 1, found
    return found[0]


def video_apply(label_tool, tmp_path, video) -> tuple[dict, object]:
    result = label_tool("video-apply", video, "--variant", "generated", env=real_tools(tmp_path / "bin"))
    assert result.returncode == 0, result.json
    assert result.json["validation"]["passed"]
    return result.json, type(video)(result.json["labelled_copy"])


@needs_ffmpeg
@pytest.mark.parametrize("suffix", ["mp4", "mov"])
def test_a_videos_copy_keeps_the_digital_source_type_without_identity_or_provenance(tmp_path, label_tool, suffix):
    video = flat_mp4(tmp_path / f"clip.{suffix}", seconds=0.5, size="640x360")
    add = with_mp4_xmp if suffix == "mp4" else with_quicktime_xmp
    add(video, full_xmp("compositeWithTrainedAlgorithmicMedia"))
    env = real_tools(tmp_path / "bin")
    assert marking(label_tool, video, env)["settled"] == "modified"

    report, copy = video_apply(label_tool, tmp_path, video)

    read = marking(label_tool, copy, env)
    assert read["settled"] == "modified"
    assert [(s["source"], s["value"]) for s in read["signals"]] == [("xmp", "compositeWithTrainedAlgorithmicMedia")]
    assert report["marking_kept"]["AISystemUsed"] == AI_FIELDS["AISystemUsed"]
    data = copy.read_bytes()
    for left_out in (b"InstanceID", b"provenance"):
        assert left_out not in data, left_out


@needs_ffmpeg
def test_an_mp4_copy_carries_its_xmp_in_a_top_level_uuid_box(tmp_path, label_tool):
    video = with_mp4_xmp(flat_mp4(tmp_path / "clip.mp4", seconds=0.5, size="640x360"),
                         xmp_packet("trainedAlgorithmicMedia"))

    _, copy = video_apply(label_tool, tmp_path, video)

    data = copy.read_bytes()
    assert b"uuid" in top_level_boxes(data)
    assert XMP_UUID + b"<?xpacket" in data


@needs_ffmpeg
def test_a_mov_copy_carries_its_xmp_in_moov_udta(tmp_path, label_tool):
    video = with_quicktime_xmp(flat_mp4(tmp_path / "clip.mov", seconds=0.5, size="640x360"),
                               xmp_packet("trainedAlgorithmicMedia"))

    _, copy = video_apply(label_tool, tmp_path, video)

    data = copy.read_bytes()
    assert b"uuid" not in top_level_boxes(data)
    moov = children(data, b"moov")
    xmp = [item for udta in children(moov, b"udta", nested=True) for item in children(udta, b"XMP_", nested=True)]
    assert len(xmp) == 1 and xmp[0].startswith(b"<?xpacket")


@needs_ffmpeg
def test_an_unmarked_videos_copy_gets_no_xmp(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=0.5, size="640x360")

    report, copy = video_apply(label_tool, tmp_path, video)

    assert "marking_kept" not in report
    assert b"xmpmeta" not in copy.read_bytes()


@needs_ffmpeg
def test_a_c2pa_marked_mp4s_copy_keeps_the_source_type_but_not_the_manifest(tmp_path, label_tool):
    unsigned = flat_mp4(tmp_path / "unsigned.mp4", seconds=0.5, size="640x360")
    video = signed(unsigned, tmp_path / "clip.mp4", manifest("trainedAlgorithmicMedia"), "video/mp4")
    env = real_tools(tmp_path / "bin")
    assert marking(label_tool, video, env)["settled"] == "generated"

    report, copy = video_apply(label_tool, tmp_path, video)

    assert report["c2pa_left_behind"] is True
    read = marking(label_tool, copy, env)
    assert read["settled"] == "generated"
    assert [s["source"] for s in read["signals"]] == ["xmp"]
    assert b"c2pa" not in copy.read_bytes()
