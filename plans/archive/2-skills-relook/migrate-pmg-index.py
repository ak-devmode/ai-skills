#!/usr/bin/env python3
"""One-off: migrate pmg-docs/plans/PLANS-INDEX.md to the canonical 5-column shape.

Approach: map each row by ITS OWN width, not by the table header, because PMG's
Active table has two row shapes and the wider one is misaligned against the header.
Anything this script cannot map confidently is left byte-identical and reported, so
a surprise is visible in the diff rather than absorbed.

Source shapes found 2026-08-09:
  Archived, 5 cols:  # | Date | Type | Location | Description
  Active,   6 cols:  # | Date | Type | Location | Status | Description
  Active,   7 cols:  # | Date | Type | Location | Project | Status | Description
                                                  ^^^^^^^ undeclared: the header
                     says 6, so cell 7 (the real Description) renders NOWHERE.
                     39 of 52 Active rows are in this state — their descriptions
                     are invisible in the rendered table today.

Target:              # | Status | Folder | Description | Created by

`Date` folds into Status (`Active (2026-06-23)` / `✅ Done (2026-03-13)`), `Type` and
`Project` are dropped (the folder path carries type; the file is entirely PMG), and
`Created by` is left blank — it fills forward from 2026-08-09 by Alex's decision, no
back-look.

Usage: migrate-pmg-index.py <index> [--write]     (default: dry-run to stdout)
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys

CANONICAL = "| # | Status | Folder | Description | Created by |"
DIVIDER = "|---|--------|--------|-------------|------------|"


def split_row(line: str) -> list[str]:
    body = line.strip()
    if not body.startswith("|"):
        return []
    body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", body)]


def is_divider(line: str) -> bool:
    return bool(re.match(r"^\|[\s:|-]+\|\s*$", line.strip()))


def is_header(cells: list[str]) -> bool:
    return bool(cells) and cells[0].strip() == "#"


def fold_status(status: str, date: str) -> str:
    """Put the date inside Status, which is where the canonical shape carries it."""
    s = status.strip()
    d = date.strip()
    if not d:
        return s or "—"
    if d in s:  # already mentions it
        return s
    if not s:
        return d
    low = s.lower()
    if low.startswith("done") or "✅" in s or low.startswith("complete"):
        return f"✅ {s.lstrip('✅ ').strip()} ({d})"
    return f"{s} ({d})"


def migrate_row(cells: list[str], table: str) -> tuple[list[str] | None, str]:
    """Return (canonical cells, note). None means leave the row alone."""
    n = len(cells)
    if table == "archived" and n == 5:
        num, date, _type, loc, desc = cells
        return [num, fold_status("✅ Done", date), loc, desc, ""], ""
    if table == "active" and n == 6:
        num, date, _type, loc, status, desc = cells
        return [num, fold_status(status, date), loc, desc, ""], ""
    if table == "active" and n == 7:
        num, date, _type, loc, _project, status, desc = cells
        return (
            [num, fold_status(status, date), loc, desc, ""],
            f"row {num or '?'}: recovered a description that rendered nowhere "
            f"({len(desc)} chars)",
        )
    if n == 5 and table == "active":
        # Shape-ambiguous: could already be canonical. Detect by whether cell 2
        # looks like a bare date (source shape) or a status (already migrated).
        if re.match(r"^\d{4}-\d{2}-\d{2}$", cells[1].strip()):
            num, date, _type, loc, desc = cells
            return [num, fold_status("Active", date), loc, desc, ""], ""
        return None, f"row {cells[0] or '?'}: already 5 cols and not date-led — left as-is"
    return None, f"row {cells[0] if cells else '?'}: unmapped {n}-col row — LEFT AS-IS"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("index")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    with open(args.index, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    out: list[str] = []
    table = "other"
    notes: list[str] = []
    counts = {"archived": 0, "active": 0, "skipped": 0, "recovered": 0}

    for line in lines:
        if line.startswith("#"):
            h = line.lstrip("# ").strip().lower()
            if h.startswith(("archived", "completed")):
                table = "archived"
            elif h.startswith("active"):
                table = "active"
            else:
                table = "other"
            out.append(line)
            continue

        if not line.strip().startswith("|") or table == "other":
            out.append(line)
            continue

        if is_divider(line):
            out.append(DIVIDER)
            continue

        cells = split_row(line)
        if is_header(cells):
            out.append(CANONICAL)
            continue

        new, note = migrate_row(cells, table)
        if note:
            notes.append(note)
        if new is None:
            counts["skipped"] += 1
            out.append(line)
            continue
        if "recovered a description" in note:
            counts["recovered"] += 1
        counts[table] += 1
        out.append("| " + " | ".join(new) + " |")

    result = "\n".join(out)

    print(f"migrate-pmg-index: {args.index}", file=sys.stderr)
    for k in ("archived", "active", "recovered", "skipped"):
        print(f"  {k:<10} {counts[k]}", file=sys.stderr)
    if notes:
        print("  notes:", file=sys.stderr)
        for nt in notes:
            print(f"    - {nt}", file=sys.stderr)

    if args.write:
        shutil.copy2(args.index, args.index + ".pre-migration")
        with open(args.index, "w", encoding="utf-8") as fh:
            fh.write(result)
        print(f"  WROTE (backup at {args.index}.pre-migration)", file=sys.stderr)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
