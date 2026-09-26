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
**Last action:** /plan-ceo-review done — HOLD SCOPE, approach C, 17 findings accepted and folded into scope.md + 5.1–5.3 (2026-09-26)
**Next action:** `/plan-eng-review` on `5-verify-lever/scope.md`
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
| 5.1 | 5.1-verify-lever-PLAN.md | Phase 1 — Contracts + deterministic scripts | Draft | Gate A |
| 5.2 | 5.2-verify-lever-PLAN.md | Phase 2 — `/verify` + `/review` on codex | Draft | Gate A |
| 5.3 | 5.3-verify-lever-PLAN.md | Phase 3 — Wiring + self-heal + rollout | Draft | Gate A |

---

## Artifacts
- `artifacts/scope-brief.md` — the 2026-09-11 brief (pain, pstack, locked design)
- `artifacts/research-poteto-2026-09-26.md` — poteto research + Complete Guide Pt. 1 notes
- `artifacts/ceo-review-2026-09-26.md` — CEO review + codex outside voice, 17 accepted findings
