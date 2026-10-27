# /review — ai-skills @ `bb3f8a58bf0b0261f02f4177d2f6853df8a8b779..486a4430269696f9e67a0a2bc2d5409b77c5b1d0` (1 commits)

**Review:** `10.4-r13` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.4-r13-01** `scripts/harness-scorecard/review_loop.py:417` (engine · reopens 10.4-r12-01) — Right-censoring is back whenever the cut is later than the logs' own extent. cut = until, and cmd_run's default until is time.time() (scorecard.py:150), but every review log the analysis reads is an rsync copy (mba-plans/ and homelab-plans/, scorecard.py:118/133) frozen at the `.pulled` stamp. A lineage rooted in (pulled - F, now - F] passes the `root_ts <= cut - F` test and is counted as fully followed up, yet nothing after `pulled` exists for it, so its fix rounds, credit-outs and SHIP are truncated. Those are the newest lineages, i.e. the trial bucket - the exact bias the reframe exists to remove, and the reframe's own comment ('Every counted lineage is then observed for the full follow-up') is false for any run made after a pull. Same applies to an explicit --until later than the pull. The original defect of the chain (newest lineages cut short at the cut) is not fully fixed. → Make the cut the earlier of until and the data's end: parse `.pulled` in cmd_run and pass min(until, pulled) (fail closed - count no lineage as matured - when the stamp is missing or unparseable, rather than falling back to now), and add a test where until is a week past the last record and a lineage rooted at until - F is 'too young', not counted.

## NOTE (2)

- **10.4-r13-02** `scripts/harness-scorecard/scorecard.py:151` (engine · reopens 10.4-r12-02) — default_since makes the default window and an --until window of the same day different lengths under one class. Verified: until = 2026-10-27T12:00Z (a default run) gives since 2026-10-06T00:00 (21.5 days, 22 calendar dates); --until 2026-10-27 gives since 2026-10-07T00:00 (21.0 days). Both class '21d', so store.previous() compares them as like-for-like while the default run carries up to a day more data. The help text and README:28 ('the 21 calendar days ending at until') describe the --until case only; for a default run the window starts one day earlier. The class now agrees, but the window it vouches for does not - r12-02's comparability concern on the fix's own line. → Derive end from until's own date (dt.datetime.fromtimestamp(until).date() + 1 day for a mid-day now, i.e. treat the default until as inclusive of today) so both cases start at D-20, or snap the default until to the end of the previous UTC day.
- **10.4-r13-03** `scripts/harness-scorecard/README.md:123` (doc-claim) — README says an unstamped review 'is left out, counted in the run's footer', and the scorecard footer prints the count only when non-zero. From the CLI that count is always 0: cmd_run always sets since, so counted() (review_loop.py:301-304) returns False for a review with no stamp and the loop `continue`s at the inwin check before the follow-up code; the `t is None` branch that increments `unplaced` is reachable only with since=None, as the new test's own comment admits (test_unstamped_review_is_left_out_of_the_follow_up). Unstamped follow-up reviews are therefore dropped with no count in every real run. → Either count unstamped reviews of a lineage before the inwin skip (so the footer number is real), or drop the footer and README claim and say counted() excludes them.

## Checked and clear

engine: closed-only filter and estimated horizon fully removed (no remaining refs to closure/last/accepted/_p90/close_ts/horizon in review_loop.py, scorecard.py, store.py), engine: follow-up boundaries inclusive and consistent (root at until - F counts; review at root + F counts; tested), engine: trial vs pre-trial symmetry - one F, one window rule, one in_window/young/before/unstamped classification, bucket from lineage rules; no per-bucket branch in the follow-up path, engine: baseline 3.1 tables unaffected - byr/fbyr/bbyr, lineages and the per-review effort-trial table are computed before and independently of the follow-up block, which only feeds 'Effort trial lineages'; the baseline replay passes explicit --since/--until so default_since does not apply (read, not replayed), engine: store.profile adds follow_up_days, so runs with a different F are never Δ-compared, engine: --follow-up < 1 raises UsageError, which main() catches, lenses: fail-open - no-cut case counts nothing, tests: scorecard suite (36 tests) passes

## Not applicable

domain: generic repo, no Kalpa/PMG groups

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex cross-model review (out of credits) - this is a single-context Claude fallback
- gstack specialist fan-out (security, performance, testing, red-team, maintainability, data-migration, api-contract) - read-only review pane, not dispatched
- full baseline replay of the ten-month window to confirm 3.1 numbers reproduce - brief forbids it; checked by reading the code path only
