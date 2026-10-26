# Eng review — scope 10 decision-queue harness (2026-10-25)

**Target:** `plans/10-decision-queue-harness/scope.md` + plan stubs 10.1–10.4 (post CEO review, `34fa127`).
**Outside voice:** codex `gpt-6.1-sol` on the integrations account (default account out of credits).
**Design doc:** none; scope.md + CEO review stand in for it (/office-hours skipped).

## 1. Scope Challenge

Complexity: ~30 changed files across two repos; new components: queue service, `packet.py`,
`door.py`, reframe judge, scorecard. The gate trips, but no smaller arrangement keeps the
approved feature set. Two simplifications fall out of the findings below (`tailscale serve`
instead of a tailnet bind; the reframe judge reuses `codex-exec.py`), both carried as decisions.
**Result: scope accepted as-is.**

Reality rows:

- REALITY: premise-table finding — scope §2 drift description wrong (see 2.4); unverified=0 after probes · dev-workbench `git diff`
- REALITY: already-done finding — `fc6e301` (10-18) added lineage rounds but the P1 TO-DO bug is still live · `scripts/verify_lib.py` `review_lineage` (`share = base == phead or ...`)
- REALITY: surface-check pass — `herdr pane wait-output --match` (`concurrency/SKILL.md:235`), `finish-table.py add/approve --help`, `tailscale` 1.102.3 on homelab (`serve` available, no config)
- REALITY: binding-decisions pass — CEO answers 42–59 and scope §11; nothing reintroduced · `scope.md` §11
- REALITY: numbers pass — baseline §3.1 [measured: `mining/lineage.py`]; r2+ non-blocking ≈1,370 findings [measured: derived from §3.1 rows]
- REALITY: deferred-asks pass — no linked issue
- REALITY: pr-count pass — ai-skills direct to main; dev-workbench one feature branch → main

## 2. Architecture

2.1 [P1] (9/10) **Tailnet bind from a user unit.** homelab services are systemd *user* units
(`~/.config/systemd/user/herdr-*.service`, `Linger=yes`); a user unit can't order after the
system `tailscaled.service`, so binding `100.87.171.87` races boot. And `navigator.clipboard`
needs a secure context: over plain `http://100.x` the copy button doesn't exist. Fix: bind
`127.0.0.1:8787`, expose with `tailscale serve --bg 8787` (HTTPS on the MagicDNS name, kept by
tailscaled). [Layer 1] → **Decision 62.**

2.2 [P1] (9/10) **Lineage bug gates the findings budget.** `review_lineage` continues a lineage
when `base == phead`, so a lane's next unit is counted as a continuation (P1 TO-DO, still live).
The budget keys on lineage round, so it would cap a first review of new code. Fix: the lineage
fix lands first in 10.2. Folded (sequencing). Note: the baseline's per-lineage depth inherits
this overcount, so true depth is lower still.

2.3 [P2] (8/10) **Packet hand-off path.** Codex lanes and read-only review panes already route via
the driver (answers 42/51). Uniform rule: every lane writes the packet to an outbox in its
worktree and prints `PACKET <id>`; only drivers POST. One identity, one code path, no env or
network needed in lanes. → **Decision 63.**

2.4 [P2] (9/10) **Scope §2 drift is mis-described.** Actual drift: an Alex-authored "Webhost
Service Ops" allow rule in `config/claude-code/settings.json`, plus codex-written trust entries
and a model-nux counter in `config/codex/config.toml` (codex rewrites that file; it recurs). Not
`AI_SKILLS_REVIEW_MODE`. Task 1.6 writes `DECISION_QUEUE_URL` into the same settings.json env
block, so the drift is directly in the path. Factual correction; human step stands.

2.5 [P2] (7/10) **Backups.** `homelab-db-backup.timer` exists; confirm it covers a new database.
Folded into Task 1.3.

2.6 [P2] (9/10, codex) **Credentials.** "Root-only file" contradicts user units. Fix: a
user-owned `0600` file read by the unit. Folded (factual).

