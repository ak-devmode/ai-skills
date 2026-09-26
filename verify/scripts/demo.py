#!/usr/bin/env python3
"""demo.py — `/verify --demo`: watch the gate catch six planted defects and pass a control.

Approach: build the `notes` fixture twice — `bad` (six planted defects) and `clean` — and
run each through the real /verify procedure (verify/SKILL.md §3): runner → judge prompt →
fresh codex probe → codex judge → record → finalize → gate, the two judges in parallel.
Then score it: every planted defect must surface as a block naming it (and the two judge
defects as judge failures), and the control must pass everything. `--check` turns the
score into the exit code, which is how the test suite runs it as an eval. A missing
judge fails `--check`: `judge: none` can pass the deterministic half, never the judge half,
and an always-failing judge fails the control — neither can satisfy the suite.

Usage:  demo.py [--check] [--keep DIR] [--timeout S]
Output: a table of planted defect → caught by → ✓/✗, then the control's result.
Exit:   0 demo ran (with --check: every expectation met) · 1 --check: an expectation
        failed · 3 could not run (fixture build or a script failed)
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AI = os.path.dirname(os.path.dirname(HERE))
S = os.path.join(AI, "scripts")
sys.path.insert(0, HERE)
import fixture  # noqa: E402

# planted defect -> (the block id that must appear, how it is caught)
EXPECT = {
    "invented-env": ("names-resolve", "runner: resolve-identifiers.py"),
    "over-build": ("no-overbuild", "judge"),
    "missing-evidence": ("changelog-entry", "judge"),
    "under-rung": ("export-runs", "gate: rung"),
    "rejection-no-reason": ("9.9-r1-02", "gate: disposition coverage"),
    "dropped-finding": ("9.9-r1-03", "gate: disposition coverage"),
}


def sh(*args, env=None, timeout=900):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env, timeout=timeout)


def verify(info, judge_line, timeout):
    """Run one fixture through the procedure. Returns (gate doc, judge line used, raw judge doc)."""
    env = dict(os.environ, VERIFY_PROJECTS=info["projects"])
    sc, unit = info["scope"], info["unit"]
    table, log = os.path.join(sc, "finish-conditions.md"), os.path.join(sc, "artifacts", f"verify-{unit}.jsonl")
    r = sh(os.path.join(S, "verify-run.py"), "run", "--table", table, "--log", log, "--owner", unit, env=env)
    if "run_id: " not in r.stdout:
        raise RuntimeError(f"runner failed: {r.stderr.strip()[-400:]}")
    run_id = r.stdout.split("run_id: ")[1].split()[0]
    used, raw = judge_line, {}
    if judge_line.startswith("codex "):
        p = sh(os.path.join(HERE, "judge.py"), "prepare", "--scope", sc, "--unit", unit, "--run-id", run_id, env=env)
        if p.returncode != 0:
            raise RuntimeError(f"judge prepare failed: {p.stderr.strip()[-400:]}")
        prompt = p.stdout.split("prompt: ")[1].split()[0]
        schema = p.stdout.split("schema: ")[1].split()[0]
        out = os.path.join(os.path.dirname(prompt), "answer.json")
        e = sh(os.path.join(S, "codex-exec.py"), "exec", "--prompt", prompt, "--schema", schema, "--out", out,
               "--cd", sc, "--timeout", str(timeout), env=env, timeout=timeout + 60)
        used = e.stdout.strip().splitlines()[-1] if e.stdout.strip() else "none codex-exec printed nothing"
        if used.startswith("codex "):
            rec = sh(os.path.join(HERE, "judge.py"), "record", "--scope", sc, "--unit", unit, "--run-id", run_id,
                     "--judge", used, "--input", out, env=env)
            if rec.returncode != 0:
                used = "none malformed judge output"
            else:
                with open(out, encoding="utf-8") as fh:
                    raw = json.load(fh)
    fin = ["finalize", "--log", log, "--run-id", run_id] + ([] if raw else ["--judge", used if used.startswith("none ")
                                                                           else "none judge did not record"])
    sh(os.path.join(S, "verify-run.py"), *fin, env=env)
    g = sh(os.path.join(S, "verdict-gate.py"), "--scope", sc, "--unit", unit, "--blocking", "--json", env=env)
    return json.loads(g.stdout.strip().splitlines()[-1]), used, raw


def main(argv):
    ap = argparse.ArgumentParser(description="/verify --demo")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--keep")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args(argv)
    root = a.keep or tempfile.mkdtemp(prefix="verify-demo-")
    try:
        bad = fixture.build(os.path.join(root, "bad"), "bad")
        clean = fixture.build(os.path.join(root, "clean"), "clean")
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        print(f"demo: could not build the fixture: {exc}", file=sys.stderr)
        return 3
    probe = sh(os.path.join(S, "codex-exec.py"), "probe")
    judge = probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else "none probe printed nothing"
    print(f"/verify --demo — fixture in {root}\nprobe: {judge}\n")
    try:
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            fb, fc = pool.submit(verify, bad, judge, a.timeout), pool.submit(verify, clean, judge, a.timeout)
            (gb, jb, rb), (gc, jc, _) = fb.result(), fc.result()
    except (RuntimeError, subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        print(f"demo: a verify step failed: {exc}", file=sys.stderr)
        return 3

    blocked = {b["id"] for b in gb["blocks"]}
    ok, lines = True, []
    for defect, (cid, how) in EXPECT.items():
        hit = cid in blocked and (how != "judge" or jb.startswith("codex "))
        if how == "judge" and cid in blocked and not jb.startswith("codex "):
            note = f"blocked only because the judge was absent ({jb}) — not a catch"
        else:
            note = ""
        ok &= hit
        lines.append(f"  {'✓' if hit else '✗'} {defect:<20} → {cid:<16} ({how}){'  ' + note if note else ''}")
    lens = {f.get("lens") for f in rb.get("findings", [])}
    if jb.startswith("codex ") and "over-build" not in lens:
        ok = False
        lines.append("  ✗ judge findings name no over-build — the no-overbuild verdict is unexplained")
    control = gc["verdict"] == "pass" and jc.startswith("codex ")
    ok &= control
    print(f"bad fixture — judge: {jb} · gate: {gb['verdict'].upper()} ({len(gb['blocks'])} blocks)")
    print("\n".join(lines))
    print(f"\nclean control — judge: {jc} · gate: {gc['verdict'].upper()} ({len(gc['blocks'])} blocks) "
          f"{'✓' if control else '✗'}")
    if not control:
        for b in gc["blocks"]:
            print(f"    control block: {b['id']} — {b['what']}")
    if not judge.startswith("codex "):
        print(f"\n⚠ No judge ran ({judge}). The two judge defects cannot be caught and the control's judge rows "
              "cannot pass. Fix codex (`codex login`), or run /verify inside Claude Code for the fallback judge.")
    print(f"\nresult: {'every planted defect caught, control passes' if ok else 'EXPECTATIONS NOT MET'}")
    return (0 if ok else 1) if a.check else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
