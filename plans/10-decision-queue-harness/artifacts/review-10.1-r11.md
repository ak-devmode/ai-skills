# /review — ai-skills @ `fc51f4a5a274b1b14bb0864a9f9ae6a017c2366a..85e22e8fbf09157ab96f1e85c8382d80d13d5daa` (4 commits)

**Review:** `10.1-r11` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (1)

- **10.1-r11-01** `concurrency/SKILL.md:332` (engine Shell Injection) — The stdin example still interpolates the pasted reply into double-quoted shell source. A reply containing $(command), backticks, or closing quotes executes locally before ssh or check-reply runs. Piping does not prevent expansion. The relay at line 337 and plan/SKILL.md:528 retain the same unsafe pattern. → Pass reply content through a safely written file or a quoted heredoc, and use argument-array execution for the herdr relay. Never interpolate pasted content into shell source.

## SHOULD FIX (1)

- **10.1-r11-02** `concurrency/SKILL.md:327` (doc-claim 6) — FLUSHED 0 while parked is normal after a successful flush: cmd_flush skips packets with .sent markers even while they remain open awaiting an answer. The prescribed every-wake flush therefore falsely diagnoses healthy parked lanes as misconfigured. Counts also include retries from earlier wakes, so they need not match newly printed packet IDs. → Check each expected packet's .sent marker and reported rejection/blocked state on the box; distinguish already delivered packets from newly sent packets instead of requiring count equality.

## NOTE (0)


## Checked and clear

Both touched files read in full; relevant packet.py, door.py, schema validator and fixture contracts inspected, Skill lint passed for both files with advisory notes only, Enum and CLI flag completeness, Local-maxima and invented-reality checks, Dirty-comment checks, Gate-integrity diff inspection: no gate relaxations

## Not applicable

SQL, database migrations and data repairs, Async/sync mixing, ORM column safety, Time-window and timing-test changes, Frontend rendering, CI/CD and release distribution changes, Build: repository explicitly declares no build

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- Unit suite attempted: 426 tests reported 470 errors and 2 skips; the read-only sandbox prevents temporary-directory creation.
- Approval-class check attempted but refused the supplied SHA by resolving origin/<SHA>; no approval classes were checked.
- Live Claude Code skill invocation and box SSH/queue integration were not exercised.
- Independent specialist sub-reviews were not run; delegation was not authorized.
