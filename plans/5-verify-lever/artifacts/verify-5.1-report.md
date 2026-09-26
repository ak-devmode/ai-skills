# Verify report — unit 5.1

**Run:** `5.1-20260926T100859-79e8` · **Judge:** codex gpt-6-sol · **Table revision:** 3
**Gate:** ADVISORY — would block (5.1, 4 block(s), mode advisory) · ⚠ verify advisory: 4 blocked (scripts-tests-green, names-resolve, gate-semantics-tested, scope-deliverables)

## 1. Checks

| Check | Result | Rung | Reason |
|---|---|---|---|
| contracts-generate-clean | pass | 4/4 | runner: exit 0; judge concurs |
| gate-semantics-tested | fail | 3/4 | judge downgraded runner pass: At e3b74ec the gate trusts the final result without recomputing it from pending and judged records. Changing a failed runner result to pass in the final record can pass the gate. |
| names-resolve | fail | 4/4 | runner: exit 1; judge concurs |
| no-overbuild | pass | 2/2 | judge: The revision adds the requested scripts and contracts. The shared verify_lib.py contains the table parser, message formatter, and JSONL writer used by those scripts; no unnecessary registry or parallel framework was found. |
| scope-deliverables | fail | 3/2 | judge: The revision lacks the scope's finish-conditions.md; the feature map contract uses the wrong status vocabulary; and the identifier resolver accepts a route whose prefix has no declaration. |
| scripts-tests-green | inconclusive | 4/4 | judge downgraded runner pass: The runner executed 93 tests at 36625e4, eight commits after unit 5.1 ended at e3b74ec. That run does not establish that the Phase 1 suite passed. |

## 2. Findings

- **high** · conformance · `gate-semantics-tested` · e3b74ec:scripts/verdict-gate.py:128-162 — The gate reads final.results directly and does not re-check the §5.1 authority rule against the run's pending and judged records. A forged passing final result can conceal a runner failure.
- **high** · conformance · `scope-deliverables` · git ls-tree e3b74ec plans/5-verify-lever — Phase 1's required revisioned finish-conditions.md did not land in 8173b95..e3b74ec. The current file was added in a later commit.
- **high** · invented-reality · `scope-deliverables` · e3b74ec:scripts/resolve-identifiers.py:436-449 — A route matching only the suffix of a declared path returns resolved while its group prefix is merely assumed. This violates the namespace-aware declaration check.
- **medium** · evidence · `scripts-tests-green` · artifacts/verify-5.1.jsonl, run 5.1-20260926T100859-79e8; git diff e3b74ec..36625e4 — The passing suite ran at 36625e4 on a dirty tree. Later commits changed scripts and added tests, so the 93-test result cannot prove the e3b74ec suite was green.
- **medium** · invented-reality · `names-resolve` · e3b74ec:scripts/verify_lib.py:26 — VERIFY_PROJECTS is read as an environment override without a declaration in the unit's revision. The runner correctly reports it unresolved.
- **medium** · test-plan · `gate-semantics-tested` · e3b74ec:scripts/tests/test_verdict_gate.py — The tests do not cover a final record that contradicts its runner evidence. The test plan's explicit downgrade-to-inconclusive case is also absent; the downgrade test uses fail.
- **medium** · evidence · `gate-semantics-tested` · artifacts/verify-5.1.jsonl, gate-semantics-tested pending record — Its passing command ran at 36625e4, after the gate and its tests had changed. It cannot establish the e3b74ec gate's behavior.
- **medium** · conformance · `scope-deliverables` · e3b74ec:templates/verify-contracts.md §8.1; templates/features-README.md.template — The feature map specifies working, degraded, broken, and unknown. Scope §4.1 requires roadmap, scoped, in progress, in testing, and shipped, with shipped (unproven) when evidence is absent.
- **low** · evidence · `contracts-generate-clean` · artifacts/verify-5.1.jsonl, contracts-generate-clean pending record — The supplied runner result is from 36625e4, outside the unit range. A separate fail-loud check against e3b74ec established this deliverable.

## 3. Lever candidates

Recorded, not built: a lever is built on the second sighting (verify-contracts.md §4).
- `scripts-tests-green` — gap: The available test run used a later, dirty revision. · lever: Run the unittest entrypoint in an isolated disposable checkout of e3b74ec and retain its exit code and output. · run `5.1-20260926T100859-79e8`

## 4. Feature map

`n/a`
