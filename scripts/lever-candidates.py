#!/usr/bin/env python3
"""lever-candidates.py — /closeout's writer for the `## Lever candidates` section of a
project's plans/TO-DO.md (templates/verify-contracts.md §4.9).

Approach: a lever (a tool that makes a class of gap checkable) is built on its second
sighting, never its first. Deciding "is this a second sighting" has one right answer, so
it is code. For every gated unit of the scope, take its latest final verdict run and the
candidates `verify_lib.levers()` derives from it (the judge's, plus one per
inconclusive / unreachable check), each keyed by `lever_id`. Upsert one TO-DO item per
lever_id; every sighting is a line naming scope + run. A sighting already recorded for
the same scope and run is a no-op, so re-running closeout changes nothing. A different run
of the *same* scope adds a line but never counts: re-verifying an unfixed gap would
otherwise manufacture its own second sighting. The same lever_id from a **different
scope** flips the item to BUILD NOW. The file is re-read after writing.

Usage:  lever-candidates.py --scope DIR --todo FILE [--dry-run]
Output: one line per candidate (`new` · `sighting` · `already recorded`), then
        `SECOND SIGHTING: <lever_id> — build the lever now` for each item that just flipped.
Exit:   0 written (or nothing to write) · 2 usage · 3 malformed input / write did not land
"""

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_lib as vl  # noqa: E402

HEAD = "## Lever candidates"
NOTE = ("<!-- Written by scripts/lever-candidates.py (verify-contracts.md §4.9). One item per\n"
        "     lever_id; a lever is built on its second sighting, from a different scope. -->")
ITEM = re.compile(r"^- \[[ x]\] \*\*`([a-z0-9-]+)`\*\*")
SIGHT = re.compile(r"^\s+Sighting: (\S+) · run (\S+)")
BUILD = "BUILD NOW (second sighting)"


def scope_label(scope):
    """`<docs repo>/<scope folder>` — unique across projects, stable across archiving."""
    parts = os.path.realpath(scope).split(os.sep)
    docs = parts[parts.index("plans") - 1] if "plans" in parts else "?"
    return f"{docs}/{parts[-1]}"


def collect(scope):
    table = vl.parse_table(os.path.join(scope, "finish-conditions.md"))
    by_id = {r["check_id"]: r for r in table["rows"]}
    units = sorted({r["owner"].split("/")[0] for r in table["rows"]})
    out = []
    for u in units:
        recs = vl.read_jsonl(os.path.join(scope, "artifacts", f"verify-{u}.jsonl"))
        finals = [r for r in recs if r.get("run_state") == "final"]
        if not finals:
            continue
        final = finals[-1]
        raw_path = os.path.join(scope, "artifacts", f"verify-{u}-judge-{final['run_id']}.json")
        raw = {}
        if os.path.exists(raw_path):
            with open(raw_path, encoding="utf-8") as fh:
                raw = json.load(fh)
        elif not str(final.get("judge", "")).startswith("none "):
            # A model judged this run, so its named levers exist somewhere — reading none
            # would report "no candidates" when there are some (review 5.3-r1-06).
            raise vl.ContractError(vl.message(
                "ERROR", f"judge output for run {final['run_id']} is missing",
                "the raw judge answer judge.py record keeps beside the verdict log", "no such file",
                raw_path, "tooling", f"restore it from git, or re-run /verify {u}", f"{vl.CONTRACT} §4.9"))
        for c in vl.levers(final, raw):
            row = by_id.get(c["check_id"], {})
            c.update(run_id=final["run_id"], touches=f"{row.get('repo', '?')} · {c['check_id']}")
            out.append(c)
    return out


