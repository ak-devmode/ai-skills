# /review — ai-skills @ `3e1517e3acae01d20dc8b23a6467a6145bf191fc..55da072eece0f4e1f4bad1284aed96dd66d646a2` (3 commits)

**Review:** `10.2-r2` · **Reviewer:** claude-fallback codex out of credits (operator) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (operator)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (operator)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 1 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.2 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (0)


## SHOULD FIX (0)


## NOTE (1)

- **10.2-r2-01** `scripts/verify_lib.py:499` (engine) — The lineage rule is now picked by the child review's own `rules_version` stamp (`rid not in stamped`). Decision 65 versions rules by lineage root (`lineage_rules` reads the root), and the r1-02 commit message says the same. Every new record is stamped with RULES_VERSION, so an in-flight pre-cutover lineage switches to the fix-sha rule on its first review recorded after merge. Example: r1 and r2 are unstamped, r2 has no `fixed` disposition in r3's range, and r3 starts at r2's head. r3 then restarts at round 1 where the old rule gave round 3 and the round-3 STOP. No existing log is affected: no review record under ~/Projects carries rules_version 2 yet, so the 194.1 back-compat holds. Separately, the base==phead git-unsure path now continues prid silently, while the docstring still says git-unsure reviews warn on stderr. → Key the old/new linking choice on the parent lineage's root stamp. `out[prid][0]` is known at that point, so the rule is root-scoped like `lineage_rules`. Or state in the docstring that the child's stamp decides and the transition is accepted. Add the stderr warning on the held-is-None path, or drop the claim.

## Checked and clear

10.2-r1-01 resolved: `vl.judge_took` requires a reframe in the finding's lineage whose `removes` names it, with the latest verdict `accepted` and no `overturns`. dispose (reframe_check) and the gate (review_presence_blocks) both call it, and the gate blocks a hand-written `--by judge`. `--by user` is recorded with `call: user` and printed as the user's call. Fails closed on an unknown lineage. `overturns` is a str, so the join is safe., 10.2-r1-02 resolved for existing logs: unstamped child reviews keep the old base==phead continuation without git. There are no stamped records in the wild (grep of ~/Projects review logs), so closed units such as 194.1 keep their stops. git-unsure on base==phead now continues prid instead of the repo's highest round, which closes the 149.2 inflation., 10.2-r1-03 resolved: `record --effort` (choices EFFORT_LEVELS) stamps the tier codex ran at. A codex record without it gets `effort: null` plus a WARN, and a mismatch with the lineage's tier is printed. SKILL.md §2.4 now passes --effort, and no other skill calls record with a codex reviewer., All three lineage_links callers (review.py rounds, verdict-gate) unpack the new 3-tuple via `*`., dispose print: `fix` is always a dict (`fix.get('sha')` predates the range), so `fix.get('call')` cannot raise., Test suite: python3 -m unittest discover -s scripts/tests ran 346 tests, OK (2 skipped). It includes the judge_took, gate-block and 194.1-shape regressions.

## Not applicable

domain checks (generic repo)

**Verdict:** SHIP

## What this review did not cover

- codex gate: codex out of credits (operator brief); Claude fallback pass
- gstack engine not loaded in full and specialist fan-out not dispatched: a single-context pass over a 5-file, 285-line fix range
- the 300-log old-vs-new gate sweep was not re-run; reliance on the fix writer's report plus the grep showing no stamped records
