# Updating references and alt text

A **Labelled Copy** helps only if the project actually shows it. After you produce one for an image that sits inside the project you are working in, point the project's references to it, make its alt text say the image is AI-generated or AI-modified, and tell the user which references you couldn't update.

Do this once the Labelled Copy is final (the user approved the preview, or said they don't need one), for every Labelled Copy, including each one of a batch. Skip it only when the user said to leave their pages alone. The original stays where it is and keeps its bytes; only the pages and files that use it change. They are edited in place, because version control covers undo.

The project root is the one the user named; otherwise the root of the git repository you work in, or the folder you work in when there is no repository. Use the same `--root` in every command.

## Steps

1. **Find the references.** Run:

   ```
   uv run <skill folder>/scripts/label_tool.py references <image> --root <project root>
   ```

   `<image>` is the original, not the Labelled Copy. When the Labelled Copy existed before this run (the image was labelled again), the tool doesn't find pages already showing it: search the project for the copy's file name too, and check those alts in step 3. The tool searches the project's HTML, Markdown, styles, templates, source files (JavaScript and TypeScript, Python, Ruby, Go, Java, Rust, PHP, C#) and data files (not dependencies, build output or hidden folders), changes nothing, and prints JSON with:
   - `labelled_copy`: the Labelled Copy's path;
   - `updatable`: each reference that resolves to the original, with its `file` (relative to the project root), `line`, `kind`, the `reference` as written, its `replacement` pointing to the Labelled Copy, the image's current `alt` text (for `markdown-image` and `html-img`; `null` when there is none or when it is computed), and `alt_expression`: the raw computed alt of an `<img>` as written, such as `{title}` in JSX or `"title"` for a Vue `:alt`, else `null`. The `kind` is one of:
     - `markdown-image`: a Markdown image, `![alt](path)`;
     - `markdown-definition`: a reference definition, `[r]: path`, that reference-style images such as `![alt][r]` use. Its `images` lists each of them, with its `line` and `alt`;
     - `html-img`: an `<img>` tag or JSX element;
     - `html-source`: a `<source srcset>` inside a `<picture>`, which has no alt of its own;
     - `link`: a link to the image, such as `[full size](path)` or `<a href>`, rather than the image shown;
     - `other`: anything else, such as an import, a CSS `url()`, a data or front-matter field.
   - `not_updatable`: each reference it found but can't safely change, with its `file`, `line`, `reference` and `reason`: `dynamic` (the path is built from a variable or template expression), `external` (a URL on another host, such as a CDN or CMS), `unresolved` (the path leads to no file in the project, such as a build alias or a moved file) or `shared` (a Markdown link definition that both an image and a link use: give the image its own definition pointing to the Labelled Copy, and leave the link's on the original).

   Done when the command exits 0. On an error, no reference was searched: for `outside_project`, check `--root` and the original's path and run again; for `no_labelled_copy`, finish `references/image.md` first; otherwise tell the user what `error.message` says, in plain words, and report that the references were not updated.
