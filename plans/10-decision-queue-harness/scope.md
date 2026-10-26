# Decision-queue harness
**Project:** ai-skills  **Branch:** `feature/10-decision-queue` worktree in ai-skills, cut over to main in one step (CEO review); `feature/10-decision-queue` in dev-workbench  **Date:** 2026-10-25
**Created by:** Alex
**Scope folder:** ~/Projects/ai-skills/plans/10-decision-queue-harness/
**Source repo(s):** ~/Projects/ai-skills, ~/Projects/dev-workbench
**Primary repo (worktree):** none — multi-repo (skills in ai-skills, queue service in dev-workbench)
**Backlog:** none

## 1. Context

A 21-day log analysis across both machines (`artifacts/baseline-2026-10-25.md`) found that
the harness optimizes for closing review findings, a target with no ceiling. Review loops
converge, but slowly: ~81% of fix work goes to non-blocking findings, each fix is new code for
the next round, and reframes almost never happen (22 of 4,044 dispositions; 85% of
`local-maxima` findings were patched). An early draft of this context claimed loops plateau
forever; that came from counting rounds per unit instead of per lineage (baseline §3.1). Alex types ~100 prompts a day, many of which are approvals or re-orientation
rather than decisions. This scope changes the target: **every lane ends in one of two states —
done, or a decision in Alex's queue** — and gives that queue a browser surface beside herdr.

## 2. Repo Graph

| Repo | Role | Trunk | Current Branch | HEAD SHA | SDK Pin | In Scope? | Notes |
|---|---|---|---|---|---|---|---|
| ai-skills | primary (skills, scripts) | main | main | 3db4084 | n/a | YES | standalone leaf; direct-to-main |
| dev-workbench | queue service + systemd/install | main | main | e68b4ce | n/a | YES | no CROSS-REPO.md |
| gstack | pattern source (`/browse`) | — | — | — | — | READ-ONLY | upstream-tracking, never edited |

**Drift flagged in Step 0.5:** dev-workbench has uncommitted `config/claude-code/settings.json`
and `config/codex/config.toml` changes. Corrected in eng review: they are Alex's "Webhost Service
Ops" allow rule plus a sensitive-targets carve-out, and codex-written trust entries and a model
nux counter — not `AI_SKILLS_REVIEW_MODE`. 10.1 adds the queue URL to the same `settings.json`,
so commit Alex's rule first.
**Snapshot taken:** 2026-10-25

## 3. ADR Alignment

No ADR matches — ai-skills has no ADRs, and the scope touches no WellMed/PMG architecture.

## 4. Phases

### 4.1 Phase 1 — Decision queue v1, usable today · gate D (deployed on homelab, observed live), then A

- **Packet** — one structured JSON object per decision: machine, workspace, agent, repo,
  branch, head sha, scope/unit, door (`one-way` / `two-way` / `info`), type, title, options with
  a recommendation, what it blocks, what the lane continues on, a type-specific payload, and a
  prefilled reply that opens with a lane tag `[lane <machine>/<workspace>/<agent> <packet-id>]`.
