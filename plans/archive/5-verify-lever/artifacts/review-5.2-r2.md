# /review — ai-skills @ `c8c049b..HEAD` (17 commits)

**Review:** `5.2-r2` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 5 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.2 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (3)

- **5.2-r2-01** `scripts/verdict-gate.py:187` (fail-open) — The latest codex review clears a fallback warning without checking its range. A codex review of only an unrelated or narrower range can therefore remove the marker while the fallback-reviewed commits remain unreviewed by codex. → Clear the marker only when the codex review covers the fallback-reviewed commits for this unit.
- **5.2-r2-02** `verify/scripts/demo.py:123` (fail-open) — The over-build lens is checked across all findings, independently of the no-overbuild check. An unrelated over-build finding plus a generic finding on no-overbuild can make the eval claim the planted over-build was caught. → Require the over-build finding to name the no-overbuild check and identify the planted defect.
- **5.2-r2-03** `scripts/codex-exec.py:72` (engine) — An exact VERIFY_CODEX_MODEL slug is silently replaced by its cache upgrade. With the current cache, gpt-5.5 resolves to gpt-5.6-sol even before its retirement date, breaking the documented exact-slug override. → Use exact slugs as given; apply upgrade resolution only to family selections when appropriate.

## SHOULD FIX (2)

- **5.2-r2-04** `plans/5-verify-lever/progress.md:270` (doc-claim) — This correction says clinic_3 is not a dev tenant, but the unsuperseded Decisions Log entry at line 37 still names it as the dev trial target. → Mark the earlier decision superseded without adding private environment details.
- **5.2-r2-05** `plans/5-verify-lever/closeout-prep.md:320` (doc-claim) — The risk flag says codex-exec.py still misclassifies out-of-credits errors, although this range fixes that classification. It leaves a false open risk in the handoff. → Mark the risk resolved and cite commit 0aefa7f.

## NOTE (0)


## Checked and clear

Engine: SQL and data safety, LLM output trust boundary, shell injection, and enum consumers, Engine: changed subprocess calls, type boundaries, and version consistency, Lenses: adjacent code, silent failure, local maxima, dirty comments, and identifier declarations, git diff --check and both changed skill lints passed

## Not applicable

Domain groups 3.1–3.8: generic repository, Engine: ORM fields, async endpoints, time windows, rendered frontend, and distribution pipeline

**Verdict:** DO NOT SHIP

## What this review did not cover

- The full unittest suite could not run: the read-only filesystem prevents temporary-directory creation.
- Live codex probe, exec, and VERIFY_EVAL=1 could not run with restricted network and no writable scratch space.
- Filesystem integration tests for concurrent review-log writes could not run without write access.
- Claude Code skill registration and live fallback invocation could not be checked in this Codex session.
- Parallel specialist sub-reviews were not performed.
