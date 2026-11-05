"""`label_tool video-tools` and `video-inspect`: the FFmpeg check and the read-only inspection of a video.

PATH is replaced in each test, so the real ffmpeg and ffprobe are seen only
through wrappers the test puts there, or not at all. The Windows lookup is
simulated with LABEL_TOOL_PLATFORM=windows on this machine: it shows that
`ffmpeg.exe` is found through PATHEXT, not that the tool runs on Windows.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from helpers import sha256
from videos import fake_tool, flat_mp4, needs_ffmpeg, real_tool, real_tools, tool_env, without_tools

pytestmark = needs_ffmpeg


def test_both_tools_available(tmp_path, label_tool):
    result = label_tool("video-tools", env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    assert result.json["ready"] is True
    for name in ("ffmpeg", "ffprobe"):
        assert result.json["tools"][name]["status"] == "available"
        assert result.json["tools"][name]["path"] == str(tmp_path / "bin" / name)
        assert result.json["tools"][name]["version"]
    assert "install" not in result.json


def test_capabilities_are_reported_apart_from_validated_paths(tmp_path, label_tool):
    result = label_tool("video-tools", env=real_tools(tmp_path / "bin"))

    capabilities = result.json["capabilities"]
    assert capabilities["encoders"]["libx264"] is True
    assert capabilities["filters"]["overlay"] is True
    assert capabilities["pixel_formats"]["yuv420p"] is True
    assert capabilities["muxers"]["mp4"] is True
    assert capabilities["decoders"]["h264"] is True
    # What the build can do is not a claim that labelling is validated.
    assert "capability" in result.json["note"] and "validated" in result.json["note"]


@pytest.mark.parametrize("missing", ["ffmpeg", "ffprobe"])
def test_one_tool_missing(tmp_path, label_tool, missing):
    bin_dir = tmp_path / "bin"
    present = "ffprobe" if missing == "ffmpeg" else "ffmpeg"
    real_tool(bin_dir, present)

    result = label_tool("video-tools", env=tool_env(bin_dir))

    assert result.returncode == 0, result.json
    assert result.json["ready"] is False
    assert result.json["tools"][missing]["status"] == "missing"
    assert result.json["tools"][present]["status"] == "available"
    assert result.json["install"]["steps"]
    assert "again" in result.json["install"]["after"]


def test_an_unusable_tool_is_not_available(tmp_path, label_tool):
    bin_dir = tmp_path / "bin"
    real_tool(bin_dir, "ffprobe")
    fake_tool(bin_dir, "ffmpeg", "echo 'dyld: Library not loaded' >&2; exit 134")

    result = label_tool("video-tools", env=tool_env(bin_dir))

    assert result.json["ready"] is False
    assert result.json["tools"]["ffmpeg"]["status"] == "unusable"
    assert "Library not loaded" in result.json["tools"]["ffmpeg"]["message"]
    assert result.json["install"]["steps"]


def test_windows_guidance_when_tools_are_missing(tmp_path, label_tool):
    env = {**without_tools(tmp_path), "LABEL_TOOL_PLATFORM": "windows"}

    result = label_tool("video-tools", env=env)

    install = result.json["install"]
    assert install["platform"] == "windows"
    assert install["simulated"] is True
    text = " ".join([*install["steps"], install["after"]])
    assert "winget install --id Gyan.FFmpeg.Essentials --exact --source winget" in text
    assert "ffmpeg-release-essentials.zip" in text and "Path" in text
    assert "reopen" in text.lower() and "ffprobe -version" in text


@pytest.mark.parametrize("platform, command", [("macos", "brew install ffmpeg"), ("linux", "apt install ffmpeg")])
def test_guidance_for_macos_and_linux(tmp_path, label_tool, platform, command):
    env = {**without_tools(tmp_path), "LABEL_TOOL_PLATFORM": platform}

    result = label_tool("video-tools", env=env)

    assert result.json["install"]["platform"] == platform
    assert any(command in step for step in result.json["install"]["steps"])
    assert "not validated" in result.json["install"]["note"]


def test_windows_lookup_finds_exe_through_pathext(tmp_path, label_tool):
    bin_dir = tmp_path / "bin"
    real_tool(bin_dir, "ffmpeg", "ffmpeg.exe")
    real_tool(bin_dir, "ffprobe", "ffprobe.exe")
    env = {**tool_env(bin_dir), "LABEL_TOOL_PLATFORM": "windows", "PATHEXT": ".COM;.EXE;.BAT"}

    result = label_tool("video-tools", env=env)

    assert result.json["ready"] is True, result.json
    assert result.json["tools"]["ffmpeg"]["path"].endswith("ffmpeg.exe")
    assert result.json["tools"]["ffprobe"]["path"].endswith("ffprobe.exe")


def test_tools_are_never_installed(tmp_path, label_tool):
    empty = tmp_path / "empty-bin"
    empty.mkdir()

    label_tool("video-tools", env=tool_env(empty))

    assert list(empty.iterdir()) == []


# --- video-inspect ---------------------------------------------------------------


def test_inspect_reads_streams_timing_and_colour(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4", seconds=2, rate=25, audio=True,
                     extra=("-vf", "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"))
    before = sha256(video)

    result = label_tool("video-inspect", video, env=real_tools(tmp_path / "bin"))

    assert result.returncode == 0, result.json
    info = result.json
    assert info["container"]["format"] == "mp4"
    assert info["container"]["duration"] == pytest.approx(2.0, abs=0.05)
    assert info["video"]["codec"] == "h264"
    assert (info["video"]["width"], info["video"]["height"]) == (320, 180)
    assert (info["video"]["display_width"], info["video"]["display_height"]) == (320, 180)
    assert info["video"]["rotation"] == 0
    assert info["video"]["frame_rate"] == "25/1"
    assert info["video"]["constant_frame_rate"] is True
    assert info["video"]["pix_fmt"] == "yuv420p" and info["video"]["bit_depth"] == 8
    assert info["video"]["colour"]["primaries"] == "bt709"
    assert info["video"]["colour"]["dynamic_range"] == "sdr"
    assert [a["codec"] for a in info["audio"]] == ["aac"]
    assert sha256(video) == before


def test_inspect_reports_rotation_as_displayed(tmp_path, label_tool):
    plain = flat_mp4(tmp_path / "plain.mp4", size="320x180")
    from videos import ffmpeg
    rotated = tmp_path / "rotated.mp4"
    ffmpeg("-display_rotation", "90", "-i", plain, "-c", "copy", rotated)

    result = label_tool("video-inspect", rotated, env=real_tools(tmp_path / "bin"))

    assert result.json["video"]["rotation"] in (90, -90, 270)
    assert (result.json["video"]["display_width"], result.json["video"]["display_height"]) == (180, 320)


def test_inspect_does_not_promise_rendering(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4")

    result = label_tool("video-inspect", video, env=real_tools(tmp_path / "bin"))

    assert "labelling" in result.json
    assert result.json["labelling"]["supported"] in (True, False)


def test_inspect_malformed_input_is_a_structured_error(tmp_path, label_tool):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"garbage" * 50)

    result = label_tool("video-inspect", broken, env=real_tools(tmp_path / "bin"))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "unreadable_video"


def test_inspect_missing_file(tmp_path, label_tool):
    result = label_tool("video-inspect", tmp_path / "gone.mp4", env=real_tools(tmp_path / "bin"))

    assert result.json["error"]["code"] == "not_found"


def test_inspect_without_tools_asks_for_installation(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4")

    result = label_tool("video-inspect", video, env=without_tools(tmp_path))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "video_tools_missing"
    assert "video-tools" in result.json["error"]["message"]


def test_image_labelling_works_without_ffmpeg(tmp_path, label_tool):
    image = tmp_path / "photo.png"
    Image.new("RGB", (1000, 800), (90, 160, 210)).save(image)
    env = without_tools(tmp_path)

    scored = label_tool("score", image, "--variant", "generated", env=env)
    applied = label_tool("apply", image, "--variant", "generated", "--corner", "tr", env=env)

    assert scored.returncode == 0, scored.json
    assert applied.returncode == 0, applied.json
    assert Path(applied.json["labelled_copy"]).is_file()


def test_rendering_is_not_claimed_before_a_validated_path(tmp_path, label_tool):
    video = flat_mp4(tmp_path / "clip.mp4")

    result = label_tool("video-apply", video, "--variant", "generated", env=real_tools(tmp_path / "bin"))

    assert result.returncode != 0
    assert result.json["error"]["code"] == "video_not_supported_yet"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bin", "clip.mp4"]
