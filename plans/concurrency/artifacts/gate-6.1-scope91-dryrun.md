# Gate 6.1 artifact — partitioner known-answer test over wellmed scope 91

Run: 2026-08-23, procedure SKILL.md §4 applied by hand against
`kalpa-docs/plans/91-wellmed-finance-jurnal/` (stubs of 2026-08-13).
Expected answer (fixed in scope.md §6.1 BEFORE the run): dispatch 91.2 only;
91.1 human-gated; 91.3–91.7 refused.

## 1. Dry-run output produced

```
CONCURRENCY PLAN — scope 91 @ wellmed        [DRY RUN — nothing dispatched]
ready frontier (cap 2):
  91.2  seat=opus  branch=concurrency/91-91.2
        worktree=<backbone worktree>  freeze=saga/accounting + connector dirs
        pane label: 91#91.2@opus
excluded:
  91.1  HUMAN-GATED: Alex renews Jurnal company 760986 or issues creds
        against sandbox.jurnal.id company 71368 (stub: "Blocked on a human
        step (H1). Nothing here proceeds until a writable Jurnal company
        exists." Gate A, human)
  91.3  BLOCKED by 91.1: bootstrap writes against the Jurnal API; payload
        contract re-verification is 91.1's output. Also Gate A+D (human
        supplies per-tenant credentials).
  91.4  BLOCKED by 91.2 (posts through the connector contract 91.2 defines)
        and 91.3 (control product must be funded/bootstrapped first).
  91.5  HUMAN-GATED (domain-ownership toggle is Alex's call, open Q 9.1)
        and BLOCKED by 91.4.
  91.6  BLOCKED by 91.3 (webhook registration happens there) and 91.4
        (emitter-before-consumer: 91.6 reads payment events against
        documents 91.4 posts). NOTE: 91.6's own stub declares NO dependency
        — both edges come from §4.2 rule 3 (domain rules) and rule 1 applied
        to the index row, not from the stub.
  91.7  BLOCKED by 91.4–91.6 (reconciles what they post/read); Gate A
        (Alex signs).
Run again with --dispatch to execute.
```

## 2. Verdict

Matches the pre-registered answer exactly. The 91.6 case demonstrates the
edge-rule requirement: stub-text-only classification would have put 91.6 in
the ready frontier (its stub is silent on dependencies); the domain rules
(emitter-before-consumer) and cross-referencing the index row excluded it.

## 3. Observations filed for the 91 refresh pass (6.5 precondition)

- 91.2's stub carries a "## Phase 1: Sandbox, credential hygiene…" heading at
  line 24 — likely a program phase-map section, but verify it is not stale
  copied content before executing 91.2.
- Whether `saga.*.postfinancejournal` was already renamed anywhere on
  `origin/develop` since 08-13 must be content-grepped before dispatching
  91.2 (done-means-written rule).
