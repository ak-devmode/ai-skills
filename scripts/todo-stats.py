#!/usr/bin/env python3
"""todo-stats.py — count what is actually in a plans dir's TO-DO.md.

Approach: TO-DO.md reached 473 open items across 133 sections without anyone
noticing, because nothing measured it. `/plan` §11.1-11.2 appends deferred items
automatically at plan completion; nothing removes one except a human deciding to.
A one-way valve grows monotonically, so the fix is not discipline — it is a number
someone sees. This prints that number for a SessionStart hook.

Deliberate non-goals, each load-bearing:

  NO ACTION ITEM.  Counts only. The moment it tells you to do something it becomes
                   the nightly-backmerge PR: ignored, then muted, then disabled.
                   (Alex's scope-104 lesson: "A number on a dashboard survives a
                   deliberate divergence period." An action item does not.)
  NO DUE DATES.    Age, not deadlines. A due date on a deliberately-deferred item
                   manufactures urgency it never had; you blow through it correctly,
                   and then every date in the file is noise.
  NEVER BLOCKS.    Exit 0 always. Prints nothing when it cannot parse. A hook that
                   errors at session start is a hook that gets disabled, and then
                   the visibility fix is gone permanently.

Output shape (one line per plans dir that has a TO-DO.md):

    kalpa TO-DO: 473 open (+12 since 2026-07-10) · 48 P1+ · 118 unverified >90d

WHY THE DELTA NEEDS STORED STATE, AND WHY IT IS NOT REWRITTEN EVERY RUN
A count with no trend is the dashboard nobody reads. But rewriting the baseline on
every session start makes the delta "since last session", which is ~always 0 and
destroys the trend it exists to show. So the baseline advances only once it is older
than BASELINE_MAX_AGE_DAYS, giving a real multi-week window. Baseline lives at
~/.claude/todo-stats-baseline.json (override: $TODO_STATS_BASELINE) — unversioned
local state, matching gstack's ~/.gstack/ convention. It is derived data: losing it
costs one missing delta and self-heals on the next run. It deliberately does NOT
live in a git repo, because a session-start hook that writes into ai-skills would
dirty the very repo the surrounding hook reports on.

THE HEADLINE STALENESS METRIC IS "NEVER VERIFIED", NOT ">90 DAYS OLD"
The plan this implements specified `118 unverified >90d`. That premise is measurably
wrong: on 2026-08-10 the OLDEST date anywhere in kalpa's TO-DO.md is 2026-05-13 and
the 90-day cutoff is 2026-05-12, so the true count is ZERO. The file is not old — it
is ~3 months of accumulation that was almost never re-checked.

A segment printing `0 unverified >90d` would therefore read as reassurance ("nothing
is stale") while the actual state is 469 open items of which 3 carry a verification
stamp. That is the precise failure this whole exercise exists to prevent, so the
headline is `N never verified` instead — computable today, and it states the real
thesis: the file asserts undone-ness it never re-verifies. The `>90d` age segment is
kept but appears only once it is non-zero, which is the point at which it starts
carrying information rather than false comfort.

Age comes from a `VERIFIED STILL TRUE <ISO>` stamp (the convention Alex hand-wrote on
the cashier migration-runner item, matched here rather than replaced), falling back to
the section's dated heading, then the OLDEST ISO date in the item. Oldest, not newest:
an unverified item's age is when it was raised, and items accrete later annotations, so
newest-date would make a much-discussed ancient item look fresh.

KNOWN LIMITS, stated honestly:
  - An item with no stamp and no date anywhere is undatable and is excluded from
    the >90d count (surfaced by --verbose, not in the hook line).
  - "P1+" means P0 or P1 appearing anywhere in the item block. An item discussing
    another item's priority counts once, wrongly. Cheap and close enough for a
    trend number; do not build a gate on it.
  - Closed-in-place `- [x]` items are counted and reported separately because
    TO-DO.md's own convention is to MOVE closed items to archive/TO-DO-archive.md.
    A rising closed-in-place count is a second rot signal, not progress.
  - 46 of kalpa's 133 sections carry no date in their heading, so items under them
    are datable only if they date themselves. Those are excluded from the age count
    and surfaced by --verbose as `undatable`.
  - It counts the WORKING TREE, which can lag origin. kalpa-docs is multi-author and
    was 4 commits behind mid-way through building this (those commits added 2 items),
    so a session that starts before a fetch reports a slightly stale number. Fetching
    here was rejected deliberately: network I/O in a SessionStart hook can hang, and a
    hook that delays every session start is a hook that gets removed. A trend number
    tolerates being a few items stale; a slow session start does not.

Exit: 0 always. Usage: todo-stats.py <plans-dir> [<plans-dir> ...] [--json|--verbose]
"""

