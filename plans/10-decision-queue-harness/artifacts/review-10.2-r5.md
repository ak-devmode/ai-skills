# /review — ai-skills @ `95d20cee7bc190f855c3bb21e023105fb2f9e5cc..21be2cddbf797300461b2b093a02cac3a3dca5cb` (1 commits)

**Review:** `10.2-r5` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 1 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.2 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.2-r5-01** `scripts/verify_lib.py:620` (engine correctness) — repeated_reframe matches against EVERY rejected reframe in the lineage, not only earlier ones (its docstring says 'earlier rejected reframes'). Because reframe_call recomputes the repeat on every call, a reframe the judge accepted and the loop built (stamped user_call=None, findings disposed --reframed --by judge) flips to call 'user' / kind 'repeat' as soon as a LATER review in the lineage proposes something >=0.85 similar and the judge rejects it (e.g. 'already built'). Reproduced: u-r1 accepted -> reframe_call ('judge','accepted'), judge_took None; append u-r2 similar + rejected -> reframe_call('u-r1') = ('user','repeat', 'repeats one this lineage rejected — u-r2: already built') and judge_took refuses. Effects: verdict-gate review_presence_blocks now blocks u-r1's already-recorded `--by judge` dispositions, packet_stuck loses its qualifying reframe (case 2 can fire), and the hold text claims r1 repeats a rejection that came after it. → Only count rejected reframes that precede this one: compare lineage round (lineage[rid][1] < lineage[review_id][1]) or log position of the rejecting verdict vs this reframe record; add a test where a later similar rejection leaves an earlier judge accept as 'judge'.

## NOTE (0)


## Checked and clear

Every consumer routes through vl.reframe_call: cmd_record [REFRAME] line, cmd_reframe_prepare refusal, cmd_reframe_record (under lock, on recs+[rec]), packet_stuck, reframe_check and verdict-gate via vl.judge_took; packet_repeat/judged_reframes calls only build packet/prompt content after the call is decided. No remaining reader of reframe-verdict fields outside verify_lib., Fail-closed paths: exception -> user; no reframe record -> user; unknown verdict -> user; accepted with no user_call stamp -> user; missing checkout or range -> door unknown -> user; finding anchor outside checkout/primary checkout or unknown finding id -> user; door.py one-way with no paths -> user. Verified by reading and by test_review_packets (17 OK)., 10.2-r4-03: _latest takes each review's latest verdict; a superseded accept is never consulted., 10.2-r4-01: a repeat is held whatever its own verdict says and the stamp records the repeat reason; reframe-record emits case 3 for it, dispose --by judge and the gate refuse it., 10.2-r4-02: repo_relative normalizes absolute anchors against the checkout and its primary checkout (git-common-dir), rejects '..' escapes., cmd_reframe_record branch coverage: call user / judge / rejected+kind rejected / else not-judged — 'unjudged' unreachable after appending rec; packet ids stable per (review, case) so case 3 emitted at record and again at reframe-record dedups., Full suite python3 -m unittest discover scripts/tests at 21be2cd: OK (skipped=2).

## Not applicable

domain: generic repo (ai-skills) — no Kalpa/PMG groups

**Verdict:** SHIP

## What this review did not cover

- codex out of credits: Claude fallback, single context — gstack engine and specialist fan-out (§3.2) not run per the brief's keep-output-small, read-only pane instructions
- review/SKILL.md prose re-read only for the changed hunks
