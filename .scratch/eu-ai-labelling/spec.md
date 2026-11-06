# eu-ai-labelling: label AI-generated content with the EU icons from Claude Code and Codex

Status: ready-for-agent

## Problem Statement

Since 2 August 2026, Article 50(4) of the EU AI Act requires a Deployer to disclose Deepfakes and Public-Interest Text that AI generated or manipulated. The European Commission publishes official EU Icons for this disclosure, and Section 2 of the Code of Practice on transparency of AI-generated content describes how to place them. People who produce content with coding agents often get it wrong:

- they don't know whether a Label is legally required for a given piece of content;
- they don't know which Icon Variant fits;
- they don't know where and how to place it so that it is perceivable, accessible and survives resharing.

Doing it by hand is tedious: compositing icons into images, choosing a corner that doesn't cover the subject, picking a colour with enough contrast, writing alt text, adding a translated text label to articles, building a reusable component for a website. In a project where the agent keeps producing content, it is also easy to forget to label new files.

## Solution

`eu-ai-labelling` is a public, MIT-licensed plugin for both Claude Code and OpenAI Codex, published at `condensetech/eu-ai-labelling`. It has a single entry point: `/eu-ai-labelling` in Claude Code and `$eu-ai-labelling` in Codex.

When invoked, the agent:

1. **Assesses.** It runs a guided Disclosure Assessment. It answers from context what it can and asks the user the rest. The result is a Disclosure Outcome (Required, Not Required or Unclear) with a recommended Icon Variant, a one-line reason and a "not legal advice" note. The human always decides whether to label, and a Voluntary Label is always allowed.
2. **Labels**, according to the content type:
   - **Image:** a Labelled Copy with the Fully AI-Generated or Partially AI-Modified EU Icon burned into the pixels. The corner is chosen smartly, the colour has enough contrast, and the original is untouched.
   - **Text (Markdown/HTML):** the Basic EU Icon plus a plain-language text label in the document's language, placed at the top near the headline, with accessible markup.
   - **Site:** a reusable label component adapted to the project's framework, with ARIA support and an optional second layer.
   - **Creative Work:** a label outside the frame is offered, such as a caption, alt text or an icon next to the image, instead of burn-in.
3. **Optionally watches a project.** A project can opt in with a config file declaring Content Paths, defaults and Exemptions. A hook then reminds the agent, without blocking, when it writes or edits content there that isn't yet labelled.

## User Stories

### Invocation and packaging

1. As a Claude Code user, I want to install the plugin with `/plugin marketplace add condensetech/eu-ai-labelling`, so that I can start labelling without manual setup.
2. As a Codex user, I want to install the same plugin with `codex plugin marketplace add condensetech/eu-ai-labelling`, so that I get identical behaviour in my tool of choice.
3. As a Claude Code user, I want to invoke the plugin as `/eu-ai-labelling`, so that I remember one short command.
4. As a Codex user, I want to invoke the plugin as `$eu-ai-labelling`, so that it works like other Codex skills.
5. As a user, I want a single entry point for images, text and sites, so that I don't need to know which sub-tool to pick.
6. As a user, I want the agent to pick up the skill automatically when I say "label this image as AI-generated", so that I don't have to remember the command.
7. As a user, I want the plugin to need no system packages beyond `uv` (or Python with Pillow), so that installation can't fail on missing native libraries.
8. As a user, I want the README to state clearly that the plugin isn't legal advice, so that I don't over-rely on it.

### Disclosure Assessment

