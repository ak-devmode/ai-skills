# Progress: `/verify` + the verification lever

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔code mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each phase's surface against live code before entering it; raise gaps in
   batched blocks, not per-step.
3. Wrap + commit + check in at every phase boundary; progress updates land more often than
   that. This file alone must be enough for a cold context to resume.
4. Public repo: no credentials, tenant names beyond `clinic_3`, internal URLs, or PHI
   posture in anything committed here. Env specifics live in the private test-suite.
5. Dogfood: from Phase 2 on, this scope's own commits go through the codex `/review` gate
   and its phases through `/verify`.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/5-verify-lever/scope.md
**Last action:** Plan 5.1 Task 1.1 drafted — contracts + templates + examples + test_contracts.py (2026-09-26)
**Next action:** Alex reviews `templates/verify-contracts.md`; on approval, Task 1.2 (`resolve-identifiers.py`)
**Open blockers:** None
**Key files changed:** `scripts/plans-index.py` (70d1222 — unplanned fix, see Progress Log)

---

## Decisions Log
- (2026-09-11) Brief locked: two verification classes, rung not score, feature as the unit,
  codex judge + Claude fallback, lever on second sighting, fail-loud floor. See `artifacts/scope-brief.md`.
- (2026-09-26) Codex is the opposing voice for both `/review` and `/verify`; headless, no herdr.
- (2026-09-26) Every review finding gets a disposition; `/verify` audits rejections.
  Target failure: local maxima (over-building, invented names/contracts/paths).
- (2026-09-26) Review wherever there is a commit; commit-less phases get verify only.
- (2026-09-26) Older scopes self-heal: `/plan` drafts the finish-condition table, Alex confirms once.
- (2026-09-26) Seam: `/verify` defines the adapter contract; the private product test-suite
  fulfils it. Feature map + adapter live in the test-suite, not kalpa-docs.
- (2026-09-26) Test-suite becomes a kalpa-docs program (needs a PRD), scope 89 folded in;
  first member = fail-loud sweep + lints (moved out of this scope, Alex accepted).
