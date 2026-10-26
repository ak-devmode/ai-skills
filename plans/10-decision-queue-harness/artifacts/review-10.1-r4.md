# /review — dev-workbench @ `98a4109732a022f068f002e67486f9827b7eab5e..0951c26920984dca5363dc65c454a2fa7d306bf0` (7 commits)

**Review:** `10.1-r4` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**Findings:** 7 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (3)

- **10.1-r4-01** `config/systemd/decision-queue.service:17` (engine Distribution & CI/CD Pipeline) — The service still cannot import decision_queue. uv --project selects the project without changing directories; the unit has no WorkingDirectory, and pyproject.toml has no build backend to install the package. Starting the project interpreter outside queue/ reproduces 'No module named decision_queue'. → Set WorkingDirectory=%h/.local/share/decision-queue or use uv --directory. Correct the equivalent README invocation.
- **10.1-r4-02** `queue/decision_queue/db.py:79` (engine Race Conditions & Concurrency) — Concurrent packet and event transactions can permanently lose the event's effect. The replay SELECT cannot see an uncommitted event, while that event's UPDATE cannot see the uncommitted packet. Both requests then commit successfully; retries return as duplicates without applying the missing close, stale, or touch. → Acquire the same transaction-scoped lock keyed by packet_id in both insertion paths before inserting or applying effects. Add a deterministic two-connection regression test.
- **10.1-r4-03** `queue/decision_queue/db.py:45` (engine SQL & Data Safety) — Excluding reversal_cost acknowledges different packet content as an identical retry. Even without any touch event, changing only commits_stacked or as_of returns 200 duplicate:true while discarding the submitted value, violating the new conflict contract. → Preserve the original packet content or its canonical digest separately from mutable projection fields, and compare retries against that immutable value.

## SHOULD FIX (4)

- **10.1-r4-04** `queue/decision_queue/db.py:87` (engine Time Window Safety) — Replaying an early closed event sets closed_at before the packet's received_at. stats() subtracts received_at from closed_at, so the newly supported event-before-packet sequence produces negative answer and parked durations. → Define the measurement for packets received after closure and update the timestamp calculation or exclude those samples. Test both statistics endpoints' duration fields for this sequence.
- **10.1-r4-05** `queue/tests/test_queue.py:301` (fail-open lenses §2 · scaffolding) — The drift guard skips when its source path is wrong, including an explicitly configured DQ_SCHEMA_SOURCE typo. It skipped in this review, so a green test run cannot establish the README's schema-sync claim. → Fail for an invalid explicit source path and provide a required canonical schema source in the verification environment.
- **10.1-r4-06** `queue/README.md:22` (doc-claim lenses §6) — The route table still promises 200 for retried packet IDs and says unknown-packet event effects are no-ops. HEAD instead returns 409 for changed packet content and replays stored effects when packets arrive. → Document identical versus conflicting retries, the new POST refusals, and deferred event replay.
- **10.1-r4-07** `queue/README.md:69` (doc-claim lenses §6 · scaffolding) — The test instructions say missing PostgreSQL binaries cause a skip, but conftest.py now fails by default and requires DQ_ALLOW_SKIP_PG=1 for an explicit skip. → Update the prerequisite and opt-out instructions to match the fixture.

## NOTE (0)


## Checked and clear

SQL parameterization and referenced database column names, HTML escaping and render fallback, JSON content-type enforcement and browser cross-site header checks, Changed shell code: injection and explicit activation-failure reporting, Adjacent-code reads for touched files and called project functions, Local-maxima and dirty-comment lenses, Shell syntax: bash -n install.sh passed, In-memory compilation of 10 Python source/test files passed, Three standalone tests passed, ShellCheck executed; reported diagnostics are outside changed hunks

## Not applicable

New enum values or widened input acceptance, LLM-generated URL fetching or code execution, Async/sync mixing, Frontend framework rendering, Version and changelog consistency, New distributed artifact publishing, Data repair commands

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- Read repository-root CLAUDE.md: absent; read config/claude-code/CLAUDE.md instead.
- Read ARCHITECTURE.md and verify accepted ADRs: absent from this checkout.
- Run the full test suite: read-only filesystem prevents pytest temporary files and PostgreSQL cluster creation.
- Run the build: uv build cannot initialize its cache under the read-only filesystem.
- Run Python lint: uv cannot initialize its cache; no standalone ruff executable is available.
- Compare the vendored schema with its canonical source: source absent, so the drift test skipped.
- Run approval-class verification: helper rejected origin/<SHA> resolution; direct inspection confirms no approval-classes.json at the supplied base.
- Validate Linux systemd activation and tailscale browser behavior: this macOS environment has no systemd runtime or deployment access.
- Run parallel specialist sub-reviews: agent delegation was not authorized by the applicable instructions.
