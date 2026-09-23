# Scope: /concurrency — herdr-backed multi-agent dispatch

Created: 2026-08-23 · Owner: Alex · Repo: ai-skills · Branch: `feature/concurrency-skill`

## 1. Objective

`/concurrency` is the single controlled home for every "no human in the loop"
agent train. Given a scope's plan surface, it partitions the work into
non-overlapping, dependency-ordered units and dispatches each to a visible,
named herdr pane running the right model — then supervises by agent *state*,
not by watching scrollback. Nothing in this family runs wild: every capability
lands behind a gate, dry-run first.

Two operating tiers:
- **Active tier** — 2–4 primary sessions spawning 1–12 small panes Alex can
  expand to inspect.
- **Overnight tier** — a named persistent herdr session running a long task in
  auto mode, checked in the morning (or from a phone over SSH).

## 2. Ground truth (verified 2026-08-23, this machine)

- herdr 0.8.2 via homebrew, running as a brew service (`homebrew.mxcl.herdr`)
  — survives logout; UI attaches by typing `herdr` in Ghostty.
- Socket CLI chain proven headless end-to-end:
  `workspace create --cwd --env` → `pane run` → `pane read` → `workspace close`.
- ⚠ `pane read --source recent` returns **empty** with no UI client attached —
  use `--source visible` or `--source detection`. This is the exact mode the
  skill runs in; recent is a trap.
- Native `herdr worktree` subcommand exists — worktree-per-partition is a
  built-in, not scripted.
- Supervision primitives: `herdr agent wait <pane> --until done|blocked`,
  `herdr notification show`, `pane.report_agent` states
  `idle|working|blocked|done|unknown`.
- codex-cli 0.139.0 installed and authed (`~/.codex/auth.json`), `-m` flag.
- No `herdr --skill` flag exists — layout construction is this skill's job,
  via the CLI helpers.

## 3. Model routing table (v1)

| Seat | Invocation | Role |
|------|-----------|------|
| claude / Opus 4.8 | `claude` (global default model: opus) | primary implementation + judgment |
| codex / GPT-5.6 sol | `codex -m <5.6-sol id>` (pin exact id in 6.1) | secondary implementation, review passes |
| GLM 5.2 | Claude Code + per-pane env: `ANTHROPIC_BASE_URL` → OpenRouter, model `z-ai/glm-5.2` | mechanical / bulk tasks |

Rules:
- All routing config lives in ONE block inside the skill, so swapping the GLM
  provider (OpenRouter → Z.ai coding plan if dogfood volume justifies the flat
  $18/mo) is a one-block change.
- Provider overrides are injected **per-pane** via herdr `--env` — a GLM seat's
  base-URL override must never leak into a normal Claude session.
- New seats (kimi etc.) are new rows, not new code paths.

## 4. Design

```
  scope plan stubs (/scope output, or ad-hoc task list)
        |
        v
  +--------------------+     edges:
  | partition DAG      |     - file/service overlap  => same partition
  | builder            |     - emitter-before-consumer
  +--------------------+     - schema-leads-code
        |                    - implementer-leads-caller (gRPC)
        v                    - human-gated tasks => marked, never dispatched
  ready frontier only
        |
        v  (per partition)
  +---------------------------------------------+
  | herdr worktree add  -> own branch           |
  | herdr workspace create --cwd <wt> --env ... |
  | pane named: <scope>#<partition>@<model>     |
  | agent launched per routing table            |
  | /freeze pins agent to partition's paths     |
  +---------------------------------------------+
        |
        v
  supervision loop: herdr agent wait --until blocked|done
        |                 |
        v                 v
  notification        read tail (--source detection),
  to Alex             record outcome in dispatch log
        |
        v
  landing: MANUAL. one branch per partition; Alex merges.
```

## 5. Safety rails (the "controlled and debugged before running wild" clause)

- **Evaluate, then one inline gate.** `/concurrency` judges whether parallelism
  is worth it (bails to `/plan` if not), prints the DAG + dispatch plan (pane
  names, models, worktrees, freeze paths), and dispatches on a single inline
  `[y/N]`. (Superseded scope #3's original dry-run + `--dispatch` two-step — see
  ai-skills scope #4 (2026-08-30). The human veto stays; the flag + re-run
  ceremony is gone.)
- **Refuse-to-parallelize is the default verdict.** A task pair joins the
  parallel set only when disjointness is *shown* (paths + dependency edges);
  anything uncertain serializes.
- **Pane cap** starts at 2 (phase 6.2), raised only by gate.
- **Spawned agents never push, never open PRs, never merge.** Local commits in
  their own worktree-branch only.
- **Dispatch log** — every dispatch appends to `~/.config/herdr/concurrency-log.jsonl`:
  who, what partition, which model, worktree, outcome. Debuggability before scale.
- **Human-gated tasks** (credential renewals, prod actions) are surfaced as
  blocked-on-Alex, never attempted.

## 6. Phases

- [ ] **6.1 Skeleton + dry-run partitioner** — skill file, routing table
  (pin codex 5.6-sol id, wire GLM/OpenRouter env block), DAG builder, plan
  printer. **Gate: partitioner run over wellmed scope 91 must produce the
  known-correct answer** — dispatch 91.2 only; 91.1 flagged human-gated
  (Jurnal sandbox renewal); 91.3–91.7 refused as dependency-blocked. A
  partitioner that parallelizes 91.4 fails the gate.
- [ ] **6.2 Live dispatch, claude-only, cap 2** — worktree + pane + freeze +
  supervision loop + notification + dispatch log. Gate: one real 2-pane run,
  outcomes read back correctly, log complete.
- [ ] **6.3 Multi-model seats** — codex + GLM panes live; raise cap. Gate:
  each seat completes a real task in its pane and its output is collected.
- [ ] **6.4 Overnight profile** — `herdr --session overnight`, auto-mode agent
  in own worktree, notification on done/blocked, morning-review checklist.
- [ ] **6.5 Register + dogfood on scope 91** — merge, re-run
  `bash ~/Projects/ai-skills/setup.sh`, restart session. Dogfood precondition:
  **refresh pass over scope 91 first** (untouched ~2 weeks; re-validate phase
  surface against develop — 118.1's dispense-sign fold-in and the 91.2
  routing-key rename are the likely drift points).

## 7. Out of scope

- Auto-landing / auto-merge of spawned agents' branches.
- Cross-machine dispatch (herdr `--remote` exists; later).
- kimi or further seats beyond the three in §3.
- Replacing /scope or /plan — /concurrency consumes their output.
