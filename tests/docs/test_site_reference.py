"""End-to-end: the site reference gives the agent one accessible label component to adapt.

Site integration has no script: the agent copies the official Basic SVGs
into the web project and adapts the framework-agnostic HTML/CSS reference
implementation in `references/site.md` to the project's stack. These checks
read the shipped reference the way the agent does, run its copy step exactly
as written in a throwaway project, and hold the reference to the ticket: the
Basic EU Icon with a translatable text label, an Icon Colour for light or
dark backgrounds, and an optional second layer that is a keyboard-operable
disclosure announced to screen readers. The reference script runs unchanged
in a small fake DOM. Whether the agent adapts it well to a project is judged
by the headless run in tests/evals (the `site_component` scenario).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

from helpers import SKILL_DIR, fenced, section, step

SITE_MD = SKILL_DIR / "references" / "site.md"


class Elements(HTMLParser):
    """Every element of an HTML fragment with its attributes, plus inline scripts and styles."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict]] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self._raw: str | None = None

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag in ("script", "style"):
            self._raw = tag

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        self._raw = None

    def handle_data(self, data):
        if self._raw == "script":
            self.scripts.append(data)
        elif self._raw == "style":
            self.styles.append(data)

    def find(self, tag: str, **attrs) -> list[dict]:
        return [a for t, a in self.elements if t == tag and all(a.get(k) == v for k, v in attrs.items())]

    def with_class(self, cls: str) -> list[tuple[str, dict]]:
        return [(t, a) for t, a in self.elements if cls in (a.get("class") or "").split()]


def reference() -> Elements:
    snippets = fenced(section(SITE_MD.read_text(), "Reference implementation"), "html")
    assert snippets, "the Reference implementation section has no ```html block"
    parsed = Elements()
    parsed.feed("\n".join(snippets))
    return parsed


def test_reference_shows_the_basic_icon_from_the_projects_copy_with_an_empty_alt():
    parsed = reference()

    icons = [a for t, a in parsed.with_class("eu-ai-label__icon") if t == "img"]
    assert icons, "no <img class=\"eu-ai-label__icon\"> in the reference"
    for icon in icons:
        # Served from the project's own copy, not the plugin.
        assert icon["src"].rsplit("/", 1)[-1] in {"ai-basic-black.svg", "ai-basic-white.svg"}
        assert "skill" not in icon["src"] and "assets/icons" not in icon["src"]
        # The visible text label names the content: an icon name in `alt` would
        # make the button read "AI Generated with AI".
        assert "alt" in icon, "the icon has no alt attribute"
        assert icon["alt"] == "", f"the icon's alt repeats the text label: {icon['alt']!r}"


def test_reference_second_layer_touches_the_label_so_hover_can_reach_it():
    # A margin between the label and the second layer lies outside both boxes:
    # crossing it fires mouseleave and closes the layer (WCAG 1.4.13, hoverable).
    css = "\n".join(reference().styles)
    rule = re.search(r"\.eu-ai-label__details\s*\{([^}]*)\}", css)
    assert rule, "no .eu-ai-label__details rule in the reference CSS"
    assert re.search(r"top:\s*100%", rule.group(1)), "the second layer does not start at the label's bottom edge"
    assert not re.search(r"margin(-top)?\s*:", rule.group(1)), f"a margin opens a gap the pointer must cross: {rule.group(1)}"


def test_reference_text_label_is_visible_and_translatable():
    text = SITE_MD.read_text()
    parsed = reference()

    assert parsed.with_class("eu-ai-label__text"), "no visible text label element"
    rules = section(text, "Adapting it")
    # The strings and the optional second layer are inputs of the component.
    for prop in ("`label`", "`details`", "`background`"):
        assert prop in rules, f"the adaptation rules do not make {prop} a component input"
    wording = section(text, "Wording")
    # The phrases come from label_tool (run as written in test_label_snippets).
    assert "label_tool.py wording" in wording and "`label`" in wording
    assert not re.search(r"^\|", wording, re.M), "the wording table is back in the reference"


def test_reference_second_layer_is_a_keyboard_disclosure_announced_to_screen_readers():
    parsed = reference()

    toggles = [a for t, a in parsed.with_class("eu-ai-label__toggle")]
    assert [t for t, _ in parsed.with_class("eu-ai-label__toggle")] == ["button"], (
        "the second layer must open from a native <button> (focusable, Enter and Space)"
    )
    toggle = toggles[0]
    assert toggle.get("type") == "button"
    assert toggle.get("aria-expanded") == "false"
    details = [a for t, a in parsed.with_class("eu-ai-label__details")]
    assert len(details) == 1
    assert toggle.get("aria-controls") == details[0].get("id"), "aria-controls does not name the second layer"
    assert "hidden" in details[0], "the second layer must start hidden"



