# Progress: Decision-queue harness

## Index record

Script-owned (`plans-index.py`); PLANS-INDEX.md is rendered from it.

<!-- plans-index:begin -->
| # | Status | Folder | Description | Created by |
|---|---|---|---|---|
| 10 | 🚧 In progress (2026-10-26) — 10.1 + 10.2 running as concurrent lanes | `10-decision-queue-harness/` | Re-targets the harness from closing review findings to surfacing decisions: every lane ends done or with a decision in Alex's queue. Adds structured decision packets, a one-way/two-way door rule with a per-repo floor, and a queue page on homelab that both machines write to over the tailnet; Alex answers by pasting an edited prefilled reply into the named pane. Review loops stop on diminishing returns and emit packets instead of patching local maxima, drivers merge their own PRs to develop outside the floor, and the 21-day log analysis becomes a re-runnable scorecard. | Alex |
| 10.1 | 🚧 In progress (2026-10-26) — lanes A packet/door, B queue service | `10-decision-queue-harness/` | Phase 1 — Decision queue v1, usable today: packet schema, packet.py/door.py, homelab queue service with the data-model template, /plan and /concurrency wiring. | Alex |
| 10.2 | 🚧 In progress (2026-10-26) — lane C review changes, lineage fix first | `10-decision-queue-harness/` | Phase 2 — Review and verify re-pointed at decisions: diminishing-returns exit rule, lineage fix, --reframed disposition, packets from cascade/convergence/run-cap stops. | Alex |
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
**Last action:** /plan 10.1 + 10.2 Phase 0 done (2026-10-26); plans Ready to execute; dev-workbench drift committed (28850dc)
**Next action:** /concurrency launches lanes A (10.1 packet schema + packet.py/door.py, ai-skills), B (10.1 queue service + data-model template, dev-workbench), C (10.2 review changes, lineage fix first, ai-skills); this pane drives
**Open blockers:** none
**Key files changed:** None yet

---

## Decisions Log
- (2026-10-25) Frame, doors, homelab queue, paste-back return path, structured packets,
  data-model template first, diminishing-returns review exit, driver merges, and the teammate
  seam: all from the scoping rounds, recorded in scope.md §11.
- (2026-10-25) CEO review: baseline round counts were per unit, not per lineage (corrected,
  baseline §3.1). Phase 2 exit rule dropped; replaced by round-1-uncapped findings budget,
  per-round reframe prompt judged by a fresh agent, three review cases to the queue, round-1
  effort trial. Harness errors never stop work (dead queue → `Blocked` in pane). Driver merges
  include degraded reviews (flagged) and `--admin`. Details: scope.md §4 and the review report.
- (2026-10-26) /plan start: Alex overrode the Repo Graph drift stop (decision 76); his dev-workbench config committed as-is (75); 10.1 and 10.2 run as concurrent lanes.
- (2026-10-26) Eng review: queue on 127.0.0.1 behind `tailscale serve` (HTTPS MagicDNS URL kept);
  one packet path via lane outboxes, drivers POST; rules-version stamp on review records for
  cutover; lineage fix lands first; no should-fix cap at any round (later-round findings are
  mostly defects in fixes, baseline §3.2–3.3); round-aware review prompt with `reopens`; fix
  discipline (fail closed by default unless reasoned) with a chain stop. Declined: splitting
  large round-1 reviews (codex credits).

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-10-26 | /plan 10.1 + 10.2 | Phase 0 done | Ready to execute; repo-graph drift overridden by Alex; lanes via /concurrency |
| 2026-10-26 | /plan-eng-review | Done | outside voice codex-int; 46 issues, 0 critical gaps; finish table rev 3 approved; gstack pulled to 1.91.226 |
| 2026-10-25 | /plan-ceo-review | Done | HOLD SCOPE; outside voice = in-host Claude; finish table rev 2 pending approval |
| 2026-10-25 | finish table + table creates | Approved | rev 1; packets/events/views creates approved |
| 2026-10-25 | /scope | Done | Scope created — decision queue v1 today, then review re-pointing, driver merges, UI template + scorecard in parallel |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Resolve dev-workbench uncommitted settings.json / codex config.toml | [x] Done | committed 28850dc on Alex's yes, 2026-10-26 (local) |
| Approve the `decision_queue` table creates (scope §7) | [x] Done | Alex, 2026-10-25 |
| Approve finish-conditions.md | [x] Done | rev 1, Alex, 2026-10-25 |
| Approve finish-conditions.md rev 2 | [x] Done | Alex, 2026-10-25 |
| Enable tailnet HTTPS certs; `tailscale set --operator=alexk` on homelab | [x] Done | Alex, 2026-10-26 |
| Approve finish-conditions.md rev 3 | [x] Done | Alex, 2026-10-26 |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 10.1 | 10.1-decision-queue-harness-PLAN.md | Phase 1 — Decision queue v1 | In progress | gate D then A |
| 10.2 | 10.2-decision-queue-harness-PLAN.md | Phase 2 — Review/verify re-pointed | In progress | gate C, concurrent with 10.1 |
| 10.3 | 10.3-decision-queue-harness-PLAN.md | Phase 3 — Driver merges | Draft | gate D, after 10.1 packet tooling |
| 10.4 | 10.4-decision-queue-harness-PLAN.md | Phase 4 — UI template, scorecard, herdr | Draft | gate A, after 10.1 packet tooling |