- (2026-09-26) Invented-reality check built as a script in this scope (Alex: yes).
- (2026-09-26) `/review` flags dirty comments (workaround / hack / TODO-as-justification).
- (2026-09-26) clinic_3 in dev = temporary trial target; permanent = stood-up tenant per env.
- (2026-09-26) Faithful-port rule lives in `/verify`, not global CLAUDE.md.
- (2026-09-26) Brief's credentials redacted (`eaeb441`); brief moved to `artifacts/`.
- (2026-09-26) CEO review: approach C — a deterministic row passes only on runner evidence; the codex judge may only downgrade. Required fail/inconclusive blocks; latest run per check decides; evidence bound to SHAs. Gate enforced by plans-index.py, advisory for 3 clean scopes then blocking. Non-codex judge → ⚠ in PLANS-INDEX (Alex's D3 idea).
- (2026-09-26) Codex CLI upgraded 0.152.1 → 0.157.1 (npm) — the old CLI rejected gstack's model; live evidence for the judge-failure handling (F2).

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-09-11 | brief | Done | Placeholder brief — pain, pstack take/leave, locked design |
| 2026-09-26 | /research (scope 6 live test) | Done | poteto since 2026-09-11 → `artifacts/research-poteto-2026-09-26.md` |
| 2026-09-26 | /scope | Done | Phased, 3 plans (5.1–5.3), each exits on gate A |
| 2026-09-26 | /plan-ceo-review | Done | HOLD SCOPE; approach C (scripts + runner evidence floor, codex judge downgrade-only). Codex outside voice: 11 findings, 7 new. All 17 accepted → `artifacts/ceo-review-2026-09-26.md` |
| 2026-09-26 | /plan-eng-review | Done | 7 Claude + 9 codex findings, all accepted → `artifacts/eng-review-2026-09-26.md`; test plan → `artifacts/eng-review-test-plan-2026-09-26.md`. CEO + ENG CLEARED |
| 2026-09-26 | /plan-devex-review | Done | Triage. Getting started 3→8 (setup warns, `/verify --demo`, README section), errors 4→8 (message contract with cause class), stale-clone warning → `artifacts/devex-review-2026-09-26.md` |
| 2026-09-26 | Unplanned fix | Done | `scripts/plans-index.py`: `add` accepts per-plan `N.P` numbers; duplicate check compares the exact `#` cell (70d1222). Found by /scope §5.9 — stub rows were refused as non-integer |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Approve the Phase 1 contracts (finish table, verdict, disposition log, feature map, adapter) | [ ] Pending | 5.1 exit gate |
| Go/no-go after seeing a real `/verify` verdict (dogfood + clinic_3) | [ ] Pending | 5.2 exit gate |
| Announce the ai-skills `git pull` to the team after rollout | [ ] Pending | 5.3 exit gate; CLAUDE.md §2.1 |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 5.1 | 5.1-verify-lever-PLAN.md | Phase 1 — Contracts + deterministic scripts | Ready to execute | Gate A |
| 5.2 | 5.2-verify-lever-PLAN.md | Phase 2 — `/verify` + `/review` on codex | Ready to execute | Gate A |
| 5.3 | 5.3-verify-lever-PLAN.md | Phase 3 — Wiring + self-heal + rollout | Ready to execute | Gate A |

---

## Artifacts
- `artifacts/scope-brief.md` — the 2026-09-11 brief (pain, pstack, locked design)
- `artifacts/research-poteto-2026-09-26.md` — poteto research + Complete Guide Pt. 1 notes
- `artifacts/ceo-review-2026-09-26.md` — CEO review + codex outside voice, 17 accepted findings
- `artifacts/eng-review-2026-09-26.md` — eng review + codex outside voice, 16 accepted findings
- `artifacts/eng-review-test-plan-2026-09-26.md` — test plan (edge cases + critical paths)
- `artifacts/devex-review-2026-09-26.md` — DX triage review, persona, scorecard

---

## Plan 5.1: Contracts + deterministic scripts

### Resume Context (Plan 5.1)
**Last action:** Task 1.1 drafted — awaiting Alex's review
**Next action:** on approval, deepen 1.2–1.4 detail here, then Task 1.2
**Open blockers:** None

### Task Detail
Deepened at start of run (`/markdown-style` §8.9.2), from scope.md §4.1 + eng review. The
plan file is unchanged; where this block and the plan differ, the plan wins, so ask.
- **1.0** — `scripts/tests/` (`_helpers.py` runs scripts as subprocesses or loads them by
  path, since hyphenated names can't be imported) + `test_entrypoint.py` (compile-checks every
  `scripts/*.py`). CLAUDE.md §6 `Test:` line (the field `/closeout` §5.2 detects first);
  scripts/README.md gets a Tests note. **Deviation:** the plan allowed "0 tests is a pass",
  but on Python ≥ 3.12 `unittest discover` exits 5 when no tests run, so the entrypoint ships
  with one real test.
- **1.1** — templates in `templates/`, filled examples in `templates/examples/`. Each contract
  opens with a reader/writer header. Plus `scripts/tests/test_contracts.py`: generate each file
  from its template, assert no example rows. Stop for Alex's review.
- **1.2–1.4** — detail written when 1.1's contracts are approved, since those contracts fix
  the scripts' field names and messages. Tests follow the eng review's coverage map
  (`artifacts/eng-review-2026-09-26.md` §2). Every error message is checked against the
  message contract.

### Session: 2026-09-26 (Alex / Claude)
- **Phase 0** ✅ DONE. Input and related-doc paths all resolve. Status is Ready (Alex's go
  signal, 8173b95). `Executed by` was stamped. Repo Graph check exited 4 because the numbered
  heading doesn't match what the script looks for; this is a single-repo scope with linear
  history, and it's logged as a ledger risk flag. herdr pane present, but Primary repo is none,
  so no worktree. Ledger created. Branch: `main` (direct-to-main per CLAUDE.md §2). Sibling
  plans 5.2 and 5.3 read.
- **Unplanned (before Phase 0):** `/markdown-style` §8.9.2/§11.5.3 contradicted `/plan` §8.1
  on stub deepening. Resolved: detail goes in progress.md. Files: `markdown-style/SKILL.md`,
  `plan/SKILL.md`, `scope/templates/plan-stub.md.template` (e8bdc4d, pushed).

#### Task 1.0: Test entrypoint — ✅ DONE
- **Files created:** `scripts/tests/_helpers.py`, `scripts/tests/test_entrypoint.py`
- **Files modified:** `CLAUDE.md` (§6 `Test:` line + suite note), `scripts/README.md` (Tests note)
- **Verified:** `python3 -m unittest discover scripts/tests` → 1 test OK, exit 0; `grep '^Test:' CLAUDE.md` hits

#### Task 1.1: Contract documents — ⏸️ WAITING_HUMAN (review)
- **Files created:** `templates/verify-contracts.md` (the spec, §1–§10); templates
  `templates/finish-conditions.md.template`, `features-README.md.template`, `feature.md.template`,
  `feature-map-handoff.md.template`; examples `templates/examples/finish-conditions.md`,
  `verify-log.jsonl`, `review-log.jsonl`, `features/README.md`, `features/sign-in.md`,
  `feature-map-handoff.md`; `scripts/tests/test_contracts.py`
- **Verified:** suite 10 tests OK. Mutation check: a planted table row, and a row parked in an
  HTML comment, are both caught by the detector.
- **Design calls for Alex:** one normative spec, with templates only for files that get
  generated per scope. `verify-run.py` is the only writer of the verdict log, for all three run
  states. A table revision bump invalidates earlier verdicts. Every row is required. The message
  contract is lint-skill's four fields plus `cause` and `docs`.

#### Unplanned: `repo-graph-check.py` numbered heading + empty-section false pass (Alex: fix now)
- **Files modified:** `scripts/repo-graph-check.py`, `plan/SKILL.md` (§5.6.1 exit-4 wording, 3.8.2)
- **Files created:** `scripts/tests/test_repo_graph_check.py`
- **Why:** the heading regex missed `## 2. Repo Graph`, the numbering `/markdown-style`
  requires. Fixing only that would have exposed a second defect: a prose-only section parses
  to zero rows and printed "all unchanged — proceed", a false pass. Both are fixed, and both
  are covered by table-driven tests. Scope 5 now returns exit 4, "nothing was checked".
- **Verified:** suite 12 tests OK.

#### Task 1.1 — ✅ DONE (Alex approved contracts 2026-09-26)
- Alex also decided that disposition coverage (every finding ID dispositioned) is enforced in
  `verdict-gate.py` rather than by `/verify` judgment, so it can't drift. Spec §5.2/§6
  updated to match. This adds to Task 1.4.