# A DOM just big enough for the reference script: the reference's own markup
# as a tree, class selectors, attributes, `hidden`, focus, and events that
# bubble (click, keydown) or not (mouseenter, mouseleave). The script runs
# unchanged against it, then the actions are replayed on the labelled toggle
# and the state after each one is printed as JSON.
FAKE_DOM = r"""
const vm = require("vm");
const { tree, script, actions } = JSON.parse(require("fs").readFileSync(0, "utf8"));
const doc = { activeElement: null, listeners: {}, addEventListener(t, f) { (this.listeners[t] ||= []).push(f); } };
function build(node, parent) {
  const el = {
    tag: node.tag, attrs: { ...node.attrs }, parent, listeners: {},
    get hidden() { return "hidden" in this.attrs; },
    set hidden(v) { if (v) this.attrs.hidden = ""; else delete this.attrs.hidden; },
    getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; },
    setAttribute(n, v) { this.attrs[n] = String(v); },
    addEventListener(t, f) { (this.listeners[t] ||= []).push(f); },
    focus() { doc.activeElement = this; },
    contains(other) { for (let e = other; e; e = e.parent) if (e === this) return true; return false; },
    querySelector(s) { return this.querySelectorAll(s)[0] || null; },
    querySelectorAll(s) { return all(this, s); },
  };
  el.children = node.children.map((c) => build(c, el));
  return el;
}
function all(root, sel) {
  if (!/^\.[\w-]+$/.test(sel)) throw new Error("unsupported selector " + sel);
  const out = [];
  const walk = (el) => el.children.forEach((c) => {
    if ((c.attrs.class || "").split(/\s+/).includes(sel.slice(1))) out.push(c);
    walk(c);
  });
  walk(root);
  return out;
}
const root = build(tree, null);
doc.querySelectorAll = (s) => all(root, s);
doc.querySelector = (s) => all(root, s)[0] || null;
function dispatch(target, type, init, bubbles) {
  const event = { type, target, ...init, preventDefault() {} };
  for (let el = target; el; el = bubbles ? el.parent : null) {
    (el.listeners[type] || []).forEach((f) => f.call(el, event));
  }
  if (bubbles && target !== doc) (doc.listeners[type] || []).forEach((f) => f.call(doc, event));
}
vm.runInNewContext(script, { document: doc, String });
const toggle = doc.querySelector(".eu-ai-label__toggle");
const label = toggle.parent;
const details = label.querySelector(".eu-ai-label__details");
const states = actions.map((action) => {
  if (action === "mouseenter" || action === "mouseleave") dispatch(label, action, {}, false);
  else if (action === "click") { toggle.focus(); dispatch(toggle, "click", {}, true); }
  // A key goes to the focused element, else to the page itself.
  else if (action === "Escape") dispatch(doc.activeElement || doc, "keydown", { key: "Escape" }, true);
  else if (action === "focus-details") doc.activeElement = details; // e.g. a link inside it
  else if (action === "focus-elsewhere") doc.activeElement = root; // a control elsewhere on the page
  else throw new Error("unknown action " + action);
  return { expanded: toggle.getAttribute("aria-expanded"), hidden: details.hidden, focused: doc.activeElement === toggle };
});
console.log(JSON.stringify(states));
"""


