# Progress: Visible research lanes — /research pane mode

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔code mismatch = STOP, investigate in-context, report before proceeding.
2. Never edit `research/workflows/deep-research-lean.js` in this scope — pull and
   mirror it. The Iris session owns it.
3. Wrap + commit + check in at the phase boundary; progress updates land more
   often than that. This file alone must be enough for a cold context to resume.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/6-research-lanes/scope.md
**Last action:** Plan 6.1 Task 1.4 done — live run + interrupt test passed (2026-09-26)
**Next action:** Phase 1 CHECKPOINT (gate A) — Alex go/no-go on pane mode as default, then /closeout
**Open blockers:** Alex's go/no-go
**Key files changed:** research/SKILL.md, research/scripts/lanes.py, herdr/SKILL.md, README.md, ARCHITECTURE.md, dev-workbench CLAUDE.md

---

## Decisions Log
- (2026-09-23) Pane mode alongside Workflow mode; panes default, Workflow offered.
- (2026-09-23) One context per lane; separate verify lane (Claude's call, Alex skipped).
- (2026-09-23) Fresh tab per run in the current workspace; panes left open; no pane cap; no dispatch log.
- (2026-09-23) Lane failure detected by state, never a fixed timeout; 15-min stall only flags.
- (2026-09-23) Output + report in the driver's scratchpad.
- (2026-09-23) /plan-ceo-review skipped (Alex): small skill change, premises settled in scoping.

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-09-23 | /scope | Done | Atomic scope, one plan (6.1), exit gate A |
| 2026-09-23 | /plan-ceo-review | Skipped | Alex's call |
| 2026-09-26 | /plan 6.1 Task 1.4 | Done | Live run (3 lanes + verify) + separate interrupt test; lanes.py agent-name bug fixed |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Trust `~/.cache/research-lanes` once (start `claude` there, choose trust, exit) | [x] Done 2026-09-23 (verified in ~/.claude.json) | Task 1.4 precondition; `lanes.py open` checks it |
| Pick the first live research question | [x] Done 2026-09-26 | poteto on verification since 2026-09-11 (input to scope 5) |
| Go/no-go after the live run | [ ] Pending | Phase exit gate A |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 6.1 | 6.1-research-lanes-PLAN.md | Phase 1 — /research pane mode | 1.0–1.4 ✅ — at gate A checkpoint | |

---

## Artifacts
(none yet)

---

## Plan 6.1: /research pane mode

### Resume Context (Plan 6.1)
**Last action:** Tasks 1.0–1.3 done (2026-09-23)
**Next action:** Task 1.4 — first live run. Lane-home trust is done; only
blocker is Alex running `/research <real question>` in a herdr pane.

### Session: 2026-09-23
- Phase 0 ✅ — inputs resolve; main == origin/main; inside herdr (w14:pD);
  Primary repo "none" so no worktree; Status flipped Draft → Ready to execute on
  Alex's go; ledger bootstrapped.
- Task 1.0 ✅ — mirrored `deep-research-lean.js` @ `3bf467b` (three-way verdict,
  empty-search loud-fail, round-robin cap). The .js is untouched.
- Task 1.1 ✅ — `research/SKILL.md` v0.2.0: mode choice (panes default, Workflow
  offered, Workflow only outside herdr); frontmatter conforms (version, no
  AskUserQuestion); headings numbered.
- Task 1.2 ✅ — `research/scripts/lanes.py` (open / launch / claims / wait) +
  SKILL.md §3. Tested: claims ranking and round-robin, done/failed
  classification, 3×2 grid layout, cap<1 → exit 2. Live smoke launch found that
  **`--dangerously-skip-permissions` no longer skips the folder-trust dialog**
  (Claude Code 2.1.280), so lanes now start in a fixed pre-trusted
  `~/.cache/research-lanes`; `open` checks trust up front. Test tabs closed.
- Task 1.3 ✅ — `herdr` §2 research-tab carve-out; README + ARCHITECTURE rows for
  /research (both were missing since its 09-01 adoption); CLAUDE.md research
  carve-out (lives in dev-workbench, see below).

#### Unplanned: herdr §4 trust-dialog correction
**Files modified:** `herdr/SKILL.md` (v0.1.2). §4 claimed bypass mode skips the
trust dialog; disproved live. Dated correction added, not a rewrite.

#### Unplanned: CLAUDE.md stale `/freeze` mention
**Files modified:** `dev-workbench/config/claude-code/CLAUDE.md` — dropped
"+ `/freeze` per lane" (/freeze was removed from dispatch 2026-09-02).
**Committed** on dev-workbench `feature/1password-migration` (Alex's call) as
`e4c4074`, with the herdr v9 hook as `a85d76b`; branch pushed.

### Session: 2026-09-26
- Task 1.4 ✅ — live run `poteto-verify-r1` (tab w14:t6): 3 Sonnet angle lanes
  (pstack repo · her X writing · talks/third-party) + verify lane. 19 claims
  extracted, all 19 verified under cap 24: 18 supported, 1 refuted, 0 unconfirmed.
  Lanes visible and named; driver supervised by state; report cites sources.
  Report copied to `5-verify-lever/artifacts/research-poteto-2026-09-26.md`
  (it is scope 5's input).
- **Interrupt path** — no lane was interrupted during the main run (all finished
  first), so a separate throwaway run `interrupt-test-r1` (tab w14:t7) was
  launched and Alex hit Esc. `wait` returned `failed — agent idle with no
  t1-throwaway.json` within the 60 s grace; driver did not hang. Acceptance met.
- **Bug found + fixed (lanes.py):** agent names were `r-<run folder>-<lane>`;
  herdr caps names at 32 chars of [a-z0-9_-], so 2 of 3 lanes were refused at
  launch. `agent_name` now uses a stable 6-char sha1 of the run folder + a
  sanitized lane, truncated to 32. The already-started lane was renamed with
  `herdr agent rename` so `wait` could find it.
- **Observed, not fixed:** X article pages yielded no claims (a2 found poteto's "Complete Guide to pstack" Pt. 1/2 but extracted
  nothing) — X pages are likely unfetchable by WebFetch. Worth a note in
  SKILL.md's caveats if it recurs (second sighting).
