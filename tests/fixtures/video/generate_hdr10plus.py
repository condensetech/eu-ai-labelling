"""Regenerate the tiny real HDR10+ fixtures with an HDR10_PLUS-enabled libx265."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from videos import frame_side_data, hdr10_video, hdr10plus_info, hlg_video

with tempfile.TemporaryDirectory() as tmp:
    metadata = hdr10plus_info(Path(tmp) / "hdr10plus.json", frames=1)
    for name, make in (("hdr10plus.mp4", hdr10_video), ("hlg-hdr10plus.mp4", hlg_video)):
        path = Path(__file__).parent / name
        make(path, seconds=0.04, size="64x64", source="0x202020", hdr10plus=metadata)
        assert "HDR Dynamic Metadata SMPTE2094-40 (HDR10+)" in frame_side_data(path), (
            "Regeneration requires libx265 built with HDR10_PLUS enabled"
        )
