# /review — ai-skills @ `361ae685b906ef3638bde5fd29e6e537363397b1..f7f3d30d24f155b9990746b5d0cbfce018f28580` (4 commits)

**Review:** `10.3-r1` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 7 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.3 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (4)

- **10.3-r1-01** `scripts/driver-merge.py:228` (fail-open verdict) — run_gate treats verdict-gate.py exit 0 as the go-ahead, but the gate's default mode is advisory (verify_lib.GATE_MODE = "advisory"; no plans dir sets **Gate mode:**), where every block exits 0. Run now on this scope, `verdict-gate.py --unit 10.3 --json` prints verdict "advisory", "6 blocked — no final verdict", and exits 0. So a unit with no /verify verdict, a failed verify, undispositioned findings or unreviewed fix commits merges, with only a ticker marker. The test table locks this in: 'gate advisory flagged' expects a merge. → Class: delegating a merge decision to a check whose exit code means 'reported', not 'passed'. Call verdict-gate.py with --blocking, or refuse when the JSON verdict is "advisory" (keep "pass", and decide explicitly whether "not-judged"/predates qualify). Flip the 'gate advisory flagged' test case to a refusal. If merging under advisory is intended, that is Alex's call: say so in scope §4.3, because 'Done' under advisory is a much weaker bar than 'merged'.
- **10.3-r1-02** `scripts/driver-merge.py:392` (fail-open driver) — 'Lanes never merge' rests only on packet.is_driver, which is true for any caller passing --driver. The documented command (plan/SKILL.md step 4) includes --driver, and lanes run /plan, so a lane that runs that step merges. A lane is identifiable: herdr sets $HERDR_AGENT_NAME to the lane name, yet a lane-named session passing --driver is still accepted. The docstring ('merge refuses a lane outright'), README ('refuses a lane before any gh call') and plan/SKILL.md:511 ('the script refuses it') all claim an enforcement the code does not have. → Refuse merge when $HERDR_AGENT_NAME is set to anything other than "driver", whatever the --driver flag says (a named herdr agent that is not the driver is a lane), and add a test row: HERDR_AGENT_NAME=lane-x plus --driver is refused before gh. Keep --driver only for sessions outside herdr. Also correct the three docs to describe what is actually enforced.
- **10.3-r1-03** `scripts/driver-merge.py:193` (fail-open checks) — BLOCKED → --admin bypasses every branch-protection rule, including required status checks that never reported. statusCheckRollup lists only contexts that have reported. A required check that never reports (a path-filtered workflow, a queued workflow not yet created, a renamed job) leaves the PR BLOCKED 'Expected — waiting for status'. cond_checks passes as long as some other check ran green, and --admin then merges past the missing required check. Scope §4.3 allows --admin 'under the same conditions', and 'CI is green with real runs' does not hold here. → Class: inferring why GitHub blocks from mergeStateStatus alone. Before using --admin, read the base branch's required checks (gh api repos/{slug}/branches/{base}/protection/required_status_checks, plus rulesets: gh api repos/{slug}/rules/branches/{base}). Require every required context to be present and SUCCESS in the rollup, and fail closed when protection is unreadable on a BLOCKED PR. Alternatively, admit --admin only when reviewDecision is REVIEW_REQUIRED and the required checks are satisfied.
- **10.3-r1-04** `scripts/driver-merge.py:272` (fail-open verdict) — covered() checks only the head end: that the review saw the PR head, or only plans/ changed after it. It never checks that the unit's reviews cover the PR's start. cond_verdict picks any review of this repo in the unit, so a PR whose merge-base..head contains commits before the review's base merges unreviewed. Examples: code committed before the ledger base was recorded, a stacked lane branch carrying another unit's commits, or a lane that ran two units on one branch with one PR. → Compute the commits in merge-base..head, drop those touching only plans/, and require each remaining commit to sit inside some review record's base..head for this repo in the unit (or at least require the earliest review base to be an ancestor-or-equal of the merge-base). Refuse with the uncovered shas named. Add test rows for a pre-base code commit and a stacked branch.

## SHOULD FIX (2)

- **10.3-r1-05** `scripts/driver-merge.py:184` (fail-open checks) — 'Real green runs' is self-referential when the PR edits the CI that produces them: .github/workflows/ (and similar CI config) is not on the floor, so a PR that weakens or stubs its own test job (e.g. `run: true`) gets a real SUCCESS and merges to develop, which deploys to dev. An agent making its own CI pass is a known failure mode, and nothing here catches it. → Treat a PR touching CI definitions (.github/workflows/, .github/actions/, CODEOWNERS, other repos' CI config) as not auto-mergeable: either add them to the floor in one-way-doors.defaults (a 10.1 surface, so record the decision) or add a driver-merge condition that refuses with a two-way packet.
- **10.3-r1-06** `scripts/driver-merge.py:364` (silent-failure merge) — When gh pr merge exits non-zero, the PR is assumed unmerged without being read back. gh can exit non-zero after GitHub has merged (a network drop after the mutation, a post-merge step failing). The driver then prints NOT MERGED, writes a 'Not merged' packet asking someone to fix and re-run, and posts no `merged` event, though the PR landed. Task 3.2 says every merge posts an event. → On a non-zero rc, run the same read-back (state, mergeCommit). If it reads MERGED with a merge commit, take the merged path (print MERGED, post the event, flag the gh error). Otherwise keep the refusal.

## NOTE (1)

- **10.3-r1-07** `plan/SKILL.md:503` (doc-claim base) — Docs say pmg-docs and ai-skills PRs merge to main, but neither repo has any CI workflow. cond_checks refuses an empty rollup as vacuous green, so the driver can never merge them (fail-closed, not unsafe). Scope §4.3's 'pmg-docs merge to main' is unreachable as built. → Either state in plan/SKILL.md and scope §4.3 that a repo with no CI always parks as a two-way packet, or give those repos a minimal real check. Don't relax the vacuous-green rule.

## Checked and clear

cond_checks: empty / skipped-or-neutral-only rollups refused; pending, failed, unknown type/state refused, cond_base: a code repo's main is refused; only develop (code) / main (kalpa-docs, pmg-docs, ai-skills) pass, door floor: merge-base..head via door.py, base-revision .one-way-doors, fail-closed on no merge-base; f7f3d30 migration/ pattern correct and tested, gh pr view errors / non-JSON / missing refs → Refuse, no merge; UNKNOWN mergeState retried then refused, merge uses --match-head-commit, never --auto; read-back MERGED + merge sha required before the event, verdict: missing/malformed log, no review of repo, `none` reviewer, non-SHIP without acceptance all refuse, c1cdafc resolve-identifiers: excluding google.golang.org/protobuf/ runtime imports from the proto skip is correct

## Not applicable

domain groups — generic repo (ai-skills)

**Verdict:** DO NOT SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex unavailable (out of credits): Claude fallback, single-context pass
- no specialist fan-out (read-only review pane, brief asked for small output)
- no live gh calls against a real PR / branch protection; GitHub semantics of BLOCKED and statusCheckRollup reasoned from docs, not exercised
- gstack engine telemetry (§3.4) not logged: read-only pane
