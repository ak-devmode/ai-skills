#!/usr/bin/env bash
# Stamp a plan file's `**Executed by:**` header from git config — /plan §3.1.
#
# Approach: derive the name (repo config, then global); never prompt, never guess.
# Four cases, decided by what the header holds now:
#   TBD                      -> replace with "<name> / Claude"
#   absent                   -> insert "<name> / Claude" after **Created by:** (or
#                               after the first bold header field)
#   already names <name>     -> no-op
#   names someone else       -> append ", then <name> / Claude" (a handoff stays legible)
# The write is read back; a stamp that did not land is exit 1, never a success line.
#
# Usage:  stamp-executed-by.sh <plan-file> [--repo DIR]
# Output: "stamped: …" | "unchanged: …" on stdout.
# Exit:   0 ok · 1 write did not land · 2 usage · 3 no git user.name anywhere

set -uo pipefail

plan="${1:-}"; [ -f "$plan" ] || { echo "usage: stamp-executed-by.sh <plan-file> [--repo DIR]" >&2; exit 2; }
repo="$(dirname "$plan")"
[ "${2:-}" = "--repo" ] && repo="${3:?--repo needs a dir}"

name="$(git -C "$repo" config --get user.name 2>/dev/null || git config --global --get user.name 2>/dev/null || true)"
if [ -z "$name" ]; then
  echo "stamp-executed-by: no git user.name (repo or global) — write 'TBD / Claude' and surface it" >&2
  exit 3
fi
want="$name / Claude"

python3 - "$plan" "$name" "$want" <<'PY'
import re, sys
path, name, want = sys.argv[1:]
text = open(path, encoding="utf-8").read()
line_re = re.compile(r"^\*\*Executed by:\*\*[ \t]*(.*)$", re.M)
m = line_re.search(text)
if m:
    cur = m.group(1).strip()
    if cur in ("", "TBD", "TBD / Claude"):
        new = line_re.sub(lambda _: f"**Executed by:** {want}", text, count=1)
    elif name in cur:
        print(f"unchanged: {path} (Executed by: {cur})"); sys.exit(0)
    else:
        new = line_re.sub(lambda _: f"**Executed by:** {cur}, then {want}", text, count=1)
else:
    anchor = re.search(r"^\*\*Created by:\*\*.*$", text, re.M) or re.search(r"^\*\*[^*]+:\*\*.*$", text, re.M)
    if not anchor:
        sys.exit("stamp-executed-by: no header field to anchor on — add **Executed by:** by hand")
    i = anchor.end()
    new = text[:i] + f"\n**Executed by:** {want}" + text[i:]
open(path, "w", encoding="utf-8").write(new)
back = line_re.search(open(path, encoding="utf-8").read())
if not back or want not in back.group(1):
    sys.exit(f"stamp-executed-by: write did not land in {path}")
print(f"stamped: {path} (Executed by: {back.group(1).strip()})")
PY
