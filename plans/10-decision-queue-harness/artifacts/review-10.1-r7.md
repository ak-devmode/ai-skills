# /review — ai-skills @ `bb0bc6dfbba98d3e6dbab35996b943ec381dacf2..ef078ba12c7d402192d471b3d54f0b7caad23fe4` (1 commits)

**Review:** `10.1-r7` · **Reviewer:** claude-fallback codex out of credits (dispatch brief) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (dispatch brief)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (dispatch brief)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (1)

- **10.1-r7-01** `scripts/packet.py:221` (fail-open engine) — Every 4xx other than 409/404-on-event becomes a permanent `.rejected` marker, and flush now continues past it (NOT_SENT) instead of breaking. Transient or config 4xx are therefore made permanent: 408 Request Timeout, 429 Too Many Requests, 401/403 from an expired or missing credential, and a 404 on /packets (packet path at line 291 maps `missing` to `rejected`) from a wrong DECISION_QUEUE_URL base path. One flush against a misconfigured or rate-limiting queue marks every pending packet and event in every outbox `.rejected`; they are never retried and no command clears the marker. Before this commit those retried as Blocked. → Classify only definitive content refusals as rejected (400, 409 conflict, 413, 415, 422); treat 401/403/404-on-packets/408/429 as blocked (retry, break the flush). Optionally stop the flush after the first rejection of a kind that could be systemic, and document how to clear a marker (or have `new --id` re-send clear it on success).

## SHOULD FIX (1)

- **10.1-r7-02** `scripts/packet.py:561` (silent-failure engine) — An event whose packet was marked `.conflict` or `.rejected` is retried forever: the packet is never re-posted, so the queue keeps answering 404 for the event, try_send returns Held (line 280), and flush lists it and POSTs it again on every run. The module doc (lines 28-30) promises the 404 event is 'retried after the packet', which can never happen here; this is the endless-retry path the commit set out to remove. → In the events loop, before posting, check ev['packet_id'] against `<pid>.conflict`/`<pid>.rejected` in the same outbox and mark/skip the event (e.g. `evt-<id>.rejected` with 'packet refused'), or Hold only while the packet is unsent-but-unmarked. Add a test: packet 400 then its close event, flush twice, assert one /events POST at most.

## NOTE (1)

- **10.1-r7-03** `scripts/packet.py:291` (engine engine) — After a packet `.conflict` (the queue holds different content under this id), the packet's later events (close/stale/touch) still POST and get 200, so they apply to the queue's other-content packet rather than this lane's. Likely benign when the conflict is an edited re-send of the same logical packet, but it is undocumented. → Decide whether events for a conflicted packet should be sent; if not, skip them in flush like the rejected case above, and state the stance in the failure-stances doc.

## Checked and clear

2xx ok -> .sent marker only on ok; no refused kind writes .sent (try_send lines 274-293), 3xx via _NoRedirect and non-200/201/204 success codes stay blocked, 5xx/network/timeout stay Blocked and break the flush, flush checks .sent before markers and markers before POST; event marker path evt-<id>.<kind> matches _refusal's stem, 409 on packets/events no longer counted as sent; tests cover 409, 400, 503, event-404-then-packet, test_packet.py: 48 tests pass at head (run by reviewer)

## Not applicable

domain checks (generic repo)

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- codex gate not run (out of credits per dispatch brief; probe answered but exec was not attempted)
- no gstack engine load or specialist fan-out: single-context Claude pass on a 2-file range
- no live queue service exercised; behaviour inferred from code and the stub
