# Adding a label component to a site

A web developer wants a reusable **Label** component in their site. You copy the official **Basic** EU Icon SVGs into the project and adapt the one framework-agnostic reference implementation below to the project's stack. No per-framework component ships with the plugin: you write it into the project, in its own conventions.

The component shows:

1. the **Basic** EU Icon (the official "AI" icon), in the **Icon Colour** that suits the background it sits on;
2. a plain-language **text label** next to it, in the page's language, passed in so the site can translate it;
3. optionally, a **second layer**: a short explanation of what AI generated or modified, opened on hover or click, and operable by keyboard and screen reader.

## Steps

1. **Read the project.** Find its stack (React, Vue, Astro or plain HTML: check `package.json` dependencies, `astro.config.*`, `vite.config.*`, `.vue`/`.astro`/`.jsx`/`.tsx` files), whether it uses TypeScript, how it styles components (plain CSS files, CSS modules, Tailwind, scoped `<style>`), where components live (`src/components/` is common), its static folder (`public/` for Vite, Next.js and Astro; otherwise the folder the site already serves images from) and whether it has an i18n setup. For a stack other than these four, adapt the same reference to it by the same rules. **An Existing Label:** while scanning, look for the project's own AI-label component or AI disclaimer: an "AI generated" badge, an AI icon, a notice next to AI-made content or in the footer. When you find one, follow **An Existing Label** in SKILL.md before step 2; labelling anyway adds this plugin's component beside it and leaves the existing one untouched. When you find none, say nothing about Existing Labels. Done when you know the framework, the component folder, the static folder, the styling convention and any Existing Label you found.
2. **Copy the icons** into the static folder (see **Copy the icons**). Done when both SVGs exist in the project.
3. **Write the component** from **Reference implementation**, following **Adapting it**. Done when the component file (and its stylesheet, if separate) exists in the project.
4. **Use it** where the user asked (for example next to an AI-generated image or at the top of an AI-written article), with the text label in that page's language (see **Wording**) and, if the user wants the second layer, a `details` text saying what AI generated or modified there. The wording of each use, `generated` or `modified`, comes from what the user said of that content; when they haven't said, ask SKILL.md step 2's question about it and wait. If the user named no place, show a usage example and ask where it goes. Done when the component is used where asked, or the user has the example.

## Copy the icons

Copy the Black and White Basic icons, byte for byte and keeping their names:

```
uv run <skill folder>/scripts/label_tool.py copy-icons --to <static folder> --colour both
```

Identical copies already there are kept. The component refers to them by the URL the site serves them at: a file in `public/` is served at the site root, so `public/ai-basic-black.svg` is `/ai-basic-black.svg`.

## Wording

The icon is always **Basic**: it stays the official English "AI" artwork. The text label says **generated** or **modified**, as the user said of the content it marks, in the page's language. Print it from label_tool's wording table (English, Italian, French, Spanish and German):

```
uv run <skill folder>/scripts/label_tool.py wording --wording <generated|modified> --document <page>
```

Its `label` is the component's `label` (in English "Generated with AI" or "Modified with AI"). `<page>` is a page the component appears on. Which language the tool picks, and when you add `--lang` or translate the label yourself, is in `references/text.md` (**Wording**). For a site with an i18n setup, run it once per language the site has, with `--lang <code>` for each, to fill the message keys.

The second layer names what AI made there, plainly: "The illustration in this article was generated with AI." / "The cover photo was edited with AI: the background was replaced."

## Reference implementation

Plain HTML and CSS, with a few lines of script for the second layer. This is the version **with a second layer**:

```html
<span class="eu-ai-label">
  <button type="button" class="eu-ai-label__toggle" aria-expanded="false" aria-controls="eu-ai-label-details-1">
    <img class="eu-ai-label__icon" src="/ai-basic-black.svg" alt="" width="32" height="32">
    <span class="eu-ai-label__text">Generated with AI</span>
  </button>
  <span class="eu-ai-label__details" id="eu-ai-label-details-1" hidden>The illustration in this article was generated with AI.</span>
</span>

<script>
  for (const label of document.querySelectorAll(".eu-ai-label")) {
    const toggle = label.querySelector(".eu-ai-label__toggle");
    const details = label.querySelector(".eu-ai-label__details");
    if (!toggle || !details) continue;
    let pinned = false; // opened by click or keyboard: stays open until closed
    const show = (open) => {
      toggle.setAttribute("aria-expanded", String(open));
      details.hidden = !open;
    };
    toggle.addEventListener("click", () => { pinned = !pinned; show(pinned); });
    label.addEventListener("mouseenter", () => show(true));
    label.addEventListener("mouseleave", () => { if (!pinned) show(false); });
    // On the document, not the label: hover can open the layer while focus is elsewhere.
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || details.hidden) return;
      const focusInside = label.contains(document.activeElement);
      pinned = false;
      show(false);
      if (focusInside) toggle.focus();
    });
  }
</script>

<style>
  .eu-ai-label { position: relative; display: inline-flex; align-items: center; font-size: 0.875rem; line-height: 1.25; }
  .eu-ai-label__toggle { display: inline-flex; align-items: center; gap: 0.4em; padding: 0.25em 0.4em; margin: 0; border: 0; background: none; color: inherit; font: inherit; cursor: pointer; }
  .eu-ai-label__toggle:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
  /* The official SVG pads the round icon with 16-20% of white space: enlarge it and pull the padding in, so the visible icon is about 1.25em. */
  .eu-ai-label__icon { flex: none; width: 1.94em; height: 1.94em; margin: -0.345em -0.384em -0.345em -0.305em; }
  .eu-ai-label__details { position: absolute; top: 100%; left: 0; z-index: 10; width: max-content; max-width: min(20rem, 90vw); padding: 0.5em 0.75em; border: 1px solid #767676; border-radius: 0.25em; background: #fff; color: #1d1d1b; }
  .eu-ai-label__details[hidden] { display: none; }
</style>
```

