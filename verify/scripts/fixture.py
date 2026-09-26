#!/usr/bin/env python3
"""fixture.py — build the `notes` verifier fixture: a git repo with a base and a unit
commit, plus a scope folder (scope.md, finish table, ledger base, review log).

Approach: `verify/tests/fixtures/notes/base/` is committed as the base; the unit commit is
assembled from `parts/` according to which of the six planted defects the variant keeps
(see that folder's README). The finish table, ledger and review log are generated here so
every variant differs from the clean control in exactly the defects it names — a repaired
copy is the bad fixture with one defect fixed, never a separately hand-written tree.

Usage:  fixture.py build ROOT [--variant bad|clean|repaired-<defect>]
Output: `projects: … · scope: … · repo: … · unit: 9.9` on stdout; the tree under ROOT.
Exit:   0 built · 2 usage
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AI_SKILLS = os.path.dirname(os.path.dirname(HERE))
FIX = os.path.join(os.path.dirname(HERE), "tests", "fixtures", "notes")
DEFECTS = ("invented-env", "over-build", "missing-evidence", "under-rung", "rejection-no-reason", "dropped-finding")
UNIT, REPO_KEY = "9.9", "fixture/notes"
HEADER = ("| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung "
          "| unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=fixture", "-c", "user.email=fixture@example.test",
                           *args], check=True, capture_output=True, text=True).stdout.strip()


def read(name):
    with open(os.path.join(FIX, "parts", name), encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def defects_for(variant):
    if variant == "bad":
        return set(DEFECTS)
    if variant == "clean":
        return set()
    if variant.startswith("repaired-") and variant[len("repaired-"):] in DEFECTS:
        return set(DEFECTS) - {variant[len("repaired-"):]}
    raise ValueError(f"unknown variant {variant!r}: bad, clean, or repaired-<{'|'.join(DEFECTS)}>")


def build(root, variant="bad"):
    d = defects_for(variant)
    projects = os.path.join(root, "projects")
    repo = os.path.join(projects, REPO_KEY)
    scope = os.path.join(projects, "fixture-plans", "9-notes")
    shutil.copytree(os.path.join(FIX, "base"), repo)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base: note store")
    base = git(repo, "rev-parse", "HEAD")

    env = "NOTES_EXPORT_BUKET" if "invented-env" in d else "NOTES_EXPORT_BUCKET"
    export = read("export_registry.py" if "over-build" in d else "export_direct.py").replace("{{ENV}}", env)
    write(os.path.join(repo, "notes", "export.py"), export)
    if "over-build" in d:
        write(os.path.join(repo, "notes", "exporters", "__init__.py"), "")
        write(os.path.join(repo, "notes", "exporters", "registry.py"), read("registry.py"))
    write(os.path.join(repo, "tests", "test_export.py"), read("test_export.py"))
    if "missing-evidence" not in d:
        with open(os.path.join(repo, "CHANGELOG.md"), "a", encoding="utf-8") as fh:
            fh.write(read("changelog_entry.md"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feature: export notes as text")
    head = git(repo, "rev-parse", "HEAD")

    resolver = os.path.join(AI_SKILLS, "scripts", "resolve-identifiers.py")
    rows = [
        ("names-resolve", "Every identifier the unit references is declared", "runner",
         f"python3 {resolver} --repo . --range $VERIFY_BASE..HEAD", 4),
        ("tests-pass", "The repo's tests pass", "runner", "python3 -m unittest discover -s tests -t .", 4),
        ("export-runs", "export_text() runs end to end", "runner",
         'python3 -c "from notes.export import export_text; export_text()"', 5 if "under-rung" in d else 4),
        ("no-overbuild", "One export function; no plugin system (scope 4.1)", "judge", "judge", 2),
        ("changelog-entry", "The export is documented in CHANGELOG.md under Unreleased", "judge", "judge", 2),
    ]
    table = "".join(f"| {cid} | {what} | {UNIT} | B | `{cmd.replace('|', chr(92) + '|')}` | {REPO_KEY} | . | - | - "
                    f"| {rung} | no | {'runner record' if kind == 'runner' else 'judge reason'} |\n"
                    for cid, what, kind, cmd, rung in rows)
    write(os.path.join(scope, "finish-conditions.md"),
          f"# Finish conditions — 9-notes (fixture: {variant})\n\n**Schema version:** verify/1\n**Revision:** 1\n\n"
          f"{HEADER}{table}")
    write(os.path.join(scope, "scope.md"), read("scope.md"))
    write(os.path.join(scope, "closeout-prep.md"), f"## Phase 1: export\n\n- base: {UNIT} {REPO_KEY} {base}\n")

    rng = {REPO_KEY: f"{base}..{head}"}
    finding = {"schema": "verify/1", "ts": "2026-09-26T00:00:00Z", "record": "finding", "review_id": f"{UNIT}-r1",
               "reviewer": "codex fixture", "range": rng, "category": "engine", "group": "", "severity": "note", "fix": ""}
    recs = [dict(finding, finding_id=f"{UNIT}-r1-01", file="notes/export.py", line=1, text="module docstring vague"),
            dict(finding, finding_id=f"{UNIT}-r1-02", file="notes/store.py", line=5, text="store is global state"),
            dict(finding, finding_id=f"{UNIT}-r1-03", file="notes/store.py", line=9, text="add() returns a count")]
    disp = {"schema": "verify/1", "ts": "2026-09-26T00:01:00Z", "record": "disposition", "by": "fixture"}
    recs.append(dict(disp, finding_id=f"{UNIT}-r1-01", disposition="fixed", sha=head, reason=None))
    recs.append(dict(disp, finding_id=f"{UNIT}-r1-02", disposition="rejected", sha=None,
                     reason="" if "rejection-no-reason" in d else "append-only in-memory store is the scope's design"))
    if "dropped-finding" not in d:
        recs.append(dict(disp, finding_id=f"{UNIT}-r1-03", disposition="rejected", sha=None,
                         reason="the count is the documented return value"))
    write(os.path.join(scope, "artifacts", f"review-{UNIT}.jsonl"), "".join(json.dumps(r) + "\n" for r in recs))
    return {"projects": projects, "scope": scope, "repo": repo, "unit": UNIT, "base": base, "head": head,
            "defects": sorted(d)}


def main(argv):
    ap = argparse.ArgumentParser(description="Build the notes verifier fixture.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("root")
    b.add_argument("--variant", default="bad")
    try:
        a = ap.parse_args(argv)
        info = build(a.root, a.variant)
    except SystemExit as exc:
        return 2 if exc.code else 0
    except ValueError as exc:
        print(f"fixture.py: {exc}", file=sys.stderr)
        return 2
    print(" · ".join(f"{k}: {v}" for k, v in info.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
