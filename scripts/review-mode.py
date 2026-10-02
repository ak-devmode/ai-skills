#!/usr/bin/env python3
"""review-mode.py — which mode /review and /verify run in: lean or full.

Approach: one resolver for both skills, so the two can never disagree on a run (CLAUDE.md
§3.6.1). Precedence is flag > env > default. A flag is `--full` or `--lean`. The env var
is AI_SKILLS_REVIEW_MODE, set per machine in ~/.claude/settings.json → env. The default
is `lean`: one bundle read by one Sonnet subagent, cheap enough for a regular seat. `full`
is the codex gate with the full Claude fallback. An env value that is neither is an error,
never a silent lean: a typo in a setting must not quietly change what a review covers.

Usage:  review-mode.py [--full | --lean]
Output: one line, `mode: <lean|full> (<flag|env|default>)` — the skills print it in the
        report header as-is.
Exit:   0 resolved · 2 usage (both flags, or a bad AI_SKILLS_REVIEW_MODE value)
"""

import os
import sys

MODES = ("lean", "full")
ENV = "AI_SKILLS_REVIEW_MODE"


def resolve(flags, env):
    """(mode, source), or (None, why) when the inputs are contradictory or invalid."""
    picked = [f[2:] for f in flags]
    if len(set(picked)) > 1:
        return None, "--full and --lean together"
    if picked:
        return picked[0], "flag"
    value = (env or "").strip().lower()
    if not value:
        return "lean", "default"
    if value not in MODES:
        return None, f"{ENV}={env!r} is not one of {', '.join(MODES)}"
    return value, "env"


def main(argv):
    unknown = [x for x in argv if x not in ("--full", "--lean")]
    if unknown:
        print(f"usage: review-mode.py [--full | --lean] (got {' '.join(unknown)})", file=sys.stderr)
        return 2
    env = os.environ.get("AI_SKILLS_REVIEW_MODE")
    mode, source = resolve(argv, env)
    if mode is not None and source == "flag" and resolve([], env)[0] is None:
        print(f"review-mode.py: warning — {resolve([], env)[1]}; the flag decides this run", file=sys.stderr)
    if mode is None:
        print(f"review-mode.py: {source} — fix it, or pass --full / --lean for this run", file=sys.stderr)
        return 2
    print(f"mode: {mode} ({source})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
