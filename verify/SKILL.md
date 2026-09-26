---
name: verify
version: 0.1.0
description: |
  Independent verification of a unit of scoped work. A deterministic runner executes
  every finish-condition row the unit owns and records evidence; a judge from the
  opposing model family (codex, headless, fresh context, read-only) reads that evidence
  plus git and decides — one-way: it can confirm or downgrade a runner result, never
  upgrade one. Reports the evidence rung per check, never a score, then runs the
  verdict gate that decides whether the unit may be marked Done.

  Use when asked to "verify", "/verify", "verify this phase", "verify plan 5.1",
  "check this was built as scoped", "run the finish conditions", or at a /plan
  checkpoint and at /closeout. Never asks the author for data: disk, git and the
  running app only.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# /verify — Independent Verification

## 1. Why This Skill Exists

Two scopes closed on "it said so" while shortcutting what the scope asked for, and the
retro found the instruction was never the gap — an independent loop was. So: a script
runs the checks (it cannot be talked out of a red result), and a judge that did not
write the work reads the evidence. The contracts are in `templates/verify-contracts.md`;
this skill is the procedure. Every step with one right answer is a script call below —
do not re-implement one in prose.

1.1 **The judge never receives narrative.** It gets the prompt `judge.py prepare`
renders from disk — finish table, the run's records, the revision range. Never paste
what the session did, why, or what it believes. That is the one property that makes
the verdict worth having (same rule as `/ready-to-clear` §1.1).

1.2 **Never ask the author for data.** If a fact is not on disk, in git, or observable
in the running app, the check is `inconclusive` and becomes a lever candidate.

1.3 **Report the rung, never a score.** 1 said so · 2 pointed at the line · 3 showed the
bad case can't happen · 4 ran a script that fails loud · 5 reproduced in the running app.

---

## 2. Inputs

2.1 **Unit** — a plan number (`5.1`). The scope folder holds `finish-conditions.md`,
`closeout-prep.md` (base SHAs) and `artifacts/`. Resolve the plans dir with
`~/Projects/ai-skills/scripts/resolve-plans-dir.sh`; the scope folder is
`<plans>/<N>-<slug>/`.

2.2 **No `finish-conditions.md`** — stop. Report that the scope predates the gate and
that `/plan` drafts a table for Alex to confirm once. Do not invent rows here.

2.3 **Revision range** — per repo, `base..HEAD`, base from the ledger
(`ledger-init.sh --repo`). An older phase with no recorded base: pass
`--range REPO=BASE..HEAD` explicitly and say where the base came from. **An empty range
is a failure**, never a clean pass — on a direct-to-main repo a branch diff is empty by
construction, which is why the range is explicit.

Set once for the steps below:

```bash
S=~/Projects/ai-skills/scripts; V=~/Projects/ai-skills/verify/scripts
SCOPE=<scope folder>; UNIT=<N.P>
TABLE=$SCOPE/finish-conditions.md; LOG=$SCOPE/artifacts/verify-$UNIT.jsonl
```

---

## 3. Procedure

3.1 **Run the checks.** `$S/verify-run.py run --table $TABLE --log $LOG --owner $UNIT`
— note the `run_id:` it prints. A non-zero exit here is information, not a stop: the
failed rows are recorded as evidence. Exit 3 (malformed table) or a class-A placement
refusal *is* a stop — report it with its message.

3.2 **Render the judge prompt.** `$V/judge.py prepare --scope $SCOPE --unit $UNIT
--run-id $RUN [--range …]` → prints `prompt:` and `schema:` paths; the prompt's directory
is the scratch `$WORK` for this run (`OUT=$WORK/answer-$RUN.json`). Exit 3 (no range,
empty range) is a stop.

3.3 **Probe codex — fresh, every call.** `$S/codex-exec.py probe`. The last stdout line
is the judge line: `codex <model>` means proceed with §3.4; `none <reason>` means §3.5.
Never reuse an earlier probe result, and never use gstack's probe (it caches failures).

3.4 **codex judges.**
```bash
$S/codex-exec.py exec --prompt $PROMPT --schema $SCHEMA --out $OUT --cd $SCOPE --timeout 600
```
Bash tool timeout above 600 s. Last stdout line `codex <model>` → record with that exact
line (§3.6). `none <reason>` → §3.5 with that reason.

3.5 **Fallback: a fresh Claude subagent.** Dispatch is pre-authorized — this skill
declares `Agent`. Spawn one subagent whose entire prompt is: "Read `<PROMPT>` and follow
it exactly. Write only the JSON object it asks for, matching `<SCHEMA>`, to `<OUT>`. Do
not modify any other file." Nothing else — no narrative. Its judge line is
`claude-fallback <the reason codex could not judge>`. If the subagent cannot be spawned
or writes nothing usable, the judge line is `none <reason>`: skip §3.6 and finalize with
`--judge 'none <reason>'`. A fallback or `none` judge is not a failure of this skill; it
is recorded, and the index shows `⚠ judge:` until a codex verdict clears it.

3.6 **Record the verdict.** `$V/judge.py record --scope $SCOPE --unit $UNIT --run-id $RUN
--judge "<judge line>" --input <OUT>`. Exit 3 (malformed answer — a check missing, an
unknown lens) → nothing is recorded; finalize with `--judge 'none malformed judge output'`.

3.7 **Finalize.** `$S/verify-run.py finalize --log $LOG --run-id $RUN` (add
`--judge 'none <reason>'` when §3.6 did not record). This applies the authority rule and
writes the one `final` line.

3.8 **Gate and report.** `$V/judge.py report --scope $SCOPE --unit $UNIT --run-id $RUN`
writes `artifacts/verify-$UNIT-report.md` and prints the gate verdict. Advisory mode is
the default until three scopes pass cleanly: blocks are reported, the unit is not held.

---

## 4. Standard Rows

These make the lenses checkable. `/scope` emits them into a finish table; `/plan`'s
self-heal adds them to a drafted one. Owner = the unit.

| check_id | check | rung | when |
|---|---|---|---|
| `names-resolve` | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | 4 | every unit that commits code |
| `scope-deliverables` | `judge` | 2 | always |
| `no-overbuild` | `judge` | 2 | every unit that commits code |
| `test-plan-followed` | `judge` | 2 | a `/plan-eng-review` test plan exists |
| `rejections-justified` | `judge` | 2 | `/review` ran on the unit |
| `faithful-port` | a source-vs-destination diff command, or `judge` | 4 / 2 | the scope ports or follows a source artifact |

`$VERIFY_BASE` is exported by the runner from the ledger's base for that row's repo.
Disposition *coverage* (every finding dispositioned) is the gate's job, not a row.

**Faithful-port rule.** Where a scope says to port or follow a source: read the source →
produce → read the result back *from the destination* → diff per unit → done only on an
empty diff or differences all on a pre-approved exceptions list. A port verified any
other way is at most rung 1, whatever it claims.

---

## 5. Reporting

5.1 Lead with the gate verdict and the judge line, then one line per check: result,
rung reached / required, reason. Then findings, highest severity first, each naming its
check. Then lever candidates — recorded, not built; a lever is built on the second
sighting from a different scope or run.

5.2 **Never soften a block.** An `inconclusive` is not "probably fine". A fallback judge
is stated as a fallback, in the first line.

5.3 **Public repos hold class-B verdicts on their own content only.** Class-A evidence
stays in the product's private scope folder; the runner enforces this and a refusal is
reported, never worked around.
