# /review — ai-skills @ `4cdea98569089e565e778d165e36a0ff558a6843..352f53a8191086e19a49f6af40bf0cd99f96c437` (2 commits)

**Review:** `10.2-r3` · **Reviewer:** claude-fallback codex not authed · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex not authed` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex not authed` (and the index carries it) until a codex re-review of this unit.
**Findings:** 4 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.2 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (1)

- **10.2-r3-01** `review/scripts/review.py:1622` (fail-open engine) — Case 1 (accepted reframe touching a one-way door, no overturns) is fail-open. reframe-record first prints the plain accepted line `[REFRAME] … accepted … build it, then record each finding it replaced`, and only afterwards, and only if packet_overturn() succeeds in writing a packet, prints `do not build it until the packet is answered`. Whether this is a door case is computed inside the emission, so any emission failure loses the classification too: packet_for returns None when the repo is not under VERIFY_PROJECTS, packet.py exits non-zero (outbox unwritable, schema refusal), or door.classify raises (it is called without a guard inside reframe_door). Each of these leaves stdout saying 'build it' and a generic stderr warning. Even on success, stdout carries both 'build it' and 'do not build it'. Scope §4.2 sends a door-touching accepted reframe to Alex, and the 10.2 fix discipline says new guards fail closed. The emission-failure test covers only case 2 via record, not reframe-record. → Separate the decision from the emission. Classify (overturns or reframe_door, with any exception from door.classify treated as one-way) before printing the accepted line. When it is Alex's call, print the hold line ('do not build until answered: packet or inline question') in place of 'build it', whatever happens to the emission. Then try the packet. Add a test where emission fails on a door-touching accepted reframe and assert stdout never says 'build it'.

## SHOULD FIX (2)

- **10.2-r3-02** `review/scripts/review.py:1379` (engine engine) — The packet's repo is os.path.join(vl.PROJECTS, e['repo']), and e['repo'] is repo_key(main_worktree(...)): the primary checkout, not the worktree that was reviewed. packet.py new runs with cwd set to that primary checkout. So for every herdr lane (concurrency worktrees, the main use case of scope 10), the packet lands in the primary checkout's .decision-queue/outbox, and its `branch` and `head_sha` record whatever the primary checkout has checked out (usually main), not the lane's reviewed head. A repo outside ~/Projects falls back to its basename under PROJECTS, which can resolve to an unrelated repo with the same name. The verify side uses os.getcwd(), so the two emitters disagree about where a packet goes. → Record the reviewed repo's actual path (the --repo argument record already has) and pass it to packet_for in place of the PROJECTS reconstruction, or have cmd_record/cmd_reframe_record pass a.repo through. Pass --range base..head so the packet ties to the reviewed head.
- **10.2-r3-03** `review/scripts/review.py:641` (doc-claim engine) — For case 3, record prints `[REFRAME] … judge it before fixing them — review.py reframe-prepare …` and then a `[PACKET] … repeat case — Alex's call` line for the same review. review/SKILL.md says case 3 is emitted 'before any re-judging', and §4.2 says a reframe already rejected and proposed again is Alex's to see, not the loop's to re-judge (repeated_reframe's docstring says the same). Nothing in reframe-prepare refuses a repeat, though, and the stdout tells the driver to re-judge. A re-judge that accepts would then proceed to build while the packet waits. → Run repeated_reframe before the [REFRAME] judge-it line. On a repeat, replace that line with the hold (Alex's call, do not re-judge), and have reframe-prepare refuse (or warn on) a reframe that repeated_reframe matches.

## NOTE (1)

- **10.2-r3-04** `review/scripts/review.py:1480` (doc-claim engine) — Case 2 fires on any blocking finding in a round 3 or later review with no SHIP, including a defect first raised in round 3. The plan and §4.2 say 'a blocking finding that survived two rounds'. The SKILL text documents the wider reading ('round 3 or later with no SHIP'), so this is a definition drift, not a hidden one. Separately, the docstrings of packet_stuck ('Fail-closed: an unknown round is round 0, so it never fires early') and repeated_reframe ('Fails closed toward a packet: … no proposal text is not a repeat') call fail-closed behaviour that is fail-open: an unknown input produces no packet. → Either narrow round-3 stuck to blocking findings whose file or lineage carried a blocking finding in an earlier round, or state in §4.2/SKILL that round-3-no-SHIP counts as survival. Reword both docstrings to say 'fails open (no packet) because …', with the reason.

## Checked and clear

verify run-cap STOP: a packet only when the gate label is not PASS (verdict-gate prints PASS only for a clean pass), stable id per run, and stop_packet never raises, emission failures in record/case 2 and verify warn on stderr and keep exit 0 (test_an_emission_failure_never_stops_the_review; full suite of 435 tests OK), no-URL path: emission writes only the outbox, and the inline question is still printed (convergence/[REFRAME]/run-cap lines unchanged), stable_id output fits the schema id pattern ^[A-Za-z0-9_-]{8,64}$, and packet.py new --id re-sends idempotently, option order matches --recommended 1 and each body's recommendation in all four packets, fallback local-maxima findings (advisory) are excluded from case 2

## Not applicable

domain checks: generic repo (ai-skills)

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- codex unavailable (codex not authed): Claude fallback, single context
- gstack engine and specialist fan-out not loaded: read-only lane brief, kept to a direct diff read against scope §4.2 and plan Task 2.5
- did not exercise packets from a real herdr worktree end to end
