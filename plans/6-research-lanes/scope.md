# Visible research lanes — /research pane mode
**Project:** ai-skills  **Branch:** main  **Date:** 2026-09-23
**Created by:** Alex
**Scope folder:** ~/Projects/ai-skills/plans/6-research-lanes/
**Source repo(s):** ~/Projects/ai-skills
**Primary repo (worktree):** none — skill-markdown edits in ai-skills, direct-to-main per its CLAUDE.md §2
**Backlog:** none

## 1. Context

`/research` runs `deep-research-lean` through the Workflow tool: every agent
lives inside the invoking session's process, and herdr has nothing to show.
The 2026-09-23 Iris run spent 36 agents / ~1.7M tokens with none of it visible
or interruptible while it drifted. Alex wants research lanes he can watch and
interrupt, sitting beside `/concurrency` as one herdr-pane UX. Pane mode is
added **alongside** the Workflow mode, not replacing it — the unattended run
stays available for cloud/overnight use.

## 2. Repo Graph

`CROSS-REPO.md` declares ai-skills a standalone leaf — no Pattern Sources, no
contract Consumers. Snapshot N/A.

## 3. ADR Alignment

No ADRs in ai-skills. N/A.

## 4. Phases

Atomic — one plan, `6.1-research-lanes-PLAN.md`. Zero internal gates; the one
exit gate is **A (human)**: Alex's go/no-go after watching the first live
pane-mode run.

## 5. Architecture

```
  /research <q>   (driver = invoking session, Opus, inside a herdr pane)
     |
     | 1. scope the question -> N angles (3-8), agree verifyCap   (driver)
     | 2. ask mode: [panes] (default)  or  workflow
     |
     +-- workflow --> Workflow({name:"deep-research-lean", ...})   (unchanged)
     |
     +-- panes -----> NEW TAB in the driver's current workspace
                      label: "research <slug> r<k>"  (fresh tab per run/rerun)
                        |
          +-------------+-------------+-----------+
          v             v             v           v
      lane: angle1  lane: angle2 ... angleN   lane: verify
      claude --model sonnet, ONE context      claude --model sonnet
      search -> fetch -> extract claims       starts after all angle lanes
      writes <run>/angle-<i>.json             never saw the sources;
      prints  LANE-DONE angle-<i>             3-way verdict per claim
                                              (supported|refuted|unconfirmed)
                                              writes <run>/verify.json
                        |                           |
                        +------------+--------------+
                                     v
                    driver: supervise by STATE (not scrollback)
                      done   = LANE-DONE marker seen
                      failed = pane closed | idle/blocked w/o marker
                               (Esc interrupt lands here)
                      stall  = no new output 15 min -> flag to Alex, never kill
                                     v
                    driver synthesizes (Opus) from <run>/*.json
                    report -> <scratchpad>/research/<run>/report.md
                    failed angles = missing-coverage tier + offer re-run
                    panes + tab LEFT OPEN (Alex closes by hand)
```

`<run>` = `<driver scratchpad>/research/<slug>-r<k>/`.

## 6. What Already Exists

- `research/SKILL.md` — Workflow-only skill. Carries `AskUserQuestion` in
  `allowed-tools`, no `version`, unnumbered headings: all three violate ai-skills
  CLAUDE.md §3.1–3.3. Fixed in this scope since the file is being rewritten.
- `research/workflows/deep-research-lean.js` — schemas + prompts to mirror, NOT
  edit: `SCOPE_SCHEMA`, `SEARCH_SCHEMA`, `EXTRACT_SCHEMA`, the three-way verify
  verdict from `3bf467b`, the empty-search loud-fail from `fbd51de`, per-angle
  coverage + unconfirmed tier from `e884ef6`.
- `herdr/SKILL.md` — naming (§2), worker launch + trust (§4), gotchas (§7).
  §2 says skills never create tabs; this scope adds a research carve-out.
- `concurrency/SKILL.md` §7.1 — marker-wait supervision
  (`pane wait-output --match`), the pattern lanes reuse.