import datetime
import json
import os
import re
import sys

BASELINE_MAX_AGE_DAYS = 30
STALE_AFTER_DAYS = 90

# A top-level checkbox item. Nested items (4 of 507 in kalpa today) are folded into
# their parent's block rather than counted, so one logical item is one count.
ITEM = re.compile(r"^- \[([ xX])\]")
HEADING = re.compile(r"^(#{1,6}) ")
SECTION = re.compile(r"^## +(.*)$")
ISO = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
PRIORITY = re.compile(r"\bP([0-9])\b")

# Matches Alex's hand-written form -- "**VERIFIED STILL TRUE 2026-08-01 (not stale):**"
# -- and a plainer "VERIFIED 2026-08-01". Matching the field-invented convention beats
# minting a competing one: he wrote it under real conditions, which is the strongest
# available signal about what he will actually read.
STAMP = re.compile(r"VERIFIED(?:\s+STILL\s+TRUE)?[:\s]+\**\s*(20\d\d-\d\d-\d\d)", re.I)


def _parse_date(text):
    try:
        return datetime.date.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def _newest(dates):
    real = [d for d in dates if d]
    return max(real) if real else None


def _oldest(dates):
    real = [d for d in dates if d]
    return min(real) if real else None


def parse_items(text):
    """Split a TO-DO.md into item records. Shared parsing layer -- the sweep skill
    imports this rather than growing a second, competing parser."""
    items = []
    section = None
    section_date = None
    current = None

    def flush():
        if current is not None:
            items.append(current)

    for line in text.splitlines():
        m_sec = SECTION.match(line)
        if m_sec:
            flush()
            current = None
            section = m_sec.group(1).strip()
            section_date = _newest(_parse_date(d) for d in ISO.findall(line))
            continue

        m_item = ITEM.match(line)
        if m_item:
            flush()
            current = {
                "open": m_item.group(1) == " ",
                "section": section,
                "section_date": section_date,
                "body": [line],
            }
            continue

        if HEADING.match(line):
            # A non-## heading still ends the item it follows.
            flush()
            current = None
            continue

        if current is not None:
            current["body"].append(line)

    flush()

    for it in items:
        blob = "\n".join(it["body"])
        it["text"] = blob
        # Newest stamp (last time anyone checked) but OLDEST plain date (when it was
        # raised) -- see the module docstring on why newest-date would flatter age.
        it["stamped"] = _newest(_parse_date(d) for d in STAMP.findall(blob))
        it["raised"] = _oldest(_parse_date(d) for d in ISO.findall(blob))
        it["priority"] = min(
            (int(p) for p in PRIORITY.findall(blob)), default=None
        )
    return items


