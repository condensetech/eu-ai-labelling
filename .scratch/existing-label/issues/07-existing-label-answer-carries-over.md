# 07: Keep the Existing Label answer when an image switches to a caption

**What to build:** An image whose Existing Label the user already answered for ("add the EU Icon anyway") can be switched from burn-in to a caption at the preview of step 5 of `references/image.md`. `references/creative-work.md` step 1 then runs its own Existing Label check, and nothing says the earlier answer carries over, so the agent may ask the same question twice. See [spec](../spec.md).

**Blocked by:** none

**Status:** ready-for-agent

- [ ] The answer about an image's Existing Label holds for that image whether it ends up burned in or captioned: `creative-work.md` doesn't ask it again. Say it once, where the check runs, by pointing to the **Already decided** rule in SKILL.md **An Existing Label** rather than restating it.
- [ ] The same holds in a batch: a file whose Existing Label answer is settled is never asked about again, after a switch to a caption too.
- [ ] Doc test for `creative-work.md`. No eval scenario: the switch needs a second turn, which the eval harness doesn't run.
