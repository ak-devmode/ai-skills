#!/usr/bin/env python3
"""scan-archive-drift.py — find finished scopes that were never archived.

Approach: /closeout's final act is moving the scope folder into archive/. When a run
ends early or goes through /closeout-extended (whose neighbor passes all skip the
archive step), a finished scope stays at the plans root and reads as live work. This
scans for that state so a SessionStart hook can surface it.

Choosing the signal took some care — two candidates both fail:

  PLANS-INDEX status cell   Unreliable: it is the thing that goes stale. Scope 99's
                            row still said "Scoped" and 57's said "MERGED ...
                            Remaining: closeout post-flight". Neither claimed done.
                            It also false-positives: scope 92's cell reads "Phase 1
                            Done - Phase 2 deferred", which is genuinely not finished.

  progress.md prose         Unreliable: caught 57 ("## 0. SCOPE 57 COMPLETE") but
                            missed 99, whose text only said "Core scope 99 DONE"
                            in a Next-action line.

So this uses BOTH signals, OR'd, because neither alone covers the two known misses:

  A. STRUCTURAL — progress.md's Plans table has >=1 row and EVERY row is Done.
     Catches 99 (4/4 Done). Misses 57.
  B. PROSE — an explicit whole-scope completion header ("SCOPE COMPLETE",
     "ALL PLANS COMPLETE", "SCOPE <N> COMPLETE").
     Catches 57. Misses 99.

Why 57 defeats signal A: its own Plans table was STALE — row 57.1 still read
"Draft - active" long after the index recorded it merged. The table is maintained by
hand, so a scope can finish without its table saying so. Signal B is the backstop for
exactly that, and vice versa.

KNOWN LIMIT, stated honestly: a scope that keeps NEITHER its Plans table nor a
completion header current will not be caught. This is a safety net, not a proof. The
enforcing check is verify-archive.sh, run inside /closeout itself.

Exit: 0 always (advisory, never blocks a session). Prints nothing when clean.
Usage: scan-archive-drift.py <plans-dir> [<plans-dir> ...]
"""

import os
import re
import sys

# A Plans-table row: | 99.1 | <file> | <phase> | **Done (2026-07-23)** | notes |
ROW = re.compile(r"^\|\s*(\d+)\.(\d+[a-z]?)\s*\|(.*)$", re.IGNORECASE)

# Done markers, and the words that mean "not done" even when "done" appears nearby
# (e.g. "Done pending live verify", "blocked", "in progress").
DONE = re.compile(r"\bdone\b|\bcomplete[d]?\b|\bmerged\b|\bshipped\b|✅", re.IGNORECASE)
NOT_DONE = re.compile(
    r"\bpending\b|\bblocked\b|\bin progress\b|\bwip\b|\btodo\b|\bdraft\b|"
    r"\bdeferred\b|\bnot started\b|\bwaiting\b|🔲|⏸|🟡|❌",
    re.IGNORECASE,
)


COMPLETE_HEADER = re.compile(
    r"scope\s+complete|all\s+plans\s+complete|scope\s+\d+\s+complete|"
    r"all\s+\d+\s+plans\s+complete",
    re.IGNORECASE,
)


def prose_complete(progress_path):
    """Signal B — an explicit whole-scope completion statement.

    Restricted to the file's head, where the Resume Context / status header lives, so a
    passing mention deep in a progress log does not trip it.
    """
    try:
        with open(progress_path, "r", encoding="utf-8", errors="replace") as fh:
            head = "".join(fh.readlines()[:40])
    except OSError:
        return False
    return bool(COMPLETE_HEADER.search(head))


def plans_table_verdict(progress_path):
    """Signal A — return (n_rows, n_done) for the child-plan rows in a progress.md."""
    try:
        with open(progress_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return (0, 0)

    rows = 0
    done = 0
    for line in lines:
        m = ROW.match(line)
        if not m:
            continue
        rest = m.group(3)
        # Skip the table's own separator/header artifacts.
        if set(rest.strip()) <= set("-| "):
            continue
        rows += 1
        if DONE.search(rest) and not NOT_DONE.search(rest):
            done += 1
    return (rows, done)


def scan(plans_dir):
    findings = []
    try:
        entries = sorted(os.listdir(plans_dir))
    except OSError:
        return findings

    for name in entries:
        path = os.path.join(plans_dir, name)
        if not os.path.isdir(path):
            continue
        if name in ("archive",) or name.endswith("-program"):
            continue
        if not re.match(r"^\d+[-.]", name):
            continue
        progress = os.path.join(path, "progress.md")
        if not os.path.isfile(progress):
            continue
        rows, done = plans_table_verdict(progress)
        table_says_done = rows > 0 and rows == done
        prose_says_done = prose_complete(progress)
        if table_says_done or prose_says_done:
            num = re.split(r"[-.]", name)[0]
            if table_says_done and prose_says_done:
                why = f"{done}/{rows} plans Done + completion header"
            elif table_says_done:
                why = f"{done}/{rows} plans Done"
            else:
                why = "completion header in progress.md (Plans table may be stale)"
            findings.append((num, name, why))
    return findings


def main():
    dirs = sys.argv[1:]
    if not dirs:
        print("usage: scan-archive-drift.py <plans-dir> [...]", file=sys.stderr)
        return 0

    for plans_dir in dirs:
        if not os.path.isdir(plans_dir):
            continue
        findings = scan(plans_dir)
        if not findings:
            continue
        label = os.path.basename(os.path.dirname(plans_dir.rstrip("/")))
        print()
        print(
            f"Archive drift in {label}/plans — scope(s) reading as finished but still "
            f"at the plans root:"
        )
        for num, name, why in findings:
            print(f"  - scope {num} ({name}) — {why}; not archived")
        print("  Run /closeout for each (it archives + repoints PLANS-INDEX). Verify with:")
        print(
            f"    ~/.claude/skills/closeout/scripts/verify-archive.sh "
            f"{plans_dir} <scope-number>"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
