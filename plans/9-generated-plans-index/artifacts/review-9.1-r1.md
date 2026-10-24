# /review — ai-skills @ `6e4e6b67ec984ea656ded73a23de0f2537030d5f..193a692c98902c2f3ccd466339e90d0d39c84e68` (4 commits)

**Review:** `9.1-r1` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**full**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 16 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 9.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (0)


## SHOULD FIX (8)

- **9.1-r1-01** `scripts/plans-index.py:339` (silent-failure engine) — render/migrate regenerates PLANS-INDEX.md from the scope tables only; other tables (Pending PRDs), prose and the `**Gate mode:**` line are dropped with exit 0. A blocking graph (kalpa-iris) silently falls back to advisory in verify_lib.gate_mode. → migrate should refuse or warn on non-scope content or a Gate mode line, and move the line to README.md.
- **9.1-r1-02** `scripts/plans-index.py:276` (silent-failure engine) — write_block/write_text open with 'w' and write in place: a crash truncates the scope's progress.md, and concurrent sessions lose updates. → Write to a temp file and os.replace.
- **9.1-r1-03** `scripts/claim-scope-number.sh:61` (fail-open engine) — `render --stdout 2>/dev/null | ... || true` turns a render failure into local_max=0, so an unpushed loose-PRD number can be claimed twice. → Exit non-zero when render fails.
- **9.1-r1-04** `scripts/claim-scope-number.sh:34` (engine engine) — tree_nums uses ls-tree --name-only, so a file like plans/2026-10-24-notes.md counts as scope 2026 and the next claim is 2027. → Restrict to tree entries (ls-tree -d / type column).
- **9.1-r1-05** `scripts/claim-scope-number.sh:79` (engine engine) — Branch-name source now counts a number only if the branch tip has plans/<n>-*/; a pushed branch that claimed a number before creating the folder is missed, so two sessions can claim it. No test covers the regression. → Also count a branch whose tip has an index or loose-record row for the number.
- **9.1-r1-06** `scripts/plans-index.py:320` (engine engine) — Nothing detects the same scope number in two records or in a record plus a loose file; check passes because committed==fresh render, and status edits only the first match. → Make check/render fail on duplicate numbers.
- **9.1-r1-07** `scope/SKILL.md:674` (doc-claim engine) — Publish lines (scope §5.8, §7.2; plan §8.5b) say only bot mode drops index files; in local mode render also rewrites archive/INDEX.md, which §7.2 never publishes, so check later fails and claim reads a stale archive index. → Name archive/INDEX.md in the local-mode publish path list.
- **9.1-r1-08** `plan/SKILL.md:810` (doc-claim engine) — §11.4 and repo-cleanup D4.3 do not say move --with-plans repoints child N.P rows without changing their Status; an archived Done scope can show Draft children. → Require a plans-index.py status per child.

## NOTE (8)

- **9.1-r1-09** `scripts/plans-index.py:228` (engine engine) — Begin/end markers are matched as whole lines anywhere; a progress.md quoting them in a code fence is parsed or overwritten as the block. → Anchor to the block position or ignore fenced regions.
- **9.1-r1-10** `scripts/plans-index.py:508` (silent-failure engine) — branch_rows ignores rows the branch deleted; a mistyped path yields '0 row(s) changed' with exit 0. → Fail on a missing file or zero rows when rows were expected.
- **9.1-r1-11** `scripts/plans-index.py:974` (engine engine) — move_record promoting a loose row does two sequential write_block calls; a failure between them leaves the row in both places. → Write both atomically or in a recoverable order.
- **9.1-r1-12** `scripts/plans-publish.sh:44` (engine engine) — Bot-mode skip compares to abs_dir/PLANS-INDEX.md using logical pwd; a differently spelled or symlinked path bypasses the skip and commits the rendered index. → Use pwd -P on both sides.
- **9.1-r1-13** `closeout/scripts/verify-archive.sh:37` (fail-open engine) — render --stdout does not run lost_rows, so a clobbered record block reports 'NO INDEX ROW' rather than the real cause. → Run the lost-rows check or surface the render refusal.
- **9.1-r1-14** `prd/SKILL.md:277` (doc-claim engine) — Example hardcodes --folder prd-{slug}.md, but the text says a folder-form PRD lands in the folder's record; only --folder prd-{slug}/ does that and it is never shown. → Show both forms.
- **9.1-r1-15** `repo-cleanup/SKILL.md:364` (doc-claim engine) — Still says the registry (PLANS-INDEX.md) is 'edited', contradicting the script-only rule; cross-repo-init/SKILL.md:365 is the same leftover. → Reword to go through plans-index.py.
- **9.1-r1-16** `scope/AGENTS.md:162` (doc-claim engine) — After the claim-scope-number.sh instruction, the next line still says 'Assign the next whole number', the prose numbering the script replaced. → Delete the line.

## Checked and clear

verify_lib.gate_mode change, scan-archive-drift.py block parsing, prose flags/subcommands/exit codes vs plans-index.py --help, no duplicate section numbers (lint-skill.py 0 ISSUE), unit suite: 310 tests OK, 2 skipped

## Not applicable

domain groups: generic repo

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- codex unavailable (out of credits): Claude fallback with two read-only subagents (scripts, prose), not the full gstack specialist fan-out
- scripts/README.md exit codes for render/migrate/check not fully verified
- new tests other than claim-scope-number only skimmed
