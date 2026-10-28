# Progress: Decision-queue harness

## Index record

Script-owned (`plans-index.py`); PLANS-INDEX.md is rendered from it.

<!-- plans-index:begin -->
| # | Status | Folder | Description | Created by |
|---|---|---|---|---|
| 10 | 🚧 In progress (2026-10-26) — 10.1 + 10.2 running as concurrent lanes | `10-decision-queue-harness/` | Re-targets the harness from closing review findings to surfacing decisions: every lane ends done or with a decision in Alex's queue. Adds structured decision packets, a one-way/two-way door rule with a per-repo floor, and a queue page on homelab that both machines write to over the tailnet; Alex answers by pasting an edited prefilled reply into the named pane. Review loops stop on diminishing returns and emit packets instead of patching local maxima, drivers merge their own PRs to develop outside the floor, and the 21-day log analysis becomes a re-runnable scorecard. | Alex |
| 10.1 | 🚧 In progress (2026-10-26) — lanes A packet/door, B queue service | `10-decision-queue-harness/` | Phase 1 — Decision queue v1, usable today: packet schema, packet.py/door.py, homelab queue service with the data-model template, /plan and /concurrency wiring. | Alex |
| 10.2 | 🚧 In progress (2026-10-26) — lane C review changes, lineage fix first | `10-decision-queue-harness/` | Phase 2 — Review and verify re-pointed at decisions: diminishing-returns exit rule, lineage fix, --reframed disposition, packets from cascade/convergence/run-cap stops. | Alex |
| 10.3 | 🚧 In progress (2026-10-27) — lane merges | `10-decision-queue-harness/` | Phase 3 — Driver merges its own PRs (develop for code, main for docs repos) when green with real checks and no floor path; floor hits become packets. | Alex |
| 10.4 | 🚧 In progress (2026-10-27) — lanes ui-packet, scorecard, attention | `10-decision-queue-harness/` | Phase 4 — UI-change template (old/new screenshots), harness scorecard from the mining scripts, herdr attention filter ignores finished lanes. | Alex |
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
**Last action:** final cutover landed (ai-skills 5cebe49, dev-workbench be36d57; queue restarted first); v2 card verified live; 10.1 acceptance met (real cards: homelab2026 24, MBA 9)
**Next action:** /verify 10.1 → 10.2 → 10.3 → 10.4; /document-release for the review-loop change; lane teardown; /closeout
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
- (2026-10-28) Merge gate round-3 stop answered (Alex): 83 narrow --admin to 'review approval is the only unmet requirement and every entry of every required check passed', else park; 84 take the reframe — lanes identified from the driver-written dispatch log, herdr-name lookup deleted.
- (2026-10-28) Merge gate round 4: --admin kept narrowed (83) and made fail-closed on any protection beyond checks + reviews (live repos have only those); 86 (Alex) invert lane identity — the driver registers its own pane, every unregistered pane is a lane.
- (2026-10-28) Cards too verbose (Alex, first live card): 85 fix now as one lane — schema v2 caps (question title, ≤400-char context, option label + one-line why, evidence folded), one decision per packet, render order question → recommendation → options → context → folded evidence, writing rules in the skills.
- (2026-10-27) Scorecard reopen chain (10.4-r12-01 → r10-02 → r5-03): reframed by the driver (fix discipline; overturns no decision) — fixed follow-up cohort (`--follow-up`, default 7 d) replaces closed-only filtering and the data-estimated horizon.
- (2026-10-27) Driver merges (10.3 review, driver calls): merge only when verdict-gate.py --blocking reads pass (advisory/not-judged/unknown never merge, so merged is a stricter bar than Done); a repo with no CI (pmg-docs, ai-skills today) never auto-merges — vacuous green refuses it and it parks as a two-way packet; CI definitions (.github/workflows/, .github/actions/, CODEOWNERS, .circleci/, .gitlab-ci.yml, Jenkinsfile, buildspec*) and singular migration/ are floor paths.
- (2026-10-27) Wiring round-3 stop (10.1-r11 reopened r8-01/02): reframed on Alex's yes (80) — pasted replies only via a file, never shell source; flush count check dropped. Review-packets lane: "is this reframe Alex's call" consolidated into one function (driver call, reopen chain at round 2).
- (2026-10-26) Lane B round-3 stop: r5-01 rejected — service never deployed, no older server to upgrade from (Alex, 78); r5-02 fixed with one more review round (Alex, 79).
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
| 10.3 | 10.3-decision-queue-harness-PLAN.md | Phase 3 — Driver merges | In progress | gate D, after 10.1 packet tooling |
| 10.4 | 10.4-decision-queue-harness-PLAN.md | Phase 4 — UI template, scorecard, herdr | In progress | gate A, after 10.1 packet tooling |

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