**Without a second layer**, there is nothing to open, so there is no button and no script: the icon and the text label sit side by side.

```html
<span class="eu-ai-label">
  <img class="eu-ai-label__icon" src="/ai-basic-black.svg" alt="" width="32" height="32">
  <span class="eu-ai-label__text">Generated with AI</span>
</span>
```

(Add `gap: 0.4em` to `.eu-ai-label` for this form.)

What makes it accessible, and must survive the adaptation:

- The text label is real, visible text next to the icon, and it names the content. The icon is an `<img>` with `alt=""`, so the button reads "Generated with AI", not "AI Generated with AI".
- The second layer opens from a native `<button type="button">`: it is focusable, and Enter and Space open it with no extra code.
- `aria-expanded` on the button tells screen readers whether the second layer is open, and `aria-controls` names it by `id`. The second layer comes right after the button in the page, so a screen reader reads it next once it is open.
- Hover opens it; leaving closes it unless it was opened by click or keyboard. Escape always closes it, wherever focus is, so content shown on hover can be dismissed (WCAG 1.4.13); when focus was inside the label, it returns to the button.
- There is no gap between the label and the second layer: the layer starts at the label's bottom edge (`top: 100%`, no margin), so the pointer can move onto it without leaving the label, and content shown on hover stays hoverable (WCAG 1.4.13). The button's own padding keeps the layer clear of the text. Keep it that way when restyling: space inside the layer goes in its `padding`, never in a `margin` outside it.
- The `id` is unique on the page.

## Adapting it

Turn the reference into one component in the project's framework. Its inputs:

- `label`: the text label (required, no hard-coded wording inside the component), e.g. "Generated with AI".
- `background`: `light` (the default) shows `ai-basic-black.svg`, the Black Icon Colour; `dark` shows `ai-basic-white.svg`, the White Icon Colour. Pick by the background the label sits on, not by the page theme alone.
- `details`: the second layer's text (or content). Optional: without it, render the form **Without a second layer**.

Rules for every framework:

- The component has **no runtime dependency on the plugin**. Reference only the SVGs copied into the project, by the URL the site serves them at; never a path into the skill folder or the plugin, never an import from it, and add no npm package.
- If the project has an i18n setup (react-i18next, react-intl, vue-i18n, Astro's i18n routing, a messages file), pass `label` and `details` from its message keys and add the keys for the site's languages; otherwise pass plain strings in the page's language.
- Keep the class names, or follow the project's convention (CSS modules, Tailwind classes, scoped styles) with the same rules. Follow the project's language: TypeScript when it uses TypeScript, with typed props.
- Keep every accessibility point listed above.

Per framework:

- **React** (and Next.js): a function component, e.g. `src/components/AiLabel.jsx` (`.tsx` with TypeScript) plus `AiLabel.css` imported by it. Make the `id` with `useId()`. Keep `open` in `useState` and a `pinned` ref (`useRef`) for whether a click opened it; render the details with `hidden={!open}` and set `aria-expanded={open}`; attach `onMouseEnter` and `onMouseLeave` to the wrapper and `onClick` to the button; while `open`, listen for Escape on `document` in a `useEffect` (removed in its cleanup), and on Escape unpin, close and, when focus was inside the wrapper, focus the button through a ref. In Next.js App Router, add `"use client"` at the top. Images in `public/` are served from `/`.
- **Vue**: a single-file component, e.g. `src/components/AiLabel.vue`, with `defineProps`, a `ref` for `open` and a plain `pinned` flag for whether a click opened it, the id from `useId()`, `:aria-expanded="open"`, `v-show` or `:hidden` on the details, `@mouseenter` and `@mouseleave` on the wrapper and `@click` on the button; a `keydown` listener on `document` added in `onMounted` and removed in `onUnmounted`; on Escape while open, unpin, close and, when focus was inside the wrapper, focus the button through a template ref. Put the CSS in `<style scoped>`. With Vite, images in `public/` are served from `/`.
- **Astro**: `src/components/AiLabel.astro` with the props in `Astro.props`, the markup from the reference, the CSS in its `<style>` and the reference script in a `<script>` (Astro bundles it once per page and the loop handles every label). Keep the script's behaviour unchanged: a click-opened layer stays pinned on leaving, and Escape, wherever focus is, unpins and closes it, returning focus to the button when it was inside the label. Make the `id` unique per instance, e.g. `` `eu-ai-label-${crypto.randomUUID()}` `` in the frontmatter. Images in `public/` are served from `/`.
- **plain HTML**: paste the markup where the label goes, numbering each `id` (`eu-ai-label-details-1`, `-2`, ...); put the CSS in the site's stylesheet and the script once per page, before `</body>` or in the site's script file.

## Done

The step is done when the project holds the two copied SVGs and the component, adapted to its stack, with the accessibility points above, and it is used where the user asked (or they have a usage example). When the project has a build or type-check script, run it and fix what it reports; otherwise say in the report that the component wasn't built. Report to the user:

- the component's file(s) and how to use it, with one example per page language you used;
- the copied SVGs' paths and the URLs the component loads them from;
- where you used it, if you did, with the text label and the second layer's text;
- that the component needs nothing from the plugin at runtime;
- each Existing Label found, only when you found one: where it is and what it says.
