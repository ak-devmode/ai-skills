# Progress: Decision-queue harness

## Index record

Script-owned (`plans-index.py`); PLANS-INDEX.md is rendered from it.

<!-- plans-index:begin -->
| # | Status | Folder | Description | Created by |
|---|---|---|---|---|
| 10 | 📝 Draft (2026-10-25) | `10-decision-queue-harness/` | Re-targets the harness from closing review findings to surfacing decisions: every lane ends done or with a decision in Alex's queue. Adds structured decision packets, a one-way/two-way door rule with a per-repo floor, and a queue page on homelab that both machines write to over the tailnet; Alex answers by pasting an edited prefilled reply into the named pane. Review loops stop on diminishing returns and emit packets instead of patching local maxima, drivers merge their own PRs to develop outside the floor, and the 21-day log analysis becomes a re-runnable scorecard. | Alex |
| 10.1 | 📝 Draft (2026-10-25) | `10-decision-queue-harness/` | Phase 1 — Decision queue v1, usable today: packet schema, packet.py/door.py, homelab queue service with the data-model template, /plan and /concurrency wiring. | Alex |
| 10.2 | 📝 Draft (2026-10-25) | `10-decision-queue-harness/` | Phase 2 — Review and verify re-pointed at decisions: diminishing-returns exit rule, lineage fix, --reframed disposition, packets from cascade/convergence/run-cap stops. | Alex |
| 10.3 | 📝 Draft (2026-10-25) | `10-decision-queue-harness/` | Phase 3 — Driver merges its own PRs (develop for code, main for docs repos) when green with real checks and no floor path; floor hits become packets. | Alex |
| 10.4 | 📝 Draft (2026-10-25) | `10-decision-queue-harness/` | Phase 4 — UI-change template (old/new screenshots), harness scorecard from the mining scripts, herdr attention filter ignores finished lanes. | Alex |
<!-- plans-index:end -->

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔code mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each phase's surface against live code before entering it; raise gaps in
   batched blocks, not per-step.
3. Wrap + commit + check in at every phase boundary; progress updates land more frequently than
   boundaries (compaction defense). This file alone must be sufficient for a cold context to resume.
4. v1 is iterative: ship the usable thing, then narrow in live use. No polish passes.
5. Never write SSM values, never touch prod, never merge from a lane.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/10-decision-queue-harness/scope.md
**Last action:** Scope created (2026-10-25)
**Next action:** /plan-ceo-review on scope.md, then /plan 10.1
**Open blockers:** dev-workbench uncommitted config changes (scope §2 drift); codex out of credits on both accounts until later today
**Key files changed:** None yet

---

## Decisions Log
- (2026-10-25) Frame, doors, homelab queue, paste-back return path, structured packets,
  data-model template first, diminishing-returns review exit, driver merges, and the teammate
  seam: all from the scoping rounds, recorded in scope.md §11.

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-10-25 | /scope | Done | Scope created — decision queue v1 today, then review re-pointing, driver merges, UI template + scorecard in parallel |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Resolve dev-workbench uncommitted settings.json / codex config.toml | [ ] Pending | before 10.1 touches dev-workbench |
| Approve the `decision_queue` table creates (scope §7) | [ ] Pending | at handoff |
| Approve finish-conditions.md | [ ] Pending | scope §5.10.1 |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 10.1 | 10.1-decision-queue-harness-PLAN.md | Phase 1 — Decision queue v1 | Draft | gate D then A |
| 10.2 | 10.2-decision-queue-harness-PLAN.md | Phase 2 — Review/verify re-pointed | Draft | gate C, concurrent |
| 10.3 | 10.3-decision-queue-harness-PLAN.md | Phase 3 — Driver merges | Draft | gate D, concurrent |
| 10.4 | 10.4-decision-queue-harness-PLAN.md | Phase 4 — UI template, scorecard, herdr | Draft | gate A |

---

## Artifacts
- `artifacts/baseline-2026-10-25.md` — 21-day both-host baseline
- `artifacts/mining/` — mine.py, mine2.py, reviews.py
