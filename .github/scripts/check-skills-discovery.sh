#!/usr/bin/env bash
# The skills-discovery job in .github/workflows/tests.yml; why it exists is
# explained there.
#
# Usage: check-skills-discovery.sh <skills-cli-version> [repo-dir]
#
# `add <dir> --list` lists and exits without installing. It has no JSON
# mode (--json is rejected with --list), so the plain listing is parsed:
# colour is turned off with NO_COLOR, and the spinner's cursor escapes are
# stripped. In the listing, each skill name is a line of "│" and four
# spaces; its description is indented further.
set -euo pipefail

version=${1:?usage: check-skills-discovery.sh <skills-cli-version> [repo-dir]}
repo_dir=${2:-.}
expected=eu-ai-labelling

if ! output=$(cd "$repo_dir" && NO_COLOR=1 DO_NOT_TRACK=1 \
    npx -y "skills@$version" add . --list </dev/null 2>&1); then
  printf '%s\n' "$output"
  echo "::error::The skills CLI failed."
  exit 1
fi

clean=$(printf '%s\n' "$output" | tr '\r' '\n' | sed -E $'s/\x1b\\[[0-9;?]*[A-Za-z]//g')
printf '%s\n' "$clean"

found=$(printf '%s\n' "$clean" | sed -nE 's/.*Found ([0-9]+) skills?.*/\1/p' | tail -n1)
listed=$(printf '%s\n' "$clean" | sed -nE 's/^│ {4}([^ ].*[^ ]|[^ ])[[:space:]]*$/\1/p')
listed_count=$(printf '%s' "$listed" | grep -c . || true)

# If the count and the names disagree, the CLI's output format changed and
# the parsing above needs updating.
if [[ "$found" != "$listed_count" ]]; then
  echo "::error::The CLI reported '${found:-no count}' skills but $listed_count names were parsed. Has its output format changed?"
  exit 1
fi

if [[ "$listed" != "$expected" ]]; then
  echo "::error::Expected the skills CLI to list only $expected, but it listed:"
  printf '%s\n' "${listed:-(nothing)}" | sed 's/^/  /'
  exit 1
fi

echo "OK: the skills CLI lists only $expected."
