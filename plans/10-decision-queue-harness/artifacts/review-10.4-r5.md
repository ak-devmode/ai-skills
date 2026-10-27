# /review — ai-skills @ `40add649e1246e619717602181273e4f6c7c07e8..8cbc75c6916c1f133eca204cbca435b930a1222e` (4 commits)

**Review:** `10.4-r5` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 5 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (5)

- **10.4-r5-01** `scripts/harness-scorecard/review_loop.py:179` (silent-failure engine) — rounds() runs under redirect_stderr(io.StringIO()) and the buffer is discarded. review_lineage's fail-closed path prints a [WARN] to stderr whenever git cannot tell whether a range holds a fix or overlaps an earlier review, and then continues the prior/highest round instead of starting at round 1. Those are exactly the cases that inflate the §3.1 lineage-round table, and they depend on which host's clones hold the commits (homelab-only worktree branches, pruned history). The scorecard throws the signal away, so a run can shift reviews from r1 into r4+ with no note; stamped_round_mismatches only catches records that carry a stamped round. → Keep the captured stderr, count the `[WARN] lineage of` lines per unit, and put the total (plus the units affected) in notes and in the printed footer next to `rounds() calls`. Apply the same treatment to any other stderr capture in analyze: name what was suppressed, never drop it.
- **10.4-r5-02** `scripts/harness-scorecard/review_loop.py:284` (engine engine) — The effort-trial comparison is bucketed only by trial vs pre-trial (lineage rules) and round 1 vs fix rounds. The scope's decision rule says the bump is 'kept per bucket' when findings move earlier without more credit-outs, and review.py stamps `effort_base` on every codex record for this purpose. The scorecard never reads effort_base: `tiers` counts only the bumped `effort`. So it cannot say whether the trial pays off for, say, low→medium but not high→xhigh, which is the decision the trial exists to inform. → Key the trial tables (codex rows and the lineages table) by effort_base as well, e.g. `trial · base low · round 1`, with pre-trial lineages bucketed by verify_lib.effort_for on their range (or by their stamped effort, which equals the base under rules 1). Count records that are missing a base as `unstamped` instead of dropping them.
- **10.4-r5-03** `scripts/harness-scorecard/review_loop.py:288` (engine engine) — 'Fix rounds/lineage' is the max in-window round per lineage minus 1, and it counts lineages that are still open. Trial lineages are by definition the newest, so more of them are mid-loop at the cut and their round counts are truncated. That biases the trial bucket toward fewer fix rounds, which is the very metric that decides whether the trial stays. In the other direction, a pre-trial lineage whose r1 fell before `since` is counted from its in-window rounds only. → Count a lineage only when it is closed (its latest review's verdict is SHIP, or the unit was accepted) and its root is in the window. Report the number of open lineages excluded per bucket.
- **10.4-r5-04** `scripts/harness-scorecard/scorecard.py:147` (engine engine) — store.previous() returns the latest stored run whatever its flags were, and --no-git and --no-sessions runs are saved by default. After a `--no-git` run, the next full run's Δ for §3.2 compares against a table where every finding was `unresolved`, and §3.3 compares against an empty table. After a `--no-sessions` run, every §1/§2/§4 row shows 'new'. The p4-scorecard-reproduces replay of the baseline window also becomes the Δ reference for the next default 21-day run. The Δ looks like movement but comes from the configuration. → Store the flags (git, sessions) and the window in `result`, and have previous() pick the latest run with the same flags. Either skip saving partial runs, or print the Δ reference's flags and window and suppress Δ cells for tables that the reference did not compute.
- **10.4-r5-05** `scripts/harness-scorecard/scorecard.py:74` (engine engine) — cmd_pull has no test. The suite never exercises the MBA-only guard (non-Darwin refuses), refusing to overwrite a wrong or non-symlink `mba/claude-projects`, failing when homelab lacks .claude/projects, the read-back that fails a pull which copied nothing, or the .pulled stamp. These are the pull's safety claims (MBA → homelab only, read-only, read back), and a regression in any of them would ship green. → Add tests with platform.system, subprocess.run (ssh/rsync) and HOME patched to a temp dir. Assert the non-Darwin refusal, both symlink refusals, the missing-dir refusal, that an empty read-back exits 1 without writing .pulled, and that rsync is only ever invoked with the homelab host on the source side.

## NOTE (0)


## Checked and clear

Rounds per lineage: review_loop.analyze calls rv.rounds() once per unit (test_rounds_called_once_per_unit) and reads the round from the lineage map, never the unit's r<n> (test_rounds_follow_lineage_not_unit_rn)., Lineage history: every record up to `until` feeds rounds(), and only reviews stamped at or after `since` are counted (test_since_keeps_history_for_lineage, test_until_drops_later_records)., No raw text in outputs: the store holds only tables (cols, numeric rows, labels taken from reviewer family, model, permission mode and category names) plus notes (scope/unit ids, exception class names). Prompt text is classified in memory and never returned. Rejection reasons are only regex-tested. The CLI test asserts that a planted secret reaches neither the store nor stdout., Pull direction: runs only on Darwin; homelab is touched only by a read-only `[ -d ]` probe and as the rsync sender. No --delete. Errors exit non-zero, and an empty read-back is a failure., Store: never overwrites an earlier run (os.link onto a microsecond stamp), reads the write back, and a corrupt previous run gives a WARN with no Δ instead of a crash., Effort-trial bucketing by lineage rules_version matches verify_lib.review_effort, which bumps only when the lineage's rules are 2+., Suite: test_harness_scorecard.py passes (17 tests) via `discover -s scripts/tests`.

## Not applicable

Kalpa/PMG domain groups — generic repo (ai-skills).

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex out of credits — Claude fallback, single context; gstack specialist subagents not dispatched (read-only pane, tool output kept small per brief).
- Did not run the full ai-skills suite (p4-unit-suite) — only the scorecard test file.
- Did not re-run the scorecard on the real ~/.cache/harness-logs baseline window to check p4-scorecard-reproduces; that belongs to /verify's judge row.
- Did not run cmd_pull against homelab2026 (no network side effects from a review pane).
- sessions.py categories/SIG regexes were checked for text leakage only, not re-validated against baseline §1/§2/§4 numbers.
