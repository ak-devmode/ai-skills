#!/usr/bin/env bash
# Bootstrap or extend a closeout-prep.md ledger — /plan §5.13.
#
# Approach: the ledger lives in the scope folder (child plan) or plan folder
# (standalone). If it is absent, copy the shared template, fill its header and
# its seeded phase block; if present, append a timestamped `## Phase …` header so
# a resumed or restarted phase adds a block instead of overwriting one. The header is read back before
# success is reported — a ledger that "was initialized" but isn't on disk is the
# failure the whole closeout chain inherits.
#
# With --repo, it also records each repo's HEAD as the unit's base SHA under the
# header (`- base: <unit> <repo> <sha>`, repo relative to $VERIFY_PROJECTS or
# ~/Projects) — verdict-gate.py's range is base..HEAD (verify-contracts.md §5.2).
# Only the FIRST base per unit+repo is kept: a resumed phase must not shrink the range.
#
# Usage:  ledger-init.sh <folder> --plan <plan-path> --phase "<P>: <name>" [--slug S] [--resumed]
#                        [--repo PATH ...]
#   --resumed  header reads "(resumed <ISO> after compaction)" — the template's form
# Output: "created: …" or "found: …", then "phase header: …", then one "base: …" line per repo.
# Exit:   0 ok · 1 write did not land · 2 usage · 4 template missing

set -uo pipefail

folder="${1:-}"; shift || true
plan=""; phase=""; slug=""; verb=started; repos=()
while [ $# -gt 0 ]; do
  case "$1" in
    --resumed) verb=resumed; shift ;;
    --repo) repos+=("${2:-}"); shift 2 ;;
    --plan) plan="${2:-}"; shift 2 ;;
    --phase) phase="${2:-}"; shift 2 ;;
    --slug) slug="${2:-}"; shift 2 ;;
    *) echo "ledger-init: unknown arg $1" >&2; exit 2 ;;
  esac
done
[ -d "$folder" ] && [ -n "$plan" ] && [ -n "$phase" ] || {
  echo "usage: ledger-init.sh <folder> --plan <plan-path> --phase \"<P>: <name>\" [--slug S]" >&2; exit 2; }

here="$(cd "$(dirname "$0")" && pwd)"
tmpl="$here/../templates/closeout-prep.md.template"
[ -f "$tmpl" ] || { echo "ledger-init: template not found at $tmpl — check ai-skills installation" >&2; exit 4; }

ledger="$folder/closeout-prep.md"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ -n "$slug" ] || slug="$(basename "$folder")"

header="## Phase $phase ($verb $ts$([ $verb = resumed ] && echo ' after compaction'))"

if [ -f "$ledger" ]; then
  echo "found: $ledger"
  printf '\n---\n\n%s\n' "$header" >> "$ledger"
else
  # The template seeds one `## Phase 1: {{PHASE_NAME}}` block — fill it, don't add a second.
  esc="$(printf '%s' "$header" | sed 's/[&|]/\\&/g')"
  sed -e "s|{{PLAN_OR_SCOPE_SLUG}}|$slug|g" \
      -e "s|{{PATH_TO_PLAN}}|$plan|g" \
      -e "s|^## Phase 1: {{PHASE_NAME}}.*$|$esc|" \
      -e "s|{{ISO_TIMESTAMP}}|$ts|g" "$tmpl" > "$ledger"
  grep -q "^\*\*Schema version:\*\*" "$ledger" || { echo "ledger-init: $ledger missing schema line after copy" >&2; exit 1; }
  if grep -q '{{PHASE_NAME}}' "$ledger"; then echo "ledger-init: template phase seed not filled" >&2; exit 1; fi
  echo "created: $ledger"
fi

grep -qF "$header" "$ledger" || { echo "ledger-init: phase header did not land in $ledger" >&2; exit 1; }
echo "phase header: $header"

# ---- base SHAs (verify-contracts.md §5.2) ----
unit="$(basename "$plan" | sed -nE 's/^([0-9]+\.[0-9]+)-.*/\1/p')"
[ -n "$unit" ] || unit="$(basename "$plan" .md)"
new=()
if [ ${#repos[@]} -gt 0 ]; then
  root="${VERIFY_PROJECTS:-$HOME/Projects}"
  [ -d "$root" ] || { echo "ledger-init: projects root $root does not exist — base SHAs name repos relative to it (cause: environment; next: set VERIFY_PROJECTS)" >&2; exit 1; }
  projects="$(cd "$root" && pwd -P)"
fi
for r in ${repos[@]+"${repos[@]}"}; do
  sha="$(git -C "$r" rev-parse HEAD 2>&1)" || {
    echo "ledger-init: cannot record base SHA — expected a git repo at $r, found: $sha (cause: environment; next: git -C $r status)" >&2; exit 1; }
  abs="$(cd "$r" && pwd -P)"
  name="${abs#"$projects"/}"
  [ "$name" != "$abs" ] || { name="$(basename "$abs")"; echo "ledger-init: note — $abs is outside $projects; recorded as '$name'" >&2; }
  if grep -qE "^- base: $unit $name [0-9a-f]+$" "$ledger"; then
    echo "base: kept $(grep -E "^- base: $unit $name " "$ledger" | head -1 | sed 's/^- base: //')"
  else
    new+=("- base: $unit $name $sha")
  fi
done
if [ ${#new[@]} -gt 0 ]; then
  block="$(printf '%s\n' "${new[@]}")"
  tmp="$ledger.tmp.$$"
  awk -v h="$header" -v b="$block" '{print} $0==h && !done {print ""; print b; done=1}' "$ledger" > "$tmp" && mv "$tmp" "$ledger"
  for l in "${new[@]}"; do
    grep -qxF -e "$l" "$ledger" || { echo "ledger-init: base line did not land in $ledger: $l" >&2; exit 1; }
    echo "base: ${l#- base: }"
  done
fi