9. As a Deployer, I want the agent to tell me whether a Label is legally required for my content, so that I comply with Article 50(4).
10. As a Deployer, I want the agent to infer answers from context, such as having generated the image itself, so that I'm only asked what it can't know.
11. As a Deployer, I want to be asked whether my image resembles real or realistic persons, places or events and could pass as authentic, so that Deepfakes are identified correctly.
12. As a Deployer, I want to be asked whether my text is published to a broad audience to inform on public-interest matters, so that Public-Interest Text is identified correctly.
13. As a Deployer, I want to be asked whether a named person or entity with Editorial Responsibility substantively reviewed the text, with no AI edits after sign-off, so that I can use the editorial exception correctly.
14. As a Deployer, I want to be told that spell-checks, automated review or cursory approval don't count as human review, so that I don't wrongly claim the exception.
15. As a Deployer, I want to be asked whether the content is a Creative Work, so that I get the lighter disclosure that doesn't hamper the work.
16. As a Deployer, I want to be asked whether the content is fully AI-generated or human-made and partly AI-modified, so that the right Icon Variant is chosen.
17. As a Deployer, I want a Disclosure Outcome of Required, Not Required or Unclear with a one-line reason, so that I understand the recommendation.
18. As a Deployer, I want every outcome to carry a "not legal advice" note, so that responsibility stays clear.
19. As a Deployer whose content is Not Required, I want the option to apply a Voluntary Label anyway, so that I can be transparent beyond the law.
20. As a Deployer, I want to be told that using the EU Icons without signing the Code of Practice doesn't signal adherence to the Code, so that I don't misrepresent my status.
21. As a Deployer with an Unclear outcome, I want to be pointed to the official guidance and the AI Act Service Desk, so that I can resolve it.
22. As a user who already knows what they want, I want to say "label as fully AI-generated" and skip the assessment, so that I'm not slowed down.
23. As a Deployer, I want to be reminded that text generated before 2 August 2026 but published after it still needs a Label, so that I don't miss legacy content.

### Image labelling

24. As a creator, I want the EU Icon burned into my image's pixels, so that the Label survives resharing and downloading.
25. As a creator, I want my original image left untouched and a Labelled Copy written next to it, so that I never lose the unlabelled version.
26. As a creator, I want the Fully AI-Generated icon on fully generated images and the Partially AI-Modified icon on modified photos, so that viewers know what kind of AI involvement there was.
27. As a creator, I want the agent to look at my image and propose a corner that doesn't cover faces, text or the main subject, so that the Label doesn't ruin the image.
28. As a creator, I want the top-right corner preferred when it is free, so that placement follows the Code of Practice's suggestion.
29. As a creator, I want to be asked when no corner is clearly suitable, so that I stay in control of ambiguous cases.
30. As a creator, I want the icon colour (black, white or the 50% variants) chosen automatically for at least 3:1 contrast against the area underneath, so that the Label is perceivable.
31. As a creator, I want a fallback with an opaque backing plate when neither colour gives enough contrast, so that busy backgrounds still get a readable Label.
32. As a creator, I want the icon sized relative to the image, with a sensible minimum, so that it's clearly visible without dominating.
33. As a creator, I want to override the corner, size and colour, so that I can match my own taste or brand.
34. As a creator, I want a preview of the result before it is final, so that I can approve or adjust.
35. As a creator, I want PNG, JPEG and WebP supported, so that my common formats work.
36. As a creator, I want a clear refusal for animated GIF or WebP and for SVG images, so that I know these aren't supported yet.
37. As a photographer, I want my colour profile and EXIF metadata kept in the Labelled Copy, so that colours and provenance aren't lost.
38. As a creator, I want JPEG copies re-encoded at high quality, so that labelling doesn't visibly degrade the image.
39. As a creator, I want to label a whole folder of images in one go, so that batch work is fast.
40. As a creator labelling a batch, I want the assessment asked once with shared answers and only per-file questions where files differ, so that I'm not asked the same thing repeatedly.
41. As a creator labelling a batch, I want all uncertain placements gathered into one question, so that I can resolve them together.
42. As an artist, I want my Creative Work image to get a Label outside the frame, as a caption, alt text or an icon next to it, so that the Label doesn't hamper the work.
43. As an artist, I still want to be able to choose burn-in for a Creative Work, so that the choice stays mine.

### Text labelling

