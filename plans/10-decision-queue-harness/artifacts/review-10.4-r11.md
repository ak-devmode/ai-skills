# /review — dev-workbench @ `f7074db42263782e49e7e7bea38b225f924f6ca6..c471f7b0278306a04bf07e740aced95b522a0292` (1 commits)

**Review:** `10.4-r11` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 1 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (0)


## NOTE (1)

- **10.4-r11-01** `queue/decision_queue/app.py:145` (silent-failure) — Adjacent, pre-existing, not introduced by c471f7b. When a reply write times out after headers and part of the body are out (a reader stalled past SOCKET_TIMEOUT, still reachable with chunked writes), the TimeoutError reaches _guard's `except Exception`, which logs `internal error: TimeoutError('timed out')` and calls _json(500) on the same socket: a second status line and JSON body are appended into the first reply's body stream. Observed in the pre-fix scratch run of the new test (stderr `internal error: TimeoutError('timed out')`). The header (app.py:5, 'never a half-write') claims otherwise; ops see a timeout logged as an internal error. → Track whether headers were sent (e.g. a flag set in _send before end_headers); in _guard, if they were, log the write failure as a client timeout and set close_connection instead of writing a 500. Same class: any exception after end_headers.

## Checked and clear

10.4-r9-01 resolved: every reply goes through _send (no other wfile write in app.py), wbufsize is the default 0 so each WRITE_CHUNK slice is its own sendall and SOCKET_TIMEOUT bounds each chunk, Regression test fails with the fix reverted: pre-fix app.py in a scratch copy -> 1200918 of 4005419 body bytes, TimeoutError; with the fix both slow-reader tests pass (8.1 s, 2.1 s), memoryview slicing: body is always bytes (len() already used for Content-Length); empty body (303) writes nothing, same bytes on the wire as before, Trade-off comment (app.py:15-17) is accurate: per-chunk bound gives at most ~size/64 KB x 15 s per thread; bind is 127.0.0.1 behind tailscale serve (config.BIND_HOST), matching 'tailnet-only', lenses: fail-open (stalled reader still dies within one SOCKET_TIMEOUT per chunk), dirty-comment (SOCKET_TIMEOUT/WRITE_CHUNK comments match behaviour), engine checklist: no SQL, auth, or concurrency surface changed in the range

## Not applicable

domain rules — generic repo, data-migration, api-contract specialists — no schema or route change in range

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex cross-model gate — codex out of credits (Claude fallback)
- specialist sub-agent fan-out — not dispatched: 42-line single-file fix, read-only brief to keep output small; single-context pass
- Linux timing of the new test — run on macOS loopback only; margin per 64 KB chunk vs the 1 s test timeout not measured on Linux
