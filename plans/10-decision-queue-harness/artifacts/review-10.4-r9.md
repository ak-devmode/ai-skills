# /review — dev-workbench @ `7d8618f5bca73703832346aad494e48da12c7602..f7074db42263782e49e7e7bea38b225f924f6ca6` (2 commits)

**Review:** `10.4-r9` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 1 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.4-r9-01** `queue/decision_queue/app.py:79` (engine · reopens 10.4-r7-02) — The r7-02 fix does not let a slow reader finish; it replaces the 60 s cut with a 15 s one. _send writes the whole page in one self.wfile.write(body), and wfile is unbuffered, so that is one sock.sendall. Since Python 3.5 a socket timeout bounds the WHOLE sendall call, not each op: a scratch probe (settimeout(2), 4 MB sendall, a reader draining steadily and never stalling 2 s) raised timeout at 2.0 s on Python 3.13. With SOCKET_TIMEOUT=15, a GET /p/<id> carrying two capped shots (>3 MB, the test's own size) is cut for any link below about 270 KB/s. The r7-02 cutoff was about 70 KB/s, so this is a regression on the decision page. The header comment (app.py:11-13, 'bounded by the per-op SOCKET_TIMEOUT alone ... a merely slow one finishes') and REQUEST_DEADLINE's comment (:34) state the opposite. The new test cannot see it: it sleeps 1.5 s, then drains at loopback speed under a 10 s socket timeout, so sendall finishes inside the timeout. The test checks that the deadline is cancelled, not that a slow reader is served. → Write the body in bounded chunks (e.g. 64 KB per wfile.write) so SOCKET_TIMEOUT applies per chunk of progress, and check every other large write for the same single-sendall pattern. Make the regression test read at a throttled rate, with a socket timeout shorter than the whole transfer but longer than any one chunk; it must fail on the current single write. State the trade-off in the comment: a per-chunk timeout lets a slow-read client hold a handler thread for transfer-size / chunk x SOCKET_TIMEOUT. Either cap that with a generous reply deadline or say why it is acceptable on a tailnet-only queue.

## NOTE (0)


## Checked and clear

10.4-r7-01 resolved: config.ui_allowed_tenants() returns an empty frozenset when unset, _tenant_error refuses every ui packet (400, reason names DQ_UI_ALLOWED_TENANTS) and lets non-ui through; serve's start line, README step 4 and the docstring agree; the test's unset case fails with the fix reverted (old code returned 201), r7-01 test hygiene: the autouse conftest fixture sets the demo allowlist, and the guard test deletes or overrides it per case; the set-but-empty case is still covered, deadline cancel placement: _request_read runs after a full body read, after the 413 drain, on /views/reset and at the top of do_GET; the early-error replies that skip it are small and stay guarded (fail closed); the protocol is HTTP/1.0, one request per connection, so a cancelled watchdog never leaves a second request unguarded, r7-02 test fails with the fix reverted (a 0.5 s watchdog cuts the blocked reply), queue tests: pytest -k 'tenant or slow or deadline or cap' — 12 passed, lenses: fail-open (the tenant guard now fails closed), silent-failure, local-maxima

## Not applicable

domain rules — generic repo, SQL migrations/data safety — no schema or query change in range, LLM trust boundary — no surface

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex cross-model pass — codex out of credits (Claude fallback)
- full queue suite not run — only the affected subset
- specialist sub-reviewer fan-out not dispatched — 91-line fix range, single-context pass
- no real slow-link (phone) measurement — the timeout behaviour is shown by a scratch socket probe, not against the running queue
