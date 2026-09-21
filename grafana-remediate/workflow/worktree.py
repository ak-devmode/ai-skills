#!/usr/bin/env python3
# Per-alarm throwaway worktree lifecycle (scope 146, Phase 2, Task 2.3).
#
# Approach: the workflow reproduces a defect in an ISOLATED git worktree so it never
# mutates the operator's checkout, and it owns the cleanup so worktrees don't accumulate
# on Alex's machine (or the cloud sandbox). Lifecycle, per the scope's Key Decisions:
#   - created ONLY at entry to the repro gate (most alarms never reach it);
#   - pruned on any exit EXCEPT a verify-gate failure (those are kept for inspection);
#   - age-swept regardless (a crashed run that never pruned still gets collected).
#
# This is the runtime worktree the WORKFLOW creates per alarm — a different mechanism
# from /plan's herdr driver worktree. Base repos live under ~/Projects/wellmed/<repo>;
# worktrees are created under a workflow-owned scratch root so the age-sweep can safely
# reap the whole directory.
#
# Stdlib only. `run()` executes inside the worktree with a timeout and merged output so
# the repro/verify gates can judge rc + text.

import os
import shutil
import subprocess
import time
from pathlib import Path

SCRATCH = Path(os.environ.get("ALARM_WT_ROOT",
                              Path.home() / ".cache" / "alarm-remediation" / "worktrees"))
MAX_AGE_S = int(os.environ.get("ALARM_WT_MAX_AGE_S", 24 * 3600))  # age-sweep horizon


class Worktree:
    """One throwaway checkout of `repo` at `base_ref`. Use as a context manager;
    __exit__ prunes UNLESS .keep is set (verify-gate failure keeps it)."""

    def __init__(self, repo_path, base_ref="origin/main", signature="wt"):
        self.repo_path = Path(repo_path)
        self.base_ref = base_ref
        self.keep = False
        SCRATCH.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "-" for c in signature)[:48]
        self.path = SCRATCH / f"{self.repo_path.name}-{safe}-{int(time.time())}"

    def _git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.repo_path), *args],
                              capture_output=True, text=True)

    def create(self):
        self._git("fetch", "--quiet", "origin")
        r = self._git("worktree", "add", "--detach", str(self.path), self.base_ref)
        if r.returncode != 0:
            raise RuntimeError(f"worktree add failed: {r.stderr[:300]}")
        return self

    def run(self, cmd, timeout=900):
        """Run a shell command inside the worktree. Returns (rc, merged_output)."""
        p = subprocess.run(cmd, cwd=str(self.path), shell=True,
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)

    def apply_diff(self, diff_text):
        patch = self.path / ".alarm-fix.patch"
        patch.write_text(diff_text)
        r = self._git("apply", str(patch), cwd=self.path)
        return r.returncode == 0, r.stderr

    def prune(self):
        self._git("worktree", "remove", "--force", str(self.path))
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self):
        return self.create()

    def __exit__(self, exc_type, exc, tb):
        # Keep on a verify-gate failure (self.keep) OR an unexpected exception, for
        # inspection. Otherwise prune. Age-sweep is a separate, unconditional pass.
        if not self.keep and exc_type is None:
            self.prune()
        return False


def age_sweep(now=None):
    """Reap any worktree dir older than MAX_AGE_S, regardless of how it was orphaned.
    Runs at the start of every workflow invocation so a crashed run self-heals."""
    now = now or time.time()
    reaped = []
    if not SCRATCH.exists():
        return reaped
    for d in SCRATCH.iterdir():
        try:
            if now - d.stat().st_mtime > MAX_AGE_S:
                shutil.rmtree(d, ignore_errors=True)
                reaped.append(d.name)
        except FileNotFoundError:
            continue
    return reaped
