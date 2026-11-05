# eu-ai-labelling

A plugin for Claude Code and OpenAI Codex that applies the official EU Icons as visible labels on AI-generated or AI-modified content, following Article 50(4) of the EU AI Act and Section 2 of the Code of Practice on transparency of AI-generated content.

> **Not affiliated with the EU.** This project is not affiliated with, endorsed by or connected to the European Commission or any EU institution. The EU Icons are the Commission's; this plugin only applies them.
>
> **Not legal advice.** The plugin helps you apply labels; it does not tell you what the law requires of you and does not certify compliance. Check the official guidance, or ask a lawyer, for your own situation.
>
> **No adherence signal.** Using the EU Icons without signing the Code of Practice doesn't signal adherence to the Code of Practice.

## Install

Claude Code:

```
/plugin marketplace add condensetech/eu-ai-labelling
/plugin install eu-ai-labelling@eu-ai-labelling
```

Run both: the first command only adds the marketplace, the second installs the plugin. Then start a new session (or run `/reload-plugins`) so `/eu-ai-labelling` shows up. To check the install, run `claude plugin list` in a terminal: `eu-ai-labelling@eu-ai-labelling` should be listed as enabled.

Codex:

```
codex plugin marketplace add condensetech/eu-ai-labelling
```

then open `/plugins` in Codex and install **EU AI Labelling**.

