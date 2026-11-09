# 03: CI job that checks what the skills CLI finds

**What to build:** A separate job in `.github/workflows/tests.yml` that runs the real `skills` CLI against the checkout and fails unless the only skill it lists is `eu-ai-labelling`. It guards against a newly installed development skill being shipped under this repo's name. See [spec](../spec.md).

**Blocked by:** none

**Status:** ready-for-agent

- [ ] The job sets up Node 22.20 or later and runs `npx -y skills@<exact version> add . --list`, with the version pinned so the check changes only when someone bumps it. The CLI must not install anything.
- [ ] It fails when any skill other than `eu-ai-labelling` is listed, and when `eu-ai-labelling` is missing. Parse the listing in a way that doesn't break on the CLI's spinner and colour output (check whether the CLI has a plain or non-interactive mode).
- [ ] It runs on push and pull request, like the `fast` job, and doesn't make the `fast` job slower.
- [ ] A comment in the workflow says what the job guards against and points to the spec's fallback plan for when it fails.
