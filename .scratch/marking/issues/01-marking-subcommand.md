# 01: `marking` subcommand reads and grades a file's Marking

**What to build:** A deterministic `label_tool.py marking <file>` subcommand for images and videos. It reads the five sources in the [spec](../spec.md), grades each signal as precise, vague or ignored, and applies the conflict rules. It prints one JSON object with the signals and the overall `settled` result. Nothing in the skill's procedure uses it yet (ticket 02).

**Blocked by:** none

**Status:** resolved

- [x] `c2pa-python` added to the script's inline dependencies. Under the `python3` fallback without it, the subcommand still runs and reports `c2pa: unavailable`.
- [x] Reads IPTC DigitalSourceType from XMP in PNG, JPEG, WebP, MP4 and MOV.
- [x] Reads C2PA manifests: Provider (claim generator / signer), actions, digitalSourceType and signature validity. It doesn't judge whether a signer is trustworthy.
- [x] Reading never reaches the network: remote-manifest fetching and OCSP are turned off through `c2pa.Settings`. A file whose manifest is only remote counts as having no C2PA.
- [x] Pin `c2pa-python>=0.38,<0.39`, the oldest range uv resolves on Linux, Windows and macOS. (Checked 2026-11-09: 0.38.2 has only macOS wheels, so uv picks 0.38.1 on Linux and 0.38.0 on Windows.) Signature validity is the Reader's `validation_state` (`Valid` or `Trusted`), not trust in the signer.
- [x] Reads EXIF/XMP `Software`/`CreatorTool`, the generator PNG text chunks (`parameters`, `prompt`, `workflow`) and video container tags via ffprobe (`encoder`, `comment`, `com.apple.quicktime.*`). A video without ffmpeg/ffprobe gets the existing `video-tools` error handling.
- [x] Grading as in the spec:
  - precise: `trainedAlgorithmicMedia` gives `generated`, `compositeWithTrainedAlgorithmicMedia` gives `modified`, from XMP or from a C2PA manifest whose signature validates;
  - vague: the other AI-ish values, tool names, generator chunks, invalid or unsigned C2PA;
  - ignored: human-origin values.
- [x] Conflict rules: a valid active C2PA manifest decides. Otherwise precise signals that disagree become vague. The output gives `settled: generated|modified|null` and the quotable signals for the origin question.
- [x] A file without any Marking gives `settled: null` and no signals, with no error.
- [x] The subcommand is documented in the script's docstring and `--help`.
- [x] Unit tests on small generated fixtures cover each source, each grade, both conflict rules, `c2pa: unavailable` and an unmarked file.
