# /review — ai-skills @ `f7f3d30d24f155b9990746b5d0cbfce018f28580..9e2c0ac92e1e1d823862c6ad6f4c9cd90fe98c6b` (7 commits)

**Review:** `10.3-r2` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 6 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.3 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (1)

- **10.3-r2-01** `scripts/driver-merge.py:157` (fail-open · reopens 10.3-r1-02) — The r1-02 fix depends on herdr putting $HERDR_AGENT_NAME into a lane's environment, and nothing does that. New evidence: this review pane was launched by herdr (HERDR_PANE_ID, HERDR_TAB_ID, HERDR_WORKSPACE_ID and HERDR_SOCKET_PATH are all set) and $HERDR_AGENT_NAME is unset. Nothing in ai-skills (herdr/SKILL.md, herdr-pane.sh, concurrency/SKILL.md) sets it. Lanes are named with `herdr pane rename` / report-metadata, and the driver with `herdr agent rename $HERDR_PANE_ID driver` (herdr/SKILL.md:73). A rename after launch cannot change a running process's environment. So a real lane gets `name` == '' and falls through to pk.is_driver(a). The `--driver` in /plan's documented step-4 command then accepts it, which is exactly the r1-02 scenario. The real driver is in the same position: it also has no HERDR_AGENT_NAME and is a driver only because of --driver. Lane and driver are still indistinguishable. The test 'lane with --driver refused before gh' passes only because it injects HERDR_AGENT_NAME=lane-x, a state production does not produce. plan/SKILL.md:516-518 and the docstring now describe a protection that does not fire for real lanes. → Decide lane vs driver from something a lane actually carries. Inside herdr (HERDR_PANE_ID set), ask herdr for this pane's agent name over its socket/CLI and accept only `driver`. If the lookup fails, refuse (fail closed), and never fall back to --driver while HERDR_PANE_ID is set. Make --driver count only when no HERDR_* pane context exists. Replace the test's injected HERDR_AGENT_NAME with a case where only HERDR_PANE_ID is set plus --driver, and expect a refusal.

## SHOULD FIX (3)

- **10.3-r2-02** `scripts/driver-merge.py:505` (fail-open · reopens 10.3-r1-06) — The r1-06 read-back after a non-zero `gh pr merge` reads only `state,mergeCommit`, and any MERGED is treated as this merge. --match-head-commit guarantees the merged head only when gh succeeded. On the failure path, gh may have failed because the head moved (a lane pushed an unreviewed commit) or for any other reason, and the PR may then have been merged by someone else or at a different head. The driver still prints MERGED with the read-back sha and posts a `merged` event claiming it merged the reviewed head. That event covers commits no condition checked. → Read `state,mergeCommit,headRefOid` back. Treat it as this merge only when headRefOid == facts['head']. Otherwise report it as merged, but not by this run at the checked head: no `merged` event, or one flagged with the actual head. Add a test with merge_rc=1 and a read-back MERGED at a different head.
- **10.3-r2-03** `scripts/driver-merge.py:263` (fail-open) — The --admin precondition from r1-03 matches required checks by name only. A SUCCESS from any source with that name counts. The code ignores the classic protection's `checks[].app_id` and the ruleset's `integration_id`, which are GitHub's binding of a required check to the app that must report it, and --admin then bypasses GitHub's own enforcement of that binding. Any token with commit-status write access can post a StatusContext `e2e`=success on the head, for example `gh api repos/o/r/statuses/<sha> -f context=e2e -f state=success`. That turns a required check that never reported (the r1-03 scenario) into an --admin merge. Agents making their own CI pass is the failure mode r1-05 named. → Carry (context, app_id/integration_id) from both protection sources. Require a SUCCESS CheckRun from that app when an app is bound (the rollup's CheckRun carries checkSuite.app, or read check-runs for the head). When the binding cannot be verified, refuse --admin.
- **10.3-r2-04** `scripts/one-way-doors.defaults:41` (engine) — The r1-05 fix widens the global one-way-door floor, but this floor is not merge-only. door.py also reads it for /concurrency and /plan §6.9 packet promotion (a lane's two-way packet whose --range touches .github/workflows/ now goes out one-way and parks the lane) and for /review case-1 reframe packets. Editing CI is reversible, and the file's own contract (line 3) says a hit 'makes the change one-way'. So every unit that adds or edits a workflow now parks on a door that is not one. That includes adding CI to pmg-docs/ai-skills, which r1-07's note implies is the path to auto-merge. The refusal packet also offers 'Rework the PR off the floor' (driver-merge.py:439) for a CI edit. → Keep the floor for irreversible changes. Give driver-merge its own 'never auto-merge' path list (CI definitions) as a separate condition that writes a two-way packet ('Alex reviews the CI change and merges by hand'). Revert the defaults lines and move their door tests to driver-merge's table.

## NOTE (2)

- **10.3-r2-05** `scripts/driver-merge.py:263` (engine) — Only SUCCESS counts as a satisfied required check. GitHub accepts a required check that concluded SKIPPED or NEUTRAL (a job skipped by `if:`) as passing. A BLOCKED PR whose only block is reviews, with a required job skipped by `if:`, is refused --admin and parks. This fails closed, but it will produce packets for PRs that are fine. → Either accept SKIPPED/NEUTRAL for a required check that is present in the rollup (absence stays a refusal), or document that skipped required checks always park.
- **10.3-r2-06** `scripts/driver-merge.py:242` (engine) — The rulesets read is one page (per_page=100, no --paginate). A branch with more than 100 active rules would drop the required_status_checks rules past page 1, and the missing checks would read as not required. That is unlikely at this scale, but it is a fail-open path in a function whose docstring promises unreadable is never read as 'nothing required'. → Use `gh api --paginate`, or refuse when the response holds exactly per_page entries.

## Checked and clear

10.3-r1-01 fix: run_gate passes --blocking and accepts only verdict `pass` with exit 0; advisory/predates/unknown/unreadable all refuse, and the table asserts --blocking on every gate call, 10.3-r1-04 fix: unreviewed() requires every non-plans/ PR commit to sit in some review range of this repo in the unit; git failures, malformed ranges, empty and unreadable commits refuse; stacked-branch and pre-base cases tested, 10.3-r1-03 fix structure: classic protection and rulesets both read; unreadable protection or rulesets refuses --admin (apart from the app-binding gap above), 10.3-r1-07: docs state that a repo with no CI parks as a two-way packet, lenses: silent-failure — every new gh/git call's failure path refuses with a reason, tests: test_driver_merge + test_door pass (27 tests, run here)

## Not applicable

domain rules — generic repo (ai-skills), data-migration / SQL safety — no schema or SQL in range

**Verdict:** SHIP AFTER BLOCKING

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex gate: out of credits — this is a claude-fallback single-context pass
- specialist fan-out (security, red-team, testing, …) not dispatched: the brief asked this read-only pane to keep tool output small
- gstack engine telemetry (gstack-review-log) not run
- no network: could not confirm GitHub's live responses for branch-protection/rulesets endpoints (403/404 wording, rulesets on private free-plan repos) or how statusCheckRollup lists checks bound to an app
- could not observe a real /concurrency lane's environment; HERDR_AGENT_NAME absence is inferred from this herdr-launched review pane and from the skills that launch panes
