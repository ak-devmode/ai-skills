# /review — dev-workbench @ `ef9bae08c8e2ddf77de0d4f43be33b5688e56159..51bc62811de12a74427386a520fcc63108889bdc` (1 commits)

**Review:** `10.4-r1` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (1)

- **10.4-r1-01** `config/herdr/helpers/herdr-agent-view:146` (silent-failure engine) — The driver pane-id set embedded in the attention filter goes stale in the normal flow, and nothing re-snapshots it. `stale()` compares the signature only when `ensure` runs, and `ensure` runs only on a herdr.sock change (LaunchAgent WatchPaths; systemd service is PartOf herdr-server). That means once per server boot. Drivers rename themselves mid-server (`herdr agent rename $HERDR_PANE_ID driver`, ai-skills/herdr/SKILL.md:73). So a driver started after the view was applied is missing from the set: when it finishes in another space, its `done` never surfaces until Alex toggles by hand or the server restarts. That hides the one signal scope 4.4 keeps ('only drivers that need Alex surface'). The rule fails closed for lanes but open, as silence, for drivers. PLUGINS.md:51 ('`ensure` re-applies the view when that set changes') claims a trigger that does not exist. → Give the drift check a trigger. Have the driver-rename step run `herdr-agent-view ensure` right after `herdr agent rename … driver` (herdr SKILL.md, cross-repo), and add a periodic backstop (`StartInterval` in the plist template, a `.timer` for systemd) so a rename/clear done by hand also converges. Then correct PLUGINS.md §3 to name the real triggers. Class: every derived-snapshot input to the view (driver set today) needs an event that refreshes it, not only a boot.

## SHOULD FIX (1)

- **10.4-r1-02** `config/herdr/helpers/herdr-agent-view-test.py:79` (engine engine) — The drift test proves only that `signature()` changes with a new driver. It does not exercise `read_record`/`stale` (old 2-field record parses to sig ''; attention + matching sig not stale; attention + new driver stale; rest mode ignores the set), so the path that is meant to keep the embedded set fresh has no coverage. That is how the missing trigger above went unseen. → Add fixture cases for read_record's parse of 2- and 3-field records and for stale() with a monkeypatched boot_marker/agent_list/STATE in a temp dir: attention+same set -> not stale, attention+new driver -> stale, rest+new driver -> not stale (beyond the config mtime check).

## NOTE (1)

- **10.4-r1-03** `config/herdr/helpers/herdr-agent-view:141` (dirty-comment engine) — The `stale()` docstring still says 'Both are a stat(), so the steady state costs nothing', and `ensure`'s comment at line 200 says 'Steady state is two stat() calls'. In attention mode, `stale()` now makes an `agent.list` socket round-trip. → Update both comments: attention mode adds one agent.list call.

## Checked and clear

Plan Task 4.3 acceptance: a lane (never named `driver`) reaching done/PARTITION-DONE matches neither the blocked clause nor the driver-done clause, so it no longer raises the attention count or the helper toast, whatever the state of the driver set, Blocked always counts, lane or driver; current-space agents always show, Fail closed with no drivers: the `in` over an empty pane_id list matches nothing, agent.list field names checked live (read-only): `name` is present on renamed agents, `pane_id` and `agent_status` match what the helper reads, read_record keeps backward compatibility: an old 2-field record yields sig '' and is treated as stale in attention mode, never as a crash, Toast count uses needs_attention, which matches the filter minus the current-space clause, PLUGINS.md native-toast note answers the scope's per-pane toast question (not possible in 0.9.1; toasts still fire for lanes)

## Not applicable

domain groups: generic repo (dev-workbench), data-migration, api-contract: no schema or API surface in range

**Verdict:** SHIP AFTER BLOCKING

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex unavailable (out of credits): single-context Claude fallback, not a cross-model review
- gstack specialist fan-out (security/performance/testing/red-team/maintainability) not dispatched; this was one checklist pass over a 197-line diff, read-only pane brief
- no live behaviour test of agent.view.set or of the pane_id filter field against herdr; the filter semantics are inferred from the helper's own test interpreter
- did not verify whether herdr allows more than one agent named `driver` at once (would mutate live state)
