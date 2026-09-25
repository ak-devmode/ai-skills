#!/usr/bin/env bash
# Branch survey for /cross-repo-init §2.1–2.2: which branch holds current truth,
# and which remote branches are live work vs already integrated.
#
# Approach, all read-only (never checks out):
#   1. default branch from origin/HEAD, falling back to main when origin/HEAD is
#      unset (the old `symbolic-ref | sed || echo main` never fell back — `||`
#      tested sed's exit, so the branch came out empty).
#   2. survey-branch cascade: CROSS-REPO.md `trunk-branch:` → origin/develop if it
#      is >= 5 commits ahead of default OR adds files default lacks → default.
#   3. classify every remote branch against the survey trunk: MERGED (no commits
#      trunk lacks), SQUASHED (ahead by ancestry, but `git cherry` shows every
#      commit already applied), LIVE (real unmerged work).
#
# Usage:  repo-survey.sh [repo-dir] [--no-fetch]
# Output: KEY=value lines, then one classified line per branch, on stdout.
# Exit:   0 ok · 1 not a git repo

set -uo pipefail

dir="$PWD"; fetch=1
for a in "$@"; do
  case "$a" in --no-fetch) fetch=0 ;; *) dir="$a" ;; esac
done
root="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || { echo "repo-survey: not a git repo: $dir" >&2; exit 1; }
g() { git -C "$root" "$@"; }

[ "$fetch" -eq 1 ] && g fetch --prune -q origin 2>/dev/null

default="$(g symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)"
default="${default#origin/}"; default="${default:-main}"
current="$(g branch --show-current 2>/dev/null)"

survey=""; reason=""
declared="$(grep -oE 'trunk-branch: *[A-Za-z0-9._/-]+' "$root/CROSS-REPO.md" 2>/dev/null | head -1 | awk '{print $2}')"
if [ -n "$declared" ]; then
  survey="$declared"; reason="CROSS-REPO.md trunk-branch"
elif g show-ref --verify --quiet refs/remotes/origin/develop && [ "$default" != develop ]; then
  ahead="$(g rev-list --count "origin/$default..origin/develop" 2>/dev/null || echo 0)"
  added="$(g diff --name-only --diff-filter=A "origin/$default...origin/develop" 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${ahead:-0}" -ge 5 ]; then survey=develop; reason="origin/develop +$ahead ahead of $default"
  elif [ "${added:-0}" -gt 0 ]; then survey=develop; reason="origin/develop adds $added file(s) $default lacks"; fi
fi
[ -n "$survey" ] || { survey="$default"; reason="${reason:-default branch}"; }

echo "REPO=$(basename "$root")"
echo "REPO_ROOT=$root"
echo "REMOTE_URL=$(g remote get-url origin 2>/dev/null || echo '(no remote)')"
echo "DEFAULT_BRANCH=$default"
echo "CURRENT_BRANCH=${current:-(detached)}"
echo "SURVEY_BRANCH=$survey"
echo "SURVEY_REASON=$reason"

trunk="origin/$survey"
g rev-parse --verify -q "$trunk" >/dev/null || { echo "NOTE: $trunk does not exist — classification skipped"; exit 0; }
echo "-- remote branches vs $trunk --"
for ref in $(g for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -vE '/(HEAD|gh-pages)$|^origin$'); do
  [ "$ref" = "$trunk" ] && continue
  ahead="$(g rev-list --count "$trunk..$ref" 2>/dev/null || echo 0)"
  when="$(g log -1 --format=%cs "$ref" 2>/dev/null)"
  if [ "${ahead:-0}" = 0 ]; then
    echo "MERGED    $ref  ($when)"
  elif ! g cherry "$trunk" "$ref" 2>/dev/null | grep -q '^+'; then
    echo "SQUASHED  $ref  ($when, +$ahead by ancestry, all patches upstream)"
  else
    echo "LIVE      $ref  ($when, +$ahead)"
  fi
done
