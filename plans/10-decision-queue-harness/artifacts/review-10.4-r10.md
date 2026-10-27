# /review — ai-skills @ `8cbc75c6916c1f133eca204cbca435b930a1222e..734c50a5ebd048424cb81fe149417a704a01508f` (7 commits)

**Review:** `10.4-r10` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 4 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (2)

- **10.4-r10-01** `scripts/harness-scorecard/review_loop.py:251` (engine · reopens 10.4-r5-02) — base_of() buckets every trial review without effort_base as `unstamped`, but review.py:628 stamps effort_base only for codex reviewers (`base if codex else None`). So a trial lineage whose root was a claude-fallback (a codex credit-out at round 1) or a lean review always lands in `trial · base unstamped`, never its real base tier, while a pre-trial lineage with the same root is recomputed into its tier via effort_for on its range. The per-tier trial rows therefore undercount credit-outs on the trial side only, and Credit-outs % is half the keep-per-bucket decision rule. Codex fix rounds of such lineages also leave their tier, since lk takes the root's base. The docstring's justification ('review.py's stamp is the tier it ran from') holds only for codex reviews; a non-codex review never had a stamp to trust. → Apply the same rule to both buckets: effort_base when stamped, else effort_for on the review's own range through git.stat (`unresolved` when git cannot read it). Keep `unstamped` only for a codex trial review that should have carried a stamp. Add a test with a trial lineage rooted on a `claude-fallback … out of credits` review, asserting it counts under its range's tier.
- **10.4-r10-02** `scripts/harness-scorecard/review_loop.py:358` (engine · reopens 10.4-r5-03) — Excluding open lineages replaces truncation with right-censoring, and the bias points the same way. Whether a lineage is closed at the cut depends on its length: one that SHIPs at r1 closes at once, while one still looping at r3 is open. Dropping open lineages keeps the short ones and drops the long ones, more so the closer the root is to `until`. Trial lineages are the newest, so the trial bucket loses more of its long lineages and still shows fewer fix rounds per lineage and fewer credit-outs (tr_all/tr_out are closed-only too). The new 'Open (excluded)' column gives a count, but no rounds, so a reader cannot correct for it. This is the metric that decides whether the trial is kept. → Make the censoring equal across buckets instead of conditional on the outcome. Count only lineages whose root is at least a maturity horizon before `until` (e.g. the observed p90 root-to-close time, or a fixed 7 days), whether closed or not, and report the open ones' current rounds as a lower bound beside them. Add a test where a long trial lineage is still open near `until` and must not lower the trial's fix rounds/lineage.

## NOTE (2)

- **10.4-r10-03** `scripts/harness-scorecard/scorecard.py:156` (engine) — Window class is round((until - since)/86400). With --since and no --until, `until` is time.time(), so the class depends on the hour of the run: the same `--since 2026-10-06` gives 21d before noon UTC and 22d after. Two runs meant to be comparable then never match each other, and the run prints 'No previous run … no Δ' with no hint as to why. → Compute the class from calendar days (date(until) - date(since)), or snap a no-`--until` run's `until` to end of day before deriving the class.
- **10.4-r10-04** `scripts/harness-scorecard/review_loop.py:356` (dirty-comment) — counted(root) is False for a root with no timestamp when `since` is set, and cmd_run always sets `since`. So an unstamped root is reported under 'Rooted before window (excluded)', which says something about its date that was never known. → Split it out ('Unstamped root (excluded)'), or rename the column to cover both cases.

## Checked and clear

10.4-r5-01 fix: lineage WARNs captured per unit (prefix matches verify_lib.py:510/522), other stderr counted apart, captured in `finally` so a failed unit's stderr is counted too, and printed by cmd_run, 10.4-r5-04 fix: store.previous matches flags + window class; legacy runs match nothing; a newer unreadable run stops the search with a WARN rather than falling through to an older reference, 10.4-r5-05 fix: PullTest covers non-Darwin refusal, both symlink refusals, missing homelab source, empty read-back without stamp, and the stamp on success, UsageError: only day() raises it; the other run-time ValueErrors now surface as failures, not exit 2, errors='replace' on git/rsync/ssh output: only ASCII hunk headers, numstat counts and paths are parsed, Git.stat file/line counts match verify_lib.diff_stat's shape for effort_for (binary files count as files, 0 lines), --no-git: Git(enabled=False) returns None, so base_of yields `unresolved`, not a crash, scripts/tests/test_harness_scorecard.py: 30 tests pass

## Not applicable

domain checks — generic repo, data-migration, API contract, frontend/design — no surface in range

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex cross-model gate — codex out of credits (claude-fallback)
- specialist fan-out (security/performance/testing/red-team/maintainability) not dispatched: a single-context pass on a 436-line fix range, from a read-only pane told to keep tool output small
- full scorecard replay over the pulled logs — excluded by the brief (CPU); bias claims reasoned from code and tests
- gstack review telemetry (gstack-review-log) — not written from a read-only pane
