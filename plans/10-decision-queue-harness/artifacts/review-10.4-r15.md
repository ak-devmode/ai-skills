# /review — dev-workbench @ `3b7f6a3102210005b2f5c0cfc708c388b963b23b..66aebf01f4f021a84386956e578228665fd4bea6` (2 commits)

**Review:** `10.4-r15` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**Findings:** 4 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (3)

- **10.4-r15-01** `queue/decision_queue/render.py:320` (engine LLM Output Trust Boundary) — The feed displays the recommended option but copies an independently supplied, hidden reply. A schema-valid packet can recommend option 1 while its reply selects option 2; I reproduced this with the new fixture. Hiding the reply removes the user's opportunity to notice the discrepancy before copying. → Bind concealed actions to their displayed choice: derive the feed reply from the displayed recommendation and packet identity, or expose discrepancies for review. Cover every v2 door and mismatched replies.
- **10.4-r15-02** `queue/decision_queue/schema/packet.schema.json:48` (engine Completeness Gaps) — The new patterns use `$`, which Python's jsonschema implementation permits before a final newline. packet_error accepts a 100-character title followed by a newline, violating both the length and single-line constraints. The same bypass accepts context/evidence/label/why at their cap plus one newline. → Use absolute end-of-input matching supported by both validators. Fix all five sibling patterns in the canonical schema and re-vendor; add cap-plus-newline and single-line negative cases.
- **10.4-r15-03** `queue/decision_queue/schema/packet.schema.json:106` (engine Completeness Gaps) — The recommendation-text prohibition handles only '(recommended)' and '(Recommended)'. A non-recommended option labeled 'Other choice (RECOMMENDED)' validates and retains that marker when rendered, contradicting the flag and allowing two options to appear recommended. → Apply the same case-insensitive marker handling used by _REC_TEXT to the canonical schema and its vendored copy. Test marker variants on recommended and non-recommended options.

## NOTE (1)

- **10.4-r15-04** `queue/decision_queue/render.py:113` (doc-claim 6) — The claimed never-raise behavior fails for naive datetimes: _age(datetime.datetime(2026, 10, 28)) raises TypeError because now is timezone-aware while dt is naive. Current PostgreSQL timestamps are aware, so this does not demonstrate a normal-path outage. → Handle naive and aware timestamps consistently, or narrow the documented guarantee. Extend the age test to cover timezone awareness.

## Checked and clear

Lenses §1: read every changed text file, adjacent callers and storage functions; inspected both added screenshots., SQL/data safety and concurrency: changed projection uses declared content storage and parameterized packet lookup; no new writes or races., Frontend escaping: new dynamic fields pass through esc(); direct rendering probes covered all three packet types and doors without image leakage into feeds., Gate Integrity: no removed tests, weakened assertions, relaxed thresholds, or added suppressions., Approval classes: exact-range scan completed; no classes declared at the base., Schema parity: matches the cited ai-skills concurrency-10-cards companion source. The default ai-skills main checkout remains v1 and fails the drift comparison., Seven filesystem-independent tests passed with the companion schema configured; service Python files compiled in memory; git diff --check passed., Lenses §§3–5: no introduced silent-error suppression, unnecessary abstraction, invented identifier, or workaround-excusing comment.

## Not applicable

Python async/sync mixing: no asynchronous execution surface., Shell injection: no added shell execution., LLM prompts: no prompt or tool-capability changes., Time-window queries: no bucket or reporting-window changes., Distribution/CI/CD and version consistency: no pipeline, package-version, or release changes., Timing-dependent tests and crypto/entropy: no relevant added or changed operations.

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- Read repository CLAUDE.md: absent from the reviewed revision and main checkout.
- Read repository ARCHITECTURE.md and accepted ADR guidance: ARCHITECTURE.md is absent.
- Complete PostgreSQL/HTTP integration tests: read-only sandbox prevents creating the throwaway database and temporary test files.
- Package build: python -m build --no-isolation failed because the build module is unavailable.
- Lint: python -m ruff check failed because ruff is unavailable; no repository lint command is configured.
- Live browser clipboard and responsive-layout checks: the service could not be started with its required temporary PostgreSQL database.
- Independent specialist sub-reviewers: not run; sub-agent delegation was not authorized for this session.
