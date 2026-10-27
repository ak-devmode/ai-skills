# harness-scorecard

## 1. What it is

The harness baseline (scope 10, `plans/10-decision-queue-harness/artifacts/baseline-2026-10-25.md`)
as a re-runnable scorecard. The one-off mining scripts became these modules:

```
scorecard.py    CLI: pull | run                          (mining: —)
sessions.py     §1 volume, §2 activity cost, §4 attention (mine.py, mine2.py)
review_loop.py  §3 reviewers, §3.1 lineage rounds,        (reviews.py, lineage.py,
                §3.2 where findings land, §3.3 per line,   infix.py, fixpairs.py)
                effort trial
store.py        run store, delta, markdown tables
```

Tests: `scripts/tests/test_harness_scorecard.py` (synthetic logs, stdlib only).

## 2. Usage

```
scripts/harness-scorecard/scorecard.py pull
nice -n 10 scripts/harness-scorecard/scorecard.py run [--since YYYY-MM-DD] [--until YYYY-MM-DD]
```

- `pull` from the MBA (refuses elsewhere). Reads homelab2026 over ssh (rsync's sender side;
      nothing is written there). Exit 1 when ssh fails or a destination reads back empty.
- `run` defaults to the 21 days before now. It takes minutes and a CPU core: lineage
      resolution and §3.2/§3.3 read git ancestry and diffs in `~/Projects`. Run it once per
      look, not in a loop.
- `--no-sessions` skips the transcript scan, `--no-git` skips the §3.2/§3.3 diff analyses,
  `--no-save` prints without storing.

Exit codes: 0 ok · 1 a step failed (named on stderr) · 2 usage.

## 3. Data

3.1 **Cache** `~/.cache/harness-logs/` (the baseline layout):

```
mba/claude-projects    -> ~/.claude/projects        (symlink)
mba/codex-sessions     -> ~/.codex/sessions         (symlink)
homelab/.claude/projects, homelab/.codex/sessions   (copied)
mba-plans/, homelab-plans/   Projects/** and .herdr/worktrees/** plans/**/artifacts/** (copied)
.pulled                      last successful pull (UTC)
```

Copies are never pruned. Worktrees are deleted after merge, and their review logs survive
only here.

3.2 **Store** `~/.cache/harness-scorecard/<UTC stamp>.json`: one file per run, numbers
only. The next run's Δ columns compare against the latest file. If that file is unreadable,
the run prints a WARN and leaves Δ out. The Δ is advisory, so it never blocks today's numbers.

3.3 **No text leaves the logs.** Transcripts and review logs can carry patient data. The
scorecard classifies prompt text in memory and stores and prints counts only. Never commit
cache or store contents to the repo.

## 4. Method notes

4.1 **Rounds are per lineage.** They come from review.py's own `rounds()`, called once per unit
(calling `review_round()` per id re-runs it and makes the count quadratic). A unit's `r<n>` is
never used. The lineage rule is versioned (decision 65), so an unstamped, pre-cutover lineage keeps
the old rule and old windows reproduce.

4.2 **Window.** Review records stamped after `--until` are dropped before lineage resolution, so the
logs read as they were on that day. Every earlier record feeds the lineage, but only reviews
stamped on or after `--since` are counted. Session records count when their timestamp falls in
the window.

4.3 **The baseline's §3.1 had no lower bound.** It counted every review logged up to 2026-10-25
(621 reviews, 72 of them before 2026-10-04). To reproduce it, run
`run --since 2026-01-01 --until 2026-10-25`. The 21-day default is the honest window going
forward.

4.4 **Queue answers.** A typed prompt that starts `[lane ` is a pasted decision-queue reply (the
packet's prefilled reply). Its latency is the wait since that session's last assistant message.
The other prompt categories are regex. Treat their shares as ±5 points.

4.5 **Effort trial.** Codex reviews split into trial (lineage rules 2+) and pre-trial, then into
round 1 and fix rounds. The lineage table shows fix rounds per lineage and the share of
codex credit-outs (the fallback reviewer is the noisy one). The trial is kept per bucket when
findings move earlier without more credit-outs. A stamped `round` that disagrees with the
recomputed one is counted under `stamped-round mismatches`.

4.6 **Not carried over.** §3.3's hand-read sample (new defect vs not fully fixed) needs a reader,
not a script, so the scorecard does not reproduce it.
