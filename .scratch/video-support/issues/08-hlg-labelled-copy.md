# 08: Produce an HLG Labelled Copy

**What to build:** A user can label a supported HLG video using the HDR workflow while preserving HLG's own transfer and colour characteristics rather than converting it to HDR10 or SDR.

**Blocked by:** 07 - Produce an HDR10 Labelled Copy.

**Status:** resolved

- [x] Extend the established HDR rendering, preview and validation path with a documented, validated HLG profile and a real HLG source fixture. Check the capabilities required by that specific path before rendering.
- [x] Preserve the source's required bit depth, HLG transfer function, colour primaries, matrix/range and applicable metadata. Do not substitute PQ signalling or inject HDR10-only metadata as a generic HDR shortcut.
- [x] Apply and verify an HLG-appropriate colour/luminance treatment for the EU Icon and backing plate in both excerpts and the full Labelled Copy. Confirm that image content outside the Label has not undergone an unintended transfer-function conversion.
- [x] Retain supported source container/codec and tracks, visibility settings, fixed position, atomic replacement and approval behaviour. Stop and ask when preservation cannot be established, with no automatic HLG-to-SDR or HLG-to-PQ conversion.
- [x] Independently inspect and decode the produced video, and report visual validation separately from metadata validation. Clearly record unavailable HDR-display or native-platform verification.
- [x] Demonstrate successful HLG labelling and preview, missing-capability handling and an unsupported-profile case. Run relevant HDR10 and SDR regressions to prevent the shared HDR path from conflating profiles.
- [x] Update skill guidance, workflow evaluations and documented support with the combinations actually verified.

## Comments

New validated path `mp4-hevc-hlg`: MP4, HEVC Main 10, `yuv420p10le`, BT.2020 / `arib-std-b67` / `bt2020nc` / limited range (else `colour_not_validated`). It is a data entry beside `mp4-hevc-hdr10` and shares its whole path: libx265 at CRF 14, the `hvc1`/`hev1` tag kept, tracks kept, rotation and variable timing stopping, the same `needs` (renamed `HDR_FILTERS` / `HDR_PIXEL_FORMATS`). The path's `signal` (`pq` or `hlg`) is the only switch. No mastering display is required. No MOV twin.

- **Label:** the overlay is scaled to 0.75 (BT.2408 HDR reference white for HLG) in signal space, then composited in 10-bit with `overlay=format=yuv420p10` as for PQ. Measured: the plate is at code 720 (expected 721), the brightest Label sample is 727, and outside the Label the mean change is 1.07 codes with a level shift of 0.05.
- **Signalling:** the VUI keeps `arib-std-b67`, so the alternative transfer characteristics SEI (`atc-sei`) isn't needed and isn't written. It exists for streams whose VUI says `bt2020-10`. libx265 gets `-x265-params` with exactly the source's static metadata. For a source without any, that is only `log-level=error`, so no HDR10 SEI is added. A source with a mastering display keeps it. A source with content light levels gets MaxCLL/MaxFALL raised for the Label at the luminance 75% HLG has on the mastering display's peak: the BT.2100 system gamma for that peak, 1000 cd/m2 when no peak is declared. That gives 203 cd/m2 at 1000 and about 581 at 4000. Measured: `-color_trc` and x265's `transfer=` can't override the frames' own transfer in this ffmpeg 9 build, so the negative test uses `setparams` to retag the output as PQ.
- **Validation:** `colour` proves the transfer is still HLG. `hdr_metadata` now compares the copy's static metadata with exactly what is expected, so for HLG it expects none unless the source has it. `hdr_picture` and `label_level` are shared with HDR10, with the 0.75 level. Wrapped-ffmpeg tests retag the copy as PQ, inject HDR10 master-display and max-cll, change the levels, and leave the Label at peak. Each is caught, and the previous copy is kept.
- **Previews:** `sdr_view` has an HLG branch: the inverse OETF and system gamma 1.2, per channel, normalised to 75% HLG, then the shared roll-off, BT.2020→709 and sRGB. Applying the gamma per channel is exact for greys; BT.2100 applies it to luminance, so saturated colours shift a little. This rendering also drives auto Icon Colour sampling. Tests: reference white renders near white, and 50% HLG renders at about 137 (it would be about 179 through PQ). Excerpts are real HLG through `render_command`. `hdr_note` is per profile.
- **Stops:** HLG with HDR10+ (real x265 `dhdr10-info` fixture) gives `hdr_not_validated`. HLG in MOV gives `codec_not_validated`. HLG with BT.709 primaries gives `colour_not_validated`. A rotated HLG video gives `rotation_not_validated`. A missing libx265 gives `capability_missing`, and `video-tools` reports it.
- **Regressions:** the HDR10 tests were rerun and pass. The old `test_hlg_and_sdr_hevc_have_no_path_yet` became `test_sdr_hevc_has_no_path`.
- **Evidence:** all automated, on real libx265 HLG fixtures. I viewed one tone-mapped HLG preview frame. No HDR display or native platform/player was used, and `video.hdr.note` says so.
- **Left out:**
  - No test for variable-frame-rate HLG. It stops through the path's `preserves`, as HDR10 does.
  - No workflow-eval scenario: the eval suite has no video scenarios to extend.
  - The capability test removes only libx265, not a filter.
