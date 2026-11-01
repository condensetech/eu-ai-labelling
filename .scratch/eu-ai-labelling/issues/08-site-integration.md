# 08: Site integration

**What to build:** A web developer asks to add AI labels to their site. The agent adapts one framework-agnostic HTML/CSS reference implementation to the project's stack (React, Vue, Astro or plain HTML) and copies the official SVGs into the project. The component has:
- the Basic icon with a translatable text label;
- correct ARIA attributes;
- an Icon Colour suited to light or dark backgrounds;
- an optional second layer on hover or click explaining what was generated or modified, navigable by keyboard and screen reader.

**Blocked by:** 05

**Status:** resolved

- [x] A site reference file inside the skill folder contains the reference implementation and the adaptation rules
- [x] The generated component has no runtime dependency on the plugin
- [x] The second layer is optional, keyboard-accessible and announced to screen readers
- [x] Eval: in a React project, the agent produces a component with ARIA and a translatable label

## Comments

**Built:** the new `references/site.md` holds one framework-agnostic HTML/CSS reference implementation and the rules for adapting it. The component shows the Basic EU Icon as an `<img>` with alt text, next to a visible, translatable text label. Its inputs are `label`, `iconAlt`, `background` (`light` uses the Black Icon Colour, `dark` the White one, and `auto` follows `prefers-color-scheme`) and an optional `details`. With `details`, the second layer opens from a native `<button>` with `aria-expanded` and `aria-controls`. Hover opens it, and a click or the keyboard pins it open. Escape always closes it and returns focus to the button. Without `details`, the component has no button and no script. The procedure copies `ai-basic-black.svg` and `ai-basic-white.svg` into the project's static folder with `cat`. It has rules for React, Vue, Astro and plain HTML, for projects with an i18n setup, and for the component having no runtime dependency on the plugin. In `SKILL.md`, step 1 recognises a **site**. Step 2 gives it the Basic icon and skips the assessment and step 3. Step 4 routes to `references/site.md`, and step 5 reports what it asks. The README documents site integration.

**Tested:** `tests/e2e/test_site_reference.py` checks the shipped reference against this ticket. It runs the copy commands from `site.md` exactly as written and checks that the result matches the official SVGs byte for byte. It also runs the reference script, unchanged and in Node, against the reference markup in a minimal fake DOM. It checks that hover opens the second layer and leaving closes it, that a click pins it open until a second click, and that Escape closes it, unpins it and returns focus to the button. It checks that the React and Vue adaptation rules keep the Escape, focus-return and pinning rules. `test_packaging.py` requires `references/site.md`. New eval scenario `react-site-component.json` (a Vite React project) uses a `site_component` expectation. Canned checks reject eight broken components, four broken pages, copies that are missing or redrawn, and a run that performs the assessment. The eval runner now allows `Write`. The scenario passed one headless run: the agent wrote `src/AiLabel.jsx` and `AiLabel.css`, copied both SVGs into `public/`, and used the component below the hero image.

**Open points:** the second layer's behaviour runs in a fake DOM, not in a browser: native button activation (Enter, Space) and screen-reader announcement are checked on the markup only. The behaviour tests need `node` and are skipped without it. Only React has a headless eval. Vue, Astro and plain HTML are covered by the reference's rules only.

**Follow-up tickets:** 23 (second layer hover gap and button accessible name, `site.md`), 24 (test coverage for site component hover and SKILL routing). The full test suite passes (231 passed, 28 skipped; the skips are the opt-in headless tests).
