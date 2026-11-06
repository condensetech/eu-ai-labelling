# HDR10+ fixtures

These two synthetic 64×64, one-frame videos contain real SMPTE ST 2094-40
dynamic metadata. `hdr10plus.mp4` uses PQ; `hlg-hdr10plus.mp4` uses HLG.
They let the rejection tests run even when the system's libx265 was compiled
without `HDR10_PLUS`, as in Ubuntu's package. The tests still verify the
metadata through the installed ffprobe before invoking the CLI.

Generated with FFmpeg 9.0.2 and an HDR10_PLUS-enabled libx265. Regenerate from
the repository root with the test dependencies installed:

```sh
python tests/fixtures/video/generate_hdr10plus.py
```

The generator uses a flat synthetic colour and the metadata defined in
`tests/videos.py`; no external footage is included. Regeneration asserts that
the encoded files actually contain HDR10+ metadata.