44. As a writer, I want the Basic EU Icon and a plain-language text label added at the top of my Markdown or HTML document near the headline, so that readers see the disclosure at first exposure.
45. As a writer publishing in Italian, I want the text label in Italian (e.g. "Generato con IA"), so that my readers understand it; the icon itself stays the official English "AI".
46. As a writer, I want the label wording to say generated or modified, so that the kind of AI involvement is clear.
47. As a writer of HTML, I want the icon inlined as accessible SVG with a role and label, so that screen readers announce it.
48. As a writer of Markdown, I want the icon added as an image reference to an SVG copied into my project's assets folder, so that it renders on typical Markdown hosts.
49. As a writer, I want my document edited in place, so that I don't manage duplicate files; version control covers undo.
50. As a writer, I want a hidden marker next to the label, so that tools can tell the document is already labelled.
51. As a writer, I want only the AI-made part of a mixed document labelled when that's my situation, so that the disclosure is accurate.

### Site integration

52. As a web developer, I want the agent to add a reusable AI label component in my project's own framework (React, Vue, Astro or plain HTML), so that it fits my codebase.
53. As a web developer, I want the component to support the Basic icon with a translatable text label, so that I can localise it.
54. As a web developer, I want the component to have proper ARIA attributes and alt text, so that it meets accessibility expectations (WCAG, European Accessibility Act).
55. As a web developer, I want an optional second layer, on hover or click, explaining what was generated or modified, so that curious users get detail.
56. As a web developer, I want the second layer to be keyboard and screen-reader navigable, so that it's accessible.
57. As a web developer, I want the component to choose an Icon Colour suited to its background (light or dark), so that it's always visible.
58. As a web developer, I want the official SVGs copied into my project, so that the component has no runtime dependency on the plugin.

### Projects

59. As a project maintainer, I want to ask the agent to "set up AI labelling for this project" and get a `.eu-ai-labelling.json` file, so that opting in is easy.
60. As a project maintainer, I want to declare Content Paths with glob patterns, so that content is distinguished from code.
61. As a project maintainer, I want to set project defaults (text-label language, preferred corner, voluntary-labelling policy), so that I'm not asked the same thing every time.
62. As a project maintainer, I want a non-blocking reminder whenever the agent writes or edits an unlabelled file in a Content Path, so that new content doesn't go unlabelled.
63. As a project maintainer, I want no reminders for files already labelled, whether a Labelled Copy or a document with the marker, so that I'm not nagged.
64. As a project maintainer, I want to record an Exemption for a specific file, so that the hook stops reminding me about content I've decided not to label.
65. As a project maintainer, I want no automatic behaviour at all in projects without the config file, so that the plugin stays quiet unless I opt in.
66. As a project maintainer, I want references to an image in my pages updated to point to its Labelled Copy, so that the site actually shows the labelled version.
67. As a project maintainer, I want a list of references the agent couldn't update, for example ones in a CMS, so that I can fix them by hand.
68. As a project maintainer, I want the alt text of a labelled image in my HTML or Markdown updated to mention it's AI-generated, so that screen-reader users get the disclosure.
69. As a project maintainer using Codex, I want the same hook behaviour as in Claude Code, so that the team's tools behave the same.

## Implementation Decisions

