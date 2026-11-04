# 58: Evals that can fail

**What to build:** Several eval checks pass broken output: the React eval greps the component's source (a no-op click handler, a missing import or invalid JavaScript all pass), the image eval accepts any rectangle with the icon's aspect, and "asks which corner" passes a reply that gives up without asking.

Fix:

- run the React component: a locked harness under `tests/evals/site/` (esbuild, jsdom, react) bundles it, renders two instances and replays hover, click, Enter, Space, pinning and Escape (focus inside and outside); ids are unique and the icon follows the background. Only with the model evals, so the fast suite stays offline;
- compare the burned-in region with the official icon rendered by resvg at the burned-in size, plate allowed; a plain rectangle is a negative control;
- "asks which corner" needs a question (a question-tool call or a question in the reply); the give-up reply is a negative control.

**Blocked by:** 57

**Status:** resolved

Source: review of the skill (2026-11-04); maintainer: "proceed".

- [x] Each weak check rejects its negative control
- [x] The fast suite stays offline (the site checks skip without the harness)

## Comments

- What changed: `tests/evals/site/` holds a locked harness (esbuild 0.25.0, jsdom 24.1.1, react and react-dom 18.3.1) and `run.mjs`, which bundles the component with the page that uses it, renders the page and two instances, and replays hover, click (pinned until the next click), Escape with focus inside (closes, focus back on the button) and Escape with focus elsewhere (closes, focus kept). `check_site_component` runs it for a `.jsx` or `.tsx` component and keeps the source checks for other frameworks; without `npm ci --prefix tests/evals/site` the React checks skip. CI installs the harness.
- `helpers.icon_match` renders the official icon with resvg (now a test dependency) at the size found and compares the pill's pixels, in black or white, by intersection over union; a burned-in icon scores about 0.95 (with or without a plate), the other variant or a plain rectangle about 0.8, and the bar is 0.9. The evals, the headless checks and `test_apply.py` use it in place of the pill's aspect alone.
- `assert_asks_which_corner` needs a question: in the reply, or an AskUserQuestion call.
- Negative controls: a no-op click handler, invalid JavaScript, Escape heard only inside the label, a page that doesn't import the component, a black rectangle in place of the icon, and a reply that gives up without asking which corner.
- How tested: offline suites 488 passed, 32 skipped (model). Headless with Sonnet: `react-site-component` (the model's own component built and run in jsdom, every behaviour correct), `named-variant-on-a-photo` and `face-swap-authentic-photo` (icon matched in the pixels) pass. The first React run showed the verdict check catching "`label` is required" in a prop list; a verdict now needs an article before "label" ("a label is required"), and the prop sentence is a canned case that must pass.
