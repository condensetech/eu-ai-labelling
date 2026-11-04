# 57: Cut what no scenario needs

**What to build:** The review found options no scenario or README use case needs, and one that rewrites more than it should.

Fix:

- `apply --colour` takes `auto`, `black` or `white`; the 50% Icon Colours go from the CLI and the docs (the official SVGs stay vendored, as the archive ships them);
- `references --apply` no longer rewrites `other` references (imports, CSS, data files, prose): they go to `needs_hand_edit`, still listed by discovery;
- a creative work is labelled with a caption or burn-in: the "icon next to the image" option and `snippet --as icon` go, and alt text is no longer a Label of its own, only the accessible mention added with a caption or burn-in;
- `references/site.md` drops `background=auto`, `iconAlt` and the pre-Vue-3.5 id fallback.

**Blocked by:** 56

**Status:** resolved

Source: review of the skill (2026-11-04); maintainer: "proceed".

- [x] Each cut is gone from the tool, the references, the README and the tests
- [x] `other` references are reported for a hand edit, not rewritten

## Comments

- What changed: `apply --colour` takes `auto`, `black` or `white`; the `null` contrast branch is gone (the 50% SVGs stay vendored, and the GLOSSARY says why they aren't applied). `references --apply` leaves `other` references untouched and lists them in `needs_hand_edit` with the `replacement` it would have written; `update-references.md` step 3 says to read each one and change only those that show the image. `snippet --as icon` is gone; `creative-work.md` is the caption plus an alt text mention (no marker on the alt, since the caption carries it); SKILL.md step 4 routes only the caption there. `site.md` drops `iconAlt`, `background=auto` and the pre-Vue-3.5 id fallback; the canned React component follows.
- How tested: `test_apply.py` refuses `black-50` and `white-50` as a usage error; `test_references.py` keeps a CSS `url()`, an import and a prose mention byte for byte and lists them for a hand edit; the snippet tests cover `label` and `caption` in both formats, light and dark. Offline suites: 481 passed, 32 skipped (model).