- **Packaging.** One repository serves both tools. It contains a Claude Code manifest and a marketplace file under the Claude plugin directory, which Codex also reads; a Codex plugin manifest; and a single shared skills directory. Skills are found in each tool's standard skills location at the plugin root.
- **Single skill.** The skill is named `eu-ai-labelling`, with its frontmatter `name` set explicitly so the bare `/eu-ai-labelling` resolves in Claude Code. `/eu-ai-labelling:eu-ai-labelling` remains the always-working form. Codex users invoke `$eu-ai-labelling`.
- **Skill structure.** The main skill file holds routing and the Disclosure Assessment. Procedures for each content type live in reference files inside the skill folder (image, text, site, project setup), which the skill loads only when needed. They are not separate skills, so the single entry point can't be bypassed.
- **Asset and script paths.** All bundled files are referenced by paths relative to the skill folder, never by `${CLAUDE_PLUGIN_ROOT}`, because Codex isn't confirmed to substitute that variable in skill text.
- **Icons.** Only the official Commission SVGs are bundled: 3 Icon Variants × 4 Icon Colours. Their source URL and retrieval date are recorded. The PNG set is not shipped. File names are normalised (no spaces) while keeping a mapping to the official names.
- **Icon selection by medium.** Images use the Fully AI-Generated or Partially AI-Modified icon, with no added text. Text documents and site components use the Basic icon plus a plain-language text label in the content's language, which the agent translates. The wording says generated or modified.
- **Disclosure Assessment flow.** Content type, then generated vs modified, then Deepfake test (images) or Public-Interest Text test plus the Editorial Responsibility check (text), then the Creative Work check. The result is a Disclosure Outcome (Required, Not Required or Unclear), a recommended Icon Variant, a one-line reason and a "not legal advice" note. The human decides, and a Voluntary Label is always offered. When the user names a variant explicitly, the assessment is skipped.
- **`label_tool` CLI.** One Python script with its dependencies declared inline (PEP 723): Pillow and resvg-py. It is run via `uv run`, with plain `python3` plus installed packages as a fallback. It holds all deterministic logic behind three subcommands, each emitting JSON on stdout and a non-zero exit with a JSON error on failure:
  - `score <image>`: for each corner, a busyness metric (edge/detail density), the best Icon Colour and its contrast ratio, and whether the 3:1 threshold is met. It also reports image dimensions and whether the format is supported.
  - `apply <image> --variant <generated|modified> --corner <tl|tr|bl|br> [--size] [--colour] [--plate]`: renders the SVG with resvg and composites it with Pillow. It writes the Labelled Copy as `<name>.ai-label.<ext>` next to the original and never overwrites the original. It keeps ICC and EXIF, re-encodes JPEG at quality ≥ 95, refuses animated images and SVG input, and outputs the Labelled Copy's path and the parameters used.
  - `check-hook`: reads a hook event JSON on stdin (Claude Code or Codex shape) and the project's `.eu-ai-labelling.json`. It outputs a reminder message, or nothing, for the edited file.
- **Image placement defaults.** Margin is 2% of the image's shorter side. Icon height is 6% of the shorter side, with a minimum of 24 px. Black or white is chosen for at least 3:1 contrast. If neither colour reaches that, an opaque variant on a contrasting backing plate is used. Top-right is preferred. The agent combines `score` output with its own look at the image (faces, text, subject), proposes a corner, asks when top-right is unsuitable and no corner is clearly better, and shows a preview before finishing.
- **Creative Works.** For images judged a Creative Work, the skill offers a label outside the frame (caption, alt text, or an icon next to the image) and keeps burn-in available as an option.
- **Text labelling.** The agent does this from a reference snippet, with no script. HTML gets an inline SVG with `role="img"` and an `aria-label`, followed by the text label. Markdown gets an image reference to an SVG copied into the project's assets folder, followed by the text label. Both get a marker comment of the form `<!-- eu-ai-labelling: generated|modified -->`. Documents are edited in place.
- **Site integration.** One framework-agnostic HTML/CSS reference implementation (Basic icon, translatable text label, ARIA, colour suited to light or dark backgrounds, optional keyboard-accessible second layer) that the agent adapts to the project's stack. No per-framework components are maintained.
- **Project config (`.eu-ai-labelling.json`, project root).** Contents:
  - `contentPaths`: globs.
  - `defaults`: text-label language, preferred corner, voluntary-labelling policy.
  - `exemptions`: file paths, each with an optional reason.

  Without the file there is no automatic behaviour. The skill creates the file on request.
