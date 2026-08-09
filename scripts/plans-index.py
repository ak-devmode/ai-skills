#!/usr/bin/env python3
"""PLANS-INDEX.md reader/writer — the schema is enforced here, not in prose.

Approach: parse the file into (heading, table) sections, then operate on rows as
structured records. Every write goes through a shape check, so a malformed row
cannot be appended. This exists because prose could not hold the line: /plan
§12.4 used to say "if no row exists, append one" with a seven-column template
and nothing wrote a header for it, so 40 rows accreted into an untabled fragment
that was, for a while, the ONLY index registration for scopes 101/106/107/108.
An append with no header is not a record; it is a leak.

Canonical shape (decided 2026-08-09):
    | # | Status | Folder | Description | Created by |

Commands:
    validate <index>                 read-only conformance report; exit 1 if issues
    next-number <index>              highest whole scope number + 1
    add <index> --num --status --folder --desc [--creator]
    move <index> --num --to {active,archived} [--folder] [--status]

Stdlib only. Never rewrites a row it was not asked to touch.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

CANONICAL = ["#", "Status", "Folder", "Description", "Created by"]

# Soft guidance, never enforced. The Description column is Alex's high-level
# tracking surface — he reads it from the console to see what has been going on,
# so 3-4 sentences there is the intended use, not bloat. A row past this gets a
# note; it is NEVER truncated. Truncating it would destroy the only copy of some
# decision rationale (the 2026-08-09 audit initially proposed exactly that, on
# the strength of a written 300-char cap that had been violated 80 times — a rule
# contradicted that consistently is a rule that is wrong, per markdown-style
# §2.2.3's own reasoning).
CELL_SOFT = 900

ACTIVE_HEADINGS = ("active plans", "active / in progress", "active")
ARCHIVED_HEADINGS = ("completed / archived", "archived (complete)", "archived", "completed")


def split_row(line: str) -> list[str]:
    """Split a markdown table row into cells, tolerating escaped pipes."""
    body = line.strip()
    if not body.startswith("|"):
        return []
    body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    # Split on pipes not preceded by a backslash.
    return [c.strip() for c in re.split(r"(?<!\\)\|", body)]


def is_divider(line: str) -> bool:
    return bool(re.match(r"^\|[\s:|-]+\|\s*$", line.strip()))


class Section:
    def __init__(self, heading: str, start: int):
        self.heading = heading
        self.start = start
        self.header: list[str] = []
        self.header_line = -1
        self.rows: list[tuple[int, list[str]]] = []  # (line index, cells)

    @property
    def kind(self) -> str:
        h = self.heading.lower().lstrip("# ").strip()
        if any(h.startswith(a) for a in ACTIVE_HEADINGS):
            return "active"
        if any(h.startswith(a) for a in ARCHIVED_HEADINGS):
            return "archived"
        return "other"


def parse(path: str):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    sections: list[Section] = []
    cur: Section | None = None
    for i, line in enumerate(lines):
        if line.startswith("#"):
            cur = Section(line, i)
            sections.append(cur)
            continue
        if not line.strip().startswith("|"):
            continue
        if cur is None:  # a table before any heading
            cur = Section("(no heading)", i)
            sections.append(cur)
        cells = split_row(line)
        if is_divider(line):
            continue
        if not cur.header:
            cur.header, cur.header_line = cells, i
        else:
            cur.rows.append((i, cells))
    return lines, sections


def scope_num(cell: str):
    """Whole scope number from a '#' cell, or None for sub-numbers/junk."""
    m = re.match(r"^\*{0,2}(\d+)\*{0,2}$", cell.strip())
    return int(m.group(1)) if m else None


def sub_num(cell: str) -> bool:
    return bool(re.match(r"^\*{0,2}\d+\.\d+", cell.strip()))


def slug_row(cell: str) -> bool:
    """A deliberately un-numbered row. Three valid forms: a program control surface
    or standing doc (`catalog-program`, `roadmap`); an em/en-dash or "TBD" marking a
    row that has no scope number yet (a PRD awaiting scoping); or blank. These are
    valid index rows, not malformed ones — flagging them as junk is how a validator
    earns being ignored."""
    c = cell.strip().strip("*`")
    return c in {"", "—", "–", "-", "TBD", "n/a"} or bool(
        re.match(r"^[a-z][a-z0-9-]*$", c)
    )


# ---------------------------------------------------------------- validate

def cmd_validate(args) -> int:
    lines, sections = parse(args.index)
    issues: list[str] = []
    notes: list[str] = []

    tables = [s for s in sections if s.header]
    scope_tables = [s for s in tables if s.kind in ("active", "archived")]

    print(f"PLANS-INDEX: {args.index}")
    size = os.path.getsize(args.index)
    print(f"  size: {size:,} bytes (~{size // 4000:,}k tokens if read whole)")
    if size > 20000:
        notes.append(
            f"file is {size:,} bytes (~{size // 4000}k tokens). The descriptions are "
            f"deliberate — they are the console status tracker. The cost to manage is "
            f"on the READING side: grep the rows you need, never read the whole file "
            f"into context (/plan §1.1)"
        )

    if not scope_tables:
        issues.append("no Active/Archived scope table found — cannot validate shape")
    for s in tables:
        label = s.heading.lstrip("# ").strip() or "(no heading)"
        print(f"\n  [{s.kind}] {label} — {len(s.rows)} rows, {len(s.header)} cols")
        print(f"       header: {' | '.join(s.header)}")

        if s.kind == "other":
            notes.append(f"'{label}' is not a scope table — skipped")
            continue

        if s.header != CANONICAL:
            issues.append(
                f"'{label}' header is {s.header} — canonical is {CANONICAL}"
            )

        widths: dict[int, int] = {}
        per_plan, oversized, bad_num, slugs = [], [], [], []
        for ln, cells in s.rows:
            widths[len(cells)] = widths.get(len(cells), 0) + 1
            if cells and sub_num(cells[0]):
                per_plan.append((ln + 1, cells[0]))
            if cells and scope_num(cells[0]) is None and not sub_num(cells[0]):
                (slugs if slug_row(cells[0]) else bad_num).append(
                    (ln + 1, cells[0][:40])
                )
            for ci, c in enumerate(cells):
                if len(c) > CELL_SOFT:
                    oversized.append((ln + 1, cells[0] if cells else "?", ci, len(c)))

        # A row SHORT of the canonical width renders fine (trailing cells are
        # empty) and is expected: `Created by` was added 2026-08-09 and fills
        # forward only — Alex declined a back-look, so pre-existing rows are
        # short by design. A row LONGER than the header is genuinely broken:
        # the extra cell renders nowhere and is invisible in the table.
        for n, c in sorted(widths.items()):
            if n > len(CANONICAL):
                issues.append(
                    f"'{label}': {c} row(s) have {n} cols, header declares "
                    f"{len(CANONICAL)} — the extra cell(s) render nowhere"
                )
            elif n < len(CANONICAL):
                notes.append(
                    f"'{label}': {c} row(s) have {n} cols — trailing columns "
                    f"empty, expected for rows predating 'Created by'"
                )

        if per_plan:
            notes.append(
                f"'{label}' has {len(per_plan)} per-plan rows — intentional; "
                f"phase-level rows are how Alex tracks progress from the console"
            )
        if oversized:
            worst = max(oversized, key=lambda t: t[3])
            notes.append(
                f"'{label}' has {len(oversized)} cell(s) over {CELL_SOFT} chars "
                f"(soft guidance only, nothing is truncated). Worst: row "
                f"{worst[1]} col {worst[2]} at {worst[3]:,} chars — consider moving "
                f"the detail to progress.md if it is rationale rather than status"
            )
        if bad_num:
            issues.append(
                f"'{label}' has {len(bad_num)} row(s) with an unparseable '#': "
                + ", ".join(f"L{ln}:'{v}'" for ln, v in bad_num[:5])
            )
        if slugs:
            notes.append(
                f"'{label}' has {len(slugs)} un-numbered row(s) — programs and "
                f"standing docs, valid: " + ", ".join(v for _, v in slugs)
            )

    # Disk truth: table membership must follow folder location (§11.7.2).
    plans_dir = os.path.dirname(os.path.abspath(args.index))
    live = {d.split("-", 1)[0] for d in os.listdir(plans_dir)
            if os.path.isdir(os.path.join(plans_dir, d)) and re.match(r"^\d+-", d)}
    arch_dir = os.path.join(plans_dir, "archive")
    archived = set()
    if os.path.isdir(arch_dir):
        archived = {d.split("-", 1)[0] for d in os.listdir(arch_dir)
                    if re.match(r"^\d+-", d)}

    for s in scope_tables:
        for ln, cells in s.rows:
            n = scope_num(cells[0]) if cells else None
            if n is None:
                continue
            key = str(n)
            if s.kind == "active" and key in archived and key not in live:
                issues.append(
                    f"scope {n} sits in Active (L{ln+1}) but its folder is under "
                    f"archive/ — §11.7.2: table membership follows disk state"
                )
            if s.kind == "archived" and key in live:
                issues.append(
                    f"scope {n} sits in Completed (L{ln+1}) but has a live folder "
                    f"at the plans root — §11.7.2"
                )

    print()
    if notes:
        for n in notes:
            print(f"  note: {n}")
    if issues:
        print(f"  {len(issues)} ISSUE(S):")
        for i, msg in enumerate(issues, 1):
            print(f"    {i}. {msg}")
        return 1
    print("  conformant.")
    return 0


# ------------------------------------------------------------ next-number

def cmd_next_number(args) -> int:
    _, sections = parse(args.index)
    highest = 0
    for s in sections:
        if s.kind not in ("active", "archived"):
            continue
        for _, cells in s.rows:
            n = scope_num(cells[0]) if cells else None
            if n and n > highest:
                highest = n
    print(highest + 1)
    return 0


# -------------------------------------------------------------------- add

def cmd_add(args) -> int:
    lines, sections = parse(args.index)
    target = next((s for s in sections if s.kind == "active" and s.header), None)
    if target is None:
        print("plans-index: no Active table to append to. Create one with the "
              f"canonical header: | {' | '.join(CANONICAL)} |", file=sys.stderr)
        return 2
    if target.header != CANONICAL:
        print(f"plans-index: refusing to append — Active header is {target.header}, "
              f"canonical is {CANONICAL}. Migrate the table first.", file=sys.stderr)
        return 2

    for _, cells in target.rows:
        if cells and scope_num(cells[0]) == args.num:
            print(f"plans-index: scope {args.num} already has a row in Active.",
                  file=sys.stderr)
            return 2

    row = build_row(args.num, args.status, args.folder, args.desc, args.creator)
    insert_at = (target.rows[-1][0] if target.rows else target.header_line + 1) + 1
    lines.insert(insert_at, row)
    write(args.index, lines, args.dry_run)
    print(row)
    return 0


def build_row(num, status, folder, desc, creator) -> str:
    """Escape and flatten cells. Never truncates — see CELL_SOFT."""
    cells = [str(num), status, folder, desc, creator or ""]
    out = []
    for i, c in enumerate(cells):
        c = c.replace("|", "\\|").replace("\n", " ").strip()
        if len(c) > CELL_SOFT:
            print(f"plans-index: note — col '{CANONICAL[i]}' is {len(c):,} chars. "
                  f"Kept in full; move it to progress.md if it is rationale rather "
                  f"than status.", file=sys.stderr)
        out.append(c)
    return "| " + " | ".join(out) + " |"


# ------------------------------------------------------------------- move

def cmd_move(args) -> int:
    lines, sections = parse(args.index)
    src_kind = "active" if args.to == "archived" else "archived"
    src = next((s for s in sections if s.kind == src_kind and s.header), None)
    dst = next((s for s in sections if s.kind == args.to and s.header), None)
    if src is None or dst is None:
        print(f"plans-index: need both an {src_kind} and an {args.to} table.",
              file=sys.stderr)
        return 2

    found = None
    for ln, cells in src.rows:
        if cells and scope_num(cells[0]) == args.num:
            found = (ln, cells)
            break
    if found is None:
        print(f"plans-index: scope {args.num} not found in the {src_kind} table.",
              file=sys.stderr)
        return 2

    ln, cells = found
    cells = (cells + [""] * len(CANONICAL))[: len(CANONICAL)]
    if args.status:
        cells[1] = args.status
    if args.folder:
        cells[2] = args.folder
    row = build_row(cells[0], cells[1], cells[2], cells[3], cells[4])

    dst_last = dst.rows[-1][0] if dst.rows else dst.header_line + 1
    del lines[ln]
    insert_at = dst_last + 1 if dst_last < ln else dst_last
    lines.insert(insert_at, row)
    write(args.index, lines, args.dry_run)
    print(f"moved scope {args.num}: {src_kind} -> {args.to}")
    print(row)
    return 0


def write(path: str, lines: list[str], dry_run: bool) -> None:
    if dry_run:
        print("(--dry-run: not written)", file=sys.stderr)
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate"); v.add_argument("index"); v.set_defaults(fn=cmd_validate)
    n = sub.add_parser("next-number"); n.add_argument("index"); n.set_defaults(fn=cmd_next_number)

    a = sub.add_parser("add")
    a.add_argument("index"); a.add_argument("--num", type=int, required=True)
    a.add_argument("--status", required=True); a.add_argument("--folder", required=True)
    a.add_argument("--desc", required=True); a.add_argument("--creator")
    a.add_argument("--dry-run", action="store_true"); a.set_defaults(fn=cmd_add)

    m = sub.add_parser("move")
    m.add_argument("index"); m.add_argument("--num", type=int, required=True)
    m.add_argument("--to", choices=["active", "archived"], required=True)
    m.add_argument("--folder"); m.add_argument("--status")
    m.add_argument("--dry-run", action="store_true"); m.set_defaults(fn=cmd_move)

    args = p.parse_args()
    if not os.path.isfile(args.index):
        print(f"plans-index: no such file: {args.index}", file=sys.stderr)
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