def parse_items(lines, start, end):
    """{lever_id: {"at": line index, "sightings": [(scope, run)], "last": last line index}}"""
    items, cur = {}, None
    for i in range(start, end):
        m = ITEM.match(lines[i])
        if m:
            cur = items.setdefault(m.group(1), {"at": i, "sightings": [], "last": i})
            continue
        if cur is not None and lines[i].startswith("  "):
            cur["last"] = i
            s = SIGHT.match(lines[i])
            if s:
                cur["sightings"].append((s.group(1), s.group(2)))
        elif lines[i].strip():
            cur = None
    return items


def section(lines):
    at = next((i for i, l in enumerate(lines) if l.strip() == HEAD), None)
    if at is None:
        return None, None
    end = next((i for i in range(at + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return at, end


def apply(text, cands, label, today):
    lines = text.splitlines()
    at, end = section(lines)
    if at is None:
        lines += ["", HEAD, "", NOTE, ""]
        at, end = section(lines)
    report, flipped = [], []
    for c in cands:
        at, end = section(lines)
        items = parse_items(lines, at + 1, end)
        sight = f"      Sighting: {label} · run {c['run_id']} · {today}"
        it = items.get(c["lever_id"])
        if it is None:
            new = [f"- [ ] **`{c['lever_id']}`** — {c['lever']} · gap: {c['gap']}",
                   f"      Touches: {c['touches']}", sight]
            ins = end
            while ins > at + 1 and not lines[ins - 1].strip():
                ins -= 1
            lines[ins:ins] = new
            report.append(f"new               {c['lever_id']}  ({c['check_id']}, run {c['run_id']})")
            continue
        if (label, c["run_id"]) in it["sightings"]:
            report.append(f"already recorded  {c['lever_id']}  (run {c['run_id']})")
            continue
        lines.insert(it["last"] + 1, sight)
        scopes = {s for s, _ in it["sightings"]} | {label}
        report.append(f"sighting          {c['lever_id']}  ({len(scopes)} scope(s), run {c['run_id']})")
        if len(scopes) >= 2 and BUILD not in lines[it["at"]]:
            lines[it["at"]] = lines[it["at"]].replace("** — ", f"** — {BUILD} — ", 1)
            flipped.append(c["lever_id"])
    return "\n".join(lines) + "\n", report, flipped


def main(argv):
    ap = argparse.ArgumentParser(description="Record lever candidates in TO-DO.md (verify-contracts.md §4.9).")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--todo", required=True)
    ap.add_argument("--dry-run", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    try:
        cands = collect(a.scope)
    except (vl.ContractError, ValueError, KeyError) as exc:
        print(getattr(exc, "msg", f"  [ERROR] cannot read the scope's verdicts: {exc}"), file=sys.stderr)
        return vl.EXIT_EVAL
    if not cands:
        print("lever candidates: none (no inconclusive or unreachable check, no judge-named lever)")
        return vl.EXIT_PASS
    text = ""
    if os.path.exists(a.todo):
        with open(a.todo, encoding="utf-8") as fh:
            text = fh.read()
    label = scope_label(a.scope)
    out, report, flipped = apply(text, cands, label, datetime.date.today().isoformat())
    print("\n".join(report))
    for lid in flipped:
        print(f"SECOND SIGHTING: {lid} — build the lever now")
    if a.dry_run or out == text:
        return vl.EXIT_PASS
    with open(a.todo, "w", encoding="utf-8") as fh:
        fh.write(out)
    with open(a.todo, encoding="utf-8") as fh:
        back = fh.read().splitlines()
    at, end = section(back)
    items = parse_items(back, at + 1, end) if at is not None else {}
    missing = [c["lever_id"] for c in cands if (label, c["run_id"]) not in items.get(c["lever_id"], {}).get("sightings", [])]
    if missing:
        print(vl.message("ERROR", "lever-candidate write did not land", "every candidate's sighting in the file",
                         f"missing: {', '.join(missing)}", a.todo, "tooling",
                         "check nothing else is writing TO-DO.md, then re-run", f"{vl.CONTRACT} §4.9"),
              file=sys.stderr)
        return vl.EXIT_EVAL
    return vl.EXIT_PASS


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