The image tool needs [`uv`](https://docs.astral.sh/uv/) (or Python 3.10+ with Pillow and resvg-py installed). Images, documents and sites need no other system packages.

Videos also need [FFmpeg](https://ffmpeg.org/download.html) (`ffmpeg` and `ffprobe`) installed on your machine. The plugin doesn't install it: when it is missing, the agent gives you the install steps for your platform and checks again once you are done.

## Use

There is one entry point, `/eu-ai-labelling` in Claude Code and `$eu-ai-labelling` in Codex; the agent also picks the skill up on its own when you ask it to label content as AI-generated.

Claude Code:

```
/eu-ai-labelling label photo.png as fully AI-generated
/eu-ai-labelling label article.md as fully AI-generated
/eu-ai-labelling add AI labels to my site
```

Codex:

```
$eu-ai-labelling label photo.png as fully AI-generated
$eu-ai-labelling label article.md as fully AI-generated
$eu-ai-labelling add AI labels to my site
```

### Images

`label photo.png as fully AI-generated` writes `photo.ai-label.png` next to the original, with the "AI GENERATED" EU Icon burned in. The original file is left untouched.

The agent looks at the image and puts the icon in the top-right corner when that corner is free. When it isn't, the agent moves the icon to a clean corner, or asks you if no corner is clean. It picks black or white for at least 3:1 contrast, adds an opaque backing plate when neither colour is enough, and shows you a preview before finishing. You can ask for a different corner, size or colour, e.g. "bottom-left, 80 px tall, in white". See [Placement defaults](#placement-defaults).

PNG, JPEG and WebP are supported; the Labelled Copy keeps the original's colour profile and EXIF metadata, and JPEGs are re-encoded at high quality. Animated GIF or WebP, SVG images and other formats are refused.

### Videos

`label clip.mp4 as fully AI-generated` writes `clip.ai-label.mp4` next to the original, with the EU Icon on an opaque backing plate in a fixed corner (top-right unless you ask for another). The agent asks whether you want the Label shown for the whole video or periodically; without a preference, a video up to 60 seconds shows it throughout, and a longer one for 5 seconds from the start and then for 5 seconds every 60 seconds. These are the plugin's defaults, not legal thresholds, and the window and recurrence can be changed. The original file is left untouched. The copy keeps the container, codec, dimensions, frame timing and duration of the original, and copies its audio without re-encoding; the video stream itself is re-encoded to incorporate the Label, so the copy is not bit-identical. Before the copy replaces a previous one, the tool decodes it and checks what it kept.

This version labels SDR videos of any length, with at most one audio track, in these combinations: MP4 or MOV with H.264 video, and WebM with VP9 or VP8 video. The copy stays in the original's container and codec: a MOV stays a MOV and a WebM stays a WebM, never converted to MP4. The container is read from the file, not its extension. Any other video (another codec inside MOV or WebM such as ProRes or AV1, another container, HDR, more tracks, rotation, a variable frame rate), or a combination your FFmpeg build lacks the encoder for, stops before anything is written, and the agent asks you how to proceed: nothing is converted or dropped silently.

### Text

Markdown and HTML documents are labelled in place: `/eu-ai-labelling label article.md as fully AI-generated` adds, below the headline, the Basic "AI" EU Icon, a short text label in the document's own language (e.g. "Generato con IA" for an Italian article) and a hidden `<!-- eu-ai-labelling: generated -->` marker. HTML gets the icon as an accessible inline SVG; Markdown gets an image reference to the official SVG, copied into the project's assets folder. If only part of a document is AI-made, say which part and only that part is labelled.

### Creative Works

When you present an image as an artistic, satirical or fictional work, where an icon inside the picture would get in the way, the skill asks whether you want a caption below the image, in the document or page where it is used, or the icon burned in. The caption uses the Basic "AI" EU Icon, the text label in the document's language and the marker, and the image itself is left untouched. You can also say it up front: `/eu-ai-labelling label satire.png as fully AI-generated, as a caption in post.md`.

### Batches

To label a whole folder, or several images at once: `/eu-ai-labelling label every image in shots/`. Questions are asked once for the batch: answers you give for all files hold for all of them, and per-file questions come up only for the files that differ. Each image still gets its own corner; all images with no clean corner are gathered into one question. At the end you get a summary of every Labelled Copy with its icon and corner, plus any files that were refused (animated images, SVG) or skipped (existing Labelled Copies).

### Sites

To add AI labels to a website: `/eu-ai-labelling add AI labels to my site`. The agent copies the official Basic "AI" SVGs into your project's static folder and writes one label component in your stack (React, Vue, Astro or plain HTML), adapted from a single framework-agnostic reference. The component takes a translatable text label, picks the Black or White Icon Colour for light or dark backgrounds, and can open an optional second layer on hover or click explaining what AI generated or modified; that layer is a keyboard-operable button with `aria-expanded`, closed by Escape. The component needs nothing from the plugin at runtime.

### Which icon

Naming the variant ("as fully AI-generated", "as AI-modified") settles the icon. Without it (`/eu-ai-labelling label photo.png`), the skill uses what you told it, or asks whether AI created the content from scratch or edited something that already existed.

The skill doesn't tell you whether the law requires a Label for your content: that decision is yours. Asked, it points you to the official Guidelines, the Code of Practice and the AI Act Service Desk (see [Sources](#sources)).

## Projects

The plugin stores no settings: say what you want in the request ("in Italian", "bottom-left if it's free").

The plugin doesn't watch for unlabelled content: content gets labelled when you ask for it.

After a Labelled Copy is made in a project, the agent points the image references in your Markdown and HTML pages at the copy, checks the other places that name the image (styles, templates, source and data files) and updates those that show it, updates the alt text to say the image is AI-generated or AI-modified, and lists the references it couldn't update (for example ones in a CMS) for you to fix by hand. Once you approve a video's Labelled Copy, the agent points the `<video src>` and `<source>` elements of your video players at it, keeping their subtitle and description tracks, poster and controls, changes no alt text and adds no disclosure around the player: the incorporated Label is the disclosure. Imports, components and computed paths are listed for you to check.

## Placement defaults

These are this plugin's own choices. The Code of Practice sets no minimum size, colour or margin for the Label; it suggests the top-right corner. Every default can be overridden per image.

| Setting | Default |
| --- | --- |
| Corner | top-right, when it is free of faces, text and the main subject; otherwise the cleanest corner, or you are asked |
| Icon height | 6% of the image's shorter side, at least 24 px |
| Margin | 2% of the image's shorter side |
| Icon Colour | Black or White, whichever gives at least 3:1 contrast with the area underneath |
| Fallback | an opaque icon on a contrasting backing plate when neither colour reaches that |

## Sources

- EU Icons: https://digital-strategy.ec.europa.eu/en/policies/eu-icons-labelling-ai-generated-content
- Code of Practice: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
- Guidelines on Article 50: https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations

## Development

```
uv run pytest
```

The second-layer behaviour of the site reference (`tests/docs/test_site_reference.py`) runs in Node: without `node` installed, those tests are skipped.

GitHub Actions runs the same suite on every push and pull request, without the tests marked `model` or `claude_cli` (`.github/workflows/tests.yml`).

The tests live in four folders:

- `tests/unit/`: each `label_tool` subcommand, run as a subprocess as the skill runs it.
- `tests/docs/`: the skill's references and this README. The snippets and commands the agent copies are parsed or run exactly as written, and the README is checked against the shipped files and against what `label_tool` applies.
- `tests/plugin/`: the manifests and the packaging, on the files git tracks, as the public repository serves them. With the `claude` CLI installed it also installs the plugin from the marketplace into a throwaway Claude Code config, confirms that the bare `/eu-ai-labelling` resolves to the skill, and labels an image with the installed copy's own tool and icons. Codex is checked statically: the plugin is followed from the marketplace to `.codex-plugin/plugin.json`. That takes for granted that Codex reads `.claude-plugin/marketplace.json`, confirmed by hand with codex-cli 0.166.0. Before a release, try the plugin by hand in Codex: install it from `/plugins` and run `$eu-ai-labelling label photo.png as fully AI-generated`.
- `tests/headless/` and `tests/evals/`: the skill in headless Claude Code.

Tests marked `claude_cli` are skipped when the `claude` CLI is not installed. Tests marked `model` call the model, so they are opt-in. Point `EU_AI_LABELLING_E2E_DIR` at a throwaway directory; each test creates its own project there:

```
EU_AI_LABELLING_E2E_DIR=/path/to/scratch uv run pytest tests/headless
```

The checks those runs apply to the model's replies are themselves tested on canned replies, which always run.

Skill evals live in `tests/evals/`. Each `tests/evals/scenarios/*.json` file is a scenario: the files to put in a throwaway project, the prompt to send, and what must happen: an image labelled with the expected Icon Variant (judged from its pixels), or a question back to the user (how AI was involved, or whether a creative work gets a caption or burn-in), and never a word on whether the law requires a Label. Asked whether a Label is required, the reply must point to the Guidelines, the Code of Practice and the AI Act Service Desk and offer to label. Scenarios with a `text_label` expect a document labelled in place: one marker right below the headline (or the named section), the official Basic icon and the text label in the document's language. With `below`, that Label is a Creative Work's caption right below the image reference. Scenarios with a `site_component` expect one new label component in a web project, using the copied official SVGs, with alt text, a translatable `label`, and a second layer on a `<button>` with `aria-expanded` and `aria-controls`; a React component is then built and run in jsdom, where hover, click and Escape must open and close that layer. That needs the harness in `tests/evals/site` (`npm ci --prefix tests/evals/site`); without it, those checks are skipped. A Labelled Copy must carry the official icon, compared pixel by pixel with the SVG rendered by resvg. They run against headless Claude Code the same way and are opt-in too:

```
EU_AI_LABELLING_E2E_DIR=/path/to/scratch uv run pytest tests/evals
```

## Licence

MIT, see [LICENSE](LICENSE). The bundled EU Icons are the European Commission's; see `skills/eu-ai-labelling/assets/icons/SOURCE.md`.
