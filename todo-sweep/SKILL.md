---
name: todo-sweep
version: 1.0.0
description: |
  Verify accumulated TO-DO items against the CODE and triage each into one of four
  buckets — done elsewhere, rendered moot, still true, or still true but wrongly framed.
  Proposes; never writes back unattended. Resumable across sessions, because a full
  sweep of a few hundred items does not fit one context.

  It is a VERIFIER, not a task manager. It does not prioritise, schedule, assign, or
  set due dates. If it starts growing those, stop and re-plan.

  Use when asked to "sweep the TO-DOs", "verify the TO-DO list", "todo-sweep", "check
  which TODOs are still real", "triage the backlog", or "is this TODO still true".
  Also the tool for the periodic reconciliation the SessionStart TO-DO counter makes
  visible. Do NOT use it to add items — /plan §11.1-11.2 owns intake.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# /todo-sweep — verify what the TO-DO file asserts

## 1. Why this exists

`TO-DO.md` grew to 471 open items across 133 sections, of which **3** had ever been
verified, without anyone noticing. The cause is structural, not a discipline failure:

```
  INTAKE                                   EXIT
  /plan §11.1-11.2 appends every           a human decides to remove
  deferred item automatically              an item, or nobody does
        |                                         |
        v                                         v
     automatic                                 manual
        \___________________  ___________________/
                            \/
              a one-way valve grows monotonically
```

No amount of discipline fixes an asymmetric flow. This skill is the exit side.

**The governing insight: size is not the disease, staleness is.** A 471-item file where
every item is true is a valuable asset — the "did we already do X?" grep is load-bearing.
A 100-item file where a third are lies is worse, because you stop trusting any of it, so
you stop reading, so nothing closes. **Optimise for trustworthiness and let size be a
consequence.**

An item sitting in `TO-DO.md` is not proof the work is undone. The file asserts
undone-ness it never re-verifies. Of 8 items checked by hand in plan 114.1, **one was
half-shipped, one had a wrong premise, and one had a wrong count** — the only measurement
anyone has, and the reason verification runs against code rather than against the doc.

## 2. Two things this skill deliberately does NOT do

2.1 **It is not wired into `/closeout`.** An earlier design put it there. Rejected,
for a reason that is mechanical rather than preferential: closeout is the exhausted end
of a scope, often late at night, driving to an archive. Surprising someone with three
more tasks at the done-moment teaches them to **defer harder next time**, because
deferral is how you protect that moment — so a closeout-time reconciliation would have
*increased* the accumulation it was built to reduce. **Put the signal where energy is
high (session start), never where it is spent.** The session-start counter is
`scripts/todo-stats.py`; this skill is what you run when you choose to.

2.2 **No due dates. Age instead.** A due date on a deliberately deferred item
manufactures urgency it never had; you blow through it correctly, and then every date in
the file is noise — the queue now lying in a second way. An action item against a
knowingly divergent state gets ignored, then muted, then disabled. A number survives
being deliberately ignored.

## 3. The reframe that sets the goal: a high removal rate is SUCCESS

Deferring an item lets someone else's in-flight work solve it — or better, render it
moot by doing something smarter. **Staleness is sometimes the system working.** A sweep
that treats every stale item as a failure measures the wrong thing.

Three of the four buckets are removals. When the first real run archives most of what it
touches, that is the deferral system paying off. `sweep.py status` and the proposal both
say so in words, because a bare "removed 60%" reads as an indictment of the team.

**"Rendered moot, with why" is the most valuable of the four buckets** — it is the only
record anyone will ever have of a design decision that removed the need for work.

## 4. How a run works

The deterministic bookkeeping lives in `scripts/sweep.py`; your job is the judgement.

```
  sweep.py next   ->  you verify against CODE  ->  sweep.py record  ->  (repeat)
       ^                                                  |
       |                                                  v
       +------------- resumable: state is fsync'd --------+
                                                          |
                                             sweep.py report   (proposes)
                                                          |
                                             human reads it, then
                                             sweep.py apply --write
```

4.1 **Resolve the plans dir.** `~/Projects/ai-skills/scripts/resolve-plans-dir.sh`.
From an unrecognised CWD it exits 3 — ask which plans dir rather than guessing.

4.2 **Take a batch.** `sweep.py next <plans-dir> --batch 10 [--priority]`. Emits JSON:
key, section, priority, derived owner, existing stamp, full item text. `--priority`
serves the most severe P first. Default batch is 10 — small enough that a killed session
loses no judgement, since every verdict is written as it is made.

4.3 **Verify each item against the code.** This is the whole skill.
- **Never** accept the TO-DO text as evidence about itself. It is the thing under test.
- Read the file, run the grep, check the commit, look at the running config.
- A "still true" verdict needs proof it is still true — not the absence of proof that it
  is done. Those are different, and the second one is how a wrong premise survives.