- **`scripts/packet.py`** (ai-skills) — `new` validates and writes to a local outbox, then POSTs
  when `DECISION_QUEUE_URL` is set; `close` (the lane closes its own packet when Alex's pasted
  reply arrives); `stale` (head moved past the packet's sha); `event` (ticker: done / merged);
  `check-reply` (refuses a reply whose lane tag isn't this lane's, or whose packet is closed,
  stale or another lane's).
- **Queue service** (dev-workbench `queue/`) — Python + uv, PostgreSQL already on homelab, a
  systemd user unit installed by `install.sh`, bound to 127.0.0.1:8787 and published by
  `tailscale serve` as HTTPS on homelab's MagicDNS name (a user unit cannot wait for the
  tailnet address at boot, and the copy button needs a secure context). One newest-first page with three
  densities: rich packet (one-way), compact card (two-way, vetoable until seen), ticker (done /
  merged) grouped by "since you last looked". Each card has its own URL, a header naming
  machine / workspace / agent, and an editable prefilled reply with a copy button.
- **Data-model template** first, in both styles to try: ERD with changed columns highlighted,
  and side-by-side before → after. A generic template covers every other type until it earns
  its own.
- **Door rule** — one-way stops and parks (`PARKED <packet-id>` marker in the pane); two-way
  continues with a compact card carrying a reversal-cost signal (commits stacked since).
  `scripts/door.py` classifies by a per-repo `.one-way-doors` file plus ai-skills defaults
  (migrations, protos/OpenAPI, ADRs, infra TF, SSM/env, prod). An agent may promote a door to
  one-way, never demote one. Editing `.one-way-doors` is itself one-way, judged against the
  file at the base revision, so a change cannot authorize its own removal.
- **Skill wiring** — `/plan` drivers and `/concurrency` lanes emit packets at one-way doors
  (`GATE-BLOCKED` becomes a packet). Any session may emit one. Seam: with no
  `DECISION_QUEUE_URL`, skills behave exactly as today (inline numbered questions).

**Hardening (CEO review, Alex 2026-10-25):**

- **Harness errors never stop Alex's other work.** A failed POST never parks anything: the
  packet goes to the outbox and the driver prints it in the pane with a `Blocked` note, then
  carries on with two-way work; the outbox flushes when the queue returns. A one-way door
  still stops, since that is a decision, not a harness error.
- **Packets post under the driver, one path for every lane.** Every lane (Claude, codex,
  review) writes its packet to an outbox in its worktree and prints `PACKET <id>`; only drivers
  POST, from their wait loop. Codex panes have no queue env or network and review panes are
  read-only, so one path serves all. The reply goes to the driver's pane.
- **door.py fails closed** (unparseable input = one-way) and counts renames and deletions of
  floor paths as hits.
- **Rendering is sanitized** (packets never inject HTML); a card that fails to render falls
  back to plain text, per card.
- **`packet.py touch`** refreshes a two-way card's reversal cost (commits stacked since).
- **"Reset timer"** button on the page sets the ticker's "since you last looked" mark.
- **Stats:** `GET /api/stats` returns machines seen, open / parked counts, time-to-answer and
  time-parked. Packets carry `schema_version`; client-generated packet ids make retries
  idempotent.
- `PARKED` joins the `/concurrency` §7.2 marker set so a driver's wait loop sees it.
- Lane identity outside herdr: machine + cwd + session id.
- DB credentials in a user-owned 0600 file on homelab, not SSM (the unit runs as the user).
  `tailscale serve` needs a one-time operator grant by hand; confirm `homelab-db-backup.timer`
  covers the new database. The page is bounded and `packet.py` POSTs with a 3 s timeout.
- **Build order today:** packet.py + service + compact card first, the data-model template
  second. ai-skills changes are built in a worktree and cut over to main in one step, then
  homelab pulls. Review records stamp a rules version, so a lineage started before the cutover
  finishes under the old rules while sessions keep running. dev-workbench merges its feature
  branch to main before `install.sh` runs on homelab.

### 4.2 Phase 2 — Review re-pointed at decisions · gate C, concurrent with 10.1 (B)

**Rewritten in CEO review (Alex 2026-10-25).** The first draft's exit rule (stop on re-hit-only
rounds or any `local-maxima` finding) is dropped: it rested on a miscount (baseline §3.1), it
could not close through the gate (deferral is refused before round 4), and fallback reviews
would have flooded the queue (120 `local-maxima` flags in 178 fallback reviews). The lever is
what the loop fixes and when it reframes. The existing round-3 and repeated-file stops in
`review.py convergence()` stay as they are, inline.

- **Findings budget.** Round 1 is uncapped: fix every finding that makes sense; that is where
  the meat is and where tokens are spent. From round 2, blocking findings are always fixed,
  should-fix findings are capped at the reviewer's top few, and notes are logged with at most
  one batch fix and no re-review. Gate change: notes may be `accepted` at any round.
- **Reframe prompt, every round from round 1.** The reviewer states whether a simpler design
  would remove several findings. A reframe is accepted only if it (i) meets the core
  objective from the plan and (ii) simplifies, naming what it deletes. A rejected reframe
  gets a one-line reason on the ticker.
- **Fresh judge.** A reframe is judged by a fresh agent that sees only the objective, the
  findings and the proposal, never by the driver whose design it is. The same role flags a
  finding that re-opens a decision Alex already made (121 of 264 rejections cited one), so it
  also reads scope §11, the Decisions Log and the lineage's earlier rejected reframes. It runs
  through `scripts/codex-exec.py`, as `verify/scripts/judge.py` does.
