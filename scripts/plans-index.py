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
    status <index> --num --status [--skip-verify REASON] [--blocking|--advisory]
    gate-count [<index> ...] [--discover]  clean gated scopes toward the blocking flip
    render <plans-dir> [--stdout] [--allow-loss]   records -> PLANS-INDEX.md + archive/INDEX.md
    migrate <plans-dir> [--branch REF [--base REV]] [--dry-run]   old index rows -> records
    check <plans-dir>                committed render == fresh render; size; headerless rows

Records (scope 9): once plans/README.md declares `**Index render:** bot | local`, add /
status / move write the scope's rows into the `plans-index:begin/end` block of its own
progress.md (loose rows: plans/index-loose.md), and PLANS-INDEX.md is rendered output —
by the bot on push (`bot`) or by the command itself (`local`). Without that line the
graph is not migrated and every command edits the index in place, as before. `<index>`
may be the plans dir itself.

Verification gate (templates/verify-contracts.md §5): `status` runs verdict-gate.py
before writing a Done status on a phase row (`N.P`) whose scope folder has a
finish-conditions.md — refusing in blocking mode, appending the gate's ⚠ marker
otherwise. `validate` fails on a Done phase row in such a scope that has neither a
passing gate nor a visible ⚠ advisory/skip marker: a Done written by hand. Scopes
without a finish table predate the gate and are exempt until /plan self-heals them;
phases the table lists under `**Predates gate:**` stay exempt after it.

`gate-count` counts *clean gated scopes* across the given indexes: an archived scope
whose folder has a finish-conditions.md and whose scope row and phase rows carry no ⚠
marker. /closeout prints it; at vl.BLOCKING_AFTER it adds the reminder to flip
vl.GATE_MODE to blocking (Alex, 2026-09-29: flip at 5).

Stdlib only. Never rewrites a row it was not asked to touch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

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

DONE = re.compile(r"✅|\bdone\b", re.I)
MARKER = re.compile(r"\s*⚠ (?:judge|verify)[^⚠]*")
GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verdict-gate.py")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_lib as vl  # noqa: E402  (§10 message contract for `status`)


def status_msg(level, what, expected, found, where, cause, nxt):
    return vl.message(level, what, expected, found, where, cause, nxt, f"{vl.CONTRACT} §5")

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


def parse(path: str | None, text: str | None = None):
    if text is None:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    lines = text.split("\n")

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


def row_num(value: str) -> str:
    """`add --num`: a scope (`5`) or a per-plan row (`5.1`) — /scope §5.9 adds both."""
    if not re.match(r"^\d+(\.\d+)?$", value):
        raise argparse.ArgumentTypeError(f"expected N or N.P, got '{value}'")
    return value


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


# ----------------------------------------------------------------- records
#
# Scope 9 (2026-10-24): each scope's rows live in a script-owned block inside its own
# progress.md, and PLANS-INDEX.md is rendered from those blocks — two sessions writing
# different scopes touch different files, never the shared index. Table membership
# follows disk: a record under an `archive/` folder renders as Completed / Archived, so
# no row is ever "moved" again. A graph opts in with `**Index render:** bot | local` in
# plans/README.md. Until it does (the cutover, plan 9.3) every command keeps editing the
# index in place — this code goes live on merge, and a records write against an
# unmigrated graph would render an index with almost nothing in it.

LOOSE = "index-loose.md"            # rows with no scope folder: loose PRDs, programs, _(not created)_
ARCHIVE_INDEX = os.path.join("archive", "INDEX.md")   # eng D24: archived rows render apart
RENDER_LINE = re.compile(r"^\*\*Index render:\*\*[ \t]*(.*?)[ \t]*$", re.M)
MAX_BYTES = 150_000                 # absorbed from kalpa-docs check-plans-index.py
ORPHAN = re.compile(r"^\| \d+(\.\d+)? \| \d{4}-\d{2}-\d{2} \| (scope|plan) \|")
HEADER_LINES = ["| " + " | ".join(CANONICAL) + " |", "|" + "---|" * len(CANONICAL)]


class Refuse(Exception):
    """A state the script will not guess past; main() prints it and exits 2."""


def plans_of(index: str) -> str:
    return os.path.dirname(os.path.abspath(index))


