# /review — dev-workbench @ `51bc62811de12a74427386a520fcc63108889bdc..da68dee72264031770af37bbd4271da21e4f6bf7` (3 commits)

**Review:** `10.4-r2` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.4-r2-01** `config/systemd/herdr-agent-view-ensure.service:5` (silent-failure) — The 60 s trigger turns a one-off crash into a recurring one. `ensure` exits 0 only when herdr.sock is absent (herdr-agent-view:193). When the socket file exists but nothing answers, `stale()` in attention mode calls `agent_list()`, and `call()` raises an uncaught ConnectionRefusedError, exit 1. That happens after an unclean server exit that leaves the socket behind, or during server startup. The new ensure.service also lacks the sibling's ExecStartPre readiness wait (herdr-agent-view.service:19). Before this range, `ensure` fired only on a socket change. Now it fires every 60 s, indefinitely. On macOS each run appends a traceback to the unrotated herdr-agent-view.log (plist StandardErrorPath). On Linux the ensure.service goes failed every minute. Both new comments, here and at plist:9, claim `ensure` 'exits 0 when the herdr server is down', which is false for this case. → Make `ensure` quiet on an unreachable server. In main()'s ensure branch, catch OSError (ConnectionRefusedError, FileNotFoundError) from stale()/apply() and exit 0. Or have call() raise a typed error that ensure treats as 'server down'. Then the comment claim is true for every path that reaches it.

## NOTE (1)

- **10.4-r2-02** `config/herdr/helpers/herdr-agent-view:21` (dirty-comment) — The usage line still says `ensure` re-applies 'if the server restarted (LaunchAgent)'. After this range, `ensure` also runs every 60 s from a LaunchAgent StartInterval and a systemd timer. It re-applies on a config reload and on a driver-set change too. Small related race: the ensure branch (line 201-202) reads the state, then re-reads it in apply after two socket calls. A user toggle landing in that window can be overwritten by the periodic re-apply. The window is milliseconds once a minute, so it is a note only. → Reword line 21 to: re-apply the recorded mode when it drifted (server restart, config reload, driver set change); run at server start and every 60 s.

## Checked and clear

10.4-r1-01 fix: the plist StartInterval=60 (plutil -lint OK on the rendered template) and the systemd timer OnStartupSec=45/OnUnitActiveSec=60 both run `ensure`. stale() compares the driver signature, so a driver renamed mid-server is picked up within 60 s. install.sh unload+loads the plist on macOS and links and enables the timer on Linux. The dry-run text was updated., 10.4-r1-02 fix: the new tests exercise read_record (2-field, 3-field, other marker, missing) and stale (same set, new driver, old record, rest ignores the set). They pass locally: herdr-agent-view-test.py exits 0., 10.4-r1-03 fix: the stale() docstring, the ensure comment and the plist comment now state the agent.list cost., lenses: fail-open (no drivers still fails closed), doc claims (PLUGINS.md:48 matches the wiring), checklist: enum completeness, distribution/CI wiring (install.sh link + enable)

## Not applicable

domain rules: generic repo, checklist: SQL & data safety, LLM output trust boundary, shell injection, frontend/view

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex unavailable (out of credits): Claude fallback pass
- no gstack specialist fan-out: a single-context pass over an 82-line config/test diff in a read-only pane
- could not load or run the systemd units (macOS host; no systemd-analyze verify)
- could not run a live herdr server to observe the 60 s re-apply end to end
- the driver-rename trigger half of 10.4-r1-01's disposition lives in ai-skills herdr/SKILL.md, outside this range: not reviewed
