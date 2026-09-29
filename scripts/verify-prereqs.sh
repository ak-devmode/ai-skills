#!/usr/bin/env bash
# Verification prerequisites — called by setup.sh; safe to run alone.
#
# Approach: /review and /verify need Python >= 3.9 (the scripts) and codex (the
# opposing-model judge). A teammate running `git pull && ./setup.sh` must never have
# the pull fail over these, so every check WARNS with the exact fix command and the
# script always exits 0. What a missing codex costs is said plainly: the skills still
# run, on a Claude fallback, and every verdict carries a ⚠ marker in the index.
# The live codex ping is deliberately not here (it costs credits on every setup run);
# `/verify --demo` does it.
#
# Usage:  verify-prereqs.sh
# Output: one `ok` or `!!` line per check, then a summary line.
# Exit:   0 always (warnings only) · 2 usage

set -uo pipefail
[ $# -eq 0 ] || { echo "usage: verify-prereqs.sh" >&2; exit 2; }

codex="${VERIFY_CODEX_BIN:-codex}"
warn=0
say_warn() { echo "   !! $1"; echo "      fix: $2"; warn=$((warn + 1)); }

py="$(command -v python3 || true)"
if [ -z "$py" ]; then
  say_warn "python3 not found — the verification scripts will not run" "brew install python@3.12"
elif "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  echo "   ok python3 $("$py" -c 'import platform; print(platform.python_version())')"
else
  say_warn "python3 is $("$py" -c 'import platform; print(platform.python_version())'), need >= 3.9" "brew install python@3.12"
fi

if ! command -v "$codex" >/dev/null; then
  say_warn "codex not installed — /review and /verify fall back to Claude; verdicts carry '⚠ judge: claude-fallback' in the index" \
           "npm i -g @openai/codex && codex login"
else
  status="$("$codex" login status 2>&1)"; rc=$?
  if [ $rc -eq 0 ]; then
    echo "   ok codex ($("$codex" --version 2>&1 | head -1); ${status%%$'\n'*})"
  else
    say_warn "codex is installed but not logged in (${status%%$'\n'*}) — verdicts will carry '⚠ judge:' in the index" "codex login"
  fi
fi

if [ $warn -eq 0 ]; then
  echo "   verification prerequisites ok — try: /verify --demo"
else
  echo "   $warn verification warning(s) above — setup continues; /verify --demo shows what runs without them"
fi
exit 0