2. **Point the references to the Labelled Copy and add the mention to their alt text.** The mention says the image is AI-generated or AI-modified: pass the wording of its Icon Variant. Run `references` again with `--apply`:

   ```
   uv run <skill folder>/scripts/label_tool.py references <image> --root <project root> --apply --wording <generated|modified>
   ```

   It writes each page's mention from label_tool's wording table (in English "Image generated with AI" or "Image modified with AI"), in each **page's language**, picked page by page as `references/text.md` (**Wording**) describes; add `--lang <code>` when the user named the language of every page. A page whose language the tool can't tell, or one outside its table, keeps its path change and goes to `needs_hand_edit` with the reason: add its mention by hand in step 3.

   To give a mention yourself, add `--alt-mention "<mention>"` for every page, or `--alt-mention <file>=<mention>` for one page, with `file` as `updatable` gives it. Either wins over the table for the pages it covers. The tool changes only Markdown and HTML image references and their alt text, and prints:
   - `applied`: each reference now pointing to the Labelled Copy. A `link` is left alone: it leads to the file rather than showing it, so it keeps pointing to the original.
   - `alt_updated`: each alt text with the mention added after the existing description, in brackets, as it now reads, for example `![A trail among yellow larches (Image generated with AI)](images/hero.ai-label.png)`. An empty or missing alt becomes the mention alone; suggest the user add a description too.
   - `alt_unchanged`: alts that already mention AI. Read each one against the wording now settled: keep a mention that matches it, replace one that says the other kind of involvement (generated for modified, or the reverse), and add the mention by hand when the alt names AI without saying how the image was made.
   - `needs_hand_edit`: references whose alt the tool can't edit safely, each with its `reason`, and every `other` reference, which the tool doesn't change at all because it can't tell whether it shows the image (it also carries the `replacement` it would have written). Handle them in step 3.

   Done when the command exits 0. If it fails with `overlapping_edits`, no page in the project was changed: edit the page the message names by hand (its references to the Labelled Copy, and their mentions), then run step 1 and this step again for the rest. On `internal` or another error, pages written before it may already be changed: check each file of step 1's `updatable` list, finish or report what each still needs, and report the error.
3. **Finish the alt texts the tool left.** For each entry of `needs_hand_edit`, add the mention by hand, in that page's language. Print it with:

   ```
   uv run <skill folder>/scripts/label_tool.py wording --wording <generated|modified> --document <page>
   ```

   Use its `image`; for `language_unknown` or `language_not_listed`, do as `references/text.md` (**Wording**) says. Then:
   - For an `html-source`, edit the `alt` of the `<img>` inside the same `<picture>`: it is the alt shown for every source.
   - For an `other` reference (an import, a CSS `url()`, a data or front-matter field, a mention in prose), read it first. If it shows the image (an import an `<img>` uses, a CSS background, a front-matter `image:` field), change its path to its `replacement`, then find where the image is shown and has alt text, such as `<img src={hero} alt="...">` or an `image_alt` field next to it, and add the mention there; a CSS background has no alt text. If it only mentions the file (prose, a code example), leave it.
   - For a `not_updatable` entry whose reason is `shared`, give the image its own reference definition pointing to the Labelled Copy, keep the link's definition on the original, and add the mention to the image's alt.
   - For a computed alt (`alt_expression`), never replace the expression: append the mention to it, as in ``alt={`${title} (Image generated with AI)`}`` for `alt={title}`. If you can't append to it safely, leave it and list it under **References not updated** with the mention to add by hand.

   Add no marker comment: the Labelled Copy carries the Label itself. Done when each image now showing the Labelled Copy has the mention in its alt text, where it has alt text at all.
4. **Look for what the tool can't see.** The tool finds only references that contain the image's file name. Tell the user, too, about places that may show the image and that you can't edit from here:
   - paths built entirely at run time, without the file name (`${slug}.png`, an image picked from a list);
   - a CMS, a database or a media library (signs: a CMS config such as `admin/config.yml`, a Contentful, Sanity or WordPress client, image URLs fetched from an API);
   - copies already uploaded elsewhere, such as social networks or a newsletter.

   Mention only those you have a sign of in the project, plus the CMS in general terms.

   Done when you know what to list in the report.

## Report

Add to the report of `SKILL.md` step 5:

- **References updated:** each file and line, the old path and the new one, and the alt text as it now reads;
- **References not updated:** each entry of `not_updatable` you didn't fix in step 3, with its file and line and the reason in plain words ("built from a variable, so I can't tell where it points", "a URL on another host", "points to no file in the project"), and what the user should change there by hand: the file name `<name>.<ext>` to `<name>.ai-label.<ext>`, and the alt text mention; then the places from step 4.

If the tool found no reference at all, say so, and that any place outside the project that shows the image needs the Labelled Copy by hand. Done when the user has both lists.
