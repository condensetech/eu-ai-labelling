# 07: Produce an HDR10 Labelled Copy

**What to build:** A user can label a supported HDR10 video, review representative previews and receive a validated HDR Labelled Copy without an automatic conversion to SDR.

**Blocked by:** 04 - Choose a fixed position using scenes and previews.

**Status:** resolved

- [x] Deliver a documented, validated HDR10 processing path that checks the installed decoder, filter, pixel-format and encoder capabilities and retains a supported source container and codec. Use an actual HDR10 fixture rather than an SDR fixture carrying HDR tags.
- [x] Preserve the required bit depth, colour primaries, PQ transfer function, matrix/range and relevant HDR metadata throughout decoding, compositing and encoding. Do not assume that a successful encode or copied tags proves HDR preservation.
- [x] Map the EU Icon and backing plate deliberately into the video's colour/luminance space so the Label remains readable without unintended clipping or brightness changes. Verify the underlying picture outside the Label region against a suitable re-encoding tolerance.
- [x] Address metadata correctness after modifying pixels, including mastering and content-light information where relevant. If preservation or correct output metadata cannot be established, stop and explain the limitation before proposing an alternative.
- [x] Carry the HDR treatment through scene samples, labelled excerpts and the full Labelled Copy. Do not silently change previews to SDR or claim that an SDR viewing environment verifies HDR appearance; describe any unavailable rendering/display validation explicitly.
- [x] Recognise HDR10+, Dolby Vision and other profiles distinctly. Continue only through a validated preservation path for the actual profile/build; otherwise stop and ask, without claiming they are universally impossible or silently discarding their additional metadata.
- [x] Retain the agreed timing, Creative Work, fixed-position, atomic-output and approval behaviour. Unsupported source characteristics continue to follow the existing stop-and-ask contract rather than becoming silent conversions.
- [x] Demonstrate real HDR10 output, decoded colour/bit-depth and metadata checks, Label luminance handling, missing-capability rejection, and detection of unvalidated HDR profiles. Distinguish automated evidence, actual visual review and unavailable HDR-display verification in the completion report.
- [x] Update the video instructions and support claims to describe the verified path and the remaining build/profile limitations. Keep SDR output and previews working.

## Comments

New validated path `mp4-hevc-hdr10`: MP4, HEVC Main 10, `yuv420p10le`, BT.2020 / PQ / `bt2020nc` / limited range (the path's `colour`, else the new issue `colour_not_validated`), mastering display metadata required (else the new issue `hdr_metadata_missing`). It is re-encoded with libx265 at CRF 14 and keeps the source's `hvc1`/`hev1` tag. Audio and subtitle tracks are kept (`preserves: ("tracks",)`). Rotation and variable timing still stop. No MOV twin. Its `needs` list the hevc decoder, the libx265 encoder, the render filters plus `format`, `scale`, `colorchannelmixer` and `lutrgb`, the pixel formats `yuv420p10le`, `yuva420p10le`, `rgba64le` and `rgb48le`, and the mp4 muxer. This build has no `zscale` (no libzimg), so nothing needs it.

- **Label:** the RGBA overlay goes through `colorchannelmixer`, which scales it by PQ(203 cd/m2) ≈ 0.5807, then becomes 10-bit limited BT.2020 YUVA. It is composited with `overlay=format=yuv420p10`: overlay's default is 8-bit 4:2:0. The video's transfer is never converted. Measured: plate at codes 573–574 (expected 572.7), ringing up to 580; outside the Label a mean change of about 1 code and a level shift of about 0.03.
- **Metadata:** the mastering display is copied from the source. MaxCLL = max(source, 203). MaxFALL = min(MaxCLL, ceil(source + plate area share × 203)), a conservative upper bound. Unknown (0) or absent levels stay so. The params go to libx265 explicitly (`-x265-params hdr10=1:master-display=…:max-cll=…`), because otherwise libx265 copies the source's side data unchanged, which is measured and wrong when the Label is brighter.
- **Validation:** `hdr_metadata` checks the copy's own frame side data. `hdr_picture` decodes the source and the copy to raw 10-bit at the visible time: per plane, outside the box, a mean change ≤ 3 codes and a level shift ≤ 1. `label_level` checks the plate band median within 6 codes of its PQ level, and the brightest changed Label sample ≤ reference white + 12. Tests use an ffmpeg wrapper that rewrites arguments to drop `max-cll`, change levels while keeping the tags, or leave the Label at peak. Each is caught, and the previous copy is kept.
- **Fixed on the way:** ffprobe 9 lists frame side data with empty entries for `-show_entries frame=side_data_list`. It needs `frame=side_data_list:frame_side_data`. Before the fix, `hdr_metadata` was always empty and HDR10+ / Dolby Vision frame-level detection never fired.
- **Previews:**
  - Source PNGs (and the auto Icon Colour sampling) use an SDR rendering, `sdr_view`, made from built-in filters only: the PQ EOTF relative to 203 cd/m2, a roll-off above 0.8, BT.2020→BT.709 in linear light, and sRGB.
  - The result says `frame_rendering: sdr_tone_mapped` and gives an `hdr_note`.
  - Excerpts are HDR10, rendered through `render_command` with the same metadata.
- **Stops:**
  - HLG, HDR10+ and Dolby Vision: `hdr_not_validated`. The message names the profile, and for HDR10+ and Dolby Vision the dynamic metadata that would be lost.
  - SDR HEVC: `codec_not_validated`.
- **Evidence:** the tests are automated measurements on real libx265 fixtures, and the HDR10+ fixture is real (x265 `dhdr10-info`). Dolby Vision is simulated: a wrapped ffprobe renames the HDR10+ side data, because no local encoder writes Dolby Vision. I viewed one tone-mapped frame and one plain-converted frame during development. No HDR display was used, and the docs tell the agent and the user so.
- **Left out:**
  - The 10-bit picture check runs only at a visible time. Hidden periodic gaps keep the 8-bit `label_hidden` check.
  - `hdr_checks` compares stored planes against the displayed box, which is only right because rotation stops on this path.
  - The PQ gain is linear in signal space, so the Icon's anti-aliased edges ramp non-perceptually. This is cosmetic.