2.7 [P1] (8/10, codex) **door policy can authorize its own removal.** Fix: a change to
`.one-way-doors` is itself one-way, and classification uses the base revision's policy. Folded
under answer 44 (fail closed).

2.8 [P2] (8/10, codex) **In-flight sessions see new scripts at cutover.** Skills symlink into the
main checkout (`setup.sh:103`), so a worktree protects development, not running sessions. →
**Decision 65.**

## 3. Code quality

3.1 [P2] (8/10) **Reframe judge reuses existing dispatch.** `scripts/codex-exec.py` (every failure
→ a `none …` line, tested by `test_codex_exec.py`) and `verify/scripts/judge.py`'s
prepare → codex/claude-fallback → record pattern already exist. Second caller, same contract.
Folded.

3.2 [P1] (9/10, codex + mine) **Over-cap should-fix has no disposition.** Deferral is refused
before round 4 (`review.py` dispose, `rnd <= ROUND_CAP`), and a real defect can't honestly be
rejected or accepted. Fix: cap what the reviewer *reports*, not what gets fixed: from round 2 it
returns all blocking, at most N should-fix in priority order, and notes. Nothing over-cap exists
to dispose. → **Decision 64: superseded — no cap at all** (Alex 2026-10-26; later-round findings are mostly defects in fixes, baseline §3.2–3.3). The close-out gap goes with the cap.

3.3 [P2] (8/10) **Notes.** Disposed `accepted` at any round (gate change), fix optional in the
same commit, no re-review. Folded under answer 54.

3.4 [P1] (8/10, codex) **`--reframed` could skip review of the replacement.** The replacement is
new code: it starts its own lineage at round 1 and is reviewed normally; `--reframed` closes only
the old findings and must cite the replacing commit. Folded.

3.5 [P2] (8/10, codex) **Judge needs the decision record.** It also flags findings that reopen
Alex's decisions, so it receives scope §11 and progress.md's Decisions Log alongside objective,
findings and proposal. Still no narrative. Folded.

3.6 [P2] (8/10, codex) **Reply binds to a packet, not just a lane.** The prefilled reply carries
the packet id; `check-reply` rejects a closed or stale packet and a second packet's reply. Folded.

3.7 [P2] (7/10, codex) **Repeated-finding identity.** Finding ids regenerate per review
(`review.py:649`). "Blocking finding surviving two rounds" uses the existing file-streak signal
(`convergence()` REPEAT); a re-proposed reframe is detected by the judge, which receives the
lineage's rejected reframes. Folded.

## 4. Tests

Framework: stdlib `unittest` in `scripts/tests/` (ai-skills); `pytest` via uv in `queue/`
(dev-workbench, new).