class Tree(HTMLParser):
    """An HTML fragment as nested {tag, attrs, children}, for the fake DOM."""

    VOID = {"img", "br", "hr", "input", "meta", "link", "source"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = {"tag": "#root", "attrs": {}, "children": []}
        self._stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": {k: v or "" for k, v in attrs}, "children": []}
        self._stack[-1]["children"].append(node)
        if tag not in self.VOID:
            self._stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._stack[-1]["children"].append({"tag": tag, "attrs": {k: v or "" for k, v in attrs}, "children": []})

    def handle_endtag(self, tag):
        if tag not in self.VOID and len(self._stack) > 1:
            self._stack.pop()


def run_second_layer(actions: list[str]) -> list[dict]:
    """Run the reference script, unchanged, on the reference markup and replay `actions`."""
    snippets = fenced(section(SITE_MD.read_text(), "Reference implementation"), "html")
    tree = Tree()
    tree.feed("\n".join(snippets))
    script = "\n".join(reference().scripts)
    proc = subprocess.run(
        ["node", "-e", FAKE_DOM],
        input=json.dumps({"tree": tree.root, "script": script, "actions": actions}),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


CLOSED = {"expanded": "false", "hidden": True}
OPEN = {"expanded": "true", "hidden": False}


def state(s: dict) -> dict:
    return {"expanded": s["expanded"], "hidden": s["hidden"]}


needs_node = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


@needs_node
def test_reference_second_layer_opens_on_hover_and_closes_on_leaving():
    states = run_second_layer(["mouseenter", "mouseleave"])

    assert [state(s) for s in states] == [OPEN, CLOSED]


@needs_node
def test_reference_second_layer_opened_by_click_stays_open_until_clicked_again():
    states = run_second_layer(["click", "mouseenter", "mouseleave", "click"])

    assert [state(s) for s in states] == [OPEN, OPEN, OPEN, CLOSED]


@needs_node
def test_reference_escape_closes_the_second_layer_and_returns_focus_to_the_button():
    # Opened by hover, with focus inside the second layer (e.g. on a link in it):
    # closing would strand focus on a hidden element.
    hovered = run_second_layer(["mouseenter", "focus-details", "Escape"])
    assert state(hovered[-1]) == CLOSED
    assert hovered[-1]["focused"], "Escape does not return focus to the button"
    # Opened by click: Escape unpins it, so leaving and hovering again behave as before.
    pinned = run_second_layer(["click", "Escape", "mouseenter", "mouseleave"])
    assert [state(s) for s in pinned] == [OPEN, CLOSED, OPEN, CLOSED]
    assert pinned[1]["focused"], "Escape does not return focus to the button"


@needs_node
@pytest.mark.parametrize("focus", [[], ["focus-elsewhere"]], ids=["nothing focused", "focus elsewhere"])
def test_reference_escape_closes_a_hovered_layer_while_focus_is_outside_the_label(focus):
    states = run_second_layer(["mouseenter", *focus, "Escape"])

    assert state(states[-1]) == CLOSED
    assert not states[-1]["focused"], "Escape pulled focus to the button from outside the label"


# The handlers each framework rule must wire, so the adaptation behaves as
# the reference script does in the fake DOM above.
FRAMEWORK_HANDLERS = {
    "React": ("onMouseEnter", "onMouseLeave", "onClick", "`document`", "useEffect"),
    "Vue": ("@mouseenter", "@mouseleave", "@click", "`document`", "onUnmounted"),
    "Astro": ("reference script",),
}


@pytest.mark.parametrize("framework", sorted(FRAMEWORK_HANDLERS))
def test_each_framework_rule_keeps_escape_focus_pinning_and_the_projects_own_icons(framework):
    rules = section(SITE_MD.read_text(), "Adapting it")
    match = re.search(rf"^- \*\*{framework}\*\*.*$", rules, re.M)
    assert match, f"no adaptation rule for {framework}"
    bullet = match.group(0)

    for handler in FRAMEWORK_HANDLERS[framework]:
        assert handler in bullet, f"the {framework} rule does not use {handler}"

    # Keyword anchors only: the wording is free, these behaviours are not.
    for word in ("Escape", "focus", "button", "pinned"):
        assert word in bullet, f"the {framework} rule does not mention {word!r}"
    # No runtime dependency on the plugin: the icons come from the project's own static folder.
    assert "`public/`" in bullet, f"the {framework} rule does not load the icons from the project's `public/`"
    assert not re.search(r"skill folder|assets/icons|plugin", bullet), f"the {framework} rule points into the plugin"


def test_icon_colour_follows_the_background():
    rules = section(SITE_MD.read_text(), "Adapting it")

    assert "`background`" in rules
    light = re.search(r"`light`[^\n]*ai-basic-black\.svg", rules)
    dark = re.search(r"`dark`[^\n]*ai-basic-white\.svg", rules)
    assert light and dark, "light and dark backgrounds do not map to the Black and White Icon Colours"


def test_copy_step_puts_both_official_svgs_in_the_project():
    """Run as written in test_label_snippets; here, that it copies both colours."""
    copy = section(SITE_MD.read_text(), "Copy the icons")
    commands = [line for block in fenced(copy) for line in block.splitlines() if "copy-icons" in line]
    assert len(commands) == 1 and "--colour both" in commands[0] and "--to <static folder>" in commands[0]


def test_the_project_is_checked_for_an_existing_label_while_reading_it():
    """The rule itself lives in SKILL.md (test_existing_label); site.md says where
    the check happens and what an Existing Label looks like in a project."""
    read = step(section(SITE_MD.read_text(), "Steps"), "Read the project")
    assert "**An Existing Label:**" in read, "reading the project doesn't check for an Existing Label"
    check = read.split("**An Existing Label:**", 1)[1]
    for sign in ("AI-label component", "AI disclaimer"):
        assert sign in check, f"the check never names {sign}"
    assert "**An Existing Label** in SKILL.md" in check
    # Labelling anyway adds this plugin's component beside the project's own, never in its place.
    assert "untouched" in check, "the check doesn't keep the project's own label"
    assert "Existing Label" in section(SITE_MD.read_text(), "Done")
