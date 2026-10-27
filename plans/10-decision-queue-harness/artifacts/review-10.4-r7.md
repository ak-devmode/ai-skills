# /review — dev-workbench @ `b674bfdd29bb18ef4bf3c60339aab142e2032df1..7d8618f5bca73703832346aad494e48da12c7602` (3 commits)

**Review:** `10.4-r7` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.4-r7-01** `queue/decision_queue/app.py:187` (fail-open lenses: fail-open · reopens 10.4-r4-07) — The 10.4-r4-07 fix is fail-open by default: with DQ_UI_ALLOWED_TENANTS unset (the state of every install until someone does README step 4 by hand), _tenant_error returns None and any tenant is stored and rendered, which is the defect r4-07 named. Nothing in install.sh or the unit sets it, and the only signal is a WARNING at serve start. config.py:45 gives no reason why fail-open beats fail-closed here; the fix discipline requires one. The empty-list case fails closed, so unset is the one path that stays open. → Make unset refuse ui packets (same as set-but-empty), so non-ui packets still flow and ui needs an explicit allow-list. Or have install.sh write the drop-in with the demo tenant. If fail-open is kept on purpose, write down why in config.py and the README.

## NOTE (1)

- **10.4-r7-02** `queue/decision_queue/app.py:31` (engine checklist: timeouts) — REQUEST_DEADLINE cuts the whole connection 60 s after it opens, including the response. GET /p/<id> is now the only page carrying the shots (up to ~4 MB of base64 in HTML), and it is the page the user needs to decide. On a phone link below ~70 KB/s the reply is cut, and the decision page never loads. The comment accepts this ('fires mid-reply cuts that reply'), but no test or README line covers the large-reply case. → Start the deadline at request start and cancel it once the body is read (it guards slow uploads, not slow downloads); the per-op SOCKET_TIMEOUT already bounds a stalled reader. Or document the cut for /p/<id>.

## Checked and clear

10.4-r4-01/04 resolved: render_row passes shots=False for every door; shots default off; only /p/<id> sets shots=True, 10.4-r4-02 resolved: insert_packet strips images from payload (content keeps them for retry identity); feed_page names columns, never selects content, and strips payload images in SQL too; get_packet reads only the two image strings from content, migration 004: strips payload images only where content IS NOT NULL, so pre-003 rows keep their only copy; get_packet leaves an existing image in place, jsonb #- on feed rows: schema forces payload to be an object, so the path delete cannot hit a top-level scalar, 10.4-r4-03/08 resolved: one-way ui feed test, two-images-at-both-caps test, 10.4-r4-05 resolved: per-route cap (413 over cap, bounded drain), 15 s socket timeout -> 408, watchdog; HTTP/1.0 default so one request per connection, 10.4-r4-06 resolved: _fallback scrubs data URIs and cuts long strings, tenant check runs only after schema validation passes, so payload.tenant is present, test suite: 70 passed with DQ_SCHEMA_SOURCE pointed at the ai-skills branch schema; against ~/Projects/ai-skills main the vendored-schema drift test fails, as expected until both branches land together

## Not applicable

domain rules — generic repo

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex gate: codex out of credits (probe: none codex out of credits)
- gstack specialist fan-out (security, performance, testing, red-team, …) not dispatched: single-context Claude pass over a 372-line fix range
- running migration 004 against the live homelab decision_queue database
- checking whether DQ_UI_ALLOWED_TENANTS is set on homelab (no access from this read-only pane)
- real slow-link test of GET /p/<id> under the 60 s deadline