- **What reaches Alex from review**, as packets: (1) an accepted reframe that overturns a
  recorded decision or touches a one-way door; (2) a blocking finding that survived two
  rounds with no qualifying reframe; (3) a rejected reframe the reviewer proposes again.
  Everything else proceeds.
- **Fallback `local-maxima` flags are advisory**: logged, never a stop or a packet.
- **Round-1 effort bump, as a measured trial**: one tier above `verify_lib.effort_for` on a
  lineage's first review. Kept if blocking findings move to round 1 without more codex
  credit-outs (the fallback reviewer is the noisy one).
- **Lineage fix lands first** (P1 TO-DO, folded in). `review_lineage` still continues a lane's
  lineage into its next unit (`share = base == phead`), so new code is counted as round 4 or 5;
  every round-keyed rule here would misfire until it is fixed.
- `--reframed` disposition (TO-DO, folded in) records the outcome of an accepted reframe or a
  `[CASCADE]`. It cites the replacing commit, and the replacement is reviewed as a new lineage.
- `/verify` run-cap STOP emits a packet instead of an inline question.
- Applies in lean and full modes, so teammates get the loop changes; packets publish only where
  the queue URL is configured.
- Sequencing: everything here lives in `review.py` / `verdict-gate.py` / review SKILL.md and
  starts today in its own worktree; only the packet emission waits for 10.1's `packet.py`.

### 4.3 Phase 3 — Driver merges · gate D (observe a driver-merged PR deploy to dev), after 10.1's packet tooling

- The `/plan` driver merges its own PR when CI is green, the checks show real runs (not
  skipped), the gate verdict is SHIP or accepted, and `door.py` finds nothing on the floor.
  Code repos merge to `develop`; kalpa-docs and pmg-docs merge to `main`.
- A degraded review (fallback or lean) still merges to develop, flagged on the ticker. The
  driver may use `--admin` where branch protection requires it, under the same conditions —
  what Alex does by hand today.
- A floor hit becomes a packet. Lanes never merge, and GitHub auto-merge stays off.
- Each merge posts a ticker event. The prod gate (`prod-merge-gate.py`) is untouched.

### 4.4 Phase 4 — UI template, harness scorecard, herdr attention · gate A (Alex's verdict after live use), after 10.1's packet tooling

- UI-change template: "old" shot from deployed `develop` with `/browse`; "new" shot from the
  lane's FE dev server running against the dev gateway; demo tenant read from config; behaviour
  changes called out.
- Harness scorecard: the mining scripts become `scripts/harness-scorecard/` in ai-skills.
  Pull homelab logs, run the analyses, print the baseline tables and the delta against the
  last run. Rounds are counted per lineage through `review.py`'s own functions
  (`mining/lineage.py`), never by the unit's `r<n>`. Pasted replies are tagged so answer
  latency is measurable.
- herdr attention: the `herdr-agent-view` attention filter stops counting finished lane agents,
  so only drivers that need Alex surface. Check whether herdr's native toast can filter per pane.

## 5. Architecture

```
  MBA sessions                          homelab sessions
  (drivers, lanes)                      (drivers, lanes)
       |                                      |
   packet.py new ----+              +---- packet.py new
   (outbox file      |  driver      |     (outbox file
    always)          v  HTTPS POST  v      always)
                 +------------------------+
                 | queue service (python) |---- PostgreSQL (homelab, localhost)
                 | 127.0.0.1 + ts serve   |
                 +-----------+------------+
                             |
                    browser, any tailnet device
                    newest-first: packet | card | ticker
                             |
            Alex edits prefilled reply, copies it
                             |
                             v
         pastes into the named pane (machine/workspace/agent)
                             |
         lane: packet.py check-reply -> act -> packet.py close
```

## 6. What Already Exists

- `ai-skills/concurrency/SKILL.md` §7.2 — in-pane markers (`GATE-BLOCKED`, `PARTITION-DONE`);
  `GATE-BLOCKED <task> — <what Alex must do>` is the proto-packet.
- `ai-skills/review/scripts/review.py` — `convergence()` and `cascades()` already emit
  `[CONVERGENCE]` / `[CASCADE]`; `convergence()` stops at `ROUND_CAP` 3 with no SHIP and on a
  file hit in each of the last rounds (since 2026-10-18); `rounds()` / `review_round()` count
  per lineage.