- If verifying an item turns out to be its own project, record it `true` with what you
  established and move on. Do not let one item eat the batch.

4.4 **Record the verdict.** One of exactly four buckets:

| Bucket | Meaning | Action on apply |
|---|---|---|
| `done` | someone shipped it | archive **with the SHA that did it** |
| `moot` | a better design removed the need | archive **with why** — the most valuable record |
| `true` | genuinely open | stamp `VERIFIED STILL TRUE <ISO>`, leave in place |
| `reframe` | premise drifted | rewrite the item, stamp it |

```bash
sweep.py record <plans-dir> --key <key> --bucket done \
  --why "one line a future reader can act on" \
  --evidence "internal/db/constants.go:38"   # or a SHA, PR, or stated absence
```

`record` **refuses** a verdict with no evidence, evidence that only cites the TO-DO file,
or evidence that does not look like a file:line / SHA / PR / explicit absence. The
refusal is the point: a sweep that accepts the doc as its own proof reproduces the bug it
exists to find. For `reframe`, pass the replacement text as `--rewrite`.

4.5 **Check progress any time.** `sweep.py status <plans-dir>` — triaged, remaining,
bucket distribution, removal rate, and any recorded verdict whose item no longer matches
(a teammate edited the file mid-sweep; visible, never silently dropped).

4.6 **Propose.** `sweep.py report <plans-dir> [--out FILE]` renders the full proposal and
writes **nothing** to `TO-DO.md`.

4.7 **A human applies.** `sweep.py apply <plans-dir> --date <ISO> --write` stamps the
`true` items in place and **prints the archive moves for a person to make**. Moving
sections between two files is where an unattended agent could destroy a live item, so it
is deliberately not automated. Run without `--write` first for a dry run.

## 5. The rule that makes this trustworthy: propose, never write unattended

An agent silently archiving a live item is the one failure that would end trust in the
whole mechanism, and **trust is the entire deliverable**. So:

- Nothing mutates `TO-DO.md` except `apply --write`, invoked by a human who has read the
  proposal.
- The cost is real and accepted: every run needs a human pass.
- Do not offer to "just apply it" to save the user a step. The step *is* the feature.

## 6. Fan-out is opt-in, never the default

A few hundred items serially is many context windows, and the work is embarrassingly
parallel — but subagent fan-out is the most expensive thing a session can do, and a
subagent reading untrusted content is an injection surface. **Only fan out when the user
asks for it.** When they do, one item per agent, each returning a bucket plus evidence
which the main session records — agents do not write state concurrently.

## 7. Stop conditions

Stop and say so rather than pressing on when:

- **An item's verification needs a decision, not a check.** Record what you established,
  bucket it `true`, surface it. Do not decide policy inside a sweep.
- **The file changed under you.** `status` reports orphaned verdicts. Re-run `next`.
- **You are about to add a field.** Priority, due date, assignee, effort estimate — every
  one of these turns a verifier into a task manager. The failure mode of this skill is
  becoming Jira. If it needs one, stop and re-plan.
- **A bucket does not fit.** Four buckets are deliberate. A fifth means the taxonomy is
  wrong; that is a conversation, not a `--force`.

## 8. Owner derivation is a display, not an assignment

`sweep.py owners <plans-dir>` prints the derived owner distribution. The join is a ranked
chain, because the data is uneven — of 133 sections, 79 carry an explicit `Source:` and
122 carry a scope reference somewhere:

```
  inline `Owner:`  >  `Source: scope N`  >  any scope mention  >  unattributed
        |                    |
        |                    +-- scope N -> PLANS-INDEX `Created by`
        +-- always wins; it is what a human typed
```

Only whole-number 5-column index rows carry `Created by`. Per-plan `{N}.{P}` rows are a
different table shape whose last cell is a Phase description — reading those as creators
yields owners like "Phase 0 — Discovery & Architecture…", which is the bug this note
exists to prevent recurring.

⚠ **Expect the distribution to be uncomfortable.** On kalpa it resolves 67% to one
person. **Reporting the distribution is the deliverable** — it is the input to an
ownership conversation, not the output of one. Assigning humans to repos is an
organisational decision this skill does not make.

## 9. What to write down when a sweep session ends

Append to the progress file of whatever plan or scope you are working under:

- items triaged this session, and the bucket split
- the removal rate, **stated as success** with one line of why
- every `moot` verdict's *why*, in full — that reasoning exists nowhere else
- anything that could not be verified, and what would settle it

`sweep.py status` gives you the counts; the judgement is yours to record.