#### Review loops (2026-10-26)
- Lane A: r1 SHIP 16 findings (15 fixed, r1-11 accepted for 1.5 wiring) → r3 SHIP 3 notes, batch-fixed bb0bc6d; driver contract fix ef078ba (409 = conflict, 404 event = retry) — reviewed with the cutover range.
- Lane B: r2 SHIP AFTER BLOCKING 7 → all fixed (+ D1 409 on changed retry, D2 schema drift guard); r4 SHIP AFTER BLOCKING 7 → fixed; event replay REFRAMED (driver call: delete server replay, 404 unknown-packet events, client orders) instead of patched; r5 = round-3 stop + [CONVERGENCE] db.py → decisions 78/79 to Alex.
- Watcher lesson: markers quoted in a prompt or brief echo in the pane; `~/cc/lane-watch.sh` seeds what's on screen and ignores `<placeholder>` lines.

#### Final review rounds (2026-10-27)
- Lane B: r5 round-3 stop → r5-01 rejected (Alex 78), r5-02 fixed c09d155 → r9 SHIP 0 findings.
- Lane A: 409 contract fix ef078ba → r7 (4xx classes, refused-packet events) fixed 47387a9 → r10 (marker reconcile) 82b5bdc → r12 (cleanup swallowed) 70eb05d, SHIP each round.
- Wiring (D1): r6 3 findings fixed → r8 2 → r11 round-3 stop, reopen chain → REFRAME (Alex 80): replies via file only, count check dropped (c647fc8, a17353b) → r13 SHIP, its one finding already fixed by 47387a9.
- Session note: 36 finished panes closed on Alex's ask (machine load); scope 197's lanes are the remaining load.

#### Task 1.6 — 🔄 in review (2026-10-27)
- Cutover via `~/cc/10-cutover.sh` (Alex): ai-skills main 421216f, dev-workbench main c09d155. Homelab dev-workbench pull hit codex trust-entry churn in `config/codex/config.toml`; pulled with autostash, conflict resolved as the union (TOML-validated), local churn kept uncommitted, stash dropped.
- Homelab: role + DB `decision_queue` (owner decision_queue, password only in `~/.config/decision-queue/dsn`, 0600 alexk); `install.sh` linked the user unit + `~/.local/share/decision-queue`, enabled active; migrations 001–003 applied; `tailscale serve --bg 8787` → https://homelab2026.taild4682e.ts.net (tailnet only). Backup: `homelab-db-backup` runs `pg_dumpall` in the container ⇒ covers `decision_queue`.
- Acceptance: curl POST from the MBA → 201, identical retry → 200, /api/stats shows machine mba. Test card `acc-…` on the page.
- `DECISION_QUEUE_URL` added to `config/claude-code/settings.json` env (shared by both machines), commit ef9bae0, not pushed.

- (2026-10-27) URL pushed (ef9bae0) and pulled on homelab (`~/cc/homelab-pull.sh`). Paste-back: Alex copied the test card's reply into the driver pane; `check-reply` refused it (foreign lane tag) — correct. Follow-up (two-way, not built): the queue accepts a packet whose reply tag doesn't match its own id/lane (a hand-built POST showed it; packet.py always builds it right) — add a server-side tag check.

#### Task 1.6 — ✅ DONE (2026-10-28)
- Acceptance: the live queue holds real cards from both machines (homelab2026 24, MBA 9 on the page, 2026-10-28). Final cutover via `~/cc/10-cutover-final.sh`: dev-workbench be36d57 first, homelab queue restarted, then ai-skills 5cebe49 (packet.py v2 default). Driver pane registered (dispatch-log `--status driver`); a v2 info card posted from it rendered in the new order and was closed.

