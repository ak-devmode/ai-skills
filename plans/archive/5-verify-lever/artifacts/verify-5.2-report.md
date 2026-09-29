# Verify report — unit 5.2

**Run:** `5.2-20260929T031136-b3a2` · **Judge:** codex gpt-6-sol · **Table revision:** 4
**Gate:** ADVISORY — would block (5.2, 2 block(s), mode advisory) · ⚠ verify advisory: 2 blocked (p2-fixtures, p2-scope-deliverables)

## 1. Checks

| Check | Result | Rung | Reason |
|---|---|---|---|
| p2-codex-failure-modes | pass | 4/4 | runner: exit 0; judge concurs |
| p2-fixtures | inconclusive | 4/4 | judge downgraded runner pass: The recorded command passed its deterministic tests but skipped both live-judge tests. It does not establish that the over-build and missing-evidence defects are caught or that their repaired copies pass. |
| p2-names-resolve | pass | 4/4 | runner: exit 0; judge concurs |
| p2-no-overbuild | pass | 2/2 | judge: The Phase 2 additions serve the specified runner, judge, review, and fixture workflows; I found no unrequested registry, plugin layer, or parallel implementation. |
| p2-rejections-justified | pass | 3/2 | judge: The 5.2 review log contains no rejected dispositions. I checked all 16 fixed dispositions against git; each cited commit touches its finding's file. |
| p2-review-log | pass | 4/4 | runner: exit 0; judge concurs |
| p2-scope-deliverables | fail | 2/2 | judge: Scope §4.2 requires Class A behavior through the adapter and /browse. The approved amendment moves the three-outcome trial, but does not remove that capability. verify/SKILL.md has no /browse procedure or browser tool; its Class A path consists of finish-table commands run by verify-run.py. |
| p2-skills-lint | pass | 4/4 | runner: exit 0; judge concurs |
| p2-tests-green | pass | 4/4 | runner: exit 0; judge concurs |

## 2. Findings

- **high** · conformance · `p2-scope-deliverables` · scope.md §4.2; progress.md Plan 5.2 Task Detail; verify/SKILL.md §§3–4 — The Class A trial was explicitly deferred, but the scoped /browse behavior was not. The landed /verify procedure specifies runner commands and a read-only judge without a /browse step.
- **medium** · evidence · `p2-fixtures` · scripts/tests/test_verify_fixtures.py:154; verify-5.2.jsonl run 5.2-20260929T031136-b3a2 — The runner reports OK with two skips because the judge tier requires VERIFY_EVAL=1. The default test command proves only the deterministic portion of the fixture deliverable.

## 3. Lever candidates

Recorded, not built: a lever is built on the second sighting (verify-contracts.md §4).
- `p2-fixtures` — gap: The recorded fixture run skipped the live-judge cases, leaving two planted defects and their repaired copies unverified at the final SHA. · lever: Run the existing fixture test entrypoint with VERIFY_EVAL=1 and retain its exit status and output against ac3869d. · run `5.2-20260929T031136-b3a2`

## 4. Feature map

`n/a`