def collect(todo_path, today):
    """Return a stats dict, or None when there is nothing trustworthy to report."""
    try:
        with open(todo_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None

    items = parse_items(text)
    open_items = [i for i in items if i["open"]]
    if not open_items:
        return None

    cutoff = today - datetime.timedelta(days=STALE_AFTER_DAYS)
    stale = 0
    undatable = 0
    for it in open_items:
        asof = it["stamped"] or it["section_date"] or it["raised"]
        if asof is None:
            undatable += 1
        elif asof < cutoff:
            stale += 1

    return {
        "path": todo_path,
        "open": len(open_items),
        "closed_in_place": sum(1 for i in items if not i["open"]),
        "sections": len({i["section"] for i in items if i["section"]}),
        "p1plus": sum(
            1 for i in open_items if i["priority"] is not None and i["priority"] <= 1
        ),
        "stale": stale,
        "undatable": undatable,
        "verified": sum(1 for i in open_items if i["stamped"]),
        "never_verified": sum(1 for i in open_items if not i["stamped"]),
    }


def _baseline_path():
    return os.environ.get(
        "TODO_STATS_BASELINE",
        os.path.join(os.path.expanduser("~"), ".claude", "todo-stats-baseline.json"),
    )


def read_baseline():
    try:
        with open(_baseline_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_baseline(data):
    path = _baseline_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError:
        pass  # A missing delta next run is strictly better than a failing hook.


def delta_segment(stats, baseline, today):
    """Return (segment_text, updated_entry_or_None) for this path's baseline."""
    entry = baseline.get(stats["path"])
    prior_date = _parse_date((entry or {}).get("date"))
    prior_open = (entry or {}).get("open")

    fresh = {"date": today.isoformat(), "open": stats["open"]}
    if not isinstance(prior_open, int) or prior_date is None:
        return "", fresh  # First sighting: record it, claim no trend.

    age = (today - prior_date).days
    roll = fresh if age >= BASELINE_MAX_AGE_DAYS else None
    if age == 0:
        return "", roll  # Same-day baseline: a delta against today is not a trend.
    diff = stats["open"] - prior_open
    if diff == 0:
        return f" (flat since {prior_date.isoformat()})", roll
    return f" ({diff:+d} since {prior_date.isoformat()})", roll


def format_line(label, stats, delta):
    segs = [f"{stats['open']} open{delta}"]
    if stats["p1plus"]:
        segs.append(f"{stats['p1plus']} P1+")
    segs.append(f"{stats['never_verified']} never verified")
    # Only once non-zero: a `0 unverified >90d` reads as reassurance, and today it is
    # genuinely 0 because nothing in the file predates 2026-05-13.
    if stats["stale"]:
        segs.append(f"{stats['stale']} >{STALE_AFTER_DAYS}d")
    if stats["closed_in_place"]:
        segs.append(f"{stats['closed_in_place']} closed-in-place")
    return f"{label} TO-DO: " + " · ".join(segs)


def label_for(plans_dir):
    """~/Projects/wellmed/kalpa-docs/plans -> kalpa. Mirrors scan-archive-drift.py's
    derivation, minus the -docs suffix, so the hook line stays short."""
    parent = os.path.basename(os.path.dirname(os.path.abspath(plans_dir.rstrip("/"))))
    return re.sub(r"-docs$", "", parent) or "plans"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print(
            "usage: todo-stats.py <plans-dir> [...] [--json|--verbose]",
            file=sys.stderr,
        )
        return 0

    today = datetime.date.today()
    baseline = read_baseline()
    updates = {}
    rows = []

    for plans_dir in args:
        todo = os.path.join(plans_dir, "TO-DO.md")
        stats = collect(todo, today)
        if stats is None:
            continue
        delta, roll = delta_segment(stats, baseline, today)
        if roll:
            updates[stats["path"]] = roll
        stats["label"] = label_for(plans_dir)
        stats["delta"] = delta  # Keep the leading space -- it joins onto "N open".
        rows.append(stats)

    if updates and "--no-write" not in flags:
        baseline.update(updates)
        write_baseline(baseline)

    if "--json" in flags:
        print(json.dumps(rows, indent=2, default=str))
        return 0

    for stats in rows:
        print(format_line(stats["label"], stats, stats["delta"]))
        if "--verbose" in flags:
            print(
                f"    sections={stats['sections']} verified={stats['verified']} "
                f"undatable={stats['undatable']} stale>{STALE_AFTER_DAYS}d="
                f"{stats['stale']} path={stats['path']}"
            )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 -- a session-start hook must never traceback.
        sys.exit(0)
