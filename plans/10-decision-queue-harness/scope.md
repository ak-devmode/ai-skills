# Decision-queue harness
**Project:** ai-skills  **Branch:** main (ai-skills commits direct to main); `feature/10-decision-queue` in dev-workbench  **Date:** 2026-10-25
**Created by:** Alex
**Scope folder:** ~/Projects/ai-skills/plans/10-decision-queue-harness/
**Source repo(s):** ~/Projects/ai-skills, ~/Projects/dev-workbench
**Primary repo (worktree):** none — multi-repo (skills in ai-skills, queue service in dev-workbench)
**Backlog:** none

## 1. Context

A 21-day log analysis across both machines (`artifacts/baseline-2026-10-25.md`) found that
the harness optimizes for closing review findings, a target with no ceiling. Review loops
plateau at ~1 blocking finding per round forever, `local-maxima` findings get patched instead
of reframed, and Alex types ~100 prompts a day, many of which are approvals or re-orientation
rather than decisions. This scope changes the target: **every lane ends in one of two states —
done, or a decision in Alex's queue** — and gives that queue a browser surface beside herdr.

## 2. Repo Graph

| Repo | Role | Trunk | Current Branch | HEAD SHA | SDK Pin | In Scope? | Notes |
|---|---|---|---|---|---|---|---|
| ai-skills | primary (skills, scripts) | main | main | 3db4084 | n/a | YES | standalone leaf; direct-to-main |
| dev-workbench | queue service + systemd/install | main | main | e68b4ce | n/a | YES | no CROSS-REPO.md |
| gstack | pattern source (`/browse`) | — | — | — | — | READ-ONLY | upstream-tracking, never edited |

**Drift flagged in Step 0.5:** dev-workbench has uncommitted `config/claude-code/settings.json`
and `config/codex/config.toml` changes, matching the open ai-skills TO-DO to land
`AI_SKILLS_REVIEW_MODE=full` on its `origin/main`. Resolve before 10.1 touches that repo.
**Snapshot taken:** 2026-10-25

## 3. ADR Alignment

No ADR matches — ai-skills has no ADRs, and the scope touches no WellMed/PMG architecture.

## 4. Phases

### 4.1 Phase 1 — Decision queue v1, usable today · gate D (deployed on homelab, observed live), then A

- **Packet** — one structured JSON object per decision: machine, workspace, agent, repo,
  branch, head sha, scope/unit, door (`one-way` / `two-way` / `info`), type, title, options with
  a recommendation, what it blocks, what the lane continues on, a type-specific payload, and a
  prefilled reply that opens with a lane tag `[lane <machine>/<workspace>/<agent>]`.
- **`scripts/packet.py`** (ai-skills) — `new` validates and writes to a local outbox, then POSTs
  when `DECISION_QUEUE_URL` is set; `close` (the lane closes its own packet when Alex's pasted
  reply arrives); `stale` (head moved past the packet's sha); `event` (ticker: done / merged);
  `check-reply` (refuses a reply whose lane tag isn't this lane's).
- **Queue service** (dev-workbench `queue/`) — Python + uv, PostgreSQL already on homelab, a
  systemd unit installed by `install.sh`, bound to the tailnet. One newest-first page with three
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
  one-way, never demote one.
- **Skill wiring** — `/plan` drivers and `/concurrency` lanes emit packets at one-way doors
  (`GATE-BLOCKED` becomes a packet). Any session may emit one. Seam: with no
  `DECISION_QUEUE_URL`, skills behave exactly as today (inline numbered questions).

### 4.2 Phase 2 — Review and verify re-pointed at decisions · gate C, concurrent with 10.3 and 10.4 (B)

- Exit rule: a round whose blocking findings land only on files already hit, or any
  `local-maxima` finding, stops the loop and emits a decision packet carrying the findings.
  Fresh blocking findings on new files keep looping, in any round.
- `[CASCADE]` and `[CONVERGENCE]` emit packets; `--reframed` disposition records the outcome
  (TO-DO item, folded in).
- Lineage fix: continue a lineage only when the range holds a fix named by an earlier
  disposition (P1 TO-DO, folded in).
- `/verify` run-cap STOP emits a packet instead of an inline question.
- Applies in lean and full modes, so teammates get the loop changes; packets publish only where
  the queue URL is configured.

### 4.3 Phase 3 — Driver merges · gate D (observe a driver-merged PR deploy to dev), concurrent (B)

- The `/plan` driver merges its own PR when CI is green, the checks show real runs (not
  skipped), and `door.py` finds nothing on the floor. Code repos merge to `develop`;
  kalpa-docs and pmg-docs merge to `main`.
- A floor hit becomes a packet. Lanes never merge, and GitHub auto-merge stays off.
- Each merge posts a ticker event. The prod gate (`prod-merge-gate.py`) is untouched.

### 4.4 Phase 4 — UI template, harness scorecard, herdr attention · gate A (Alex's verdict after live use), concurrent (B)

- UI-change template: "old" shot from deployed `develop` with `/browse`; "new" shot from the
  lane's FE dev server running against the dev gateway; demo tenant read from config; behaviour
  changes called out.
- Harness scorecard: the mining scripts become `scripts/harness-scorecard/` in ai-skills.
  Pull homelab logs, run the analyses, print the baseline tables and the delta against the
  last run.
- herdr attention: the `herdr-agent-view` attention filter stops counting finished lane agents,
  so only drivers that need Alex surface. Check whether herdr's native toast can filter per pane.

## 5. Architecture

```
  MBA sessions                          homelab sessions
  (drivers, lanes)                      (drivers, lanes)
       |                                      |
   packet.py new ----+              +---- packet.py new
   (outbox file      |  tailnet     |     (outbox file
    always)          v  HTTP POST   v      always)
                 +------------------------+
                 | queue service (python) |---- PostgreSQL (homelab, localhost)
                 | homelab, tailnet bind  |
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
  `[CONVERGENCE]` / `[CASCADE]`; the stop routes to the user, not to a packet.
- `ai-skills/review/SKILL.md` §5.1 — standing policy, round cap, the four stop conditions.
- `ai-skills/verify/SKILL.md` §3.9 — run cap at 2.
- `dev-workbench/config/herdr/helpers/herdr-agent-view` — `ATTENTION_FILTER` (blocked or done,
  any workspace).
- `dev-workbench/config/systemd/`, `install.sh` — symlinked service config for homelab.
- homelab2026: PostgreSQL on 127.0.0.1:5432, Python 3.14, uv, Docker; tailnet 100.87.171.87.
- gstack `/browse` — real-browser screenshots against a running URL.
- `artifacts/mining/` — the three analysis scripts behind the baseline.

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
- Review exit rule: diminishing returns (re-hits only, or a `local-maxima` finding), never a
  round count; fresh findings can keep coming in any round.
- The driver merges (develop for code, main for kalpa-docs and pmg-docs); never lanes, never
  GitHub auto-merge.
- Seam: skills work unchanged without `DECISION_QUEUE_URL`; teammates get the review-loop changes.
- Iterative v1, no polish; start wide and narrow during use.
- Overnight: ticker grouped by "since you last looked"; two-way cards wait for a look.
- Mining scripts become a re-runnable scorecard, not throwaway.
- Used live today; codex is out of credits on both accounts until later, so today's reviews run
  on the Claude fallback.
