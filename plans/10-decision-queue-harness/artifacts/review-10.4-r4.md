# /review — dev-workbench @ `ef9bae08c8e2ddf77de0d4f43be33b5688e56159..b674bfdd29bb18ef4bf3c60339aab142e2032df1` (1 commits)

**Review:** `10.4-r4` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 8 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (3)

- **10.4-r4-01** `queue/decision_queue/render.py:221` (engine Performance) — One-way ui packets render the rich card in the feed with both full shots: render_row sends every door=one-way row to _card(rich=True), which calls _payload(p) with shots on; the shots=False guard at :226 covers only the compact card. 50 one-way ui packets make one GET / of up to 50 x 4 MB ~ 200 MB of HTML built in memory on the request thread. → Class: image weight decided by door instead of route. Thread shots through render_row/_card and pass shots=False from feed(); only /p/<id> renders images. Same check for any other list view that calls render_row. Update README's '(one-way: also in the feed)'.
- **10.4-r4-02** `queue/decision_queue/db.py:150` (engine Performance) — feed_page does SELECT * FROM packets for up to 50 rows, and insert_packet stores the images twice (payload and content Jsonb). With ui packets each feed load pulls and JSON-decodes up to ~400 MB from Postgres even though compact cards discard the images; get_packet (:122) also decodes content it never renders. Adjacent code made heavy by this range (lens 1). → Class: unbounded blob columns fetched for list views. Select explicit columns for the feed, omit content, and strip payload old/new image in SQL for feed rows; omit content in get_packet.
- **10.4-r4-03** `queue/tests/test_queue.py:283` (engine Test Gaps) — The feed weight test posts only the two-way fixture; no test covers a one-way ui packet on GET /, so the 200 MB feed path ships green. → Add a one-way ui fixture and assert GET / carries no <img; cover each door the feed renders.

## NOTE (5)

- **10.4-r4-04** `queue/decision_queue/render.py:224` (doc-claim 6) — Comment 'so a 50-row page never carries 50 x 4 MB of images' is false for one-way ui packets, which render rich with shots in the feed. → Make the code match the claim (finding on render.py:221), or correct the comment.
- **10.4-r4-05** `queue/decision_queue/app.py:19` (engine Performance) — MAX_BODY is global, so POST /events (no images) now accepts 5 MB too; ThreadingHTTPServer has no socket timeout, so a tailnet client declaring 5 MB and trickling bytes holds a thread indefinitely. → Per-route body cap (256 KB for /events) and a handler timeout.
- **10.4-r4-06** `queue/decision_queue/render.py:233` (engine Performance) — _fallback dumps every column of the row as text; a ui row that fails to render puts ~8 MB of escaped base64 (payload + content) into the page. → Truncate long values in _fallback.
- **10.4-r4-07** `queue/decision_queue/schema/packet.schema.json:131` (engine Trust Boundary) — 'never a real-patient tenant' and 'no token or real-patient id in route' exist only as $comment; the queue accepts and renders any non-empty tenant/route, so a real tenant (and the screenshot of it) would be stored and shown. → Enforce a demo-tenant allowlist at the lane (packet.py) and optionally at queue ingest.
- **10.4-r4-08** `queue/tests/test_queue.py:302` (engine Test Gaps) — The MAX_BODY boundary is only exercised with one full-size image (~2 MB body); a legal two-image packet at both caps (~4 MB) is never posted, so lowering MAX_BODY below ~4.01 MB would pass. → Post a packet with both images at the 2,000,000-char cap and expect 201.

## Checked and clear

XSS: every rendered ui field (route, tenant, labels, callouts, viewport) goes through esc(), png_src: fullmatch + b64decode(validate=True) + PNG signature; no bypass found, CSP: img-src data: with nonce-only script-src, Content-Length handling: malformed or oversize rejected before read, Schema regex: anchored, linear, ~17 ms on 2M chars; trailing-newline acceptance by $ is refused by png_src fullmatch, Vendored packet.schema.json byte-identical to ai-skills HEAD schemas/packet.schema.json, Demo tenant not hardcoded anywhere in the queue, Existing tests cover png_src rejects (non-PNG, bad base64, over-cap, trailing newline, non-string), CSP header, two-way compact card

## Not applicable

domain rules (generic repo), data-migration (no schema/DDL change)

**Verdict:** SHIP

## Reframe

The feed never carries images: render_row/feed always render ui packets without shots and the feed query selects a light projection without images or content; images exist only on /p/<id>.

Deletes: the door-dependent shots path in _card (shots flag on the rich feed card) and the SELECT * blob fetch in feed_page · removes: 10.4-r4-01, 10.4-r4-02, 10.4-r4-04

## What this review did not cover

- codex unavailable (out of credits): Claude fallback, gstack engine checklist + lenses applied in one context plus two specialist subagents (security+red-team, performance+testing); maintainability, api-contract, state-machines, simplification specialists not dispatched
- Test suite not run: needs Postgres
- No browser render of the feed or /p/<id>
