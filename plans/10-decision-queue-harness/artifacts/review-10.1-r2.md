# /review — dev-workbench @ `28850dcd922c96d7663db561a31294952cc512ee..98a4109732a022f068f002e67486f9827b7eab5e` (2 commits)

**Review:** `10.1-r2` · **Reviewer:** claude-fallback codex out of credits (per dispatcher) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (per dispatcher)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (per dispatcher)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 7 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (1)

- **10.1-r2-01** `config/systemd/decision-queue.service:15` (engine Distribution & CI/CD) — ExecStart hardcodes %h/.local/bin/uv, but on homelab2026 (the only deploy target) uv is /usr/bin/uv and ~/.local/bin/uv does not exist (checked over ssh). The unit fails 203/EXEC and restart-loops every 5 s. install.sh:279 still prints 'enabled decision-queue.service', because `enable --now` on a Type=simple unit succeeds before the exec fails. So the install reports success for a service that never runs (fail-open). → Use `ExecStart=/usr/bin/env uv run --frozen --project %h/.local/share/decision-queue python -m decision_queue serve` (the PATH= line already covers /usr/bin and mise shims, matching herdr-server.service's `/usr/bin/env herdr`). In install.sh, check `systemctl --user is-active decision-queue.service` a few seconds after enabling instead of trusting the enable exit code.

## SHOULD FIX (3)

- **10.1-r2-02** `queue/decision_queue/db.py:64` (silent-failure Race Conditions & Concurrency) — A closed/stale/touch event for a packet the server does not have yet is stored, and its effect is silently dropped. The effect never applies later: insert_packet ignores events already stored, and an event retry is deduplicated (rowcount 0). Reachable path: queue down at `packet.py new` (packet stays in the outbox); queue comes back; Alex answers from the pane; the driver's `close` POSTs the event directly (try_send) before the next `flush` sends the packet. The packet then shows PARKED/open forever and inflates the parked and time-parked stats. The migration comment (events.packet_id 'may arrive before its packet') anticipates this ordering but doesn't handle it. → In insert_packet, after a new insert, apply the latest stored closed/stale/touch event for that id in the same transaction (e.g. UPDATE packets ... FROM events WHERE packet_id=%s ORDER BY received_at). Add a test that posts the event before the packet.
- **10.1-r2-03** `queue/decision_queue/render.py:174` (engine Type Coercion at Boundaries / compatibility) — There is a backslash inside an f-string expression (`{esc("card failed to render — plain text:\n" + txt)}`), which is a SyntaxError before Python 3.12. Confirmed: `ast.parse` under 3.11 fails with 'f-string expression part cannot include a backslash'. pyproject.toml and uv.lock declare requires-python >=3.11, so uv may choose a 3.11 interpreter, and then the whole package fails to import. Homelab currently has 3.14, so this does not affect today's deploy. → Move the string out of the expression (`msg = "card failed to render — plain text:\n" + txt` then `{esc(msg)}`), or raise requires-python to >=3.12 and re-lock.
- **10.1-r2-04** `queue/tests/conftest.py:18` (fail-open Gate Integrity) — PGBIN only looks in three hardcoded directories (Homebrew x2, Debian /usr/lib/postgresql/16). When none exists, the session fixture skips every DB-backed test (21 of 23). homelab2026 has no initdb on PATH and no /usr/lib/postgresql, so `pytest -q` there reports only skips, with no failures. Plan 10.1 Task 1.3's acceptance 'service tests green' therefore passes vacuously on the deploy host. → Resolve initdb via shutil.which first (plus PG_BIN env override), and make a missing binary a failure unless an explicit opt-out env (e.g. DQ_ALLOW_SKIP_PG=1) is set.

## NOTE (3)

- **10.1-r2-05** `queue/decision_queue/app.py:74` (engine LLM Output Trust Boundary) — This is about cross-site requests, not missing auth (no auth is settled). POST /packets, /events and /views/reset accept any Content-Type. Any web page open in Alex's browser on a tailnet device can forge packets with `fetch(url, {method:'POST', mode:'no-cors', body: JSON})` (text/plain, so no CORS preflight). A forged packet carries a prefilled reply textarea that Alex copies and pastes into an agent pane. That turns a drive-by page into prompt injection into a lane. The attacker needs the MagicDNS hostname, which limits the risk. → Reject POSTs whose Content-Type is not application/json (forces a CORS preflight the server never answers). For the /views/reset form, also check `Sec-Fetch-Site: same-origin` or Origin.
- **10.1-r2-06** `config/systemd/decision-queue.service:15` (engine Distribution & CI/CD) — `uv run` without --frozen/--locked runs against ~/.local/share/decision-queue, which is a symlink into the dev-workbench checkout (install.sh:268). If pyproject.toml and uv.lock drift, the service rewrites uv.lock in the repo on start, leaving the checkout dirty (the git-hygiene hook will flag it). First start also needs network to sync dependencies. → Add --frozen to ExecStart (same edit as the blocking ExecStart fix).
- **10.1-r2-07** `config/systemd/decision-queue.service:9` (doc-claim lenses §6) — `After=network-online.target` does nothing in a user unit: the user manager cannot order against system targets. At boot the service may start before PostgreSQL is up. It recovers only through migrate raising and Restart=on-failure, not through this ordering, and the line reads as if it waits. → Drop the line, or replace it with a comment that the unit relies on Restart=on-failure while PG comes up.

## Checked and clear

SQL & Data Safety: all queries parameterized; ON CONFLICT idempotency; event side-effects in the same transaction as the event insert (psycopg conn context rolls back on exception), Migrations: advisory xact lock + schema_migrations; tables match scope §7 (packets/events/views, plus schema_migrations bookkeeping; events.kind adds touch), HTML rendering/XSS: every dynamic value through esc(); ids pattern-constrained; CSP nonce-only script; per-card plain-text fallback present and tested, DSN file handling: owner/mode/regular-file/empty checks fail closed, Bind: 127.0.0.1 only, not configurable, Page bounded: PAGE_SIZE 50, MAX_PAGE 200, page param regex-capped, Vendored schema identical to lane A's ai-skills/schemas/packet.schema.json (diff -q clean), Data-model template: ERD + before/after with pure-CSS toggle per card; generic template for other types (Task 1.4), Tests: 23 passed locally (uv run pytest -q, Homebrew PG), Dirty comments: none found, Shell injection: no subprocess in service code

## Not applicable

Domain rules (generic repo — no Kalpa/PMG groups), Async/Sync mixing (sync-only code), LLM prompt issues (no prompts in range), Approval classes and data repairs (no data repairs)

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- codex cross-model gate not run: dispatcher stated codex is out of credits (probe itself reported codex gpt-6.1-sol)
- specialist fan-out (security, performance, testing, red-team, maintainability, data-migration, api-contract) not dispatched: single-context pass in a read-only review pane under a keep-output-small directive
- Did not start the unit under systemd on homelab or exercise `tailscale serve` HTTPS / copy button in a secure context (behaviour rows belong to /verify)
- Did not verify homelab-db-backup.timer covers decision_queue (README defers it to deploy)
- Did not view the committed screenshots (queue/docs/*.png) against the rendered output
- Did not run tests under Python 3.11 (only an ast.parse under 3.11)