---

## Plan 10.2: Review re-pointed at decisions

### Resume Context (Plan 10.2)
**Status:** 2.1–2.4 built on lane C, in review; 2.5 waits for 10.1 packet.py to land
**Next action:** collect lane C
**Base:** ai-skills ad15797 (closeout-prep.md)

### Session: 2026-10-26
#### Phase 0 — ✅ DONE
- Status flipped Draft → Ready to execute on Alex's word; Executed by stamped; shares 10.1's freshness result.
#### Tasks 2.3, 2.1, 2.1b, 2.2, 2.4 + rules-version stamp — ✅ DONE pending review (lane C, `concurrency/10-review`)
- dc48248 lineage continues only on a fix re-review (closes the P1 TO-DO, plans/TO-DO.md ~483) · 8358edc `dispose --reframed` · c40e04a `rules_version` stamp, lineages keep their root's rules (decision 65, 10.1 Task 1.5's stamp done here) · 90a95af findings budget + round-aware prompt + `reopens` · f8196ab fix discipline + reopens chain stop · 140b5dd reframe prompt + fresh judge · eaa3355 effort trial (`verify_lib.EFFORT_TRIAL`, default on, capped xhigh) · 3e1517e review skill 3.9.0.
- Lane notes: an accepted reframe that overturns a recorded decision fills `overturns` and goes to Alex before anything is built; the judge's objective comes from `--objective`, else scope.md §1, else exit 3; the trial flag is a code constant, not an env var; `verify_lib.schema_problems` now handles boolean and errors on unsupported types (check against lane A's `schema_check.py` at merge); 2.5 packet data lives in the new reframe / reframe-verdict records.
- Review: fresh pane `review-loop review` (w14:p1M, tab "10 lanes 2"), unit 10.2, range 14954fc..concurrency/10-review.
#### Review loop (2026-10-26)
- r1 SHIP AFTER BLOCKING 3: judge provenance unenforced (75609c8), lineage fix retroactive on closed units — versioned, sweep 0/300 logs change verdict (f65d635), effort stamp (55da072); r2 SHIP, 1 note (rule keyed on lineage root) batch-fixed aaf63aa. Full suite 346 OK.
- Lanes A + C merged on `feature/10-decision-queue` (95a8b89, 4cdea98), clean merges.
#### Task 2.5 + review rounds (2026-10-27)
- D2 (packets from review/verify): r3 4 findings fixed → r4 reopen chain (who decides "Alex's call") → CONSOLIDATED into one function 21be2cd → r5 SHIP, 1 should-fix fixed abfc579 (repeat check looks backwards only). Suites: 440 OK at 95d20ce, 444 OK at 21be2cd.

---

## Plan 10.3: Driver merges

### Resume Context (Plan 10.3)
**Status:** Phase 0 done; 3.1 + 3.2 dispatched to lane merges
**Base:** ai-skills 361ae68

### Session: 2026-10-27
#### Phase 0 — ✅ DONE
- Ready to execute (Alex: "start 10.3 and 10.4 concurrently"), Executed by stamped, freshness OK (ai-skills dirty = own plan edits). Concurrency plan approved (82).

#### Tasks 3.1 + 3.2 — ✅ DONE pending review (lane merges, `concurrency/10-merges`)
- d36f8ad `scripts/driver-merge.py` (check|merge; vacuous-green / skipped-only / prod base / floor / unreadable verdict / non-driver / gh error = no merge, packet instead), `/plan` §6.8 step 4, `merged` ticker event; 153 tests OK. Dry runs (check only): kalpa-docs #192, backbone #653 (floor hit on *.proto).
- Floor gap found by the dry run: WellMed migrations live in singular `internal/db/migration/` (7 repos); backbone #658, a tenant migration, passed the floor. Driver fix f7f3d30 adds `migration/` to the defaults; test fails without it; #658 now one-way.
- Review: pane `merges review` (unit 10.3).