- `ai-skills/scripts/verify_lib.py` `effort_for()` — review effort tiered by diff size.
- `ai-skills/review/SKILL.md` §5.1 — standing policy, round cap, the four stop conditions.
- `ai-skills/verify/SKILL.md` §3.9 — run cap at 2.
- `dev-workbench/config/herdr/helpers/herdr-agent-view` — `ATTENTION_FILTER` (blocked or done,
  any workspace).
- `dev-workbench/config/systemd/`, `install.sh` — symlinked service config for homelab.
- homelab2026: PostgreSQL on 127.0.0.1:5432, Python 3.14, uv, Docker; tailnet 100.87.171.87.
- gstack `/browse` — real-browser screenshots against a running URL.
- `artifacts/mining/` — the analysis scripts behind the baseline (`lineage.py` supersedes
  `reviews.py`'s round counts).

## 7. Table Identity Map

New database `decision_queue` on homelab PostgreSQL, write-owned by the queue service only.
No existing tables — every row below is a create.

| Table | Write-owner | Key columns | Read-by |
|---|---|---|---|
| `packets` | queue service | id, created_at, machine, workspace, agent, repo, branch, head_sha, unit, door, type, status, payload jsonb | queue page |
| `events` | queue service | id, created_at, packet_id null, kind (done / merged / closed / stale), machine, agent, body | queue page ticker |
| `views` | queue service | viewer, last_seen_at | "since you last looked" grouping |

| Table | Deviation | From | To | Rationale |
|---|---|---|---|---|
| `packets`, `events`, `views` | create | none | as above | new service; approve at handoff |

## 8. Inherited TO-DOs

| TO-DO item | Origin section | In / Out | Phase | Why |
|---|---|---|---|---|
| `review_lineage` continues a lineage whenever a range starts at a previous review's head (P1) | ai-skills TO-DO | In (auto) | 2 | same function the exit rule rewrites |
| A `[CASCADE]` stop has no way to record its outcome (`--reframed`) | ai-skills TO-DO | In (auto) | 2 | a cascade packet needs this disposition |
| Land `AI_SKILLS_REVIEW_MODE=full` on dev-workbench `origin/main` | ai-skills TO-DO | Out | — | repo hygiene, not harness design; surfaced as drift in §2, resolve before 10.1 |

## 9. NOT in Scope

- Sharing cards with people outside the tailnet. Later path: a claude.ai artifact with PHI
  scrubbed, rather than a public endpoint.
- Per-lane runtime isolation (database or full stack per lane).
- Swapping the codex review model.
- Widening Claude Code permissions.
- Any change to the prod merge gate.
- GitHub auto-merge, and lanes merging.
- Token-only levers that don't fall out of the frame. Alex: they haven't helped; not weighed.
- Auth on the queue API: tailnet-only, nobody else is on it.
- Lanes polling the queue for replies: the return path is paste-back.
- Extending the floor to non-commit one-way actions (SSM writes, prod): existing permissions
  and `prod-merge-gate.py` already block them.

## 10. Skill Sequence

### 10.1 Plan Reviews

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 1 | /plan-ceo-review | **YES** | 1st | Challenge the frame before building |
| 2 | /plan-eng-review | YES | 2nd | Service, packet schema, skill seam, door floor |
| 3 | /plan-design-review | OPTIONAL | 2nd | Information design of the cards; no polish wanted in v1 |
| 4 | /plan-devex-review | OPTIONAL | 2nd | `packet.py` / `door.py` are consumed by agents and teammates |

### 10.2 Implementation Support

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 5 | /investigate | N/A | — | Not a bug fix |
| 6 | /design-consultation | N/A | — | Internal tool, no design system needed |
| 7 | /design-html | OPTIONAL | 10.1 | For the queue page and card templates |
| 8 | /design-shotgun | OPTIONAL | 10.1 | The two data-model diagram styles |

### 10.3 Review & QA

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 9 | /review | YES | Every phase | Codex out of credits today ⇒ fallback |
| 10 | /health | OPTIONAL | After impl | |
| 11 | /qa | OPTIONAL | 10.1 | Queue page on the tailnet |
| 12 | /qa-only | YES | Every phase | Unit tests for `packet.py`, `door.py`, service |
| 13 | /browse | YES | 10.1, 10.4 | Verify the page renders; UI-template screenshots |
| 14 | /devex-review | N/A | — | No onboarding surface beyond the skills |
| 15 | /setup-browser-cookies | OPTIONAL | 10.4 | Dev FE login for "new" screenshots |

### 10.4 Ship & Post-ship

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 16 | /ship | N/A | — | Not in use; promotion is /review → PR → merge → /closeout |
| 17 | /document-release | YES | 10.2 | Team announcement of the review-loop change |
| 18 | /retro | OPTIONAL | End | The scorecard re-run is the retro |

## 11. Key Decisions Captured

- Frame: every lane ends **done or decision**; approvals that aren't decisions never reach Alex.
- Doors: one-way stops, two-way continues and stays vetoable until seen; deterministic floor
  per repo; agents promote, never demote.
- Queue lives on homelab, written over the tailnet from both machines; no SSH from homelab to
  the MBA.
- Return path is a prefilled, editable reply Alex pastes into the named pane; the lane checks
  the tag and closes its own packet.
- Packets are structured; the service renders them. Agents don't author free-form HTML.
- Data-model is the first rich template; both diagram styles get tried in live use.
- Review: round 1 uncapped; from round 2 a findings budget (blocking always, should-fix
  capped, notes logged); a reframe prompt every round judged by a fresh agent on objective +
  simplification; three cases reach Alex. Supersedes the draft's diminishing-returns exit
  rule (CEO review).
- The driver merges (develop for code, main for kalpa-docs and pmg-docs); never lanes, never
  GitHub auto-merge.
- Seam: skills work unchanged without `DECISION_QUEUE_URL`; teammates get the review-loop changes.
- Iterative v1, no polish; start wide and narrow during use.
- Overnight: ticker grouped by "since you last looked"; two-way cards wait for a look.
- Mining scripts become a re-runnable scorecard, not throwaway.
- Used live today; codex is out of credits on both accounts until later, so today's reviews run
  on the Claude fallback.
- Harness errors never stop Alex: a dead queue prints `Blocked` in the pane and work continues.
- Driver merges include degraded reviews (flagged) and `--admin` under the same conditions.
- Queue address (eng review): 127.0.0.1 behind `tailscale serve`, HTTPS on the MagicDNS name.
- One packet path (eng review): every lane writes an outbox and prints `PACKET <id>`; drivers POST.
- Cutover (eng review): review records stamp a rules version; old lineages finish on old rules.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|---|---|---|---|---|---|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | DONE (HOLD SCOPE) | outside voice: 1 critical, 8 high, 9 medium, 4 low; 18 decisions (42–59) |
| Outside voice | in-host Claude Plan agent | Independent challenge | 1 | DONE (codex unavailable, out of credits) | baseline miscount confirmed in code; gate close-out gap confirmed |
| Eng Review | `/plan-eng-review` | Architecture & tests | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | optional | — |

- **Baseline corrected:** rounds were counted per unit; the gate counts per lineage. 13% of
  reviews are at lineage round ≥4 (not 64%); `local-maxima` flags are a fallback-reviewer habit
  (120/178 vs codex 11/398). Baseline §3.1, `mining/lineage.py`.
- **Phase 2 rewritten:** exit rule dropped (miscount, no gate close-out path, would flood the
  queue); replaced by a findings budget (round 1 uncapped), a per-round reframe prompt judged by
  a fresh agent, three review cases to the queue, and a round-1 effort trial.
- **Phase 1 hardened:** non-blocking queue failure, packets posted under the driver, door.py fails
  closed, sanitized rendering, `/api/stats`, `PARKED` marker, idempotent ids, worktree cutover.
- **Phase 3:** merge condition adds the gate verdict; degraded reviews merge flagged; `--admin`
  allowed under the same conditions.
- **Sequencing:** 10.3 and 10.4 follow 10.1's packet tooling; 10.2 runs concurrent with 10.1.
- **Not adopted:** reply polling (paste-back chosen), queue API auth (tailnet-only), floor for
  SSM/prod actions (permissions + prod hook cover them).
- Finish table rev 2 awaits Alex's approval.

**VERDICT:** CEO CLEARED (HOLD SCOPE) — eng review required next.

NO UNRESOLVED DECISIONS
