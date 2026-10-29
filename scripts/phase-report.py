#!/usr/bin/env python3
"""phase-report.py — what a phase did, printed at its end and kept for later (scope 10.5).

Approach: read only the records the phase already wrote — the finish table, the verify log
and judge answers, the review log, the progress Decisions Log and the driver's merge log —
and render one markdown report. Nothing is asked and nothing is decided here; the report
replaces the finish-table approval question (verify-contracts.md §3.1.1): Alex reads the
rows after the fact and strikes or edits one through `finish-table.py add`.

  phase-report.py --scope DIR --unit N.P [--no-write]

Writes <scope>/artifacts/phase-report-<unit>.md (unless --no-write) and prints the same text.
A missing record is reported as missing in its section, never as zero.
Exit: 0 written/printed · 2 usage (no scope folder).
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_lib as vl  # noqa: E402


def jsonl(path):
    if not os.path.exists(path):
        return None
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue  # a torn line never hides the rest of the log
    return out


def one_line(text, n=160):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def rows_section(scope, unit, verify):
    out = ["## 1. Finish rows", ""]
    try:
        table = vl.parse_table(os.path.join(scope, "finish-conditions.md"))
    except (OSError, vl.ContractError) as e:
        return out + [f"No finish table read ({one_line(e)})."], []
    owned = [r for r in table["rows"] if r["owner"] == unit or r["owner"].startswith(unit + "/")]
    if not owned:
        return out + [f"No rows owned by {unit} (table rev {table['revision']})."], []
    finals = [r for r in (verify or []) if r.get("run_state") == "final"]
    results = finals[-1].get("results", {}) if finals else {}
    out += [f"Table rev {table['revision']} · approved: {table.get('approval')} · "
            f"latest verify run: {finals[-1]['run_id'] if finals else 'none'}", "",
            "| row | deliverable | result | rung | why |", "|---|---|---|---|---|"]
    for r in owned:
        res = results.get(r["check_id"], {})
        out.append(f"| {r['check_id']} | {one_line(r['deliverable'], 80)} | {res.get('result', 'not run')} | "
                   f"{res.get('rung_reached', '-')}/{r['rung']} | {one_line(res.get('reason'), 120)} |")
    return out, [r["check_id"] for r in owned]


def review_section(review):
    out = ["## 2. Review", ""]
    if review is None:
        return out + ["No review log."], [], []
    reviews = [r for r in review if r.get("record") == "review"]
    findings = {r["finding_id"]: r for r in review if r.get("record") == "finding"}
    latest = {}
    for r in review:
        if r.get("record") == "disposition":
            latest[r["finding_id"]] = r
    kinds = collections.Counter(d.get("disposition") for d in latest.values())
    sev = collections.Counter(f.get("severity") for f in findings.values())
    who = collections.Counter(("codex" if str(r.get("reviewer", "")).startswith("codex")
                               else str(r.get("reviewer", "?")).split()[0]) for r in reviews)
    out.append(f"- Rounds: {len(reviews)} reviews ({', '.join(f'{k} ×{v}' for k, v in sorted(who.items()))})")
    if reviews:
        last = reviews[-1]
        out.append(f"- Last: {last.get('review_id')} — {last.get('verdict')} ({last.get('reviewer')})")
    out.append(f"- Findings: {len(findings)} ({', '.join(f'{k} {v}' for k, v in sorted(sev.items())) or 'none'})")
    out.append(f"- Outcomes: {', '.join(f'{k} {v}' for k, v in sorted(kinds.items())) or 'none'}"
               f"{'' if len(latest) == len(findings) else f' · {len(findings) - len(latest)} without a disposition'}")
    acc = [r for r in review if r.get("record") == "acceptance"]
    out.append(f"- Accepted: {acc[-1].get('by')} ({acc[-1].get('ts', '')[:10]})" if acc else "- Accepted: not yet")
    rejected = [(fid, d.get("reason")) for fid, d in latest.items() if d.get("disposition") == "rejected"]
    nits = [(fid, d.get("reason")) for fid, d in latest.items() if d.get("disposition") == "accepted"]
    return out, rejected, nits


def verify_section(scope, unit, verify):
    out = ["## 3. Verify", ""]
    if verify is None:
        return out + ["No verify log."]
    runs = sorted({r["run_id"] for r in verify if r.get("run_id")})
    finals = [r for r in verify if r.get("run_state") == "final"]
    out.append(f"- Runs: {len(runs)} ({len(finals)} finalized)")
    if finals:
        res = collections.Counter(v.get("result") for v in finals[-1].get("results", {}).values())
        out.append(f"- Latest: {', '.join(f'{k} {v}' for k, v in sorted(res.items()))} — judge {finals[-1].get('judge')}")
    weak = []
    answers = sorted(glob.glob(os.path.join(scope, "artifacts", f"verify-{unit}-judge-*.json")))
    if answers:
        try:
            with open(answers[-1], encoding="utf-8") as fh:
                doc = json.load(fh)
            weak = [f for f in doc.get("findings", []) if f.get("lens") == "weak-row"]
        except (OSError, ValueError) as e:
            out.append(f"- Weak rows: judge answer unreadable ({one_line(e)})")
            return out
    out.append(f"- Weak rows (judge, advisory): {len(weak) if answers else 'no judge answer'}")
    out += [f"  - `{f['check_id']}` — {one_line(f.get('text'))}" for f in weak]
    return out


DECISION_REF = re.compile(r"\bAlex,? (\d{2,4})\b")


def decision_refs(text, review):
    """Decision numbers the unit cites — `Alex 98` in its progress section or in a review
    disposition — so a Decisions Log line that never names the unit still belongs to it."""
    refs = set(DECISION_REF.findall(text))
    for r in review or []:
        refs.update(DECISION_REF.findall(str(r.get("reason") or "")))
    return refs


def decisions_section(scope, unit, review=None):
    out = ["## 5. Decisions", ""]
    path = os.path.join(scope, "progress.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        return out + [f"No progress file ({one_line(e)})."]
    m = re.search(r"^## Decisions Log\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return out + ["No Decisions Log section."]
    pat = re.compile(rf"(?<![\d.]){re.escape(unit)}(?![\d])")
    sec = re.search(rf"^## Plan {re.escape(unit)}:.*?(?=^## |\Z)", text, re.M | re.S)
    refs = decision_refs(sec.group(0) if sec else "", review)
    num = re.compile(rf"(?<![\d.-])({'|'.join(sorted(refs))})(?![\d.-])") if refs else None
    hits = [l for l in m.group(1).splitlines()
            if l.startswith("- ") and (pat.search(l) or (num and num.search(l)))]
    return out + ([f"- {one_line(l[2:], 240)}" for l in hits] or [f"None mention {unit}."])


def merges_section(scope, unit):
    out = ["## 6. Merges", ""]
    recs = jsonl(os.path.join(scope, "artifacts", f"merges-{unit}.jsonl"))
    if not recs:
        return out + ["None recorded by driver-merge.py."]
    return out + [f"- {r.get('slug')}#{r.get('pr')} → {r.get('base')} @ {str(r.get('sha'))[:12]} "
                  f"({r.get('ts', '')[:16]}){' · ' + ', '.join(r['flags']) if r.get('flags') else ''}" for r in recs]


def render(scope, unit):
    art = os.path.join(scope, "artifacts")
    verify = jsonl(os.path.join(art, f"verify-{unit}.jsonl"))
    review = jsonl(os.path.join(art, f"review-{unit}.jsonl"))
    rows, _ = rows_section(scope, unit, verify)
    rev, rejected, nits = review_section(review)
    lines = [f"# Phase report — {unit}", "",
             f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} · "
             f"**Scope:** {scope}", ""]
    lines += rows + [""] + rev + [""] + verify_section(scope, unit, verify) + [""]
    lines += ["## 4. Rejections and accepted nits", ""]
    lines += [f"- rejected `{fid}` — {one_line(why)}" for fid, why in rejected]
    lines += [f"- nit `{fid}` — {one_line(why)}" for fid, why in nits]
    if not rejected and not nits:
        lines.append("None.")
    lines += [""] + decisions_section(scope, unit, review) + [""] + merges_section(scope, unit)
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scope", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    scope = os.path.abspath(os.path.expanduser(a.scope))
    if not os.path.isdir(scope):
        print(f"phase-report: no scope folder {scope}", file=sys.stderr)
        return 2
    text = render(scope, a.unit)
    if not a.no_write:
        path = os.path.join(scope, "artifacts", f"phase-report-{a.unit}.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"report: {path}", file=sys.stderr)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