```
CODE PATHS                                         USER FLOWS
[+] scripts/packet.py (new)                        [+] Answer a one-way packet
  |-- new: valid -> outbox + POST  [GAP]             |-- [GAP][->E2E] card -> edit reply -> copy -> paste
  |-- new: queue down/timeout/non-2xx                |     -> check-reply -> close (finish row p1-reply-roundtrip)
  |     -> Blocked line, exit 0    [GAP]             |-- [GAP] copy button on HTTPS (secure context)
  |-- new: retry same client id -> one row [GAP]     |-- [GAP] stale reply (head moved) refused
  |-- check-reply: wrong lane / closed /           [+] Lane emits, driver posts
  |     other packet -> refused    [GAP]             |-- [GAP] lane outbox + PACKET marker -> driver
  |-- touch / stale / event / flush [GAP]            |     wait loop matches -> POST
[+] scripts/door.py (new)                          [+] Overnight
  |-- floor path -> one-way        [GAP]             |-- [GAP] Reset timer regroups ticker
  |-- agent two-way on floor -> one-way [GAP]      [+] Queue down
  |-- rename/delete of floor path  [GAP]             |-- [GAP] driver prints Blocked, keeps working
  |-- .one-way-doors edited -> one-way, base policy [GAP]
  |-- unparseable range -> one-way [GAP]
[+] queue/ service (new)
  |-- POST /packets idempotent, schema-refused [GAP]
  |-- GET / bounded, three densities, escaped [GAP]
  |-- GET /p/<id>, /api/stats      [GAP]
  |-- broken card -> plain-text fallback [GAP]
[+] review.py / verdict-gate.py (changed)
  |-- lineage: u2 after u1 fix -> r1; fix re-review -> +1 [GAP] (TO-DO test)
  |-- no should-fix cap; round-aware prompt fill  [GAP]
  |-- note accepted at any round passes gate      [GAP]
  |-- --reframed cites replacing commit           [GAP]
  |-- `reopens` chain of two -> chain stop, reframe [GAP]
  |-- REGRESSION: blocking never accepted/deferred [★★★ test_review.py]
  |-- REGRESSION: should-fix deferral refused <= r3 [★★★ test_review.py]
  |-- reframe prompt + judge decisions            [GAP][->EVAL] replay baseline lineages (p2-exit-rule-replay)
[+] verify_lib.effort_for bump, every round      [GAP]

COVERAGE: 2/31 paths tested (new code) | GAPS: 29 (1 E2E, 1 eval)
```

Regression contract (existing behaviour, no question needed): blocking findings still can't be
accepted or deferred; should-fix deferral stays refused through round 3; every existing
`test_review.py` / `test_verdict_gate.py` case stays green. Intended changes: notes acceptable at
any round; no should-fix cap at any round; round-aware prompt with `reopens`; fix-discipline chain stop; `--reframed`.

## 5. Performance

5.1 [P3] (8/10) Lineage resolution runs git per review pair; the scorecard over 86 units took
10+ min. Fine for a periodic scorecard; per-dispose cost is one unit. No action.

5.2 [P2] (8/10) Queue page lists newest-first unbounded. Bound to the last 7 days (or 200 rows),
index `created_at`. `packet.py` POST timeout 3 s. Folded.

## 6. Outside voice (codex)

9 findings, all verified against code: 1 (over-cap close-out) → Decision 64; 2, 3, 4, 5, 6, 7 →
folded above; 8 → Decision 65; 9 (cost by round) → evidence: r1 holds ~56% of findings; r2+
non-blocking ≈1,370 findings, about a third of the total, which is what the report cap removes,
plus their re-reviews. Alex's round-1 decision stands.

## 7. Failure modes

| Path | Failure | Handled | User sees |
|---|---|---|---|
| packet POST | queue/DB down | Blocked line, outbox flush | pane line, work continues |
| tailscale serve | tailscaled down | same as above | same |
| reply paste | wrong pane / stale | check-reply refuses | refusal in pane |
| door.py | parse error | one-way | lane parks |
| judge | codex out of credits | claude-fallback, then `none` | DEGRADED header |
| cutover | session mid-review | rules-version stamp (65) | old lineage finishes on old rules |

No silent critical gaps once the folded fixes land.

## 8. Parallelization

| Step | Modules | Depends on |
|---|---|---|
| A. packet/door + schema + skill wiring | ai-skills `scripts/`, `schemas/`, plan/concurrency/herdr SKILL | — |
| B. queue service + unit + install | dev-workbench `queue/`, `config/systemd/` | schema from A (fixture copy ok) |
| C. lineage fix → budget → reframe judge → effort trial | ai-skills `review/`, `scripts/verify_lib.py`, `scripts/verdict-gate.py` | — |
| D. review/verify packets | `review/`, `verify/` | A, C |

Lanes: A, B, C in parallel (three worktrees). D after A and C. 10.3 / 10.4 after A.
Conflict flag: A and C both add files under `scripts/tests/`; new files only, no shared edits.

## 9. Implementation tasks

