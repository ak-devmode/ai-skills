#!/usr/bin/env python3
# LIVE validation of the code-defect PR path (scope 146, Phase 3 / Task 3.2, PR rung).
#
# Why this exists: the September corpus has ZERO auto-PR-eligible defects (PIPELINE=0),
# so the repro->fix->verify->PR path cannot be exercised by real Grafana data yet. This
# script plants a SYNTHETIC, self-contained reproducible defect in a throwaway worktree
# of wellmed-gateway-go and drives the REAL production pipeline (remediate._pipeline)
# over it. The mechanical harness is what's unproven — worktree create off the real
# trunk, `go test` repro execution, `git apply` of the fix, the verify oracle flipping
# on the ORIGINAL signal, and PR-summary + ES-email composition. So the agent stages are
# a SCRIPTED runner returning the known fix (I planted the bug, I know the fix): this
# isolates "does the plumbing work against real gateway-go" from "can the LLM fix it"
# (the latter is a separate, token-spending validation).
#
# The live `gh pr create` stays GUARDED OFF (allow_pr=False) — open_pr returns the
# summary without creating. Opening a real PR triggers CI + OIDC-adjacent workflows and
# is an outward action; it needs an explicit greenlight, not this validation.
#
# NOT part of the offline suite (needs network + a gateway-go checkout). Run explicitly.

import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WF = HERE.parent
sys.path.insert(0, str(WF))

import json
import remediate
import worktree as wt

REPO = Path.home() / "Projects" / "wellmed" / "wellmed-gateway-go"
PKG = "internal/alarmcanary"

# --- the synthetic seed: an off-by-one that drops nums[0]; the test is the alarm signal.
BUGGY = (
    "package alarmcanary\n\n"
    "// Sum has a synthetic off-by-one (scope-146 PR-path validation). Not real code.\n"
    "func Sum(nums []int) int {\n"
    "\ttotal := 0\n"
    "\tfor i := 1; i < len(nums); i++ { // BUG: starts at 1, drops nums[0]\n"
    "\t\ttotal += nums[i]\n"
    "\t}\n"
    "\treturn total\n"
    "}\n"
)
FIXED = BUGGY.replace(
    "\tfor i := 1; i < len(nums); i++ { // BUG: starts at 1, drops nums[0]\n",
    "\tfor i := 0; i < len(nums); i++ {\n")
TEST = (
    "package alarmcanary\n\n"
    "import \"testing\"\n\n"
    "func TestSum(t *testing.T) {\n"
    "\tif got := Sum([]int{1, 2, 3}); got != 6 {\n"
    "\t\tt.Fatalf(\"SIGNAL: Sum([1,2,3])=%d, want 6\", got)\n"
    "\t}\n"
    "}\n"
)
REPRO_CMD = f"go test ./{PKG}/ 2>&1"
# Fix diff computed from the exact seed bytes so `git apply` context matches byte-for-byte.
FIX_DIFF = "".join(difflib.unified_diff(
    BUGGY.splitlines(keepends=True), FIXED.splitlines(keepends=True),
    fromfile=f"a/{PKG}/canary.go", tofile=f"b/{PKG}/canary.go"))


def scripted_runner(prompt):
    table = {
        "You are the root-cause stage": {
            "annotation_found": True, "annotation_says": "synthetic off-by-one",
            "root_cause": "Sum drops nums[0] (loop starts at index 1)",
            "fix_available": True, "fix_class": "mechanical-diff",
            "recommended_lever": f"{PKG}/canary.go loop init", "short_circuit": False},
        "You are the repro stage": {
            "repro_available": True, "repro_cmd": REPRO_CMD,
            "signal_assertion": "test 'SIGNAL: Sum([1,2,3])' absent (rc==0) after fix",
            "notes": "self-contained package, builds offline"},
        "You are the fix stage": {
            "diff": FIX_DIFF, "files_touched": [f"{PKG}/canary.go"],
            "explanation": "start the accumulation loop at index 0 so nums[0] is included"},
        "You are the verify stage": {
            "fails_pre_fix": True, "passes_post_fix": True,
            "signal_tied": True, "verdict": "pass"},
    }
    for marker, out in table.items():
        if marker in prompt:
            return "```json\n" + json.dumps(out) + "\n```"
    raise AssertionError("prompt matched no scripted stage")


def seed_factory(repo_path, signature):
    """Create a REAL worktree off gateway-go's trunk (develop) and plant the defect."""
    tree = wt.Worktree(REPO, base_ref="origin/develop", signature="pr-validate").create()
    pkgdir = tree.path / PKG
    pkgdir.mkdir(parents=True, exist_ok=True)
    (pkgdir / "canary.go").write_text(BUGGY)
    (pkgdir / "canary_test.go").write_text(TEST)
    return tree


def main():
    inc = {"alertName": "Synthetic Sum off-by-one (scope-146 validation)", "firings": 1,
           "labels": {"env": "dev", "tier": "page", "instance": "canary"},
           "class": "code-defect", "route": "PIPELINE",
           "why": "synthetic seed", "repo": "wellmed-gateway-go",
           "annotation": "synthetic reproducible defect for PR-path validation"}

    open_pr = "--open-pr" in sys.argv
    print(f"== LIVE PR-path validation (open_pr={open_pr}): real gateway-go worktree, "
          f"real `go test`, real git apply ==")
    out, kept = remediate._pipeline(inc, runner=scripted_runner, send=False,
                                    allow_pr=open_pr, tree_factory=seed_factory)
    print(json.dumps({k: v for k, v in out.items() if k != "pr"}, indent=2, default=str))

    pr = out.get("pr", {})
    checks = {
        "route == PR (verify oracle accepted)": out.get("route") == "PR",
        "worktree pruned (not kept)": not kept,
        "PR summary produced": bool(pr.get("summary")),
        ("PR opened live" if open_pr else "PR NOT opened (guarded)"):
            (pr.get("opened") is True if open_pr else pr.get("opened") is False),
        "email dry-run, PHI-clean": out.get("sent") is False and not out.get("phi_held"),
    }
    if open_pr:
        print(f"\n== LIVE PR ==\n  url: {pr.get('url')}\n  branch: {pr.get('branch')} "
              f"-> base: {pr.get('base')}\n  reason(if not opened): {pr.get('reason')}")
    print("\n== checks ==")
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed

    print("\n== the PR that WOULD open (guarded off) ==\n")
    print(out.get("pr", {}).get("summary", "(none)"))
    print(f"\n== the ES email that WOULD send ==\nsubject bytes: {out.get('bytes')}")

    # confirm the age-sweep + prune left nothing behind
    leftover = [d.name for d in wt.SCRATCH.iterdir()] if wt.SCRATCH.exists() else []
    print(f"\nworktree scratch after run: {leftover or 'clean'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
