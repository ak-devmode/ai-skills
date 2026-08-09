#!/usr/bin/env python3
"""Anchor-based file edits that FAIL when they change nothing.

Approach: take a JSON list of edits, validate every one against the current file
contents, and write only if all of them matched exactly as declared. A missed anchor
is a non-zero exit, not a line of stdout nobody reads.

Why this exists: on 2026-08-09 three scripted edits in one session reported success
while changing nothing — a `python3 - <<PY` string-replace whose anchor didn't match
because of leading whitespace, a regex renumber anchored to `^### 12\\.` that skipped
seven body items, and a `--folder` override that wrote an invented path over a correct
one. Each printed a MISS to stdout, and each was followed by a commit. Printing is not
checking. Same lesson as /closeout §14.0 and gstack-review-log exiting 0 after writing
nothing: a green result is not a completed action.

Ops
    replace   exact substring, must match exactly `count` times (default 1)
    sub       regex, must match `expect` times, or at least `expect_min`
    cut       remove from one anchor up to (not including) another, optional `with`

Every op is all-or-nothing across the whole spec: nothing is written unless every
edit validates. That keeps a partially-applied refactor from becoming the new baseline.

Usage
    edit-guard.py spec.json            # dry run, report what would change
    edit-guard.py spec.json --write    # apply, or exit non-zero having written nothing
    edit-guard.py - --write < spec.json

Exit codes
    0  every edit validated (and applied, with --write)
    1  at least one edit failed to validate — NOTHING was written
    2  bad spec, unreadable file, or unknown op
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RED, GRN, YEL, DIM, OFF = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"


def flags_of(spec: dict) -> int:
    f = 0
    for ch in spec.get("flags", ""):
        f |= {"m": re.M, "s": re.S, "i": re.I, "x": re.X}.get(ch, 0)
    return f


def apply_one(text: str, e: dict) -> tuple[str, str]:
    """Return (new_text, note). Raise ValueError with a precise reason on failure."""
    op = e.get("op", "replace")

    if op == "replace":
        old, new = e["old"], e["new"]
        want = e.get("count", 1)
        got = text.count(old)
        if got != want:
            snippet = old.strip().splitlines()[0][:70] if old.strip() else "(empty)"
            raise ValueError(
                f"anchor matched {got}x, expected {want}x — {snippet!r}"
                + ("  (leading whitespace or a reflowed line is the usual cause)"
                   if got == 0 else "  (ambiguous: extend the anchor)")
            )
        if old == new:
            raise ValueError("old == new; this edit is a no-op")
        return text.replace(old, new), f"replaced {got}x"

    if op == "sub":
        pat, repl = e["pattern"], e["repl"]
        rx = re.compile(pat, flags_of(e))
        got = len(rx.findall(text))
        if "expect" in e and got != e["expect"]:
            raise ValueError(f"pattern matched {got}x, expected exactly {e['expect']}x — {pat!r}")
        floor = e.get("expect_min", 1)
        if got < floor:
            raise ValueError(f"pattern matched {got}x, expected at least {floor}x — {pat!r}")
        out = rx.sub(repl, text)
        if out == text:
            raise ValueError(f"pattern matched {got}x but substitution changed nothing — {pat!r}")
        return out, f"substituted {got}x"

    if op == "cut":
        a, b = e["from"], e["to"]
        i = text.find(a)
        if i == -1:
            raise ValueError(f"`from` anchor not found — {a[:70]!r}")
        j = text.find(b, i + 1)
        if j == -1:
            raise ValueError(f"`to` anchor not found after `from` — {b[:70]!r}")
        removed = text[i:j].count("\n")
        return text[:i] + e.get("with", "") + text[j:], f"cut {removed} lines"

    raise ValueError(f"unknown op {op!r} (expected replace | sub | cut)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="path to a JSON edit list, or - for stdin")
    ap.add_argument("--write", action="store_true", help="apply if ALL edits validate")
    ap.add_argument("--root", default=".", help="resolve relative file paths against this")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.spec == "-" else Path(args.spec).read_text()
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"{RED}edit-guard: spec is not valid JSON: {exc}{OFF}", file=sys.stderr)
        return 2
    if isinstance(spec, dict):
        spec = [spec]

    root = Path(args.root)
    staged: dict[Path, str] = {}
    failures: list[str] = []
    notes: list[str] = []

    for n, e in enumerate(spec, 1):
        try:
            path = root / e["file"]
        except (KeyError, TypeError):
            failures.append(f"edit {n}: missing `file`")
            continue
        if not path.is_file():
            failures.append(f"edit {n}: no such file: {path}")
            continue
        # Chain edits to the same file so multiple ops compose.
        text = staged.get(path, path.read_text())
        try:
            new, note = apply_one(text, e)
        except KeyError as exc:
            failures.append(f"edit {n} [{e.get('op','replace')}] {e['file']}: missing key {exc}")
            continue
        except ValueError as exc:
            failures.append(f"edit {n} [{e.get('op','replace')}] {e['file']}: {exc}")
            continue
        staged[path] = new
        notes.append(f"edit {n} [{e.get('op','replace')}] {e['file']}: {note}")

    for ln in notes:
        print(f"  {GRN}ok{OFF}   {ln}")
    for ln in failures:
        print(f"  {RED}FAIL{OFF} {ln}", file=sys.stderr)

    if failures:
        print(f"\n{RED}edit-guard: {len(failures)} of {len(spec)} edit(s) failed — "
              f"NOTHING written.{OFF}", file=sys.stderr)
        return 1

    if not args.write:
        print(f"\n{YEL}edit-guard: all {len(spec)} edit(s) validated across "
              f"{len(staged)} file(s). Dry run — pass --write to apply.{OFF}")
        return 0

    for path, text in staged.items():
        path.write_text(text)
    print(f"\n{GRN}edit-guard: applied {len(spec)} edit(s) to {len(staged)} file(s).{OFF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
