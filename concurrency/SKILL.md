---
name: concurrency
version: 0.2.0
description: |
  ONE responsibility: map what can run in parallel and what cannot, against a
  clear set of rules — re-derived from repo ground truth on every run, never
  from a scope's dependency claims. Then dispatch each parallel unit to a
  visible, named herdr pane running the right model seat (Opus / codex / GLM)
  and supervise by agent state plus a Claude-to-Claude gate-broadcast bus. The single
  controlled home for no-human-in-the-loop agent trains. Use when asked to
  "/concurrency", "dispatch this scope concurrently", "run these phases in
  parallel", "start an agent train", or "herd this scope". Dry-run is the
  default — nothing is dispatched without --dispatch. Do NOT use for
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

Design record: `plans/concurrency/scope.md` (ai-skills). Status lives in
`plans/concurrency/progress.md`, never here and never in scope.md.

## 1. Operating tiers

- **Active tier** — the invoking session (one of Alex's 2–4 primaries)
  dispatches 1–N small panes it supervises. Default tier.
- **Overnight tier** (`--overnight`) — one long task in auto mode, unattended
  overnight. Procedure in §11.

## 2. Preconditions — check ALL before anything else

- [ ] herdr server answers: `herdr workspace list` exits 0. If not: report and
      stop — never `brew services start` on Alex's behalf mid-skill.
- [ ] Running inside a herdr pane: `test "${HERDR_ENV:-}" = 1`. If outside,
      say so and ask before proceeding — the socket works from outside, but
      pane-context is absent and herdr's own guidance is to control only from
      within.
- [ ] Load herdr's control-surface instructions: run `herdr --skill` and
      follow it for ALL pane/workspace/worktree mechanics. This skill defines
      WHAT to dispatch; `herdr --skill` defines HOW to drive herdr.
- [ ] Target repo identified, trunk known (`develop` for wellmed/pmg, `main`
      otherwise), `git fetch` run. Never dispatch from a dirty primary tree
      without surfacing it first.
- [ ] For the GLM seat only: the OpenRouter key resolves from Keychain
      (`security find-generic-password -s openrouter-api-key -w` — check
      LENGTH only, never print). Absent ⇒ GLM rows in the plan are marked
      `seat-unavailable`, never silently rerouted. The key is looked up
      inline in the launch command, never via herdr `--env` (which would
      persist the literal in herdr session state) and never in this
      supervisor's transcript.
      GLM launch traps (cost a relaunch on 2026-08-23):
      · base URL is `https://openrouter.ai/api` — NOT `/api/v1`; the SDK
        appends `/v1/messages`, so `/api/v1` 404s and surfaces as
        "model may not exist".
      · bearer only (`ANTHROPIC_AUTH_TOKEN`); setting `ANTHROPIC_API_KEY`
        triggers an interactive use-this-key dialog that blocks the pane.
      · "model not found" with a 200-tested key+model = plumbing, not
        OpenRouter permissions — curl both endpoint styles before touching
        account settings.

## 3. Model routing table

THE single source of routing truth. New seats are new rows. Verified on this
machine 2026-08-23.

| Seat | Launch inside pane | Verified | Route to it |
|------|-------------------|----------|-------------|
| `opus` | `claude` (global default model: opus) | Opus 4.8 default | judgment, design-adjacent implementation, anything touching prod-shaped decisions |
| `codex` | `codex -m gpt-5.6-sol` (headless: `codex exec -m gpt-5.6-sol`) | codex-cli ≥0.149.0, id live-probed OK | secondary implementation, independent review passes |
| `glm` | `ANTHROPIC_BASE_URL=https://openrouter.ai/api ANTHROPIC_AUTH_TOKEN=$(security find-generic-password -s openrouter-api-key -w) ANTHROPIC_SMALL_FAST_MODEL=z-ai/glm-5-turbo claude --model z-ai/glm-5.2` | live-verified 2026-08-23 (provider DigitalOcean) | mechanical/bulk: migrations-by-pattern, test scaffolds, sweeps |

Env-leak rule: provider overrides live ONLY in the seat's launch command,
inline, as the table shows — secrets resolve from Keychain at spawn (§2),
never via herdr `--env` (persists literals in session state), never
`export`ed in the invoking session, never written to any settings file.
Provider swap (OpenRouter → Z.ai coding plan) edits this table's one row and
nothing else.

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
  4.0. Surfaced in the plan; NEVER dispatched, never attempted.
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

## 5. Dry-run output (the DEFAULT — no flag dispatches anything)

Print exactly this shape and stop:

```
CONCURRENCY PLAN — <scope> @ <repo>          [DRY RUN — nothing dispatched]
ready frontier (cap N):
  <task>  seat=<seat>  branch=concurrency/<scope>-<task>
          worktree=<path>  freeze=<paths>
          pane label: <task> @<seat>
excluded:
  <task>  HUMAN-GATED: <what Alex must do>
  <task>  BLOCKED by <task>: <edge reason>
  <task>  SERIALIZED with <task>: <shared touch-set>
Run again with --dispatch to execute.
```

## 6. --dispatch (phase 6.2+; claude-only and pane cap 2 until the 6.3 gate)

Per partition, in this order (syntax authority: `herdr --skill`):
1. `herdr worktree create --cwd <repo> --base origin/<trunk>
   --branch concurrency/<scope>-<task> --label "<task> @<seat>"
   [--env KEY=VAL ...]` — env vars ONLY for the glm seat.
   ⚠ NAMING (learned live: a codex pane displayed "@opus"): the agents
   sidebar shows the WORKSPACE label as every row's main header and the
   pane's display-agent as the subheader — so a seat name at workspace
   level lies about every other seat in the run. Workspace label = run
   name only, NO seat (`<scope> run`); seat identity goes on the PANE:
   `pane rename` + `pane report-metadata --display-agent "<task> @<seat>"`.
1b. **Layout rule (Alex, 2026-08-23): tab per scope, primaries stacked,
   short names.** The FIRST run's worktree workspace becomes the herd
   workspace; its tab is the run's tab. Each additional CONCURRENT scope/run
   gets its own TAB in that same workspace (tab label = scope number, e.g.
   `91.0`), never a new workspace. Every subsequent primary's root pane
   moves into its run's tab: `herdr pane move <pane> --tab <run-tab>
   --split down --target-pane <prev-pane> --ratio 0.5 --no-focus`. Moving a
   pane does not disturb its running agent (verified live). Names: workspace
   = run name only, NEVER a seat (`<scope> run`); tab = scope (`91.0`);
   pane label AND agent sidebar row = task + seat — `pane rename <pane>
   "<task> @<seat>"` plus `pane report-metadata <pane> --source concurrency
   --display-agent "<task> @<seat>"` (without the metadata the sidebar
   shows the workspace label for every agent — a seat name there lies
   about every other seat in the run). Helper panes a worker opens go RIGHT
   of its own pane at half size — the brief carries that instruction.
2. Launch the seat's command (table §3) in the created pane via `pane run`.
3. First instruction in every dispatched prompt: run `/freeze <paths>` for its
   partition, then the task brief, then: commit locally when done; NEVER push,
   NEVER open a PR, NEVER merge; end by printing `PARTITION-DONE <task>`.
   Claude seats additionally get the §7.2 gate-bus reporting instruction
   (`GATE-PASSED` / `GATE-BLOCKED` via SendMessage to the supervisor), and
   every brief includes: "If you need a helper terminal or sub-agent pane,
   split your OWN pane right at half size:
   `herdr pane split --current --direction right --ratio 0.5` — never a new
   workspace, never split down (down is reserved for primaries)."
4. Append one JSON line to `~/.config/herdr/concurrency-log.jsonl`:
   `{ts, scope, task, seat, branch, worktree, pane_id, status:"dispatched"}`.

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
- Read output with `pane read --source detection` (or `visible`).
  **NEVER `--source recent`** — it returns empty when no UI client is
  attached, which is exactly this skill's headless condition.
- Record every terminal state in the dispatch log (`status: done|blocked|
  failed`, plus the tail that proves it).

**7.2 Claude-to-Claude gate bus (claude + glm seats)**
Dispatched claude/glm panes are full local Claude Code sessions, so they
appear in the supervisor's `ListAgents` and are reachable via `SendMessage`
(native cross-session messaging over the local socket).
- **Bus addresses go stale (learned live 2026-08-23): session names change
  on every restart or resume.** At dispatch time, read YOUR current
  self-name from `ListAgents` ("This session is <name>") and embed THAT in
  each brief — never a name copied from an example, a progress note, or an
  earlier run, and never a raw session-id: an id looks stable but the
  worker's runtime resolves it to a herdr name at send time, so across a
  restart it delivers to a stale address (both failure modes occurred live
  in the first 91.2 dispatch). If the
  supervisor restarts while workers are out, re-handshake every live worker
  with the new name before their gates fire; a worker whose GATE message
  fails to deliver should print it in-pane and hold.
- Every dispatched Claude brief includes: "When your gate criteria are met,
  SendMessage the supervising session exactly: `GATE-PASSED <task> —
  <one-line evidence>`. If you hit a human-only blocker, send
  `GATE-BLOCKED <task> — <what Alex must do>`, then stop."
- A `GATE-PASSED` is a SIGNAL, never proof: the supervisor re-verifies from
  the consumer's vantage point (read the branch, run the gate check itself)
  BEFORE recomputing the frontier and releasing downstream partitions.
- On releasing new frontier tasks, the supervisor broadcasts a plain-text
  note to each affected running peer so it knows its upstream landed.
- The codex seat has no bus: herdr state + the `PARTITION-DONE` marker only.
- Messages are plain text and carry pointers, not payloads — evidence lives
  in the repo and the dispatch log.

**7.3 Per-partition review gate — a fresh, VISIBLE pane, before close**
Every partition's work runs through `/review` BEFORE it is accepted or landed —
the cheapest defense against drift (learned live 2026-08-24: on 91.4 the review
caught a DB-password-in-logs leak, a NOT_SERVING deploy outage, and a §4.9
zero-cost-basis silent defeat that build/test/disjointness passes all missed).
- The review is its OWN named herdr pane (e.g. `<scope>#<task>-review@<seat>`),
  NOT a hidden background subagent — a subagent buries the verdict in a
  transcript file and defeats the fresh-context-and-visible property that makes
  the gate honest (corrected live 2026-08-24). It reports its verdict on the
  bus / marker like any seat.
- It is READ-ONLY (`/review` never commits), so it rides the SAME worktree as
  the partition it reviews — that is where the branch/diff lives — and never
  needs its own worktree. It runs AFTER that partition's writer is done, so a
  reader and a writer are never live in one tree at once.
- The WORKER does not self-review; the fresh pane does. The supervisor still
  re-verifies from the branch (§7.2) before landing — the review verdict is a
  signal, not the land decision.
- Findings feed the fix→re-review loop: dispatch a fix writer into the
  partition's worktree (one writer at a time), then re-review in a fresh pane,
  then land.

## 8. Collection & teardown

- Report per partition: branch, commit shas, `PARTITION-DONE` seen or not,
  test evidence from the pane tail. Split fixed vs NOT-fixed explicitly.
- Landing is MANUAL and Alex's: hand him per-branch merge commands, bare.
- `herdr worktree remove` only after Alex confirms the branch is landed or
  abandoned — worktrees with unmerged commits are never removed automatically.
- Teardown boundary (who tidies): an atomic-unit agent may close its OWN pane
  when done, but NEVER removes its worktree — a worktree with unmerged commits
  is the ORCHESTRATOR's to remove, and only after land/abandon (above). Losing
  an unlanded worktree loses work. Default: agents report and go idle; the
  orchestrator tidies panes and worktrees once it has verified and landed.

## 9. Hard rails (restated so they can be quoted back)

1. Dry-run default; `--dispatch` is the only path to execution.
2. Refuse-to-parallelize default; uncertainty serializes.
3. Pane cap 2 until the 6.3 gate raises it.
4. Dispatched agents never push, never open PRs, never merge.
5. HUMAN-GATED tasks are surfaced, never attempted.
6. Every dispatch and every outcome lands in the JSONL log.
7. Provider env overrides are per-pane only (§3 env-leak rule).

## 10. Known traps

- `pane read --source recent` empty headless (§7).
- One git index per checkout: every WRITER partition gets its OWN worktree,
  ALWAYS — two writers in one tree corrupt the shared index, the failure this
  skill exists to prevent. One writer at a time per worktree (the worker, then
  later its fix writer). A READ-ONLY agent (a `/review` pane, §7.3) is the
  exception — it rides the worktree of the partition it reviews rather than
  taking its own. The rule is who MUTATES, not how many agents touch the tree.
- `/freeze` is per-REPO, not per-worktree (learned live 2026-08-24): two
  same-repo worktree partitions overwrite each other's freeze boundary and
  mutually block. Do NOT rely on `/freeze` for cross-partition isolation — the
  real guard is disjoint touch-sets (§4.2) + a separate worktree per writer.
  `/freeze` is at most a within-partition nicety.
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
- Radioactive-green prose in panes = default-fg text hitting Ghostty's
  Homebrew foreground (#00ff00). Claude Code prose in herdr panes carries NO
  color codes (verified via `pane read --format ansi`), so it always renders
  in the window's default foreground — TERM makes no difference (proven
  2026-08-23: TERM=xterm-ghostty confirmed in-pane, prose still green).
  ACTUAL fix: run the herd window as its own Ghostty instance with a
  per-window foreground override — the `herd` alias in ~/.zshrc
  (`open -na Ghostty.app --args --foreground="#d8d8d8" --title=herd -e
  herdr`). Main Ghostty windows keep the Homebrew look. The zshrc
  HERDR_ENV→TERM/TERMINFO block remains for terminfo correctness (export
  TERMINFO BEFORE TERM — zsh re-inits terminfo on the TERM assignment); if
  a TUI misbehaves inside a pane, suspect that block first.
- Pane content colors are NOT herdr theme tokens — theme.custom.* paints
  chrome only. Content color problems are TERM/terminfo problems.

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
- **No gate bus overnight** — the supervising session is likely gone by
  morning, so overnight briefs OMIT SendMessage and rely on the marker, the
  dispatch log, and committed work.
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
