---
name: concurrency
version: 0.9.0
description: |
  ONE responsibility: map what can run in parallel and what cannot, against a
  clear set of rules — re-derived from repo ground truth on every run, never
  from a scope's dependency claims. Then dispatch each parallel unit to a
  visible, named herdr pane running the right model seat (Opus / Sonnet / codex / GLM)
  and supervise by agent state plus in-pane status markers the supervisor reads. The single
  controlled home for no-human-in-the-loop agent trains. Use when asked to
  "/concurrency", "dispatch this scope concurrently", "run these phases in
  parallel", "start an agent train", or "herd this scope". It first judges
  whether parallelism is worth it (recommends plain /plan if not), recommends
  where each lane runs (this machine or homelab2026, and which account) from
  usage headroom, job size and Alex's plans, shows the dispatch plan, and asks
  once inline before dispatching — no separate flag, refuse-to-parallelize by
  default. Do NOT use for
  single-task work or as a substitute for /plan; this skill consumes /scope
  and /plan output, it does not replace them.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Agent
---

# /concurrency — herdr-backed multi-agent dispatch

Design record: `plans/archive/3-concurrency/scope.md` (ai-skills, archived).

## 1. Operating tiers

- **Active tier** — the invoking session (one of Alex's 2–4 primaries)
  dispatches 1–N small panes it supervises. Default tier.
- **Overnight tier** (`--overnight`) — one long task in auto mode, unattended
  overnight. Procedure in §11.

## 2. Preconditions — check ALL before anything else

- [ ] Load the `herdr` skill (workflow layer: naming, worktree lifecycle, worker
      launch/trust, layout, routing) AND run `herdr --skill` (raw CLI mechanics).
      This skill = WHAT to dispatch; the `herdr` skill = the workflow; `herdr
      --skill` = the raw CLI. The `herdr` skill's §1 preconditions (server up, in a pane)
      must pass.
- [ ] Target repo identified, trunk known (`develop` for wellmed/pmg, `main`
      otherwise), `git fetch` run. Never dispatch from a dirty primary tree
      without surfacing it first.
- [ ] For the GLM seat only: the OpenRouter key resolves from Keychain
      (`security find-generic-password -s openrouter-api-key -w` — check
      LENGTH only, never print). Absent ⇒ GLM rows in the plan are marked
      `seat-unavailable`, never silently rerouted. Env-leak rule and GLM
      launch traps: `herdr` §6.

## 3. Model routing table

**Lives in the `herdr` skill §6 — the single source.** Seats: `opus`, `sonnet`,
`codex`, `glm`; launch commands, route-to guidance, the env-leak rule, and the GLM launch
traps are all there. Never copy the table back here — a second copy drifts, and
both copies calling themselves canonical is how it did.

## 4. Partition procedure — ONE responsibility

This skill maps what can run in parallel and what cannot, against the rules
below. It does not plan, review, or execute the tasks themselves.

Input: a scope folder (plan stubs + PLANS-INDEX row) or an explicit task list
— treated as HYPOTHESES only.

**4.0 Evidence rules — never take the scope's word for it.** Every
classification is re-derived from ground truth on every run: no cached DAG,
no trust in a prior run, no trust in stub prose.
- Claimed "done" / "already exists" ⇒ content-grep `origin/<trunk>` after a
  fetch (done means written). Claimed "missing" ⇒ same grep (landed ≠ absent).
- Claimed touch-set ⇒ derive the real one by grepping the code the task names
  (files, tables, protos, routing keys). The derived set wins on conflict.
- Claimed blocker ⇒ verify it still blocks — a gate may have been passed
  since the stub was written. Claimed independence ⇒ verify nothing landed
  since that couples it.
- External gates (vendor sandboxes, credentials, prod state) that cannot be
  verified read-only from here: classify on recorded evidence (progress
  files, git log since the claim date) and stamp the verdict
  `UNVERIFIED-EXTERNAL` — visible in the output, never silently trusted.
- All checks read-only and bounded; estimate a sweep's cost before running it
  wide.

**4.1 Classify every task** into exactly one of:
- `HUMAN-GATED` — needs an action only Alex can take (credential/sandbox
  renewal, prod decision, sign-off), with the gate CONFIRMED still unmet per
  4.0. Surfaced in the plan; NEVER dispatched to a worker pane. The DRIVER
  runs its credential-free parts (inventories, config drafts, read-only
  probes) and surfaces only the true gate to Alex. A worker cannot ask
  anyone, so a human-gated task parked in a worker pane just blocks where
  nobody sees it.
- `BLOCKED` — a verified edge to an incomplete task (see 4.2).
- `READY` — all edges verified satisfied, no human gate.

**4.2 Build the dependency DAG.** Edges come from, in order of authority:
1. Repo-derived touch-set overlap (per 4.0): any overlap ⇒ same partition
   (serialized), never parallel branches over shared files.
2. Domain ordering rules (always edges, even when every document is silent):
   emitter before consumer; schema leads code; gRPC implementer leads caller.
3. Stub/index dependency claims — only those that SURVIVED 4.0 verification.
4. **Uncertain ⇒ serialize.** Refuse-to-parallelize is the default verdict;
   a pair joins the parallel set only when disjointness is SHOWN.

Every entry in the output carries its evidence (`evidence: <grep/commit/
check, or UNVERIFIED-EXTERNAL>`) so the verdict is auditable.

**4.3 The dispatch set** is the DAG's ready frontier, capped (§6). Everything
else is listed with the edge or gate that excludes it — exclusions are part
of the output, not silent.

## 5. Evaluate, present the plan, then ask once (no flag)

**5.0 Is concurrency even worth it?** Before presenting anything, judge the ready
frontier (§4.3). If it is empty or holds a single unit — everything else
serialized, human-gated, or blocked — parallelism buys nothing here. Say so and
bail to sequential; do NOT ask, do NOT dispatch:

```
CONCURRENCY — <scope> @ <repo>
Not worth parallelizing: <one-line reason, e.g. "only 91.2 is ready; 91.1 human-gated, rest serialized on shared touch-set">.
Recommend: run this with /plan sequentially.
```

**5.1 Where does this run — recommend each lane's machine and account.** Two
machines (this MacBook Air and homelab2026) and two accounts per seat (Alex's and
integrations — dev-workbench `config/accounts/accounts.tsv`; scope 3). Placement is a
recommendation that rides the §5.2 confirmation, never a silent choice.
1. **Facts — a script, not a guess:** `~/Projects/ai-skills/scripts/placement.py
   recommend --seat <opus|codex>`. It reads the usage herdr-usage merges from both
   machines (`~/.cache/herdr-usage/merged.json`, schema 1), checks each machine answers
   (`herdr --machine`) and each account's login is live there, and ranks by headroom.
   An inferred window (its reset passed since the last fetch) or one older than 15 min
   is unknown headroom, not free headroom, and the output says so; an unreachable
   machine, a dead login or an exhausted seat is never recommended. The `glm` seat bills
   OpenRouter, not an account — place it on CPU alone.
2. **Judgment on top:** job size and duration (a long or CPU-heavy lane — Go/Node
   builds, DB suites — goes to the box, which lifts the MBA's CPU cap, §9.3); what Alex
   has said he is doing (leaving or moving the MBA within hours ⇒ long jobs off the MBA;
   do not ask when he has said nothing); spread a train across accounts rather than
   draining one. Ties go to the account's home machine (the script already orders them).
3. **Box gates — check before recommending the box:** the box builds from its own clone,
   so the commit the lane's brief builds on must be on origin. That base is
   `origin/<trunk>` for a fresh lane — which passes by construction — or the driver's
   HEAD / scope branch when the lane needs work not yet on trunk; check the real one:
   `placement.py check-base --repo <repo> --base <that commit>` (exit 1 ⇒ place the lane
   locally or ask Alex to push — never push yourself). Then fetch the box's clone, quoting
   the command so `~` expands on the box: `ssh <box> 'git -C ~/<repo path under $HOME>
   fetch -q origin'`.
4. **Seat — the cheapest that can do the lane** (`herdr` §6.2). A lane that applies a
   known pattern goes to `sonnet`; `opus` only when the brief needs judgment, and the
   plan line says why. When `placement.py` shows both Claude accounts low, offer
   `codex`/`glm` for the mechanical lanes instead of draining the last headroom.
5. **Show it:** every lane line in the §5.2 plan carries `machine=` and `account=` with
   the deciding reason, and any unknown headroom is stated, not hidden. Alex's one
   `[y/N]` confirms placement too; an override ("lane 2 local") re-prints the plan and
   asks again.

**5.2 Otherwise, present the plan and ask once, inline.** Print this shape and
wait for a single confirmation — there is NO separate flag and NO re-invocation:

```
CONCURRENCY PLAN — <scope> @ <repo>
ready frontier (cap N):
  <task>  seat=<seat>  machine=<host>  account=<display>  (<why: headroom / size / plans>)
          branch=concurrency/<scope>-<task>  worktree=<path>
          pane label: <task> @<seat>
excluded:
  <task>  HUMAN-GATED: <what Alex must do>
  <task>  BLOCKED by <task>: <edge reason>
  <task>  SERIALIZED with <task>: <shared touch-set>

Proceed? [y/N]
```

Refuse-to-parallelize (§4, rule 4) still governs what reaches the frontier — the
inline `[y/N]` replaces the old two-step ceremony (dry-run, then a separate
`--dispatch` re-run), it does not remove the human veto. Invoking `/concurrency`
is itself the authorization to dispatch (per CLAUDE.md, a skill with `Agent` in
allowed-tools *is* a dispatch request); the prompt is the last look, not a second
opt-in. On anything but an explicit `y`, stop without dispatching.

## 6. Dispatch — on `y` from §5.2 (3x2 panes per lanes tab, ~6 lanes total — §9.3)

Per partition, in this order (syntax authority: `herdr --skill`):
1. `herdr worktree create --cwd <repo> --base origin/<trunk>
   --branch concurrency/<scope>-<task>` — no `--env`, for any seat (the glm
   override is inline in its launch command; `herdr` skill §6). Workspace label = run name only (`<scope> run`); seat identity
   goes on the PANE per the `herdr` skill §2 (naming).
1b. **Layout + naming: `herdr` §5 and §2.** Agents go in a new `<scope> lanes` tab in the
   driver's workspace (3x2 max, column by column), never in Alex's main tab and never left
   in the worktree's own workspace: move the created root pane into its slot. Pane identity in one call
   (rename + sidebar metadata, read back): `~/Projects/ai-skills/scripts/herdr-pane.sh name <pane> <task> <seat>`
   (`--machine <host>` for a box pane).
2. Launch the seat's command (§3) in the created pane via `pane run` — under the placed
   account: `claude-<account>` / `codex-<account>` (`herdr` skill §6), on either machine.
   claude/glm workers append `--dangerously-skip-permissions` (`herdr` skill §4: clears the
   fresh-worktree trust dialog + tool prompts; safe via worktree +
   no-push isolation). Never on the driver.
3. First instruction in every dispatched prompt: the task brief, then: commit locally when done; NEVER push,
   NEVER open a PR, NEVER merge; end by printing `PARTITION-DONE <task>`.
   Every seat additionally gets the §7.2 in-pane reporting instruction
   (`GATE-PASSED` / `GATE-BLOCKED` / `FIX-DONE` printed in its own pane, **never
   SendMessage**), and every brief includes: "If you need a helper terminal or sub-agent pane,
   run `~/Projects/ai-skills/scripts/herdr-pane.sh helper` (splits your OWN pane right at half
   size, prints its id) — never a new workspace, never split down (down is
   reserved for primaries)."
   Every brief also carries the output rule (`herdr` §6.2): "Keep tool output small —
   every token you read is re-read on every later turn. Run tests and lint with
   quiet or failures-only flags and pipe through `| tail -40`; grep logs instead of
   printing them; read files by line range; never dump a full suite, diff or lint
   report."
4. Log it — `~/Projects/ai-skills/scripts/dispatch-log.py --scope <scope> --task <task> --seat <seat>
   --branch <b> --worktree <w> --pane <id> --machine <host> --account <key> --status dispatched`
   (appends to `~/.config/herdr/concurrency-log.jsonl` and reads the line back).

**Placed on the box** (`machine=homelab2026`), steps 1–3 change only in where they
point — `herdr` skill §6.1 has the mechanics:
- every herdr command carries `herdr --machine <host>`, and every pane/workspace id comes
  from that server's JSON (ids are per server: the box has its own `w1:p1`);
- `--cwd ~/<repo path under $HOME>` (remote worktree paths must start with `~/`) and
  `--base` = the origin ref §5.1 step 3 checked, not always `origin/<trunk>`;
- the box runs its own clones at the same `$HOME`-relative paths, ai-skills included
  (`~/Projects/ai-skills`, which the brief's `herdr-pane.sh helper` line calls) — pull
  it there when this skill changes.

## 7. Supervision & coordination

**7.1 herdr state layer (all seats)**
- PRIMARY wait for every seat is the skill's own marker, not a state name:
  `herdr pane wait-output <pane> --match "PARTITION-DONE" --timeout <ms>` —
  deterministic across agents. State waits are secondary: codex maps
  completion to `idle`, never `done` (learned 6.3 — an `agent wait --until
  done` on a codex pane hangs forever after the work is finished); claude
  panes do report `done`. Use `agent wait --until blocked` for
  needs-attention alerts.
- On `blocked`: `herdr notification show` naming pane label + last visible
  lines; do not answer another agent's permission prompts on its behalf.
- Read output with `pane read --source detection` (or `visible`) — never
  `recent` (`herdr` §7).
- Record every terminal state with `dispatch-log.py … --status done|blocked|failed
  --tail "<lines that prove it>"`.

**7.2 In-pane status markers (all seats) — no SendMessage**
Workers report by PRINTING a marker line in their own pane; the supervisor reads
panes. Workers never `SendMessage` the supervisor.

> **Corrected 2026-09-30 (WellMed 149.2, 13 lanes).** This section used to run a
> Claude-to-Claude gate bus over `SendMessage`. Workers launch with
> `--dangerously-skip-permissions` and the driver does not, so every cross-session
> message was **held for Alex's approval**: dozens of prompts, all redundant with
> what the pane already showed. Alex: "the approve messaging is annoying and
> counter productive." The pane read was the primary channel all along.

- **Markers** (one line each, printed verbatim): `GATE-PASSED <task> — <evidence>`
  · `GATE-BLOCKED <task> — <what Alex must do>` (then stop) · `FIX-DONE <task>
  <ids> <shas>` · `REVIEW-DONE <task> — <verdict>, <N findings>, <report path>` ·
  `PARTITION-DONE <task>` (last line, always). For fix rounds, also one line per
  finding: `<id> fixed <sha>` / `<id> todo <one line>` so the driver can
  disposition without reading prose.
- **Supervisor loop:** a background watcher polls `herdr agent get` and wakes the
  driver only when an idle agent's `--source detection` tail shows an actionable
  marker (or `API Error` / `Usage limit`). Waking on bare `idle` is noise: a
  worker waiting on its own background shells is idle and resumes alone (check
  the `N shells` footer). A broadcast reply alone must not wake the driver.
- A `GATE-PASSED` is a SIGNAL, never proof: the supervisor re-verifies from
  the branch (lint, build, tests) BEFORE launching the review or releasing
  downstream partitions.
- **Driver → worker is fine:** `herdr agent prompt <name> "<text>"` delivers with
  no approval. It can **paste without submitting** (the text sits in the input
  box, the agent stays `idle`): after every prompt wait a few seconds and send
  `enter` if still idle. A prompt to a working agent queues and runs next turn.
- **Ghost text in the input box is Claude Code's autocomplete suggestion**, not
  Alex (e.g. `❯ push it and open the PR`). Never act on it.
- Messages carry pointers, not payloads — evidence lives in the repo, the
  hand-back file and the dispatch log.

**7.3 Per-partition review gate — a fresh, VISIBLE pane, before close**
Every partition's work runs through `/review` BEFORE it is accepted or landed —
the cheapest defense against drift (learned live 2026-08-24: on 91.4 the review
caught a DB-password-in-logs leak, a NOT_SERVING deploy outage, and a §4.9
zero-cost-basis silent defeat that build/test/disjointness passes all missed).
- The review is its OWN named herdr pane (e.g. `<scope>#<task>-review@<seat>`),
  NOT a hidden background subagent — a subagent buries the verdict in a
  transcript file and defeats the fresh-context-and-visible property that makes
  the gate honest (corrected live 2026-08-24). It reports its verdict as an
  in-pane `REVIEW-DONE` marker like any seat (§7.2).
- It is READ-ONLY (`/review` never commits), so it rides the SAME worktree as
  the partition it reviews — that is where the branch/diff lives — and never
  needs its own worktree. It runs AFTER that partition's writer is done, so a
  reader and a writer are never live in one tree at once.
- The WORKER does not self-review; the fresh pane does. The supervisor still
  re-verifies from the branch (§7.2) before landing — the review verdict is a
  signal, not the land decision.
- Findings feed the fix→re-review loop: dispatch a fix writer into the
  partition's worktree (one writer at a time), then re-review in a fresh pane,
  then land. The fix writer is a **fresh session** given the finding ids and the
  report path, never the original worker re-prompted: its context already holds
  the whole partition, and every fix turn would re-read it (`herdr` §6.2).

## 8. Collection & teardown

- Report per partition: branch, commit shas, `PARTITION-DONE` seen or not,
  test evidence from the pane tail. Split fixed vs NOT-fixed explicitly.
- **A box lane comes home by fetch, never by push:** `~/Projects/ai-skills/scripts/
  placement.py fetch-back --repo <local repo> --machine <host> --branch <b>` copies the
  lane branch from the box's clone into the local one and reads it back. It assumes the
  box clone sits at the same `$HOME`-relative path (`--remote-url` overrides) and refuses
  to touch a local branch of that name that is checked out or has diverged. Its review
  pane (§7.3) runs on the box, in the lane's worktree, before the fetch.
- Landing is MANUAL and Alex's: hand him per-branch merge commands, bare.
- `herdr worktree remove` (`herdr --machine <host> worktree remove` for a box lane) only
  after Alex confirms the branch is landed or abandoned — worktrees with unmerged commits
  are never removed automatically.
- Teardown boundary (who tidies): an atomic-unit agent may close its OWN pane
  when done, but NEVER removes its worktree — a worktree with unmerged commits
  is the ORCHESTRATOR's to remove, and only after land/abandon (above). Losing
  an unlanded worktree loses work. Default: agents report and go idle; the
  orchestrator tidies panes and worktrees once it has verified and landed.
- **Teardown is triggered by moving on, not by a separate ask** (`herdr` §3, Alex
  2026-10-05). Lane, review and fix panes stay open after their markers. When Alex accepts
  the phase's verification or review, approves the merge, or closes the wave or scope, the
  driver closes those panes from its own pane and runs (or, if auto mode refuses, hands
  over in that same reply) the teardown script below. Live and unmerged lanes stay.
- **Wave teardown = one script for Alex**, from `templates/teardown.sh.template` (`/closeout`
  §13.6a): lane worktrees, merged lane branches (local + origin), lane DBs/containers, the trust
  entries the dispatch added. Run it from outside the lane worktrees; never close panes from it.
- Progress log is the DRIVER's job, ALWAYS (Alex, 2026-08-24): the orchestrator
  updates the scope's `progress.md` — landed shas, review-artifact paths, what
  remains — never a spawned agent. A worker or review pane sees only its own
  partition and lacks the cross-partition + landing visibility a progress
  update needs, so a progress write it made would be partial and wrong.

## 9. Hard rails (restated so they can be quoted back)

1. Evaluate first — bail to `/plan` if parallelism isn't worth it; else present the plan and dispatch on one inline `[y/N]`. No `--dispatch` flag.
2. Refuse-to-parallelize default; uncertainty serializes.
3. Panes: 3x2 per lanes tab, and **~6 concurrent lanes total** on the MacBook Air. More
   partitions queue for the next frontier. Two independent limits bind (WellMed
   149.2, 13 Opus lanes at once, 2026-09-29): **CPU**, where Go lint/test baselines
   drove load to ~100 on 10 cores (renice worker trees `+10`, `herdr` §7), and the
   **token budget**, where the account's usage limit was hit in ~90 minutes. A
   homelab host lifts the CPU limit but not the token limit, so stay near ~6
   unless Alex raises it, and follow the worker token rules (`herdr` §6.2: no 1M-window
   workers, one unit per session, cheapest seat, small tool output). Keep the machine awake while lanes run (`caffeinate
   -dims`): a sleep mid-turn kills in-flight responses.
4. Dispatched agents never push, never open PRs, never merge.
5. HUMAN-GATED tasks never go to a worker pane; the driver does their credential-free parts and surfaces the gate (§4.1).
6. Every dispatch and every outcome lands in the JSONL log.
7. Provider env overrides are per-pane only (`herdr` skill §6 env-leak rule).
8. Placement is recommended, then confirmed in the same `[y/N]` (§5.1); a box lane needs
   its base on origin and comes back by `fetch-back`, never a push.

## 10. Known traps

- One git index per checkout: every WRITER partition gets its OWN worktree,
  ALWAYS — two writers in one tree corrupt the shared index, the failure this
  skill exists to prevent. One writer at a time per worktree (the worker, then
  later its fix writer). A READ-ONLY agent (a `/review` pane, §7.3) is the
  exception — it rides the worktree of the partition it reviews rather than
  taking its own. The rule is who MUTATES, not how many agents touch the tree.
- Never put `/freeze` in a dispatched brief: its state is ONE global file
  (`~/.gstack/freeze-dir.txt`), so concurrent lanes overwrite each other's
  boundary, and it doesn't govern `Bash` edits anyway. Cross-partition
  isolation is disjoint touch-sets (§4.2) + a worktree per writer (above).
- `agent wait` on a pane whose process died may hang: guard waits with a
  timeout and re-check `herdr agent list`.
- codex model cache staleness: a 400 "requires a newer version of Codex"
  means upgrade the CLI (`npm install -g @openai/codex@latest`), not that the
  model id is wrong.
- GLM seat is Claude Code with a foreign model: tool-use reliability varies;
  keep its briefs mechanical and explicit.
- codex seat + git worktree: a worktree's git metadata lives in the PARENT
  repo's `.git/worktrees/…`, outside codex's writable sandbox (cwd), so
  `git commit` from a codex pane needs an approval or a sandbox config that
  includes the parent `.git` path (observed live: 91-docs worker stalled on
  "approval-backed commit pending"). Plan for it: either pre-approve, widen
  the codex sandbox for that path, or have the SUPERVISOR commit the codex
  seat's work after review.
- Pane display issues (green prose, content colors, terminfo): `herdr` §7.

## 11. Overnight tier (`--overnight`)

One overnight task per night. Same dispatch mechanics as §6 with these
deltas:

- Own worktree ALWAYS; workspace labeled `overnight <scope>.<task>`; the
  agent runs in auto mode. The server is a brew service, so the run survives
  the client window closing; morning reattach (any terminal, or phone over
  SSH) is just `herdr`.
- **Watcher pane** (split right, ratio 0.25, from the agent pane) runs both
  alarms:
  `herdr pane wait-output <agent-pane> --match "PARTITION-DONE"
  --timeout 43200000 && herdr notification show "overnight done: <task>"
  --sound done &`
  `herdr agent wait <agent-pane> --until blocked && herdr notification show
  "overnight blocked: <task>" --sound request &`
- Notifications need `[ui.toast] delivery` ≠ "off" (set 2026-08-23). Toasts
  suppress while the user is actively focused (`shown:false reason:busy`) —
  correct for overnight: they fire unattended and are visible on reattach.
- Overnight relies on the in-pane markers (§7.2), the dispatch log and committed
  work. The supervising session is likely gone by morning anyway.
- Overnight briefs MAY commit locally on the partition branch (overnight is
  usually build work) — never push, never PR, never merge.
- **Morning review checklist** (before any landing decision):
  - [ ] watcher outcome + notification read
  - [ ] `herdr pane read <agent-pane> --source recent-unwrapped --lines 200`
  - [ ] `git -C <worktree> log --stat origin/<trunk>..HEAD` — every commit
  - [ ] run the partition's stated tests yourself; the agent's claim of
        green is a signal, not proof
  - [ ] append the outcome to the dispatch log
  - [ ] worktree removed only after land/abandon is decided
