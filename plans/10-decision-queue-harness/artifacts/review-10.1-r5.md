# /review — dev-workbench @ `0951c26920984dca5363dc65c454a2fa7d306bf0..e766b1d995e0d6ae2d53c92e1b8dcf3dfbedf425` (5 commits)

**Review:** `10.1-r5` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (2)

- **10.1-r5-01** `queue/decision_queue/db.py:74` (engine SQL & Data Safety) — Removing replay strands events already acknowledged before upgrade. The previous server accepted closed/stale/touch events for absent packets, so their clients can already have .sent markers. When those packets arrive after upgrade, they remain open with their original reversal cost: nothing applies the stored events, and migration 003 provides no transition for them. → Provide a transition for previously accepted orphan events before removing replay. Preserve their effects through a concurrency-safe compatibility path or an explicit, preview-first reconciliation procedure, and test an upgrade with an orphan event.
- **10.1-r5-02** `queue/decision_queue/db.py:98` (engine Enum & Value Completeness) — The packet-existence check bypasses the new retry contract. Resubmit an existing event id with packet_id changed to an unknown packet: this returns 404 before comparing the stored document, although changed retries must return 409. packet.py treats 404 as retryable and 409 as a permanent conflict, so this misclassifies a conflicting event indefinitely. → Resolve an already stored event id and compare its content before checking whether a new event's packet exists. Retain the post-insert conflict check for concurrent submissions, and test a changed retry naming an unknown packet.

## SHOULD FIX (0)


## NOTE (0)


## Checked and clear

Lenses §1: read all six touched files and relevant adjacent database, validation, rendering, configuration, entrypoint, installation, and client retry code., SQL parameterization, atomic status updates, duplicate insertion races, and commit-before-acknowledgment., Gate integrity: manually reviewed changed test hunks, including removed replay tests and their replacement contract tests., Lenses §4–5: no additional overbuilding, invented names, or workaround comments requiring findings., Python sources compiled in memory; git diff --check passed., Read-only pytest subset: 3 passed, 1 skipped, 39 deselected.

## Not applicable

LLM output trust boundaries and prompt changes., Shell injection, async/sync mixing, and cross-language type coercion changes., New enum values or widened schema acceptance., Frontend implementation, CI/CD workflow, release artifact, version, and changelog changes., Domain-specific rule sections: none supplied for this generic repository.

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- Read root CLAUDE.md: absent; read config/claude-code/CLAUDE.md instead.
- Read ARCHITECTURE.md and verify accepted ADRs: file absent.
- Run the full pytest suite: read-only filesystem prevents creation of the temporary PostgreSQL cluster.
- Run the schema drift comparison: default canonical schema path is absent; the test skipped.
- Complete uv build --offline --no-cache queue: temporary-directory creation denied.
- Run Ruff through uv: cache initialization denied.
- Run approval-class verification: helper could not resolve origin/0951c26920984dca5363dc65c454a2fa7d306bf0 and checked nothing.
- Generate the automated gate-diff inventory: helper requires writing an artifact; reviewed test hunks manually.
- Verify the service under Linux systemd: this host is macOS.
- Independent specialist sub-reviewers were not run.
