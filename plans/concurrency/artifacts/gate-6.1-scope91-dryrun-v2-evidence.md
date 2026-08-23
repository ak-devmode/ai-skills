# Gate 6.1 v2 — from-scratch rerun under §4.0 evidence rules

Run: 2026-08-23, after Alex's correction: never take the scope's word for it.
Supersedes v1 (`gate-6.1-scope91-dryrun.md`) as the gate record; v1 kept as
the contrast. All evidence from fetched `origin/develop` / `origin/main`
content-greps and kalpa-docs git history — read-only, bounded.

## 1. What the rerun changed vs v1

- **v1 error caught: 91.2's touch-set repo was WRONG.** v1 said backbone.
  Ground truth: `saga.*.postfinancejournal.{trigger,compensate}` lives at
  `wellmed-finance internal/queue/steps/handler.go:50-51` on
  `origin/develop`, with the "4 existing tests" in `handler_test.go` +
  `topology_integration_test.go` beside it. Backbone has ZERO hits for
  `financejournal` on any remote branch. Worktree + freeze paths move to
  wellmed-finance.
- Rename confirmed NOT done: `postaccounting` has zero hits in
  wellmed-finance (and backbone) on origin/develop. 91.2 stands.
- 91.6 premise verified: `JURNAL_FORWARD_URL` present on gateway-go
  `origin/develop` (`internal/config/env.go`, docs) — the "adopt the
  already-live route" claim is true. Exclusion edges unchanged
  (91.3 registers the webhook; 91.4 emits what 91.6 consumes).
- 91.1: no renewal recorded — no kalpa-docs commits touching `plans/91-*`
  since 2026-08-13; 91's progress.md still ends at the 08-13 credential/
  sandbox findings. Verdict `HUMAN-GATED`, stamped **UNVERIFIED-EXTERNAL**
  (Jurnal-side state not checkable read-only from here).

## 2. Dry-run output (v2)

```
CONCURRENCY PLAN — scope 91 @ wellmed        [DRY RUN — nothing dispatched]
ready frontier (cap 2):
  91.2  seat=opus  branch=concurrency/91-91.2
        worktree=wellmed-finance  freeze=internal/queue/steps/
        pane label: 91#91.2@opus
        evidence: routing key at handler.go:50-51 origin/develop; zero
        postaccounting hits; no dependency on 91.1 in stub or code
excluded:
  91.1  HUMAN-GATED (UNVERIFIED-EXTERNAL): writable Jurnal company —
        renew 760986 or issue creds vs sandbox.jurnal.id (71368)
        evidence: no renewal in kalpa-docs since 08-13 claim date
  91.3  BLOCKED by 91.1 (writes against Jurnal API; contract re-verify is
        91.1 output); Gate A+D human creds
  91.4  BLOCKED by 91.2 (posts through the contract 91.2 renames/defines —
        handler.go IS the seam) and 91.3 (funding/bootstrap)
  91.5  HUMAN-GATED (domain-ownership toggle, open Q 9.1) + BLOCKED by 91.4
  91.6  BLOCKED by 91.3 (webhook registration) and 91.4
        (emitter-before-consumer)
        evidence: route itself verified live (JURNAL_FORWARD_URL,
        gateway-go env.go origin/develop) — existence ≠ ready
  91.7  BLOCKED by 91.4–91.6; Gate A (Alex signs)
Run again with --dispatch to execute.
```

## 3. Verdict

Frontier unchanged from the pre-registered answer (91.2 only) — but the
dispatch record v1 would have produced was materially wrong (wrong repo,
wrong worktree, wrong freeze paths). The evidence rules are load-bearing,
not ceremony. Gate 6.1 PASSED on the v2 record.

## 4. Incidental observations

- New branch `origin/plan/127-acl-permission-store` appeared in kalpa-docs —
  unrelated fleet activity, noted only so the fetch delta is accounted for.
- 91 progress.md documents that the develop HMAC credential reaches TWO
  Jurnal companies with writes pinned to the credential's own company, and
  test objects were created in production 776378 (zero net GL) on 08-13 —
  context any 91.1 executor must read before touching the API.
