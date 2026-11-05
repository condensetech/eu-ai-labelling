# 04: Choose a fixed position using scenes and previews

**What to build:** A user can assess the Label across changing scenes, correct its fixed position and approve the complete video with a clear understanding of what the previews do and do not establish.

**Blocked by:** 03 - Choose continuous or periodic Label visibility.

**Status:** ready-for-agent

- [ ] Produce representative source frames from different parts of the video and short labelled excerpts using the selected rendering settings. For periodic display, include relevant visible windows and their transitions rather than sampling only times when the Label is absent.
- [ ] Use the samples, existing corner preferences and agent visual inspection to propose one fixed position that avoids obvious interference with faces, text, subtitles and the principal subject. Ask the user when the samples offer no suitable corner; do not move the Label automatically during playback.
- [ ] Keep the contrast backing plate and chosen appearance stable. Honour user adjustments to position and size while retaining the existing minimum-size and fit checks.
- [ ] Make excerpts representative of the eventual Labelled Copy: same Icon Variant, geometry, colour treatment and visibility settings. Report failed sample extraction or unavailable inspection rather than pretending a preview was checked.
- [ ] State that sampling cannot guarantee an unobstructed Label placement in every frame. Provide the full Labelled Copy for final approval; an explicit preview waiver may skip visual review but never bypass output-integrity checks.
- [ ] Rerender and renew approval when the user changes placement or visibility. Preserve the original and any previous valid Labelled Copy if preview generation or rendering fails.
- [ ] Demonstrate multiple-scene footage with competing corner content, periodic visibility, a user correction, an unsuitable-corner case and a preview failure. Update instructions and workflow evaluations to reflect the actual sampling and approval behaviour.