def render_mode(plans: str):
    """`bot`, `local`, or None (not migrated — legacy in-place edits)."""
    path = os.path.join(plans, "README.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        m = RENDER_LINE.search(fh.read())
    if m is None:
        return None
    if m.group(1) not in ("bot", "local"):
        raise Refuse(f"{path}: **Index render:** is {m.group(1)!r} — expected bot | local")
    return m.group(1)


def marker(end: bool, tag: str = "") -> str:
    return f"<!-- plans-index:{'end' if end else 'begin'}{' ' + tag if tag else ''} -->"


def esc(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", " ").strip()


def row_line(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def read_block(path: str, tag: str = ""):
    """The block's rows (escaped cells), or None when the file has no block. A begin with
    no end, or an end with no begin, is a clobbered block — refused, never guessed at."""
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        lines = [l.strip() for l in fh.read().split("\n")]
    b, e = marker(False, tag), marker(True, tag)
    if b not in lines:
        if e in lines:
            raise Refuse(f"{path}: '{e}' with no '{b}' — the record block was overwritten")
        return None
    i = lines.index(b)
    if e not in lines[i:]:
        raise Refuse(f"{path}: '{b}' with no '{e}' — the record block was overwritten; "
                     f"restore it from git (git log -p -- {path})")
    j = lines.index(e, i)
    return [split_row(l) for l in lines[i + 1:j]
            if l.startswith("|") and not is_divider(l) and split_row(l) != CANONICAL]


def atomic_write(path: str, text: str) -> None:
    """Write a sibling temp file, then os.replace it over `path` (review 9.1-r1-02): a crash
    mid-write leaves the old file whole, never a truncated progress.md — the record and the
    scope's whole log in one. Keeps the file's mode; a new file gets the umask's."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    try:
        mode = os.stat(path).st_mode & 0o7777
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".plans-index-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_block(path: str, rows: list[list[str]], tag: str = "", dry_run: bool = False) -> None:
    """Replace the block, or add it: in an existing progress.md before its first `## `
    section; a missing progress.md gets a minimal one; the loose file a heading per tag."""
    body = [marker(False, tag), *HEADER_LINES, *(row_line(c) for c in rows), marker(True, tag)]
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    elif tag:
        lines = ["# Loose index rows", "",
                 "Rows with no scope folder (loose PRDs, programs, `_(not created)_`). Script-owned:",
                 "write through `plans-index.py`, never by hand.", ""]
    else:
        lines = [f"# Progress — {os.path.basename(os.path.dirname(path))}", ""]
    stripped = [l.strip() for l in lines]
    if marker(False, tag) in stripped:
        i = stripped.index(marker(False, tag))
        lines[i:stripped.index(marker(True, tag), i) + 1] = body
    elif tag:
        lines += ["## " + ("Active Plans" if tag == "active" else "Completed / Archived"), "", *body, ""]
    else:
        at = next((k for k, l in enumerate(lines) if k and l.startswith("## ")), len(lines))
        lines[at:at] = ["## Index record", "",
                        "Script-owned (`plans-index.py`); PLANS-INDEX.md is rendered from it.", "",
                        *body, ""]
    if dry_run:
        print(f"(--dry-run: {path} not written)", file=sys.stderr)
        return
    atomic_write(path, "\n".join(lines))


class Rec:
    def __init__(self, path, tag, kind, folder, rows):
        self.path, self.tag, self.kind, self.folder, self.rows = path, tag, kind, folder, rows


def progress_file(folder: str) -> str:
    """The folder's progress file, whatever its case (kalpa-docs 45 has PROGRESS.md) — on a
    case-sensitive disk (the bot's runner) a fresh `progress.md` beside it would split the
    record from the log; on macOS the two names are one file anyway."""
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.lower() == "progress.md":
                return os.path.join(folder, name)
    return os.path.join(folder, "progress.md")


def disk_kind(rel: str) -> str:
    return "archived" if "archive" in rel.split(os.sep) else "active"


def records(plans: str) -> list[Rec]:
    out = []
    for d, dirs, files in os.walk(plans):
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and x != "node_modules")
        names = [f for f in files if f.lower() == "progress.md"]
        if d != plans and names:
            path = os.path.join(d, sorted(names)[0])
            rows = read_block(path)
            if rows is not None:
                rel = os.path.relpath(d, plans)
                out.append(Rec(path, "", disk_kind(rel), rel, rows))
    loose = os.path.join(plans, LOOSE)
    for tag in ("active", "archived"):
        rows = read_block(loose, tag)
        if rows is not None:
            out.append(Rec(loose, tag, tag, None, rows))
    return out


def num_of(cells: list[str]) -> str:
    return cells[0].strip().strip("*") if cells else ""


def numbered(cells: list[str]) -> bool:
    return bool(cells) and (scope_num(cells[0]) is not None or sub_num(cells[0]))


def sort_key(cells: list[str]):
    m = re.match(r"^(\d+)(?:\.(\d+))?", num_of(cells))
    return (0, int(m.group(1)), int(m.group(2) or -1), num_of(cells)) if m else (1, 0, 0, "")


def render_text(plans: str, recs: list[Rec] | None = None) -> tuple[str, str]:
    """(PLANS-INDEX.md, archive/INDEX.md) as text. Deterministic: rows sort by number;
    un-numbered rows (only ever loose) follow, in the loose file's order."""
    rows = {"active": [], "archived": []}
    for r in recs if recs is not None else records(plans):
        rows[r.kind].extend(r.rows)
    gen = ("<!-- GENERATED by ai-skills scripts/plans-index.py render. Do not edit: write "
           "through plans-index.py add / status / move. -->\n"
           "**Generated file — do not edit by hand.** Each scope's rows live in a script-owned "
           "block in its own `progress.md`; `plans-index.py add / status / move` write them and "
           "`render` rebuilds this file. Conventions: `plans/README.md`.")
    out = []
    for kind, title, heading, more in (
            ("active", "Plans Index", "Active Plans",
             "Completed / archived scopes: `archive/INDEX.md`."),
            ("archived", "Plans Index — Completed / Archived", "Completed / Archived",
             "Active scopes: `../PLANS-INDEX.md`. Folder paths are relative to `plans/`.")):
        body = [row_line(c) for c in sorted(rows[kind], key=sort_key)]
        out.append("\n".join([f"# {title}", "", gen, more, "", f"## {heading}", "",
                              *HEADER_LINES, *body, ""]))
    return out[0], out[1]


def slurp(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def committed_text(plans: str) -> str:
    return "\n".join(t for t in (slurp(os.path.join(plans, n)) for n in ("PLANS-INDEX.md", ARCHIVE_INDEX)) if t)


def index_rows(text: str) -> list[tuple[str, list[str]]]:
    """(table kind, cells) for every row of the Active / Archived tables in `text`."""
    _, sections = parse(None, text)
    return [(s.kind, c) for s in sections if s.kind in ("active", "archived") for _, c in s.rows]


def row_key(cells: list[str]):
    return num_of(cells) if numbered(cells) else tuple(cells)


def lost_rows(plans: str, fresh: str) -> list[list[str]]:
    """CEO R1: rows the committed render shows that a fresh render does not — a record
    block overwritten by an agent's Write would otherwise drop them without a sound."""
    new = {row_key(c) for _, c in index_rows(fresh)}
    return [c for _, c in index_rows(committed_text(plans)) if row_key(c) not in new]


def lost_msg(cells: list[str]) -> str:
    folder = cells[2] if len(cells) > 2 else "?"
    return (f"row {cells[0]} rendered before but has no record now — was its progress.md block "
            f"overwritten? Restore it from git (git log -p -- {cell_path(folder) or folder}/progress.md)")


def stray(plans: str, fresh: str) -> list[str]:
    """Review 9.1-r1-01: what a render would drop that is not a scope row — another table
    (Pending PRDs, Programs), prose, a `**Gate mode:**` line — one entry per section.
    lost_rows covers scope rows; a title heading is replaced, not lost. A generated file
    yields nothing: every line it holds is in a fresh render."""
    keep, out = set(fresh.split("\n")), []
    for name in ("PLANS-INDEX.md", ARCHIVE_INDEX):
        path = os.path.join(plans, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        counts, sec = {}, Section("(top)", 0)
        for line in lines:
            if line.startswith("#"):
                sec = Section(line, 0)
                continue
            if not line.strip() or line in keep or vl.GATE_MODE_LINE.match(line) or (
                    sec.kind != "other" and line.strip().startswith("|")):
                continue
            label = sec.heading.lstrip("# ").strip()
            counts[label] = counts.get(label, 0) + 1
        out += [f"{name} § {label}: {n} line(s) of non-scope content" for label, n in counts.items()]
    return out


def gate_lines(plans: str) -> tuple[str | None, str | None]:
    """(the index's `**Gate mode:**` value, README.md's) — a render drops the index's line,
    and verify_lib.gate_mode then falls back to advisory: a blocking graph (IRIS) would
    stop blocking without a sound. The line must live in README.md first."""
    readme, vals = os.path.join(plans, "README.md"), []
    for text in (committed_text(plans), slurp(readme)):
        m = vl.GATE_MODE_LINE.search(text)
        vals.append(m.group(1) if m else None)
    return vals[0], vals[1]


def write_text(path: str, text: str) -> bool:
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return False
    atomic_write(path, text)
    return True


def do_render(plans: str, allow_loss: bool = False) -> int:
    recs = records(plans)
    active, archived = render_text(plans, recs)
    if not recs and index_rows(committed_text(plans)):
        print(f"plans-index: {plans} has no records but its index has rows — not migrated. "
              f"Run `plans-index.py migrate {plans}` first.", file=sys.stderr)
        return 2
    twice = dupes(recs)
    if twice:  # --allow-loss is about rows vanishing; a doubled row is the opposite
        for n, ps in twice.items():
            print(f"plans-index: DUPLICATE {dupe_msg(plans, n, ps)}", file=sys.stderr)
        print(f"plans-index: render refused — {len(twice)} number(s) held twice.", file=sys.stderr)
        return 1
    index_gate, readme_gate = gate_lines(plans)
    if index_gate is not None and index_gate != readme_gate:  # --allow-loss never covers this
        print(f"plans-index: render refused — the index declares **Gate mode:** {index_gate} and "
              f"plans/README.md {'declares ' + readme_gate if readme_gate else 'does not'}; the render "
              f"would drop it and the gate would fall back to {vl.GATE_MODE}. Run `plans-index.py "
              f"migrate {plans}` (it moves the line) or move it to README.md by hand.", file=sys.stderr)
        return 1
    lost = lost_rows(plans, active + "\n" + archived)
    prose = stray(plans, active + "\n" + archived)
    if (lost or prose) and not allow_loss:
        for c in lost:
            print(f"plans-index: LOST {lost_msg(c)}", file=sys.stderr)
        for s in prose:
            print(f"plans-index: STRAY {s} — the render has no place for it", file=sys.stderr)
        print(f"plans-index: render refused — {len(lost)} row(s) and {len(prose)} section(s) would "
              f"vanish. Restore the record(s) / move the content to plans/README.md, or pass "
              f"--allow-loss if the removal is deliberate.", file=sys.stderr)
        return 1
    changed = [n for n, t in (("PLANS-INDEX.md", active), (ARCHIVE_INDEX, archived))
               if write_text(os.path.join(plans, n), t)]
    print(f"rendered {plans}: {active.count(chr(10) + '| ') - 1} active, "
          f"{archived.count(chr(10) + '| ') - 1} archived row(s)"
          + (f" — wrote {', '.join(changed)}" if changed else " — unchanged"))
    return 0


def after_write(plans: str, mode: str, dry_run: bool) -> int:
    """`local` re-renders now; `bot` leaves PLANS-INDEX.md to the bot — a dirty tracked
    render in every session would bring the shared-file conflict straight back."""
    return do_render(plans) if mode == "local" and not dry_run else 0


def cmd_render(args) -> int:
    plans = plans_of(args.index)
    if args.stdout:  # eng D23: a fresh read after a write, whatever the committed file says
        active, archived = render_text(plans)
        # Review 9.1-r1-13: still a read (exit 0), but a reader that misses a row hears why
        for c in lost_rows(plans, active + "\n" + archived):
            print(f"plans-index: LOST {lost_msg(c)}", file=sys.stderr)
        sys.stdout.write(active + "\n" + archived)
        return 0
    return do_render(plans, args.allow_loss)


def cmd_check(args) -> int:
    """Committed render == fresh render, plus the kalpa-docs guard's size and headerless-row
    checks. Never calls verdict-gate.py (progress.md rule 5: its memory blowup)."""
    plans = plans_of(args.index)
    issues = []
    try:
        recs = records(plans)
        active, archived = render_text(plans, recs)
    except Refuse as e:
        print(f"plans-index check: {plans}\n  1 ISSUE(S):\n    1. {e}")
        return 1
    issues += [dupe_msg(plans, n, ps) for n, ps in dupes(recs).items()]
    for c in lost_rows(plans, active + "\n" + archived):
        issues.append(lost_msg(c))
    issues += [f"{s} — a render drops it; move it to plans/README.md"
               for s in stray(plans, active + "\n" + archived)]
    index_gate, readme_gate = gate_lines(plans)
    if index_gate is not None and index_gate != readme_gate:
        issues.append(f"the index declares **Gate mode:** {index_gate} and plans/README.md does not "
                      f"match — a render drops the line; `migrate` moves it")
    for name, fresh in (("PLANS-INDEX.md", active), (ARCHIVE_INDEX, archived)):
        path = os.path.join(plans, name)
        if not os.path.isfile(path):
            issues.append(f"{name} missing — run `plans-index.py render {plans}`")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if text != fresh:
            issues.append(f"{name} differs from a fresh render of the records — re-render "
                          f"(`plans-index.py render`; in bot mode the bot does it on push). "
                          f"A hand edit there is overwritten, not imported.")
        orphans = [i for i, l in enumerate(text.split("\n"), 1) if ORPHAN.match(l)]
        if orphans:
            issues.append(f"{name}: {len(orphans)} headerless 7-column row(s) at line(s) "
                          f"{', '.join(map(str, orphans[:10]))} — they belong in progress.md")
        if name == "PLANS-INDEX.md" and len(text.encode()) > MAX_BYTES:
            issues.append(f"{name} is {len(text.encode()):,} bytes (limit {MAX_BYTES:,}) — it "
                          f"is read into agent context; move detail into progress.md")
    print(f"plans-index check: {plans}")
    if issues:
        print(f"  {len(issues)} ISSUE(S):")
        for i, msg in enumerate(issues, 1):
            print(f"    {i}. {msg}")
        return 1
    print("  render matches records.")
    return 0


def cell_path(cell: str) -> str:
    """The path in a Folder cell: a `code` span, a [link](target), or the bare cell."""
    m = re.search(r"`([^`]+)`", cell) or re.search(r"\]\(([^)]+)\)", cell)
    return (m.group(1) if m else cell).strip().rstrip("/")


def place(plans: str, cell: str):
    """(record folder relative to plans/, None) or (None, why the row cannot be placed)."""
    path = cell_path(cell)
    if not path:
        return None, "no folder"
    root = os.path.abspath(plans)
    full = os.path.normpath(os.path.join(root, path))
    if not full.startswith(root + os.sep):
        return None, "folder outside plans/"
    if os.path.isfile(full) or (full.endswith(".md") and not os.path.isdir(full)):
        full = os.path.dirname(full)   # a plan-file row belongs to its scope folder, written yet or not
    if not os.path.isdir(full):
        return None, "folder not on disk"
    rel = os.path.relpath(full, root)
    leaf = os.path.basename(rel)
    if rel == "." or leaf in ("archive", "pending") or leaf.endswith("-program"):
        return None, "not a scope folder (program, archive/ or plans root)"
    return rel, None


def git_out(path: str, *args):
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def branch_rows(plans: str, ref: str, base: str | None) -> list[tuple[str, list[str]]]:
    """CEO D3: the rows an open branch changed in the old index since it forked — so its
    edits become records instead of a conflict on a file nobody hand-edits any more."""
    top = (git_out(plans, "rev-parse", "--show-toplevel") or "").strip()
    if not top:
        raise Refuse(f"{plans} is not in a git repo — --branch needs one")
    rel = os.path.relpath(os.path.realpath(plans), os.path.realpath(top))
    if base is None:
        trunk = (git_out(top, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main").strip()
        base = (git_out(top, "merge-base", ref, trunk) or "").strip()
        if not base:
            raise Refuse(f"no merge-base between {ref} and {trunk} — pass --base <rev>")

    def at(rev):
        parts = [git_out(top, "show", f"{rev}:{rel}/{n}") for n in ("PLANS-INDEX.md", "archive/INDEX.md")]
        if parts[0] is None and git_out(top, "rev-parse", "--verify", "-q", rev) is None:
            raise Refuse(f"unknown revision {rev}")
        return index_rows("\n".join(p for p in parts if p))

    before = {row_key(c): c for _, c in at(base)}
    changed = [(k, c) for k, c in at(ref) if before.get(row_key(c)) != c]
    print(f"migrate --branch {ref}: {len(changed)} row(s) changed since {base[:9]}")
    return changed


def cmd_migrate(args) -> int:
    """Old index rows -> records. Idempotent; a record that already holds a different row is
    kept and reported (importing hand edits is D4, deferred). Prints every row it could not
    place in a scope record, and every row whose table will change to follow disk."""
    plans = plans_of(args.index)
    overwrite = bool(args.branch)
    old = branch_rows(plans, args.branch, args.base) if args.branch else index_rows(committed_text(plans))
    entries = []
    for kind, cells in old:
        rel, why = place(plans, cells[2] if len(cells) > 2 else "") if numbered(cells) \
            else (None, "un-numbered row (program or standing doc)")
        entries.append({"kind": kind, "cells": cells, "rel": rel, "why": why})

    # A repeated '#': one row goes to the scope record — the one already there, else the one
    # whose table agrees with disk, else the first. The rest stay loose, reported.
    groups: dict[str, list[dict]] = {}
    for e in entries:
        if numbered(e["cells"]) and not overwrite:
            groups.setdefault(num_of(e["cells"]), []).append(e)
    for num, es in groups.items():
        if len(es) < 2:
            continue
        def present(e):
            return e["rel"] and e["cells"] in (read_block(progress_file(os.path.join(plans, e["rel"]))) or [])
        keep = next((e for e in es if present(e)), None) or \
            next((e for e in es if e["rel"] and disk_kind(e["rel"]) == e["kind"]), es[0])
        for e in es:
            if e is not keep:
                e["rel"], e["why"] = None, f"duplicate # {num} ({len(es)} rows)"

    report, targets = [], {}
    if not args.branch:  # 9.1-r1-01: nothing the render drops may go silently
        report += migrate_gate_line(plans, args.dry_run)
        report += [f"  DROP   {s} — move it to plans/README.md before render"
                   for s in stray(plans, "\n".join(render_text(plans)))]
    for e in entries:
        c = e["cells"]
        if e["rel"]:
            target = (progress_file(os.path.join(plans, e["rel"])), "")
            if disk_kind(e["rel"]) != e["kind"]:
                report.append(f"  TABLE  {c[0]}: {e['kind']} -> {disk_kind(e['rel'])} (follows disk: {e['rel']}/)")
        else:
            target = (os.path.join(plans, LOOSE), e["kind"])
            report.append(f"  LOOSE  {c[0][:30] or '(blank)'}: {e['why']} -> {LOOSE}")
        targets.setdefault(target, []).append(c)

    written = kept = 0
    for (path, tag), new in targets.items():
        cur = read_block(path, tag) or []
        merged, changed = list(cur), False
        for c in new:
            key = row_key(c) if not tag or overwrite else tuple(c)
            hit = next((i for i, m in enumerate(merged)
                        if (row_key(m) if not tag or overwrite else tuple(m)) == key), None)
            if hit is None:
                merged.append(c)
                changed = True
            elif merged[hit] != c:
                if overwrite:
                    merged[hit], changed = c, True
                else:
                    kept += 1
                    report.append(f"  KEPT   {c[0]}: {os.path.relpath(path, plans)} already holds a "
                                  f"different row — the record wins")
        if changed:
            if not tag:
                merged.sort(key=sort_key)
            write_block(path, merged, tag, args.dry_run)
            written += 1
    print(f"migrate {plans}: {len(entries)} row(s), {written} record file(s) written, "
          f"{sum(1 for e in entries if not e['rel'])} loose, {kept} kept")
    for line in report:
        print(line)
    return 0


def migrate_gate_line(plans: str, dry_run: bool) -> list[str]:
    """Move the index's `**Gate mode:**` line to plans/README.md, where verify_lib.gate_mode
    reads it first — the render that follows drops it from the index."""
    index_gate, readme_gate = gate_lines(plans)
    if index_gate is None or index_gate == readme_gate:
        return []
    if readme_gate is not None:
        raise Refuse(f"the index declares **Gate mode:** {index_gate} but plans/README.md declares "
                     f"{readme_gate} — decide which is right and delete the other line")
    readme = os.path.join(plans, "README.md")
    text = slurp(readme) or "# Plans\n"
    if not dry_run:
        write_text(readme, text.rstrip("\n") + f"\n\n**Gate mode:** {index_gate}\n")
    return [f"  MOVED  **Gate mode:** {index_gate} -> README.md" + (" (--dry-run: not written)" if dry_run else "")]


def dupes(recs: list[Rec]) -> dict[str, list[str]]:
    """Review 9.1-r1-06: every number held by more than one row — two records, a record and
    the loose file, or twice in one block — to the files holding it. A render shows both
    rows and `status` would edit only the first, so neither may proceed."""
    seen: dict[str, list[str]] = {}
    for r in recs:
        for c in r.rows:
            if numbered(c):
                seen.setdefault(num_of(c), []).append(r.path)
    return {n: ps for n, ps in seen.items() if len(ps) > 1}


def dupe_msg(plans: str, num: str, paths: list[str]) -> str:
    return (f"# {num} has {len(paths)} rows ({', '.join(os.path.relpath(p, plans) for p in paths)}) "
            f"— renumber or delete one; a render would show both and status would edit only the first")


def find_record(plans: str, num: str):
    """(Rec, row index) holding row `num`, or None. Refuses a number held twice."""
    recs = records(plans)
    paths = dupes(recs).get(num)
    if paths:
        raise Refuse(dupe_msg(plans, num, paths))
    for r in recs:
        for i, c in enumerate(r.rows):
            if num_of(c) == num:
                return r, i
    return None


# ---------------------------------------------------------------- validate

def cmd_validate(args) -> int:
    plans = plans_of(args.index)
    fresh = None
    if render_mode(plans):  # validate what the records say, not a render that may lag
        fresh = "\n".join(render_text(plans))
    lines, sections = parse(args.index, fresh)
    issues: list[str] = []
    notes: list[str] = []

    tables = [s for s in sections if s.header]
    scope_tables = [s for s in tables if s.kind in ("active", "archived")]

    print(f"PLANS-INDEX: {args.index}")
    size = len(fresh.encode()) if fresh is not None else os.path.getsize(args.index)
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

    # Verification gate, detective layer (verify-contracts.md §5): a Done phase row in a
    # scope with a finish table needs a passing gate or a visible ⚠ advisory/skip marker.
    for s in scope_tables:
        for ln, cells in s.rows:
            if len(cells) < 3 or not sub_num(cells[0]) or not DONE.search(cells[1]):
                continue
            num = cells[0].strip().strip("*")
            g = run_gate(args.index, cells[2], num)
            if g is None:
                continue
            code, doc, err = g
            status = cells[1]
            if code == 3:
                issues.append(f"phase {num} (L{ln+1}) is Done but its gate could not evaluate: "
                              f"{err.strip().splitlines()[0] if err.strip() else doc}")
            elif doc.get("verdict") in ("pass", "predates-gate") or "⚠ verify skipped" in status or (
                    doc.get("verdict") == "advisory" and "⚠ verify advisory" in status) or (
                    doc.get("verdict") == "not-judged" and "⚠ verify not judged" in status and code == 0):
                # in blocking mode a not-judged unit is refused (exit 1), so its Done row is not
                # conformant whatever marker it carries (review 7.1-r4-02)
                continue
            else:
                issues.append(f"phase {num} (L{ln+1}) is Done without a passing verdict (gate: "
                              f"{doc.get('verdict')}) and no ⚠ marker — written by hand? Re-run "
                              f"`plans-index.py status {args.index} --num {num} --status ...`")

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
    plans = plans_of(args.index)
    _, sections = parse(args.index, "\n".join(render_text(plans)) if render_mode(plans) else None)
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
    plans = plans_of(args.index)
    mode = render_mode(plans)
    if mode:
        return add_record(args, plans, mode)
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
        if cells and cells[0].strip().strip("*") == args.num:
            print(f"plans-index: {args.num} already has a row in Active.",
                  file=sys.stderr)
            return 2

    row = build_row(args.num, args.status, args.folder, args.desc, args.creator)
    insert_at = (target.rows[-1][0] if target.rows else target.header_line + 1) + 1
    lines.insert(insert_at, row)
    write(args.index, lines, args.dry_run)
    print(row)
    return 0


def add_record(args, plans: str, mode: str) -> int:
    """The row goes to its folder's progress.md block (created when absent), or to the
    loose file when the folder is not on disk. One scope, one file: a session adding scope
    12 never touches the file a session adding scope 13 writes."""
    if find_record(plans, args.num):
        print(f"plans-index: {args.num} already has a row.", file=sys.stderr)
        return 2
    cells = [esc(c) for c in (str(args.num), args.status, args.folder, args.desc, args.creator or "")]
    build_row(*cells)  # the CELL_SOFT note, nothing else
    rel, why = place(plans, args.folder)
    path, tag = (progress_file(os.path.join(plans, rel)), "") if rel else (os.path.join(plans, LOOSE), "active")
    rows = (read_block(path, tag) or []) + [cells]
    write_block(path, sorted(rows, key=sort_key) if not tag else rows, tag, args.dry_run)
    print(row_line(cells))
    print(f"recorded in {os.path.relpath(path, plans)}" + (f" ({why})" if why else ""), file=sys.stderr)
    return after_write(plans, mode, args.dry_run)


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

def backlog_guard(plans: str, num: int, force: str | None) -> int:
    """Refuse to archive a kalpa-docs scope an open kalpa-orchestra backlog row still points
    at (`scoped(N)` — a done row says `done`). `--force "<reason>"` overrides, out loud."""
    common = (git_out(plans, "rev-parse", "--path-format=absolute", "--git-common-dir") or "").strip()
    owner = os.path.dirname(common) if os.path.basename(common) == ".git" else common
    if os.path.basename(owner) != "kalpa-docs":
        return 0
    root = os.path.join(vl.PROJECTS, "wellmed", "kalpa-orchestra", "projects")
    hits = []
    for proj in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, proj, "BACKLOG.md")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                cells = split_row(line)
                if f"scoped({num})" in cells:
                    hits.append(f"{proj}/BACKLOG.md:{i} {cells[0]}")
    if not hits:
        return 0
    if force:
        print(f"plans-index: archive guard overridden for scope {num} ({force}); open backlog "
              f"row(s): {', '.join(hits)}", file=sys.stderr)
        return 0
    print(status_msg("BLOCK", f"refusing to archive scope {num} — open backlog row(s) point at it",
                     f"no kalpa-orchestra backlog row at scoped({num})", ", ".join(hits),
                     root, "process", f'close the row(s) first, or pass --force "<reason>"'),
          file=sys.stderr)
    return 1


def cmd_move(args) -> int:
    plans = plans_of(args.index)
    if args.to == "archived" and backlog_guard(plans, args.num, args.force):
        return 1
    mode = render_mode(plans)
    if mode:
        return move_record(args, plans, mode)
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
    already = any(c and scope_num(c[0]) == args.num for _, c in dst.rows)
    if found is None and args.with_plans and already:
        return move_plan_rows(args, lines, src, dst)  # the scope row moved earlier; bring its plans
    in_place = found is None and already and bool(args.folder)
    if in_place:  # a repoint, not a move: /plan §2.5 put the plan in a folder
        found = next((ln, c) for ln, c in dst.rows if c and scope_num(c[0]) == args.num)
    if found is None:
        print(f"plans-index: scope {args.num} not found in the {src_kind} table.",
              file=sys.stderr)
        return 2

    ln, cells = found
    cells = (cells + [""] * len(CANONICAL))[: len(CANONICAL)]
    if args.status:
        cells[1] = args.status
    if args.folder:
        # Refuse a --folder that does not exist on disk. The row already holds a
        # path that is usually correct; overriding it with a guess replaces good
        # data with bad. This guard exists because on 2026-08-09 a `move` passed
        # --folder with an invented slug (51-manifest-ocr-pipeline) over the row's
        # own correct archive/51-padmacare-household-labels.
        want = args.folder.strip().strip("`").rstrip("/")
        base = os.path.dirname(os.path.abspath(args.index))
        if want and not os.path.exists(os.path.join(base, want)):
            print(f"plans-index: --folder '{args.folder}' does not exist under "
                  f"{base}. Omit --folder to keep the row's existing path, or pass "
                  f"one that resolves.", file=sys.stderr)
            return 2
        cells[2] = args.folder
    row = build_row(cells[0], cells[1], cells[2], cells[3], cells[4])

    if in_place:
        lines[ln] = row
        write(args.index, lines, args.dry_run)
        print(f"repointed {args.num} in {args.to}")
        print(row)
        return 0
    dst_last = dst.rows[-1][0] if dst.rows else dst.header_line + 1
    del lines[ln]
    insert_at = dst_last + 1 if dst_last < ln else dst_last
    lines.insert(insert_at, row)
    write(args.index, lines, args.dry_run)
    print(f"moved scope {args.num}: {src_kind} -> {args.to}")
    print(row)
    if args.with_plans:
        lines, sections = parse(args.index)
        src = next(s for s in sections if s.kind == src_kind and s.header)
        dst = next(s for s in sections if s.kind == args.to and s.header)
        return move_plan_rows(args, lines, src, dst)
    return 0


def move_record(args, plans: str, mode: str) -> int:
    """A move is a folder move plus a status write: membership follows disk, so moving the
    folder IS moving the rows. Every row in the record (scope + N.P) is repointed; when the
    folder already sits at the destination (moved by hand or git mv) only the write runs."""
    hit = find_record(plans, str(args.num))
    if hit is None:
        print(f"plans-index: scope {args.num} has no record.", file=sys.stderr)
        return 2
    rec, i = hit
    rel = place(plans, args.folder)[0] if args.folder and rec.folder is None else None
    if rel and disk_kind(rel) == args.to:  # a loose row whose folder now exists (/plan §2.5)
        cells = rec.rows.pop(i)
        cells = (cells + [""] * len(CANONICAL))[:len(CANONICAL)]
        cells[2] = esc(args.folder)
        if args.status:
            cells[1] = esc(args.status)
        path = progress_file(os.path.join(plans, rel))
        write_block(path, sorted((read_block(path) or []) + [cells], key=sort_key), "", args.dry_run)
        write_block(rec.path, rec.rows, rec.tag, args.dry_run)
        print(f"moved loose row {args.num} into {os.path.relpath(path, plans)}")
        return after_write(plans, mode, args.dry_run)
    if rec.folder is None:  # a loose row: its table is the block it sits in
        rows = rec.rows
        cells = rows.pop(i)
        if args.status:
            cells = (cells + [""] * len(CANONICAL))[:len(CANONICAL)]
            cells[1] = esc(args.status)
        write_block(rec.path, rows, rec.tag, args.dry_run)
        dst = read_block(rec.path, args.to) or []
        write_block(rec.path, dst + [cells], args.to, args.dry_run)
        print(f"moved loose row {args.num}: {rec.tag} -> {args.to}")
        return after_write(plans, mode, args.dry_run)
    src = rec.folder
    if args.folder:
        want = cell_path(args.folder)
    elif args.to == "archived":
        parent, leaf = os.path.split(src)
        want = src if disk_kind(src) == "archived" else os.path.join(parent, "archive", leaf)
    else:
        want = os.path.join(*[p for p in src.split(os.sep) if p != "archive"])
    if disk_kind(want) != args.to:
        print(f"plans-index: '{want}' is not an {args.to} location (archived = under an archive/ "
              f"folder).", file=sys.stderr)
        return 2
    if os.path.normpath(want) != os.path.normpath(src):
        dst = os.path.join(plans, want)
        if os.path.exists(dst):
            print(f"plans-index: {want} already exists and is not where scope {args.num}'s record "
                  f"lives ({src}) — refusing to merge folders.", file=sys.stderr)
            return 2
        if args.dry_run:
            print(f"(--dry-run: would move {src} -> {want})", file=sys.stderr)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tracked = git_out(plans, "ls-files", "--", os.path.join(plans, src))
            if tracked:
                p = subprocess.run(["git", "-C", plans, "mv", os.path.join(plans, src), dst],
                                   capture_output=True, text=True)
                if p.returncode:
                    print(f"plans-index: git mv failed: {p.stderr.strip()}", file=sys.stderr)
                    return 2
            else:
                os.rename(os.path.join(plans, src), dst)
    path = progress_file(os.path.join(plans, want)) if not args.dry_run else rec.path
    # A folder moved by hand (mv, git mv) leaves its rows naming the old path: match the
    # record's location with and without its archive/ component.
    olds = list(dict.fromkeys([src, os.path.join(*[p for p in src.split(os.sep) if p != "archive"])]))
    rows = []
    for c in rec.rows:
        c = list(c)
        if len(c) > 2:
            p = cell_path(c[2])
            old = next((o for o in olds if p == o or p.startswith(o + "/")), None)
            if old is not None and old != want:
                c[2] = c[2].replace(p, want + p[len(old):], 1)
        if num_of(c) == str(args.num) and args.status:
            c = (c + [""] * len(CANONICAL))[:len(CANONICAL)]
            c[1] = esc(args.status)
        rows.append(c)
    write_block(path, rows, "", args.dry_run)
    print(f"moved scope {args.num}: {src} -> {want}")
    return after_write(plans, mode, args.dry_run)


def move_plan_rows(args, lines, src, dst) -> int:
    """`--with-plans`: the scope's `N.P` rows follow it, repointed to --folder when given, so
    the archive gate finds no child row still pointing at the live folder."""
    plans = [(ln, c) for ln, c in src.rows
             if c and sub_num(c[0]) and c[0].strip().strip("*").split(".")[0] == str(args.num)]
    if not plans:
        print(f"no {args.num}.P rows in the source table")
        return 0
    rows = []
    for _, c in plans:
        c = (c + [""] * len(CANONICAL))[: len(CANONICAL)]
        if args.folder:
            c[2] = args.folder
        rows.append(build_row(*c))
    for ln, _ in sorted(plans, reverse=True):
        del lines[ln]
    # the scope's own row (it is in the destination table, the only place it now appears)
    at = next(i for i, l in enumerate(lines) if l.startswith("|") and scope_num(l.split("|")[1]) == args.num)
    lines[at + 1:at + 1] = rows
    write(args.index, lines, args.dry_run)
    for r in rows:
        print(r)
    return 0


# ----------------------------------------------------------------- status

def run_gate(index: str, folder_cell: str, num: str, extra: list[str] | None = None):
    """(exit, json doc, stderr) from verdict-gate.py, or None when the row's scope
    folder has no finish-conditions.md (a scope that predates the gate)."""
    folder = folder_cell.strip().strip("`").rstrip("/")
    scope = os.path.join(os.path.dirname(os.path.abspath(index)), folder)
    if not folder or not os.path.isfile(os.path.join(scope, "finish-conditions.md")):
        return None
    p = subprocess.run([sys.executable, GATE, "--scope", scope, "--unit", num, "--json", *(extra or [])],
                       capture_output=True, text=True)
    try:
        doc = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        doc = {"verdict": "error", "error": p.stdout.strip() or "no output"}
        return 3, doc, p.stderr
    return p.returncode, doc, p.stderr


def cmd_status(args) -> int:
    plans = plans_of(args.index)
    mode = render_mode(plans)
    found = None
    if mode:
        hit = find_record(plans, args.num)
        if hit:
            found = (hit, hit[0].rows[hit[1]])
    else:
        lines, sections = parse(args.index)
        for s in sections:
            if s.kind not in ("active", "archived"):
                continue
            for ln, cells in s.rows:
                if cells and cells[0].strip().strip("*") == args.num:
                    found = (ln, cells)
    if found is None:
        print(f"plans-index: {args.num} has no row in the Active or Archived table.", file=sys.stderr)
        return 2
    ln, cells = found
    cells = (cells + [""] * len(CANONICAL))[: len(CANONICAL)]
    new = MARKER.sub("", args.status).strip()
    if DONE.search(new) and sub_num(args.num):
        extra = (["--skip-verify", args.skip_verify] if args.skip_verify is not None else []) + \
            ([f"--{args.mode}"] if args.mode else [])
        g = run_gate(args.index, cells[2], args.num, extra)
        if g is None:
            print(status_msg("WARN", f"gate not run for {args.num} — no finish table",
                             "finish-conditions.md in the scope folder", f"none under {cells[2]}",
                             f"{args.index} row {args.num}", "tooling",
                             "nothing now — the scope predates the gate; /plan self-heal drafts one"),
                  file=sys.stderr)
        else:
            code, doc, err = g
            if code == 3:
                print(err or doc.get("error", ""), file=sys.stderr)
                print(status_msg("ERROR", f"refusing Done for {args.num} — the gate could not evaluate",
                                 "a gate verdict", "exit 3 (see the message above)",
                                 f"{args.index} row {args.num}", "tooling",
                                 f"verdict-gate.py --scope <scope> --unit {args.num}"), file=sys.stderr)
                return 3
            for m in doc.get("messages", []):
                print(m, file=sys.stderr)
            if doc.get("verdict") == "not-judged" and code == 1:
                print(status_msg("BLOCK", f"refusing Done for {args.num} — not judged (blocking mode)",
                                 "a judge verdict for every judge row",
                                 f"not judged: {', '.join(doc.get('not_judged', []))}", f"{args.index} row {args.num}",
                                 "tooling", 're-run /verify; the judge did not run or its answer was refused'),
                      file=sys.stderr)
                return 1
            if doc.get("verdict") == "blocked":
                ids = ", ".join(b["id"] for b in doc.get("blocks", []))
                print(status_msg("BLOCK", f"refusing Done for {args.num} — verdict gate BLOCKED",
                                 "every owned check passing", f"{len(doc.get('blocks', []))} block(s): {ids}",
                                 f"{args.index} row {args.num}",
                                 next((b["cause"] for b in doc.get("blocks", [])), "code"),
                                 'fix and re-run the checks (verify-run.py), or pass --skip-verify "<reason>"'),
                      file=sys.stderr)
                return 1
            if doc.get("marker"):
                new = f"{new} {doc['marker']}"
    if mode:
        rec, i = ln
        cells[1] = esc(new)
        rec.rows[i] = cells
        write_block(rec.path, rec.rows, rec.tag, args.dry_run)
        if not args.dry_run and (read_block(rec.path, rec.tag) or [None] * (i + 1))[i] != cells:
            print(status_msg("ERROR", f"status write for {args.num} did not land", new,
                             "a different cell on re-read", rec.path, "tooling",
                             "check nothing else is writing the record, then re-run"), file=sys.stderr)
            return 1
        print(row_line(cells))
        return after_write(plans, mode, args.dry_run)
    cells[1] = new
    lines[ln] = build_row(*cells)
    write(args.index, lines, args.dry_run)
    if not args.dry_run:
        _, again = parse(args.index)
        landed = any(c and c[0].strip().strip("*") == args.num and len(c) > 1 and c[1] == new.replace("|", "\\|")
                     for s2 in again for _, c in s2.rows)
        if not landed:
            print(status_msg("ERROR", f"status write for {args.num} did not land", new,
                             "a different cell on re-read", args.index, "tooling",
                             "check nothing else is writing the index, then re-run"), file=sys.stderr)
            return 1
    print(lines[ln])
    return 0


# ----------------------------------------------------------------- gate-count

def discover(root: str, depth: int = 4) -> list[str]:
    """Every live `plans/PLANS-INDEX.md` under root, at most `depth` levels down — the
    docs repos on this machine (ai-skills, kalpa-docs, pmg-docs, iris-docs, …)."""
    found = []
    root = os.path.abspath(root)
    for d, dirs, files in os.walk(root):
        level = d[len(root):].count(os.sep)
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "archive") and level < depth]
        if os.path.basename(d) == "plans" and "PLANS-INDEX.md" in files:
            found.append(os.path.join(d, "PLANS-INDEX.md"))
    return sorted(found)


def cmd_gate_count(args) -> int:
    clean, dirty, seen = [], [], set()
    for index in args.index + (discover(vl.PROJECTS) if args.discover else []):
        if os.path.realpath(index) in seen:
            continue  # an index passed explicitly and found by --discover counts once
        seen.add(os.path.realpath(index))
        _, sections = parse(None, committed_text(plans_of(index)))  # + archive/INDEX.md (eng D24)
        root = os.path.dirname(os.path.abspath(index))
        rows = [(s.kind, c) for s in sections if s.kind in ("active", "archived") for _, c in s.rows if len(c) > 2]
        for kind, cells in rows:
            num = cells[0].strip().strip("*")
            if kind != "archived" or not num.isdigit():
                continue
            folder = cells[2].strip().strip("`").rstrip("/")
            scope = os.path.join(root, folder)
            if not folder or not os.path.isfile(os.path.join(scope, "finish-conditions.md")):
                continue
            mine = [c for _, c in rows if c[0].strip().strip("*") in (num,) or
                    c[0].strip().strip("*").startswith(num + ".")]
            label = f"{os.path.basename(os.path.dirname(root))} {num}"
            # Clean = the whole-scope gate passes on at least one gated unit, and no row carries
            # a ⚠ — an ungated (all-predating) or unverified table never counts (5.3-r1-05).
            p = subprocess.run([sys.executable, GATE, "--scope", scope, "--all", "--json"],
                               capture_output=True, text=True)
            try:
                verdict = json.loads(p.stdout.strip().splitlines()[-1]).get("verdict")
            except (ValueError, IndexError):
                verdict = "error"
            if verdict == "ungated":
                continue
            (clean if verdict == "pass" and not any("⚠" in c[1] for c in mine) else dirty).append(label)
    n, need = len(clean), vl.BLOCKING_AFTER
    print(f"clean gated scopes: {n}/{need}" + (f" ({', '.join(clean)})" if clean else "")
          + (f" · with ⚠: {', '.join(dirty)}" if dirty else ""))
    if n >= need and vl.GATE_MODE == "advisory":
        print(f"REMINDER: {n} clean gated scopes — flip GATE_MODE to \"blocking\" in "
              f"scripts/verify_lib.py (Alex's call; verify-contracts.md §5.4)")
    return 0


def write(path: str, lines: list[str], dry_run: bool) -> None:
    if dry_run:
        print("(--dry-run: not written)", file=sys.stderr)
        return
    atomic_write(path, "\n".join(lines))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate"); v.add_argument("index"); v.set_defaults(fn=cmd_validate)
    n = sub.add_parser("next-number"); n.add_argument("index"); n.set_defaults(fn=cmd_next_number)

    a = sub.add_parser("add")
    a.add_argument("index"); a.add_argument("--num", type=row_num, required=True)
    a.add_argument("--status", required=True); a.add_argument("--folder", required=True)
    a.add_argument("--desc", required=True); a.add_argument("--creator")
    a.add_argument("--dry-run", action="store_true"); a.set_defaults(fn=cmd_add)

    m = sub.add_parser("move")
    m.add_argument("index"); m.add_argument("--num", type=int, required=True)
    m.add_argument("--to", choices=["active", "archived"], required=True)
    m.add_argument("--folder"); m.add_argument("--status")
    m.add_argument("--with-plans", action="store_true", help="also move the scope's N.P rows")
    m.add_argument("--force", metavar="REASON", help="archive despite open kalpa-orchestra backlog rows")
    m.add_argument("--dry-run", action="store_true"); m.set_defaults(fn=cmd_move)

    gc = sub.add_parser("gate-count"); gc.add_argument("index", nargs="*")
    gc.add_argument("--discover", action="store_true", help="also every plans/PLANS-INDEX.md under VERIFY_PROJECTS")
    gc.set_defaults(fn=cmd_gate_count)

    st = sub.add_parser("status")
    st.add_argument("index"); st.add_argument("--num", type=row_num, required=True)
    st.add_argument("--status", required=True); st.add_argument("--skip-verify", metavar="REASON")
    mg = st.add_mutually_exclusive_group()
    mg.add_argument("--blocking", dest="mode", action="store_const", const="blocking")
    mg.add_argument("--advisory", dest="mode", action="store_const", const="advisory")
    st.add_argument("--dry-run", action="store_true"); st.set_defaults(fn=cmd_status)

    for name, fn, extra in (("render", cmd_render, True), ("migrate", cmd_migrate, False),
                            ("check", cmd_check, False)):
        r = sub.add_parser(name)
        r.add_argument("index", help="the plans dir (or its PLANS-INDEX.md)")
        r.set_defaults(fn=fn)
        if name == "render":
            r.add_argument("--stdout", action="store_true", help="print a fresh render, write nothing")
            r.add_argument("--allow-loss", action="store_true", help="render even if rows vanish")
        if name == "migrate":
            r.add_argument("--branch", metavar="REF", help="convert one open branch's old-index edits")
            r.add_argument("--base", metavar="REV", help="--branch: the fork point (default: merge-base with origin/HEAD)")
            r.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    indexes = []
    for index in (args.index if isinstance(args.index, list) else [args.index]):
        if os.path.isdir(index):  # a plans dir stands for its index
            index = os.path.join(index, "PLANS-INDEX.md")
        indexes.append(index)
        try:
            records_mode = render_mode(plans_of(index)) is not None
        except Refuse as e:
            print(f"plans-index: {e}", file=sys.stderr)
            return 2
        if not os.path.isfile(index) and args.cmd not in ("render", "migrate", "check") and not records_mode:
            print(f"plans-index: no such file: {index}", file=sys.stderr)
            return 2
    args.index = indexes if isinstance(args.index, list) else indexes[0]
    try:
        return args.fn(args)
    except Refuse as e:
        print(f"plans-index: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
