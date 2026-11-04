// Runs the React label component an eval scenario produced, in jsdom.
//
//   node run.mjs <component.jsx> <page.jsx>
//
// Bundles the component and the page that uses it with esbuild (styles are
// dropped, images inlined), renders the page and two instances of the
// component, and replays what a visitor does on the second layer. Prints one
// JSON object; test_skill_evals.py judges it. A bundle or render error is
// printed as {"error": "..."}.

import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import * as esbuild from "esbuild";
import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const [component, page] = process.argv.slice(2).map((p) => resolve(p));

const dom = new JSDOM("<!doctype html><html><body></body></html>", { pretendToBeVisual: true, url: "http://localhost/" });
for (const key of Object.getOwnPropertyNames(dom.window)) {
  if (key in globalThis) continue;
  try { globalThis[key] = dom.window[key]; } catch { /* a getter jsdom refuses outside a page */ }
}
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function fail(error) {
  console.log(JSON.stringify({ error: String(error && error.stack ? error.message : error) }));
  process.exit(0);
}

let mod;
try {
  // One bundle, so the component, the page and the renderer share one React.
  const entry = [
    `import AiLabel from ${JSON.stringify(component)};`,
    `import App from ${JSON.stringify(page)};`,
    `export { AiLabel, App };`,
    `export { createRoot } from "react-dom/client";`,
    `export { act, createElement } from "react";`,
  ].join("\n");
  const built = await esbuild.build({
    stdin: { contents: entry, resolveDir: dirname(page), loader: "jsx" },
    bundle: true,
    write: false,
    format: "cjs",
    platform: "browser",
    jsx: "automatic",
    logLevel: "silent",
    nodePaths: [resolve(here, "node_modules")],
    loader: {
      ".js": "jsx", ".jsx": "jsx", ".ts": "tsx", ".tsx": "tsx",
      ".css": "empty", ".scss": "empty",
      ".png": "dataurl", ".jpg": "dataurl", ".jpeg": "dataurl", ".webp": "dataurl", ".svg": "dataurl",
    },
    define: { "process.env.NODE_ENV": '"development"' },
  });
  const module = { exports: {} };
  new Function("module", "exports", built.outputFiles[0].text)(module, module.exports);
  mod = module.exports;
} catch (error) {
  fail(error);
}

const { AiLabel, App, createRoot, act, createElement } = mod;
const consoleError = console.error;
console.error = () => {}; // React's development warnings are not what is judged

function render(element) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  act(() => createRoot(container).render(element));
  return container;
}

function fire(target, event) {
  act(() => { target.dispatchEvent(event); });
}

const enter = (el) => fire(el, new window.MouseEvent("mouseover", { bubbles: true, relatedTarget: document.body }));
const leave = (el) => fire(el, new window.MouseEvent("mouseout", { bubbles: true, relatedTarget: document.body }));
const escape = (el) => fire(el, new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
const click = (button) => { button.focus(); fire(button, new window.MouseEvent("click", { bubbles: true })); };

function isHidden(el) {
  for (let node = el; node && node !== document.body; node = node.parentElement) {
    if (node.hidden || node.hasAttribute("hidden") || window.getComputedStyle(node).display === "none") return true;
  }
  return false;
}

// A fresh label, with its button and the layer the button controls.
function label(props = {}) {
  const container = render(createElement(AiLabel, { label: "Generated with AI", details: "Made with AI.", ...props }));
  const button = container.querySelector("button[aria-controls]");
  const layer = button && document.getElementById(button.getAttribute("aria-controls"));
  return { container, button, layer };
}

function state({ button, layer }) {
  return { expanded: button.getAttribute("aria-expanded") === "true", hidden: isHidden(layer) };
}

const result = {};
try {
  const pageView = render(createElement(App));
  result.page_shows_a_label = [...pageView.querySelectorAll("img")].some((img) => /ai-basic-/.test(img.getAttribute("src") || ""))
    || pageView.querySelector("button[aria-controls]") !== null;

  const light = label();
  const dark = label({ background: "dark" });
  result.has_button = Boolean(light.button && light.layer && dark.button && dark.layer);
  if (!result.has_button) {
    console.log(JSON.stringify(result));
    process.exit(0);
  }
  result.ids_differ = light.button.getAttribute("aria-controls") !== dark.button.getAttribute("aria-controls");
  const icon = (c) => (c.container.querySelector("img") || { getAttribute: () => "" }).getAttribute("src") || "";
  result.light_icon = icon(light);
  result.dark_icon = icon(dark);
  result.starts_closed = state(light);

  const hover = label();
  enter(hover.button);
  const hovered = state(hover);
  leave(hover.button);
  result.hover = [hovered, state(hover)];

  const pin = label();
  click(pin.button);
  const clicked = state(pin);
  leave(pin.button);
  const left = state(pin);
  click(pin.button);
  result.click = [clicked, left, state(pin)];

  const inside = label();
  click(inside.button);
  escape(document.activeElement || document);
  result.escape_inside = { ...state(inside), focus_on_button: document.activeElement === inside.button };

  const outside = label();
  const elsewhere = document.createElement("button");
  document.body.appendChild(elsewhere);
  elsewhere.focus();
  enter(outside.button);
  escape(elsewhere);
  result.escape_outside = { ...state(outside), focus_kept: document.activeElement === elsewhere };
} catch (error) {
  console.error = consoleError;
  fail(error);
}
console.log(JSON.stringify(result));
