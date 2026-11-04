# 34: README contradicts itself on the Voluntary Label default

**What to build:** Follow-up from 11 (Release readiness). The Disclosure Assessment section of the README says "A Voluntary Label is always offered." Elsewhere the README lists `voluntaryLabelling: never` as a default, and `skills/eu-ai-labelling/references/project.md` says `never` means the agent does not offer one for a Not Required outcome. The two statements contradict each other. No test covers this prose.

Fix: reword the sentence in `README.md` to "A Voluntary Label is offered unless the project's `voluntaryLabelling` default is `never`." Optionally add a check in `tests/e2e/test_release.py` that the README and `project.md` agree on this default.

**Blocked by:** None

**Status:** resolved

Source: ticket 11 (Release readiness), review findings (minor).

- [x] The README sentence about the Voluntary Label no longer says it is always offered
- [x] The README and `references/project.md` describe the `never` default the same way

## Comments

The README now reads: "A Voluntary Label is offered unless the project's `voluntaryLabelling` default is `never`." That matches `references/project.md`. No test was added, because this is a single prose sentence.
