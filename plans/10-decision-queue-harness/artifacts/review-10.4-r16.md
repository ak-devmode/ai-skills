# /review — ai-skills @ `36f52cf0ba98e6f5d9b695e63d4d20fe7aa6cc8b..e9325f14ee0cae16fb5102bb5a3dd0907d7d2b63` (5 commits)

**Review:** `10.4-r16` · **Reviewer:** claude-fallback codex out of credits (driver brief) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (driver brief)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (driver brief)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (0)


## NOTE (3)

- **10.4-r16-01** `scripts/schema_check.py:54` (dirty-comment) — _ecma_end's docstring still says the queue's JSON Schema validator is ECMA-262, where `$` does not match before a trailing newline. 10.4-r15-02, which 8b27103 fixes, established the opposite: the queue runs Python jsonschema (re), where it does. The schema's new $comment now contradicts this docstring, and after 8b27103 no pattern in packet.schema.json ends in `$`, so the translation only serves ad-hoc schemas passed to validate(). → Reword the docstring: the shim keeps a caller-supplied `$` strict here; the packet schema itself ends patterns in (?![\s\S]) because the queue's jsonschema runs Python re.
- **10.4-r16-02** `scripts/tests/test_packet_schema.py:169` (engine) — test_cap_plus_newline_and_embedded_newline_refused validates through schema_check, which rewrites a trailing `$` to \Z. With 8b27103 reverted, every case still fails validation and the test passes. It cannot catch 10.4-r15-02, which only showed under Python jsonschema. Only test_no_schema_pattern_ends_in_a_bare_dollar guards that regression. → Run each case with patterns used verbatim (re.search(pattern, value) without _ecma_end), or drop the test as redundant with the structural one.
- **10.4-r16-03** `scripts/packet.py:368` (silent-failure) — show() now strips '(recommended)' from every label. v1 `new` still accepts a marker on a non-recommended option: `--option alpha --option 'beta (RECOMMENDED)'` with the default --recommended 1 writes alpha as recommended and the prefill as 'Option 1: alpha.' Before this change the terminal printed both markers, so the conflict was visible. Now the card shows a single clean recommendation and silently drops the author's marker on beta. This is the same class as 10.4-r15-01: the display hides a recommendation conflict. The current callers pass --recommended N, so the impact is limited to hand-written v1 packets. → In v1 `new`, refuse a '(recommended)' marker on an option that --recommended does not select, as v2_errors does for every option, rather than hiding it at display time.

## Checked and clear

10.4-r14-03 resolved: schema_version is type integer; schema_check._type_ok rejects bool for integer; _same makes enum/const bool-aware; the event schema_version also gained the integer guard; test covers true/false/'2'/2.0/1.0 with branch-skipping payload, 10.4-r14-04 resolved: show() prints context then evidence for v2 packets, including on --id reprint and optionless info packets; v1 docs without those keys print nothing extra, 10.4-r14-05 resolved: label lookahead spelled per letter (ECMA has no inline (?i)), matching packet.py REC_TEXT (re.I) on the same literal '(recommended)'; schema and CLI tests cover mixed case on both options, 10.4-r14-06 resolved: unreadable-file test now reaches the v1 body-file read and the v2 evidence-file read and asserts each one's own message, 10.4-r15-02 sibling (ai-skills side) resolved: every schema pattern ends in (?![\s\S]); structural test refuses a bare trailing $, ai-skills schema identical (minus $comment) to dev-workbench queue/decision_queue/schema/packet.schema.json at its HEAD, V2_CAPS agreement test still extracts {1,N} from the re-anchored patterns, full suite: python3 -m unittest discover scripts/tests — 507 tests OK (2 skipped); test_packet* 80 OK, lenses: fail-open (new guards fail closed), adjacent code (_type_ok, _ecma_end, v2_errors, cmd_new prefill)

## Not applicable

domain rules — generic repo, SQL/data migration, auth, frontend checklist groups — no surface in range

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex cross-model pass: not run per driver brief (codex out of credits); a fresh probe printed `codex gpt-6.1-sol`, exec not attempted
- gstack specialist fan-out not dispatched: single-context Claude pass over a 165-line fix range
- Python jsonschema not installed here: could not validate the cap+newline cases under the queue's actual validator; dev-workbench's review covers ingest
- 10.4-r14-02 (plan/SKILL.md:507 v1-shaped packet call) is out of this range and still undisposed; the brief assigns it to the driver's integration step