- [ ] **T1 (P1, CC ~10 min)** queue — bind 127.0.0.1, expose via `tailscale serve` (adopted 62)
- [ ] **T2 (P1, CC ~20 min)** review — lineage fix first; budget waits on it (2.2)
- [ ] **T3 (P1, CC ~20 min)** review — no should-fix cap; round-aware prompt (round + prior findings/dispositions), `reopens` field, round 1 every defect + class-level fixes (64 dropped, 69)
- [ ] **T4 (P1, CC ~15 min)** door — `.one-way-doors` self-protection, base-revision policy (2.7)
- [ ] **T5 (P1, CC ~15 min)** review — `--reframed` cites replacing commit; replacement reviewed as new lineage (3.4)
- [ ] **T6 (P2, CC ~15 min)** packet — reply carries packet id; check-reply rejects closed/stale/other (3.6)
- [ ] **T7 (P2, CC ~10 min)** lanes — outbox + `PACKET` marker; drivers POST (adopted 63)
- [ ] **T8 (P2, CC ~10 min)** judge — reuse `codex-exec.py`; feed scope §11 + Decisions Log + prior rejected reframes (3.1, 3.5, 3.7)
- [ ] **T9 (P2, CC ~5 min)** queue — user-owned 0600 creds; confirm backup coverage; bounded page; 3 s POST timeout (2.5, 2.6, 5.2)
- [ ] **T10 (P2, CC ~10 min)** cutover — rules-version stamp on review records (65)
- [ ] **T11 (P3)** scope §2 drift text corrected (2.4) — done in scope.md
- [ ] **T12 (P1, CC ~20 min)** review — fix discipline in SKILL.md §5 + `reopens` chain stop in review.py (72)

## 10. Decisions

- 62 tailscale serve — **adopted** (Alex 2026-10-26). Probe: tailnet has no HTTPS certs (`CertDomains` empty) and homelab has no operator set, so two one-time human steps; finish table rev 3 (URL `https://homelab2026.taild4682e.ts.net`) pending re-approval
- 63 uniform outbox — **adopted** (Alex 2026-10-26)
- 64 reviewer report cap N — **dropped**: no should-fix cap; round-aware prompt instead (Alex 2026-10-26)
- 65 cutover rule — **adopted**: rules-version stamp on review records (Alex 2026-10-26)
- 67 kill the original analysis run — done
- 68 no should-fix cap at any round — **adopted** (supersedes 64)
- 69 round-aware review prompt (round + prior findings/dispositions; `reopens`; round 1 every defect, class-level fixes) — **adopted**
- 70 sample later-round findings — done, baseline §3.3
- 71 prettier queue URL — **declined**, keep the MagicDNS name
- 72 fix discipline (class + siblings; fail closed by default unless a stated reason; regression test fails with fix reverted; tests before re-review; `reopens` chain of two stops patching) — **adopted**
- 73 split large round-1 reviews into several codex passes — **declined** (codex credits; effort beats splitting)
- 74 effort bump on every round, compared by bucket — **adopted** (Alex 2026-10-26)

## 11. Session 2 evidence (2026-10-26)

- Later rounds review the fixes: 81% of codex's later reviews are fix-only ranges and 80% of
  their findings sit on the fix's own lines (baseline §3.2, `mining/infix.py`).
- Fix code draws ~4× the findings per changed line of round 1 (0.53 vs 0.13 per 100 lines);
  of 40 sampled: 23 new defects in the fix's own code, 14 original defects not fully fixed,
  3 tests that pass with the bug restored (baseline §3.3, `mining/fixpairs.py`).
- gstack 1.91.226 pulled: its `/review` now re-reviews only fix commits with a final full pass
  (ours already does fix-only ranges; final full pass not adopted). Its engine now rates
  CRITICAL / INFORMATIONAL only, so the Claude fallback maps INFORMATIONAL to should-fix and
  process-only to note (folded into T3).
- `lineage.py` called `review_round()` per review, re-running `rounds()` each time (quadratic in
  git calls); fixed to one call per unit. The 10.4 scorecard inherits the fix.

