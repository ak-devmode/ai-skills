# /review — ai-skills @ `41e788d391e853da22217f24c8ce8d4b4abd4d2f..20ffb7b029929bd980077096e539a45bf96930b6` (5 commits)

**Review:** `10.1-r3` · **Reviewer:** claude-fallback codex out of credits (user-reported) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (user-reported)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (user-reported)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (0)


## SHOULD FIX (0)


## NOTE (3)

- **10.1-r3-01** `scripts/packet.py:335` (dirty-comment engine) — After 8b96644 the <pid>.sent marker records a send, and nothing writes state['sent'] any more. `new` still writes {"status": "open", "sent": false}, so every state.json says sent=false for its whole life, including packets the queue already holds. The field is dead and misleading to anyone who reads the outbox state (debugging, driver tooling). → Drop "sent" from the state file written by `new`, so the marker is the only record of a send.
- **10.1-r3-02** `scripts/packet.py:458` (engine engine) — The new one-way HEAD check (10.1-r1-07 fix) refuses a reply whenever the lane repo's HEAD differs from head_sha, and the message says to run `stale`, which discards the decision. The scope says one-way lanes park. But a lane that commits bookkeeping while parked (a progress or ledger note, a PARKED marker committed into plans/ in the same repo, as ai-skills' plans are) can then never accept Alex's reply to that packet; it can only stale it and re-emit. This is correct fail-closed behaviour if parked lanes never commit, but nothing enforces or documents that precondition for the Task 1.5 wiring. → In Task 1.5 wiring, state that a lane parked on a one-way packet makes no commits until check-reply passes. Alternatively, compare only the packet's --range paths or the tree, not the commit, if bookkeeping commits must be allowed.
- **10.1-r3-03** `scripts/packet.py:63` (silent-failure engine) — POST_TIMEOUT = float(os.environ.get("PACKET_POST_TIMEOUT") or 3) is evaluated at import, so a non-numeric value makes every command (new, check-reply, flush, ...) die with a traceback before argument parsing. The variable is documented as tests-only, but this is the one place where an environment value breaks the 'harness errors never stop the caller' stance for all subcommands. → Parse it defensively: fall back to 3 on ValueError, or read it inside post().

## Checked and clear

10.1-r1-01 fixed: lane_identity reads CLAUDE_CODE_SESSION_ID first and hashes toplevel(), not cwd. With no session id, `new` warns and check-reply refuses unless --lane is passed. Tests cover the env var, a subdirectory resolving to the same lane, and the session-none refusal., 10.1-r1-02 fixed: the send is recorded in a <pid>.sent marker and the state file is never rewritten across the POST. test_close_during_post_is_not_overwritten covers it., 10.1-r1-03 fixed (off-anchor, door.py): an info claim with no floor hit stays info, and an info claim on a floor path still becomes one-way. door.py tests and the packet.py test both cover this., 10.1-r1-04 fixed: globs compile with DOTALL and end with \Z, so the head (?:.*/)? and the tail .* both cross a newline. Two newline-path tests are non-tautological (without DOTALL, `$` fails before the embedded newline)., 10.1-r1-05 fixed: post() runs in a daemon worker thread with join(POST_TIMEOUT), and _NoRedirect turns any 3xx into an HTTPError, so it counts as a failure. Tests cover a slow-drip server and a redirect., 10.1-r1-06 fixed: an unreadable packet doc in try_send returns a 'Skipped:' note, flush reports it and continues, and an unreadable event file is skipped and reported. --body-file and check-reply --file now exit 1 with no traceback. Tests cover these., 10.1-r1-07 fixed: check-reply compares the lane repo's HEAD (repo_of the outbox) with head_sha for one-way packets and fails closed on an unreadable HEAD. The docstring is corrected, two-way packets are exempt, and stale/touch use the same repo., 10.1-r1-08 fixed: the negation test floors src/billing/ only through the repo file, so a regression that honoured `!` would turn it two-way., 10.1-r1-09 fixed: the send-path tests assert the state, marker and posts rather than only the stub's dedupe., 10.1-r1-10 fixed: each invalid fixture maps to an expected error. ui-two-way, event-merged and event-stale fixtures were added, plus id-trailing-newline and event-stale-no-packet., 10.1-r1-12 fixed: git diff runs with -c diff.ignoreSubmodules=none and --ignore-submodules=none. The gitlink test sets diff.ignoreSubmodules=all., 10.1-r1-13 fixed: a leading ! or ^ inside brackets becomes [^/...], which also keeps the class from matching '/', as gitignore does. Tests cover both the included and the excluded character., 10.1-r1-14 fixed: _ecma_end rewrites a trailing unescaped $ to \Z. Every pattern in schemas/packet.schema.json ends with a plain $ (none is mid-alternation), so the translation covers all of them., 10.1-r1-15 fixed: an additionalProperties value other than false raises SchemaError. The packet schema uses only false (9 sites), so validation does not start raising., 10.1-r1-16 fixed: the case test uses ADRS/, which has no lowercase twin, and asserts that the reported path keeps its case., 10.1-r1-11 accepted (packet.py does not enforce --range; deferred to the Task 1.5 wiring): no change in this range, as expected., compile_rules' new Failed is raised only inside classify's try (both call sites), so a bad floor line returns one-way with a reason, never a traceback., Tests run at HEAD 20ffb7b: test_packet*.py ran 46 tests, OK; test_door.py ran 24 tests, OK.

## Not applicable

domain: generic repo (ai-skills), no Kalpa/PMG groups

**Verdict:** SHIP

## What this review did not cover

- Codex not used: the operator reported codex is out of credits. The fresh probe printed 'codex gpt-6.1-sol', but a probe does not test credits, so this Claude fallback ran on the operator's instruction.
- Single-context pass: no gstack specialist fan-out was dispatched, and gstack's review/SKILL.md engine and telemetry (gstack-review-log) did not run. The checklist and lenses were applied by hand to a fix re-review of 12 files and 629 lines.
- .env.example could not be read (permission denied), so it is unverified whether PACKET_POST_TIMEOUT and CLAUDE_CODE_SESSION_ID need declarations for resolve-identifiers.py.
- Not run: the full scripts/tests suite (only test_packet*.py and test_door.py), and no live queue or herdr session.
