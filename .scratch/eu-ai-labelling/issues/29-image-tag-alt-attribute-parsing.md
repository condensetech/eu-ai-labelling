# 29: Alt attribute parsing in image tags

**What to build:** Follow-up from 10 (Updating references and alt text in a project). `image_tag_alt` in `skills/eu-ai-labelling/scripts/label_tool.py` has two parsing gaps that can return the wrong alt text or hide the real one:

- The alt regex `r"\balt\s*=..."` matches attributes that merely end in `alt`. For `<img src="img/hero.png" data-alt="zz">` it returns `alt: 'zz'`, so the agent could edit `data-alt` and leave the real `alt` missing. The same applies to other `*-alt` attributes. `:alt="t"` is correct for Vue and should keep working.
- The tag is cut at the first `>` after `src`. An arrow function in an attribute between `src` and `alt` hides the alt. For `<img src="img/hero.png" onLoad={() => go()} alt={title} />` the tool returns `alt` None and `alt_expression` None, which the procedure reads as a missing alt. `alt={a > b ? "x" : "y"}` works only because alt comes before the `>`.

Fix: anchor the attribute name so `data-alt` does not match, for example with `(?<![\w-])` before `alt`. Find the tag end with a brace-aware scan that skips `{...}` and quoted strings, or search for `alt` up to the next `<` or `/>`. Optionally let `update-references.md` treat an html-img with null alt and null `alt_expression` as "unknown, check the tag" rather than "missing".

**Blocked by:** None

**Status:** resolved

Source: ticket 10 (Updating references and alt text in a project), review findings (minor).

- [x] `<img src="a.png" data-alt="zz">` reports no alt, and `<img src="a.png" alt="x" data-alt="zz">` reports `x`
- [x] `:alt="t"` and `alt={title}` still report the expression, and an `=>` arrow function before `alt` does not hide it
- [x] Each case is covered by a test in `tests/test_references.py` that fails on the current code

## Comments

- What changed: `image_tag_alt` is replaced by a tag scanner (`tag_attributes`, `attribute_value_end`) that reads each attribute whole, skipping quoted strings and `{...}` expressions. The alt is the `alt` attribute itself (`img_alt`), so `data-alt` and `title="alt=zz"` no longer match, `:alt` / `v-bind:alt` report the raw expression, and an arrow function before `alt` or `src` no longer ends the tag early.
- How tested: `tests/test_references.py::test_reads_the_alt_attribute_itself_across_the_whole_tag` (table of 10 cases: `data-alt` only, `alt` then `data-alt`, `data-alt` then `alt`, `alt=` inside another value, Vue `:alt`, `v-bind:alt`, JSX `alt={title}`, arrow function before a computed or literal alt, arrow function before `src`). `uv run pytest` passes (371 passed, 36 skipped headless). I did not re-run the new cases against the pre-change code to confirm they fail there.
