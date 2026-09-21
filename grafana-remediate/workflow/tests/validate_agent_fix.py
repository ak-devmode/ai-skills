#!/usr/bin/env python3
# Real-agent fix validation (scope 146, Phase 3 / Task 3.2 option 3).
#
# Unlike validate_pr_path.py (which scripts the fix to isolate the plumbing), this drives
# the FIX stage with a REAL `claude -p` running INSIDE the worktree, to answer: given a
# reproduced failure, can the model produce a diff that actually kills the original
# signal? root-cause/repro/verify stay scripted (they set up the repro correctly); only
# the fix is the model's own work, and the mechanical verify oracle (real go test pre/post)
# is the honest judge — a bad diff cannot pass. gh PR creation stays OFF.
#
# Run explicitly (needs network + gateway-go + tokens). Reports PASS/FAIL of the real fix.

import json
import sys
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WF = HERE.parent
sys.path.insert(0, str(WF))

import remediate
import worktree as wt
sys.path.insert(0, str(HERE))
from validate_pr_path import BUGGY, TEST, PKG, REPRO_CMD, REPO  # reuse the seed

_tree_ref = {}


def seed_factory(repo_path, signature):
    tree = wt.Worktree(REPO, base_ref="origin/develop", signature="agent-fix").create()
    pkgdir = tree.path / PKG
    pkgdir.mkdir(parents=True, exist_ok=True)
    (pkgdir / "canary.go").write_text(BUGGY)
    (pkgdir / "canary_test.go").write_text(TEST)
    _tree_ref["path"] = tree.path
    return tree


def hybrid_runner(prompt):
    # Scripted for the setup stages; REAL claude -p (in the worktree) for the fix.
    scripted = {
        "You are the root-cause stage": {
            "annotation_found": True, "annotation_says": "off-by-one",
            "root_cause": "Sum drops nums[0]", "fix_available": True,
            "fix_class": "mechanical-diff", "recommended_lever": f"{PKG}/canary.go",
            "short_circuit": False},
        "You are the repro stage": {
            "repro_available": True, "repro_cmd": REPRO_CMD,
            "signal_assertion": "test SIGNAL absent (rc==0) after fix", "notes": "self-contained"},
        "You are the verify stage": {
            "fails_pre_fix": True, "passes_post_fix": True, "signal_tied": True, "verdict": "pass"},
    }
    for marker, out in scripted.items():
        if marker in prompt:
            return "```json\n" + json.dumps(out) + "\n```"
    if "You are the fix stage" in prompt:
        proc = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                              capture_output=True, text=True, timeout=900,
                              cwd=str(_tree_ref["path"]))
        if proc.returncode != 0:
            raise RuntimeError(f"claude -p (fix) exited {proc.returncode}: {proc.stderr[:300]}")
        try:
            return json.loads(proc.stdout).get("result", proc.stdout)
        except json.JSONDecodeError:
            return proc.stdout
    raise AssertionError("prompt matched no stage")


def main():
    inc = {"alertName": "Synthetic Sum off-by-one (real-agent fix)", "firings": 1,
           "labels": {"env": "dev", "tier": "page", "instance": "canary"},
           "class": "code-defect", "route": "PIPELINE", "why": "synthetic",
           "repo": "wellmed-gateway-go", "annotation": "synthetic off-by-one"}
    print("== REAL-AGENT fix validation: claude -p writes the fix inside the worktree ==")
    out, kept = remediate._pipeline(inc, runner=hybrid_runner, send=False, allow_pr=False,
                                    tree_factory=seed_factory)
    route = out.get("route")
    print(json.dumps({k: v for k, v in out.items() if k != "pr"}, indent=2, default=str))
    passed = route == "PR"
    print(f"\n[{'PASS' if passed else 'FAIL'}] real agent produced a fix that killed the "
          f"original signal (route={route})")
    if not passed:
        print("  -> finding: the real fix diff did not apply-and-pass. The fix stage "
              "likely needs the edit-in-place + `git diff` capture design rather than "
              "asking the model for a unified diff. Logged for follow-up.")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
