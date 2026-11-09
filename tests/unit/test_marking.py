"""`label_tool marking`: reads an image's or video's Marking and grades it as evidence for the Icon Variant.

Every fixture is built here (see markings.py): XMP packets written into the
file, C2PA manifests signed by a throwaway certificate, PNG text chunks and
video container tags. Nothing is fetched, and the C2PA read must not reach
the network either.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys

import pytest

from helpers import LABEL_TOOL
from markings import (
    jpeg, manifest, png, png_after_idat, remote_only, signed, tampered, webp, with_mp4_xmp, with_quicktime_xmp, xmp_packet,
)
from videos import flat_mp4, needs_ffmpeg, real_tools, without_tools


def marking(label_tool, path, env=None):
    result = label_tool("marking", path, env=env)
    assert result.returncode == 0, result.json
    return result.json


def only(signals, **fields):
    found = [s for s in signals if all(s.get(k) == v for k, v in fields.items())]
    assert len(found) == 1, signals
    return found[0]


# --- No Marking --------------------------------------------------------------------


def test_an_unmarked_image_gives_nothing_and_no_error(tmp_path, label_tool):
    report = marking(label_tool, png(tmp_path / "plain.png"))

    assert report["settled"] is None
    assert report["signals"] == []
    assert report["quotes"] == []
    assert report["settled_by"] == []
    assert report["c2pa"] == "checked"
    assert report["media"] == "image"


def test_a_missing_file_is_not_found(tmp_path, label_tool):
    result = label_tool("marking", tmp_path / "gone.png")

    assert result.returncode != 0
    assert result.json["error"]["code"] == "not_found"


def test_the_subcommand_is_documented_in_help(label_tool):
    proc = subprocess.run(["uv", "run", "--quiet", str(LABEL_TOOL), "--help"],
                          capture_output=True, text=True, timeout=300, check=True)

    assert "marking <image | video>" in proc.stdout
    assert "Marking" in subprocess.run(["uv", "run", "--quiet", str(LABEL_TOOL), "marking", "--help"],
                                       capture_output=True, text=True, timeout=300, check=True).stdout


# --- XMP DigitalSourceType ---------------------------------------------------------


@pytest.mark.parametrize("make", [
    lambda d, x: png(d / "a.png", xmp=x),
    lambda d, x: png(d / "a.png", xmp=x, compressed=True),
    lambda d, x: jpeg(d / "a.jpg", xmp=x),
    lambda d, x: webp(d / "a.webp", xmp=x),
], ids=["png", "png-compressed", "jpeg", "webp"])
def test_xmp_trained_algorithmic_media_settles_generated(tmp_path, label_tool, make):
    report = marking(label_tool, make(tmp_path, xmp_packet("trainedAlgorithmicMedia")))

    signal = only(report["signals"], source="xmp")
    assert signal["value"] == "trainedAlgorithmicMedia"
    assert signal["grade"] == "precise"
    assert signal["variant"] == "generated"
    assert report["settled"] == "generated"
    assert report["settled_by"] == [signal["quote"]]
    assert "trainedAlgorithmicMedia" in signal["quote"]
    assert report["quotes"] == []


def test_xmp_composite_with_trained_algorithmic_media_settles_modified(tmp_path, label_tool):
    # Written as an element with rdf:resource, the other form XMP allows.
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet("compositeWithTrainedAlgorithmicMedia",
                                                                        element=True)))

    signal = only(report["signals"], source="xmp")
    assert (signal["grade"], signal["variant"]) == ("precise", "modified")
    assert report["settled"] == "modified"


@pytest.mark.parametrize("code", ["algorithmicallyEnhanced", "compositeSynthetic", "algorithmicMedia"])
def test_other_ai_source_types_are_vague_and_quoted(tmp_path, label_tool, code):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet(code)))

    signal = only(report["signals"], source="xmp")
    assert signal["grade"] == "vague"
    assert "variant" not in signal
    assert report["settled"] is None
    assert report["quotes"] == [signal["quote"]]
    assert code in signal["quote"]


@pytest.mark.parametrize("code", ["digitalCapture", "digitalArt", "humanEdits", "compositeCapture"])
def test_human_origin_source_types_are_ignored(tmp_path, label_tool, code):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet(code)))

    assert report["signals"] == []
    assert report["settled"] is None


# --- C2PA --------------------------------------------------------------------------


def test_a_valid_c2pa_manifest_settles_generated_and_names_its_provider(tmp_path, label_tool):
    marked = signed(png(tmp_path / "plain.png"), tmp_path / "c2pa.png", manifest("trainedAlgorithmicMedia"))

    report = marking(label_tool, marked)

    signal = only(report["signals"], source="c2pa")
    assert signal["grade"] == "precise"
    assert signal["variant"] == "generated"
    assert signal["validation_state"] in ("Valid", "Trusted")
    assert signal["provider"] == "Example Image Generator"
    assert signal["signer"] == "Example AI Lab"
    assert signal["action"] == "c2pa.created"
    assert signal["active"] is True
    assert report["settled"] == "generated"
    assert report["settled_by"] == [signal["quote"]]
    assert "Example Image Generator" in signal["quote"]


def test_a_valid_c2pa_composite_settles_modified(tmp_path, label_tool):
    marked = signed(png(tmp_path / "plain.png"), tmp_path / "c2pa.png",
                    manifest("compositeWithTrainedAlgorithmicMedia"))

    report = marking(label_tool, marked)

    assert only(report["signals"], source="c2pa")["variant"] == "modified"
    assert report["settled"] == "modified"


def test_a_c2pa_manifest_whose_signature_fails_is_vague(tmp_path, label_tool):
    marked = tampered(signed(png(tmp_path / "plain.png"), tmp_path / "c2pa.png", manifest("trainedAlgorithmicMedia")))

    report = marking(label_tool, marked)

    signal = only(report["signals"], source="c2pa")
    assert signal["grade"] == "vague"
    assert signal["validation_state"] == "Invalid"
    assert report["settled"] is None
    assert report["quotes"] == [signal["quote"]]
    assert "invalid" in signal["quote"]


def test_a_c2pa_manifest_with_only_human_origin_actions_is_ignored(tmp_path, label_tool):
    marked = signed(png(tmp_path / "plain.png"), tmp_path / "c2pa.png", manifest("digitalCapture",
                                                                                   generator="Example Camera"))

    report = marking(label_tool, marked)

    assert report["signals"] == []
    assert report["settled"] is None


def test_a_remote_only_manifest_counts_as_no_c2pa_and_is_never_fetched(tmp_path, label_tool):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.5)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}/manifest.c2pa"
        marked = remote_only(png(tmp_path / "plain.png"), tmp_path / "remote.png",
                             manifest("trainedAlgorithmicMedia"), url)

        report = marking(label_tool, marked)

        with pytest.raises(socket.timeout):
            listener.accept()
    assert report["signals"] == []
    assert report["settled"] is None


def run_without_c2pa(*args) -> dict:
    """label_tool under plain python3 (the `python3` fallback) where c2pa-python is not installed."""
    hide = ("import runpy, sys; sys.modules['c2pa'] = None; sys.argv = sys.argv[1:]; "
            "runpy.run_path(sys.argv[0], run_name='__main__')")
    proc = subprocess.run([sys.executable, "-c", hide, str(LABEL_TOOL), *map(str, args)],
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_without_c2pa_python_the_other_sources_are_still_read(tmp_path):
    source = png(tmp_path / "plain.png", xmp=xmp_packet("trainedAlgorithmicMedia"))
    marked = signed(source, tmp_path / "c2pa.png", manifest("compositeWithTrainedAlgorithmicMedia"))

    report = run_without_c2pa("marking", marked)

    assert report["c2pa"] == "unavailable"
    assert [s["source"] for s in report["signals"]] == ["xmp"]
    assert report["settled"] == "generated"


# --- Software / CreatorTool and PNG text chunks ---------------------------------------


def test_an_ai_tool_in_exif_software_is_vague(tmp_path, label_tool):
    report = marking(label_tool, jpeg(tmp_path / "a.jpg", software="Midjourney v6"))

    signal = only(report["signals"], source="software")
    assert signal["grade"] == "vague"
    assert signal["tool"] == "Midjourney"
    assert signal["field"] == "EXIF Software"
    assert report["settled"] is None
    assert report["quotes"] == [signal["quote"]]


def test_an_ai_tool_in_xmp_creator_tool_is_vague(tmp_path, label_tool):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet(creator_tool="Adobe Firefly")))

    signal = only(report["signals"], source="software")
    assert (signal["field"], signal["tool"], signal["grade"]) == ("XMP CreatorTool", "Adobe Firefly", "vague")


def test_a_tool_that_is_not_ai_is_ignored(tmp_path, label_tool):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet(creator_tool="Adobe Photoshop 25.0",
                                                                        software="GIMP 2.10")))

    assert report["signals"] == []


@pytest.mark.parametrize("key, value", [
    ("parameters", "a lighthouse at dusk\nSteps: 20, Sampler: Euler a, Model: sd_xl_base_1.0"),
    ("prompt", '{"3": {"class_type": "KSampler"}}'),
    ("workflow", '{"nodes": []}'),
])
def test_a_generator_text_chunk_is_vague_and_quoted(tmp_path, label_tool, key, value):
    report = marking(label_tool, png(tmp_path / "a.png", text={key: value}))

    signal = only(report["signals"], source="png_text")
    assert signal["field"] == key
    assert signal["grade"] == "vague"
    assert report["settled"] is None
    assert report["quotes"] == [signal["quote"]]
    assert key in signal["quote"]


def test_a_generator_text_chunk_after_the_image_data_is_read(tmp_path, label_tool):
    report = marking(label_tool, png_after_idat(tmp_path / "a.png", "parameters", "a lighthouse, Steps: 20"))

    assert only(report["signals"], source="png_text")["field"] == "parameters"


def test_xmp_after_the_image_data_is_read(tmp_path, label_tool):
    marked = png_after_idat(tmp_path / "a.png", "XML:com.adobe.xmp",
                            xmp_packet("trainedAlgorithmicMedia").decode(), itxt=True)

    report = marking(label_tool, marked)

    assert report["settled"] == "generated"


@pytest.mark.parametrize("software", ["DALL·E 3", "DALL-E", "dalle3", "OpenAI DALL.E 2"])
def test_dall_e_is_named(tmp_path, label_tool, software):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet(creator_tool=software)))

    assert only(report["signals"], source="software")["tool"] == "DALL-E"


@pytest.mark.parametrize("software", ["Photo by Randall Edwards", "Kendall E. camera", "Dall Edwards"])
def test_a_name_that_only_contains_dall_e_is_ignored(tmp_path, label_tool, software):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet(creator_tool=software)))

    assert report["signals"] == []


def test_a_long_text_chunk_is_shortened_in_the_quote(tmp_path, label_tool):
    report = marking(label_tool, png(tmp_path / "a.png", text={"parameters": "x" * 5000}, compressed=True))

    signal = only(report["signals"], source="png_text")
    assert len(signal["value"]) <= 200
    assert len(signal["quote"]) < 300


# --- Grading together --------------------------------------------------------------


def test_a_precise_signal_settles_despite_vague_ones(tmp_path, label_tool):
    report = marking(label_tool, png(tmp_path / "a.png", xmp=xmp_packet("trainedAlgorithmicMedia"),
                                     text={"parameters": "a cat"}))

    assert report["settled"] == "generated"
    assert {s["source"]: s["grade"] for s in report["signals"]} == {"xmp": "precise", "png_text": "vague"}
    assert report["quotes"] == []


def test_precise_signals_that_agree_settle_together(tmp_path, label_tool):
    source = png(tmp_path / "plain.png", xmp=xmp_packet("trainedAlgorithmicMedia"))
    marked = signed(source, tmp_path / "c2pa.png", manifest("trainedAlgorithmicMedia"))

    report = marking(label_tool, marked)

    assert report["settled"] == "generated"
    assert len(report["settled_by"]) == 2


def test_a_valid_active_c2pa_manifest_decides_a_conflict(tmp_path, label_tool):
    source = png(tmp_path / "plain.png", xmp=xmp_packet("trainedAlgorithmicMedia"))
    marked = signed(source, tmp_path / "c2pa.png", manifest("compositeWithTrainedAlgorithmicMedia"))

    report = marking(label_tool, marked)

    c2pa = only(report["signals"], source="c2pa")
    xmp = only(report["signals"], source="xmp")
    assert report["settled"] == "modified"
    assert report["settled_by"] == [c2pa["quote"]]
    assert xmp["overridden"] is True
    assert report["quotes"] == []


def test_without_a_deciding_manifest_disagreeing_precise_signals_become_vague(tmp_path, label_tool):
    # The active manifest disagrees with itself, so it decides nothing; with the XMP, three precise
    # signals disagree, and each becomes vague.
    source = png(tmp_path / "plain.png", xmp=xmp_packet("trainedAlgorithmicMedia"))
    marked = signed(source, tmp_path / "c2pa.png",
                    manifest("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia"))

    report = marking(label_tool, marked)

    assert report["settled"] is None
    assert len(report["signals"]) == 3
    for signal in report["signals"]:
        assert signal["grade"] == "vague"
        assert signal["conflict"] is True
        assert "variant" not in signal
    assert report["quotes"] == [s["quote"] for s in report["signals"]]


# --- Videos ------------------------------------------------------------------------


@needs_ffmpeg
def test_xmp_in_an_mp4_settles_generated(tmp_path, label_tool):
    video = with_mp4_xmp(flat_mp4(tmp_path / "clip.mp4", seconds=0.2), xmp_packet("trainedAlgorithmicMedia"))

    report = marking(label_tool, video, env=real_tools(tmp_path / "bin"))

    assert report["media"] == "video"
    assert [s["source"] for s in report["signals"]] == ["xmp"]
    assert report["settled"] == "generated"


@needs_ffmpeg
def test_xmp_in_a_mov_settles_modified(tmp_path, label_tool):
    video = with_quicktime_xmp(flat_mp4(tmp_path / "clip.mov", seconds=0.2),
                               xmp_packet("compositeWithTrainedAlgorithmicMedia"))

    report = marking(label_tool, video, env=real_tools(tmp_path / "bin"))

    assert report["settled"] == "modified"


@needs_ffmpeg
def test_an_ai_tool_in_a_container_comment_is_vague(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=0.2, extra=("-metadata", "comment=Made with Runway Gen-3"))

    report = marking(label_tool, video, env=real_tools(tmp_path / "bin"))

    signal = only(report["signals"], source="container_tags")
    assert (signal["field"], signal["tool"], signal["grade"]) == ("comment", "Runway", "vague")
    assert report["settled"] is None


@needs_ffmpeg
def test_an_ai_tool_in_a_quicktime_tag_is_vague(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mov", seconds=0.2,
                     extra=("-movflags", "use_metadata_tags", "-metadata", "com.apple.quicktime.software=OpenAI Sora"))

    report = marking(label_tool, video, env=real_tools(tmp_path / "bin"))

    signal = only(report["signals"], source="container_tags")
    assert signal["field"] == "com.apple.quicktime.software"
    assert signal["tool"] == "Sora"


@needs_ffmpeg
def test_an_unmarked_video_gives_nothing(tmp_path, label_tool):
    report = marking(label_tool, flat_mp4(tmp_path / "clip.mp4", seconds=0.2), env=real_tools(tmp_path / "bin"))

    assert report["signals"] == []
    assert report["settled"] is None


@needs_ffmpeg
def test_a_video_without_ffmpeg_gets_the_video_tools_error(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=0.2)

    result = label_tool("marking", video, env=without_tools(tmp_path))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "video_tools_missing"