- `~/.claude/CLAUDE.md` "Execution parallelism goes to visible herdr panes" —
  needs a carve-out: research runs in visible lanes; short read-only fan-out
  (Explore, `/ready-to-clear`, `/review` passes) stays in-process.

## 7. Table Identity Map

No DB write/DDL surface — Step 4.5 N/A.

## 8. Inherited TO-DOs

| TO-DO item | Origin section | In / Out | Phase | Why |
|---|---|---|---|---|
| Re-test codex idle-vs-done after the herdr v9 hook | Herdr Agent Workflow (Plan 4) | Out | — | Lanes are claude seats; codex state mapping doesn't touch this |

## 9. NOT in Scope

- Editing `deep-research-lean.js` — the Iris session owns it; pane mode mirrors
  its schemas and verdict model, it does not change them.
- Scope 5 (verify lever) — the verify lane is a pluggable step so scope 5 can
  replace it; no verify redesign here.
- Pane cap — none for research lanes (Alex). No dispatch-log entries (Alex:
  overkill).
- Mid-run steering — Alex only interrupts; no steering protocol.
- Auto-closing panes or tabs.
- Pane mode outside herdr — `HERDR_ENV` unset ⇒ Workflow mode only, said plainly.

## 10. Skill Sequence

### 10.1 Plan Reviews

| # | Skill | Apply? | Notes |
|---|-------|--------|-------|
| 1 | /plan-ceo-review | **YES** | Premise check: is one-context-per-lane + separate verify lane the right cost/visibility trade? |
| 2 | /plan-eng-review | OPTIONAL | Worth it only if the lane I/O contract (JSON files + marker) looks shaky after CEO review |
| 3–4 | /plan-design-review, /plan-devex-review | N/A | No UI; the only "developer" is Alex invoking a skill |

### 10.2 Implementation Support

N/A x4 (/investigate, /design-consultation, /design-html, /design-shotgun) — not a bug, no UI.

### 10.3 Review & QA

| # | Skill | Apply? | Notes |
|---|-------|--------|-------|
| 9 | /review | OPTIONAL | Skill-markdown diff; `--engine-only` if run (not a Kalpa repo) |
| 10, 12 | /health, /qa-only | N/A | No test suite in ai-skills (CLAUDE.md §6) |
| 11, 13–15 | /qa, /browse, /devex-review, /setup-browser-cookies | N/A | No UI / browser |

### 10.4 Ship & Post-ship

| # | Skill | Apply? | Notes |
|---|-------|--------|-------|
| 16 | /ship | **N/A** | Not in use; direct-to-main per ai-skills CLAUDE.md §2 |
| 17 | /document-release | N/A | README + ARCHITECTURE rows updated inline in 6.1 |
| 18 | /retro | OPTIONAL | Small scope |

## 11. Key Decisions Captured

- 11.1 Pane mode sits **alongside** Workflow mode. `/research` asks inline which
  to run; **panes is the default**, Workflow is offered.
- 11.2 **One context per lane** runs the whole search → fetch → extract pipeline
  for its angle — no per-step subagents (startup tokens).
- 11.3 **Separate verify lane** (Claude's call; Alex skipped the question): one
  extra context that never saw the sources verifies every lane's claims, keeping
  the independence the Workflow's 3-vote panel buys. Uses the three-way verdict
  from `3bf467b`. Pluggable so scope 5 can replace it.
- 11.4 **Fresh tab per run**, including refine-and-rerun, in the driver's
  **existing workspace**. Angles are lanes (panes) inside it. Carve-out from
  the `herdr` skill's "skills never create tabs".
- 11.5 **Panes stay open** after the report; Alex closes them by hand.
- 11.6 **No pane cap** for research; lane count = angle count (3–8) + 1 verify.
- 11.7 **Failure = state, not a timeout.** Closed pane, or idle/blocked without
  the done marker ⇒ failed angle → missing-coverage tier + re-run offer. 15 min
  of no output ⇒ flagged, never killed. The driver never hangs.
- 11.8 **Output in the driver's scratchpad** (`research/<run>/`), report
  included; driver offers to copy the report somewhere durable.
- 11.9 **No dispatch log.**
- 11.10 **Lanes run Sonnet; driver synthesis stays Opus** (the session model).
