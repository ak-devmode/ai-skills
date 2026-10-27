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
nice -n 10 scripts/harness-scorecard/scorecard.py run [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--follow-up DAYS]
```

- `pull` from the MBA (refuses elsewhere). Reads homelab2026 over ssh (rsync's sender side;
      nothing is written there). Exit 1 when ssh fails or a destination reads back empty.
- `run` defaults to the 21 calendar days ending at the date of `--until` (or today): since is the
      start of the UTC day 20 days before that date, so a default run and an `--until` run of the
      same day start on the same date and are both `21d`. The cut for "matured" lineages is
      min(until, `.pulled`): the logs stop at the pull, so a later `until` observes nothing more.
      A missing or unparseable `.pulled` stamp counts no lineage as matured (stderr says so).
      It takes minutes and a CPU core: lineage
      resolution and §3.2/§3.3 read git ancestry and diffs in `~/Projects`. Run it once per
      look, not in a loop.
- `--follow-up DAYS` (default 7, printed) is the effort trial's fixed follow-up (§4.5).
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

**Both accounts are already in these inputs.** Each host's two Claude accounts share one
projects dir through a symlink made on 2026-10-02:

```
MBA       ~/.claude-int/projects   -> ~/.claude/projects    (integrations -> alex@work's dir)
homelab   ~/.claude-alex/projects  -> ~/.claude/projects    (alex@work -> integrations' dir;
                                                             ~/.claude is integrations there)
```

So `~/.claude/projects` on each host holds every account's sessions, and the default
inputs count all of them. Do not add the other account's dir as a second input: it is the
same files, and every session would be counted twice. If a symlink is ever replaced by a
real directory, that account's sessions drop out of the scorecard, and the inputs need
changing then.

3.2 **Store** `~/.cache/harness-scorecard/<UTC stamp>.json`: one file per run, numbers
only, plus the run's flags (`git`, `sessions`), window class (its length in calendar days,
`21d` by default — dates, not elapsed hours, so a `--since` run's class does not move with the
hour it ran) and follow-up.
The next run's Δ columns compare against the latest file with the **same flags, window
class and follow-up** — a `--no-git` run, a `--no-sessions` run or the ten-month baseline replay is never a
default run's reference — and the header names the reference's window and flags. A run stored
before flags existed matches nothing. If a newer file is unreadable, the run prints a WARN and
leaves Δ out. The Δ is advisory, so it never blocks today's numbers.

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
forward. An exact reproduction needs the 2026-10-25 snapshot of the cache. A later pull copies
logs that snapshot missed: after the 2026-10-27 pull, the same window holds 100 units and 683
reviews, not 86 and 622.

4.4 **Queue answers.** A typed prompt that starts `[lane ` is a pasted decision-queue reply (the
packet's prefilled reply). Its latency is the wait since that session's last assistant message.
The other prompt categories are regex. Treat their shares as ±5 points.

4.5 **Effort trial.** Codex reviews split into trial (lineage rules 2+) and pre-trial, then by
base tier (`effort_base`, effort_for's tier before the bump), then into round 1 and fix rounds.
One rule buckets both sides: the stamped `effort_base`, else effort_for on the review's own
range (review.py stamps codex reviews only, so a fallback or lean review is always recomputed);
a range git cannot read is `unresolved`; `unstamped` is only a codex trial review that lacks
the stamp it should carry. A lineage takes its root's base. The lineage table shows fix rounds
per lineage, the share of codex credit-outs (the fallback reviewer is the noisy one) and the
share that reached SHIP, over a **fixed follow-up F** (`--follow-up`, default 7 days), the same
for every bucket: a lineage counts when its root is in the window and at or before `until − F`,
and its outcome is read only from reviews within F of its root. Nothing is estimated from the
data and nothing depends on whether a lineage closed. **Why:** trial lineages are the newest,
so at any cut more of them are still looping. Counting them as they stand truncates their
rounds; dropping the open ones keeps the short lineages and loses the long; a cut estimated
from closed lineages inherits the same skew. All three right-censor the trial bucket toward
fewer fix rounds — the metric that decides the trial. A fixed follow-up observes every counted
lineage for the same F, so none is cut short. Lineages rooted after `until − F` (too young),
rooted before `--since` (counted from their tail only), or with an unstamped root are excluded
and counted in their own columns; a review with no stamp cannot be placed in F and is left
out, counted in the run's footer. The trial is kept per bucket when
findings move earlier without more credit-outs. A stamped `round` that disagrees with the
recomputed one is counted under `stamped-round mismatches`.

4.6 **Not carried over.** §3.3's hand-read sample (new defect vs not fully fixed) needs a reader,
not a script, so the scorecard does not reproduce it.
