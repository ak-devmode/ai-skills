# /review — ai-skills @ `734c50a5ebd048424cb81fe149417a704a01508f..bb3f8a58bf0b0261f02f4177d2f6853df8a8b779` (4 commits)

**Review:** `10.4-r12` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.4-r12-01** `scripts/harness-scorecard/review_loop.py:439` (local-maxima · reopens 10.4-r10-02 · advisory (fallback reviewer)) — The maturity horizon is estimated with the same bias it is meant to remove. H is the p90 of root-to-close durations over CLOSED in-window lineages only (durs, line 437). (a) Right-censoring moves into the estimator: long lineages rooted near the cut are still open, so they are absent from durs and H comes out low. That is r10-02's 'keeps the short, drops the long' mechanism, now applied to the horizon. (b) A lineage that SHIPs at round 1 closes at its root review's own stamp (closure() returns ts_of(last) == root_ts), so its duration is exactly 0. Those zeros are the outcome being measured, and they push the p90 down. Verified: _p90([0]*9+[3d]) == 0. With H == 0, which is not None, every in-window lineage counts, including ones rooted seconds before the cut, and open lineages count as lower bounds. That is the original truncation, made worse. Trial lineages are the newest, so they sit nearest any too-short horizon and still show fewer fix rounds. H is also pooled over the outcome distribution, so it shifts between runs and when trial lineages close faster. The README says the cut is 'never on the outcome', but H is computed from outcomes. This is the third link of a reopens chain (r5-03 → r10-02 → this): a design problem, not another patch. See reframe. → Do not estimate the horizon from the data. Measure every lineage over the same fixed follow-up F from its root (see reframe).

## NOTE (1)

- **10.4-r12-02** `scripts/harness-scorecard/scorecard.py:72` (engine · reopens 10.4-r10-03) — window_class now classes a `--until D` run with the default since as 22d, while a default run is 21d. With --until, until = D 23:59:59 and since = until − 21×86400 = (D−21) 23:59:59, so d(until+1) − d(since) = 22. With no --until, since and until share a time of day, giving 21. Verified: window_class(day('2026-10-26',end=True)−21d, …) == '22d' and the default run gives '21d'. The fix's own line makes two 21-day windows incomparable, the class of defect r10-03 was about. The old round() gave 21 for both. The README's '`21d` by default' holds only without --until. → With no --since, derive since as the start of the UTC day 21 days before until's date (or pass day() dates on both ends), so both paths yield 21d. Add the --until-only case to the window-class test.

## Checked and clear

engine: base_of one-rule fix (r10-01) — non-codex reviews on both sides are recomputed via effort_for; review.py stamps effort_base for codex under rules 1 and 2 alike, so dropping the rules-1 `effort` branch loses nothing, engine: unstamped-root column (r10-04) — root_ts None is now its own column before the window test, engine: lineage bucket/lk is root-derived (lineage_rules maps every review to its root's version), so first-seen-review keying of trial_lin is order-independent, engine: load_logs(until) filters post-cut records, so cut == until is consistent with closure and maxr, lenses: fail-closed on no closed lineage (H None) is stated and implemented, tests: test_harness_scorecard.py 34 tests pass

## Not applicable

domain — generic repo, engine: SQL/data-migration, auth, frontend, LLM-trust boundaries — no surface

**Verdict:** SHIP

## Reframe

Fixed follow-up per lineage. Choose a constant F (e.g. 7 days, a named constant or --follow-up flag). A lineage counts when its root is stamped and root_ts <= cut − F. Its fix rounds and credit-outs are only those of reviews stamped within root_ts + F. Every lineage in every bucket then gets the same exposure, and the count does not depend on closure or on any statistic of the outcome. The metric becomes 'fix rounds within F'. A lineage longer than F is capped equally on both sides, and F can be chosen well past typical loop length.

Deletes: closure() and its acceptance-ordering logic; the `last` latest-review map; _p90; the H estimate and the notes['trial_maturity_horizon'] entry with its print block in scorecard.py; the 'Open at cut (rounds a lower bound)' column; the 'horizon unknown → none counted' fail-closed path · removes: 10.4-r12-01, 10.4-r10-02

## What this review did not cover

- codex cross-model gate — out of credits (claude-fallback)
- gstack specialist fan-out not dispatched — read-only pane brief scoped a single focused pass
- full scorecard replay — brief forbids it (CPU); horizon behaviour on real logs (actual H, share of r1 SHIPs) not measured