#### Review loop (2026-10-27)
- r1 DO NOT SHIP 7 (advisory gate exit read as pass, lanes could merge, --admin past unreported checks, unreviewed commits before the review base, self-greening CI, gh error after merge, no-CI repos) → all fixed; r2 SHIP AFTER BLOCKING 6 (driver identity read from an env var herdr never sets; read-back head; app-bound checks; CI off the floor → own two-way list; SKIPPED/NEUTRAL; ruleset pagination) → fixed; r3 SHIP AFTER BLOCKING 5 = round-3 stop: --admin re-derivation drew findings 4 rounds running (convergence), lane identity reopened a third time (reframe proposed: identify lanes from dispatch-log, delete the herdr-name lookup) → decisions 83/84 to Alex.

---

## Plan 10.4: UI template, harness scorecard, herdr attention

### Resume Context (Plan 10.4)
**Status:** Phase 0 done; 4.1 → lane ui-packet, 4.2 → lane scorecard, 4.3 → lane attention
**Base:** ai-skills 361ae68 · dev-workbench ef9bae0

### Session: 2026-10-27
#### Phase 0 — ✅ DONE
- Same as 10.3. UI-packet skill guidance goes in scripts/README.md (plan/SKILL.md belongs to lane merges).
#### Tasks 4.1–4.3 (2026-10-27)
- 4.3 attention (dev-workbench `concurrency/10-attention`): 51bc628 → r1 SHIP AFTER BLOCKING (driver set goes stale) fixed 8156f8a (60 s ensure timer, off-anchor), da68dee, 22d954a → r2 SHIP, 2 findings fixed by driver 24a2418 (ensure quiet on a dead socket). Toast per-pane filtering not possible in herdr 0.9.1. TODO at integration: ai-skills herdr/SKILL.md — run `herdr-agent-view ensure` right after renaming to driver.
- 4.1 ui-packet: ai-skills 1c5531b (schema `ui` payload, packet.py --type ui, README "UI packets", demo tenant from `$DQ_UI_DEMO_TENANT`), dev-workbench b674bfd (side-by-side render, PNG-only + size re-checked server-side, CSP img-src data:, body cap 5 MB); fixture card screenshot `queue/docs/ui-card.png`. TODO at integration: declare `DQ_UI_DEMO_TENANT` (and `DECISION_QUEUE_URL`, `PACKET_POST_TIMEOUT`) in ai-skills `.env.example`. Review running (two repos, one pane).
- 4.2 scorecard (`concurrency/10-scorecard`): 064d26f..8cbc75c `scripts/harness-scorecard/`; §3.1 lineage table reproduced exactly on the 10-25 logs (291/153/99/43/20/15), suite 466 OK. Driver calls pending: include `~/.claude-int/projects` going forward (baseline layout counted `~/.claude` only); README/CLAUDE.md rows at integration. Review queued after the ui review (same unit log).
#### Review loops closed (2026-10-27)
- attention: r1 → r2 SHIP, all fixed (24a2418 driver).
- ui-packet: schema r3 (4 rejected: consumer pinned pre-unit / out-of-unit c1cdafc → TO-DO) → r6, r8 SHIP 0; queue r4 → r7 → r9 → r11 SHIP, last note deferred to TO-DO `[review 10.4-r11-01]`. Real-patient guard: packet.py requires tenant == $DQ_UI_DEMO_TENANT (a declaration check, worded as such); queue refuses ui unless DQ_UI_ALLOWED_TENANTS is set. Env vars declared in .env.example (c9be6d5).
- scorecard: r5 → r10 (reopen) → r12 (reopen chain) → REFRAME 486a443 fixed follow-up cohort → r13 SHIP, 3 fixed (36af6a5 cut = min(until, pull), e170c7b, 244ccb6). Baseline undercounted: a fresh pull finds 100 units / 683 reviews in the 10-25 window vs 86 / 622.
#### Phase-4 cutover (2026-10-27)
- `feature/10-phase4` worktrees: ai-skills merges ui-packet + scorecard (76d1da3, 5384660) + b2cfd26 (herdr driver step runs `herdr-agent-view ensure`; scorecard rows in CLAUDE.md + scripts/README.md); dev-workbench merges attention + ui-packet (253aa71, a25225f). Clean merges. dev-workbench: queue 72 passed (drift guard vs the merged schema), agent-view 30 checks OK.
