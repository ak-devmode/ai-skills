# /review — ai-skills @ `a1be8c30fadc04109f5321590eaba97a7393800a..64a72d69f91ac469ba89c4ac49f26211f384a43f` (5 commits)

**Review:** `7.1-r4` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 7.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>")`

## BLOCKING (3)

- **7.1-r4-01** `scripts/verdict-gate.py:397` (engine) — Any NOT-JUDGED row crashes the whole-scope gate: closeout_view passes cause='not-judged' to verify_lib.message, whose assertion permits only code, environment or tooling. Reproduced AssertionError('not-judged'); --all emits neither its JSON verdict nor its marker, breaking closeout. → Render NOT-JUDGED diagnostics with cause='tooling' and level='WARN'; test --all with unjudged rows in both text and JSON modes.
- **7.1-r4-02** `scripts/plans-index.py:299` (fail-open) — validate accepts a Done row carrying '⚠ verify not judged' even when the gate exits 1 in blocking mode. An advisory Done row therefore remains 'conformant' after switching to blocking, and a hand-written marker bypasses the detective gate. Reproduced validate returning 0 for that blocking verdict. → Accept the NOT-JUDGED marker only when the gate exits 0; require a validation failure when blocking mode returns 1.
- **7.1-r4-03** `scripts/verify-run.py:160` (fail-open) — When --owner is omitted, cmd_run assigns the first row's unit to every execute call. The new shortcut consequently checks later phases against the first phase's review log. Reproduced a 5.2 rejection check auto-passing from review-5.1.jsonl despite a standing rejection in review-5.2.jsonl; pending_of then excludes it from judging. → Resolve the rejection-audit unit from each row's owner, including its phase prefix, and test an all-row run containing phases with different rejection states.

## SHOULD FIX (0)


## NOTE (0)


## Checked and clear

Lenses §1: whole touched files and relevant callees/consumers read, Engine: shell injection and structured reviewer-output validation, Lenses §3: changed error paths checked for swallowed failures, Lenses §4: new identifiers and reuse checked, Lenses §5: workaround comments checked, Lenses §7: finding targets and severity cap applied, Changed Python files parse; both changed skills pass deterministic lint

## Not applicable

Domain rules: generic repo, SQL, database schema and migration checks, Async endpoint mixing, frontend rendering and time-window checks, Publish workflows and cross-platform release checks

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- Automated unittest suite: fixtures require temporary files and Git writes forbidden by the read-only sandbox.
- Live judge execution/retry and Claude skill invocation were not exercised.
- Specialist sub-reviewer passes were not performed.
