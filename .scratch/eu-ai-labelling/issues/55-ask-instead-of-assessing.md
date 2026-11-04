# 55: Ask the user instead of assessing the law

**What to build:** The skill runs a Disclosure Assessment: the Deepfake, Public-Interest Text, Editorial Responsibility and Creative Work tests, and a Required / Not Required / Unclear verdict printed by `label_tool outcome`. That is a legal judgement the plugin is not entitled to make, and the review found it wrong at the edges (marketing claims about health or safety, personal use, deepfakes made before 2 August 2026, the reviewer versus the party with editorial responsibility, substantive versus any later AI edit).

Fix: drop the assessment. The skill asks only about the content itself, from context first, in plain words:

- did AI create it from scratch, or edit something that already existed? This picks Fully AI-Generated or Partially AI-Modified (the wording `generated` or `modified` for text);
- for a batch, that question once, naming only the files whose answers differ.

When the user asks whether a Label is legally required, the skill says the decision is theirs, points to the Guidelines, the Code of Practice and the AI Act Service Desk, and offers to apply a Label. Drop `label_tool outcome`, the outcome block, Voluntary Label as a separate idea, and the GLOSSARY's assessment terms.

**Blocked by:** None

**Status:** resolved

Source: maintainer's decision (2026-11-04), after the review of the skill: "we should avoid legal assessment, we're not entitled to do that. we should simply understand how the user behaves, and ask them".

- [x] SKILL.md has no Disclosure Assessment, no tests of the law and no verdict; it asks only for what picks the Icon Variant and where the Label goes
- [x] Asked whether a Label is required, the skill gives no verdict and points to the official sources
- [x] `label_tool outcome` is gone
- [x] README, GLOSSARY and `references/batch.md` follow
- [x] Eval scenarios expect no verdict; the text-review scenarios become one "do I need a label?" scenario

## Comments

- What changed: SKILL.md loses the Disclosure Assessment (the four tests, Deciding the outcome, Recommending the Icon Variant, Outcome format) and step 3 "Let the human decide". Step 2 settles the Icon Variant from what the user named or said, or with one plain question (from scratch, or an edit of something real). A new section, "Whether a Label is required", says never to give a verdict and lists the Guidelines, the Code of Practice and the AI Act Service Desk; "A batch of files" keeps one round of questions. The description no longer promises an assessment. `label_tool outcome` and its constants are gone (1794 → 1599 lines), and `main` parses arguments strictly again. GLOSSARY drops Voluntary Label, Disclosure Assessment, Disclosure Outcome, Deployer, Deepfake, Public-Interest Text and Editorial Responsibility; Creative Work is redefined as what the user presents as artistic, satirical or fictional. README's "Disclosure Assessment" becomes "Which icon"; `references/batch.md` and `references/creative-work.md` follow.
- Evals: no reply may give a verdict (the old block, "a label is (not) required", "you are required to label"); saying it can't tell whether one is required is fine. `politician-deepfake`, `face-swap-authentic-photo` and `cartoon-mascot` now expect the image labelled with its variant; `unreviewed-public-interest-blog` the post labelled in place; `news-article-with-editor` becomes `asks-if-a-label-is-required` (sources, an offer, no file changed); `unclear-review` is gone; `unknown-origin` is new; `mixed-event-folder` expects only the targeted question.
- How tested: deleted `tests/unit/test_outcome.py` and `tests/docs/test_outcome_format.py`; the editorial and outcome canned replies give way to canned replies for no verdict, the official sources and the origin question, each with negative controls. Offline suites: 485 passed, 32 skipped (model).
- Headless runs with Sonnet (2026-11-04): `unknown-origin`, `asks-if-a-label-is-required`, `satirical-ai-art`, `named-variant-on-a-creative-work`, `named-variant-on-a-photo`, `mixed-event-folder`, `politician-deepfake`, `unreviewed-public-interest-blog`: 7 of 8 passed first time. `unknown-origin` failed only because the check wanted both halves in one question while the model asked one per option; the check now reads all the questions together, and the scenario passes.
