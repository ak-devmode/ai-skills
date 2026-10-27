# /review — ai-skills @ `fc51f4a5a274b1b14bb0864a9f9ae6a017c2366a..5c994cf290c46c4fa7a950f5c6db473a576b1de1` (3 commits)

**Review:** `10.1-r8` · **Reviewer:** claude-fallback codex out of credits (driver brief) · **Passes:** engine (Claude fallback, single context), lenses; domain n/a
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (driver brief)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (driver brief)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (0)


## SHOULD FIX (2)

- **10.1-r8-01** `concurrency/SKILL.md:331` (fail-open) — The box reply path tells the driver to hand-quote Alex's pasted reply into `ssh <box> '... check-reply --reply "<text>"'`, i.e. through two shells. A reply containing an apostrophe ("don't") closes the single-quoted remote command and the check never runs as written; a double-quoted variant expands `$(...)`/backticks in pasted text on the box. packet.py already supports `--reply -` (stdin), verified in a scratch repo with a reply containing an apostrophe: OK. → Pipe the reply instead of quoting it: `printf '%s' "<reply>" | ssh <box> 'cd <remote worktree> && ~/Projects/ai-skills/scripts/packet.py check-reply --lane <m>/<w>/<a> --reply -'`.
- **10.1-r8-02** `concurrency/SKILL.md:326` (doc-claim) — "Check the output names the packets you expect" cannot be followed: `flush` prints only `FLUSHED <n> packets, <m> events` plus skipped/blocked notes, never the ids it sent (scripts/packet.py cmd_flush). The guard meant to catch the silent-skip case this fix describes is therefore a count, and the instruction claims more than the tool reports. → Say what is checkable: the `FLUSHED <n>` count must equal the number of PARKED/PACKET ids the box lane printed since the last flush, and `FLUSHED 0` while a box lane is parked is a misconfigured path or env, not an empty outbox.

## NOTE (0)


## Checked and clear

10.1-r6-01 resolved: box flush runs packet.py on the box with --driver and no --outbox, so outboxes() resolves to the remote worktree's toplevel .decision-queue/outbox; check-reply over ssh reads that outbox and the lane's own HEAD via repo_of(); only the driver initiates (is_driver via --driver); lanes still never POST., 10.1-r6-01 claim 'flush silently skips a configured outbox that does not exist' verified: nonexistent --outbox prints FLUSHED 0 packets, 0 events, exit 0., 10.1-r6-02 resolved: scratch-repo run of the documented recipe — --type data-model --payload-file <fixture payload> creates a packet; the old --body recipe is refused '/payload: missing required tables'. Fixture path exists and its payload matches the documented shape. Same in plan/SKILL.md., 10.1-r6-03 resolved: scratch-repo run — session-none packet; check-reply without --lane refuses ('pass --lane M/W/A'); with --lane taken from the emitting session's own `reply:` line returns OK. find_packet still checks the packet's emitting lane fields, so --lane does not widen acceptance beyond the outbox., No defect introduced in the local-lane flush/reply wording ('repeat --outbox per local lane').

## Not applicable

domain.md groups — ai-skills is a generic repo (no Kalpa/PMG surface)

**Verdict:** SHIP

## What this review did not cover

- codex not used: out of credits per the driver brief (probe still reports a model); Claude fallback, single context
- no specialist fan-out: a 3-commit, 2-file docs diff in a read-only pane; specialist passes not dispatched
- box path not run end-to-end: no ssh to homelab2026 from this pane; verified the packet.py behaviour each step relies on locally
- gstack engine telemetry (§3.4) not written: read-only pane