- **Hooks.** A post-write/edit hook for both Claude Code and Codex. Each is a thin wrapper that calls `label_tool check-hook`. The hook reminds the agent; it never blocks. A file counts as already labelled if it has the `.ai-label.` suffix or contains the marker comment. Files listed as Exemptions are skipped. All state lives in the files and the config, with no ledger.
- **References and alt text.** After producing a Labelled Copy in a project, the agent updates references it can find to point to the copy, updates alt text to mention AI generation, and lists references it couldn't update.
- **Distribution.** Public GitHub repository `condensetech/eu-ai-labelling`, MIT licence. The README carries the not-legal-advice statement, links the official EU icons page, Code of Practice and Guidelines, and notes that using the icons doesn't signal adherence to the Code.

## Testing Decisions

- **What makes a good test:** it exercises external behaviour through a public seam (CLI input to JSON output and files written) and never internal functions. Tests stay valid if the internals are rewritten.
- **Seam 1: `label_tool` CLI, tested with pytest by invoking the CLI as a subprocess against fixture images and fixture configs.**
  - `score`: a fixture with a busy top-right and a clean bottom-left ranks the corners accordingly. Dark and light backgrounds yield white and black respectively with contrast ≥ 3:1. A mid-grey noisy region reports that the threshold isn't met.
  - `apply`: the original's bytes are unchanged and the Labelled Copy exists with the right suffix. The icon's pixels appear in the requested corner at the expected size and margin. The minimum size is enforced on small images. ICC and EXIF are preserved. JPEG quality is high. Animated and SVG inputs are refused with a JSON error. The plate fallback renders.
  - `check-hook`: no reminder without config. Reminder for an unlabelled file in a Content Path. No reminder for a file outside Content Paths, a Labelled Copy, a document containing the marker, or an Exemption. Both Claude Code and Codex event shapes are accepted.
- **Seam 2: skill evals.** These are scenario prompts with expected outcomes for the judgement parts:
  - a politician deepfake gives Required with the Fully AI-Generated icon;
  - a face swap in an authentic photo gives Required with the Partially AI-Modified icon;
  - a news article reviewed by a named editor gives Not Required, with a Voluntary Label offered;
  - an AI-written public-interest blog post with no review gives Required;
  - satirical AI art is treated as a Creative Work and offered a label outside the frame;
  - an Italian article gets the Basic icon, the text label "Generato con IA" and the marker;
  - site integration in a React project produces a component with ARIA;
  - an explicitly named variant skips the assessment.
- **Manual release check:** install from the marketplace in both Claude Code and Codex, and confirm that `/eu-ai-labelling` and `$eu-ai-labelling` resolve, that skill-relative assets and scripts resolve, and that the hook fires.
- **Prior art:** none; the repo has no code or tests yet.

## Out of Scope

- **Marking:** machine-readable metadata, watermarks, C2PA or IPTC. Marking is primarily the Provider's duty. Adding IPTC `digitalSourceType` may come later as a separate concept.
- **Video and audio** labelling, including live content and audible disclaimers.
- Animated images and labelling SVG images themselves.
- Automatic behaviour without the project config, and hooks that block.
- Per-framework maintained components.
- Detecting AI-generated content that the agent didn't produce or that the user didn't point to, including images written to disk by external tools outside the agent's file edits.
- A ledger or audit log of assessments.
- Legal advice or certification of compliance.
- Localised icon artwork; the official set is English only.

## Further Notes

- **Sources:**
  - EU icons page: https://digital-strategy.ec.europa.eu/en/policies/eu-icons-labelling-ai-generated-content
  - Code of Practice: https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
  - Guidelines on Article 50 transparency obligations: https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations
  - SVG icons: https://ec.europa.eu/newsroom/dae/redirection/document/129546
- Article 50 applies from 2 August 2026. The Guidelines were approved in draft on 20 July 2026 and apply once formally adopted. The skill's guidance text should be easy to update when they change.
- The Code of Practice sets no minimum size, colour or duration. The placement defaults above are this plugin's own choices and should be documented as such.
- The official SVG file names contain spaces and an inconsistent underscore. Normalise them when vendoring.
- Vocabulary follows `GLOSSARY.md`.