---

## Artifacts
- `artifacts/baseline-2026-10-25.md` — 21-day both-host baseline
- `artifacts/mining/` — mine.py, mine2.py, reviews.py, lineage.py (per-lineage rounds; supersedes reviews.py's round counts), infix.py (where later-round findings land), fixpairs.py (why fixes draw findings)
- `artifacts/eng-review-2026-10-25.md` — eng review record, decisions 62–74

---

## Plan 10.1: Decision queue v1, usable today

### Resume Context (Plan 10.1)
**Status:** 1.1–1.4 built on lanes A and B, both in review
**Next action:** collect lane A (1.1, 1.2) and lane B (1.3, 1.4); then 1.5 skill wiring, 1.6 deploy
**Base:** ai-skills ad15797 · dev-workbench 28850dc (closeout-prep.md)

### Session: 2026-10-26
#### Phase 0 — ✅ DONE
- Inputs and Related Docs resolve; Status flipped Draft → Ready to execute on Alex's word; Executed by stamped.
- Repo Graph: ai-skills advanced (own commits); dev-workbench diverged on the known drift — Alex overrode (76); drift committed 28850dc (75).
- Finish table rev 3 approved. Branches: lane worktrees `feature/10-decision-queue-*`, cut over to ai-skills main in one step; dev-workbench feature branch merged to main before install.
#### Task 1.0 — ✅ DONE
- dev-workbench clean: Alex's allow rule + codex trust entries committed 28850dc.

#### Task 1.1 — ✅ DONE (lane A, b7df5d2 on `concurrency/10-packet`)
- `schemas/packet.schema.json`, `scripts/schema_check.py` (stdlib subset validator, fails on unknown keywords), fixtures `scripts/tests/fixtures/packets/{valid,invalid}/`, `scripts/tests/test_packet_schema.py`.
#### Task 1.2 — ✅ DONE pending review (lane A, 41e788d)
- `scripts/packet.py`, `scripts/door.py`, `scripts/one-way-doors.defaults`, `scripts/tests/test_packet.py`, `scripts/tests/test_door.py`, `scripts/README.md`. Driver re-ran from the branch: full suite 373 OK (2 skipped).
- Lane's open calls (two-way, kept): `check-reply --lane M/W/A --outbox` lets the driver check a reply for a lane; `stale` fails open with a stated reason (it discards a pending decision, and check-reply gates anyway); `!` negations in `.one-way-doors` ignored; matching case-insensitive; door.py exit 2 on usage error, callers treat non-zero as one-way.
- Review: fresh pane `packet review` (w14:p1H), unit 10.1, range 14954fc..concurrency/10-packet.

#### Task 1.3 — ✅ DONE pending review (lane B, 9a93d0c on dev-workbench `concurrency/10-queue`)
- `queue/` (stdlib http.server + psycopg 3 + jsonschema via uv; schema vendored from b7df5d2), migrations for `packets`/`events`/`views`, `config/systemd/decision-queue.service` (user unit), `install.sh` wiring (enables only when `~/.config/decision-queue/dsn` exists). Not installed or deployed. Driver re-ran: 23 passed.
- Lane's questions, driver calls: no in-app auth (settled, scope §9); backup-timer coverage checked at deploy (Task 1.6); a retried id with different content should return 409, not `200 duplicate` (folded into the fix round); ERD without FKs is fine for v1; vendored schema copy needs a drift guard (fix round).
#### Task 1.4 — ✅ DONE pending review (lane B, 98a4109)
- ERD + side-by-side data-model styles with a no-JS per-card toggle; screenshots in `queue/docs/`.
- Review: fresh pane `queue review` (w14:p1J), unit 10.1, range 28850dc..concurrency/10-queue.

---

## Plan 10.2: Review re-pointed at decisions

### Resume Context (Plan 10.2)
**Status:** Phase 0 done; tasks 2.3 (lineage first) → 2.1 → 2.1b → 2.2 → 2.4 dispatched to lane C; 2.5 waits for 10.1 packet.py
**Next action:** collect lane C
**Base:** ai-skills ad15797 (closeout-prep.md)

### Session: 2026-10-26
#### Phase 0 — ✅ DONE
- Status flipped Draft → Ready to execute on Alex's word; Executed by stamped; shares 10.1's freshness result.
