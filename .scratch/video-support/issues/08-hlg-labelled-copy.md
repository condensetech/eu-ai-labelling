# 08: Produce an HLG Labelled Copy

**What to build:** A user can label a supported HLG video using the HDR workflow while preserving HLG's own transfer and colour characteristics rather than converting it to HDR10 or SDR.

**Blocked by:** 07 - Produce an HDR10 Labelled Copy.

**Status:** ready-for-agent

- [ ] Extend the established HDR rendering, preview and validation path with a documented, validated HLG profile and a real HLG source fixture. Check the capabilities required by that specific path before rendering.
- [ ] Preserve the source's required bit depth, HLG transfer function, colour primaries, matrix/range and applicable metadata. Do not substitute PQ signalling or inject HDR10-only metadata as a generic HDR shortcut.
- [ ] Apply and verify an HLG-appropriate colour/luminance treatment for the EU Icon and backing plate in both excerpts and the full Labelled Copy. Confirm that image content outside the Label has not undergone an unintended transfer-function conversion.
- [ ] Retain supported source container/codec and tracks, visibility settings, fixed position, atomic replacement and approval behaviour. Stop and ask when preservation cannot be established, with no automatic HLG-to-SDR or HLG-to-PQ conversion.
- [ ] Independently inspect and decode the produced video, and report visual validation separately from metadata validation. Clearly record unavailable HDR-display or native-platform verification.
- [ ] Demonstrate successful HLG labelling and preview, missing-capability handling and an unsupported-profile case. Run relevant HDR10 and SDR regressions to prevent the shared HDR path from conflating profiles.
- [ ] Update skill guidance, workflow evaluations and documented support with the combinations actually verified.
