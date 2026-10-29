# Key files (CLAUDE.md §4)

> Moved verbatim from `CLAUDE.md` on 2026-10-29 to keep CLAUDE.md under the 40k load limit. Section numbers are unchanged, so `CLAUDE.md §N` references land on the stub there, which points here.

## 4. Key files

```
prd/SKILL.md                    — PRD generator
scope/SKILL.md                  — task scoping + skill router (judgment + gates only)
scope/references/               — conventions + postmortems, loaded on demand
scope/templates/                — scope.md / progress.md / plan-stub / skill-checklist
plan/SKILL.md                   — task execution engine (Phase 0 + Pattern-First Rule)
plan/tests/verification-recipes.md  — manual test recipes for /plan rules
closeout/SKILL.md               — local self-heal
closeout-extended/SKILL.md      — cross-repo recursive self-heal
closeout-extended/tests/upward-traversal-recipe.md
cross-repo-init/SKILL.md        — trio bootstrap + maintenance (invoked by /closeout Step 8)
cross-repo-init/templates/      — CROSS-REPO / ARCHITECTURE / CLAUDE templates + examples
markdown-style/SKILL.md         — markdown formatting rules
review/SKILL.md                 — pre-landing review: lean by default (one Sonnet pass over a packed bundle); full = codex gate, Claude (gstack engine) fallback
review/rules/                   — domain.md (Kalpa/PMG groups) + lenses.md (§7: scaffolding never blocks), read by every executor
review/prompts/                 — review.md (codex/full) + review-lean.md (the lean bundle's head)
review/scripts/review.py        — review prompt / findings log (stable IDs) / dispositions
verify/SKILL.md                 — independent verification: runner + judge (lean Sonnet, or codex in full mode) + gate; fix loop capped at 2 runs
verify/scripts/judge.py         — judge prompt render (--lean bundle) / answer record (+ retry prompt) / report (every executor)
verify/scripts/demo.py          — `/verify --demo`; also the eval (`VERIFY_EVAL=1` runs it from the suite)
verify/tests/fixtures/notes/    — the planted-defect fixture (6 defects, clean control, repaired copies)
templates/verify-contracts.md   — verification contracts: finish table, verdict log, gate, dispositions
kalpa-*/SKILL.md                — WellMed/Kalpa project skills (flat, namespaced — §3.8)
member-record-amend/SKILL.md    — PMG Padma Care record-edit skill
templates/closeout-prep.md.template   — ledger schema (shared by /plan + /closeout); starts empty
templates/examples/             — filled examples of every template (never copied into output)
scripts/README.md               — contracts + exit codes for the shared scripts
scripts/resolve-plans-dir.sh    — plans-dir resolution (one owner, 5 callers)
scripts/claim-scope-number.sh   — scope numbering, race-defensive across 4 sources
scripts/plans-publish.sh        — commit named plans paths; on a shared trunk rebase, push, read back (/plan §8.5b)
scripts/ff-local-trunk.sh       — fast-forward the local trunk after a worktree merges (closeout §13.6)
scripts/plans-index.py          — plans index: add/status/move write per-scope records; render/migrate/check
scripts/todo-stats.py           — TO-DO.md counts for the SessionStart hook (counts only)
scripts/plans-folder.sh         — plan/scope folder create + related-file sweep (no clobber)
scripts/context-gather.sh       — /scope + /prd Step-0 context (greps the index, skips CLAUDE.md)
scripts/stamp-executed-by.sh    — /plan §3.1 `Executed by` stamp from git config
scripts/repo-graph-check.py     — /plan §5.6.1 Repo Graph freshness gate (exit-coded)
scripts/ledger-init.sh          — /plan §5.13 closeout-prep.md bootstrap / phase header
scripts/dispatch-log.py         — /concurrency JSONL dispatch log, read-back verified
scripts/placement.py            — /concurrency §5.1 facts: headroom per machine × account × seat, box base check, fetch-back
scripts/herdr-pane.sh           — herdr pane identity (rename + metadata) + helper split
scripts/repo-survey.sh          — /cross-repo-init default/survey branch + MERGED/SQUASHED/LIVE
scripts/lint-skill.py           — accretion linter for SKILL.md (dup-number/frontmatter/stale-name fail; growth/duplicate/size advise)
scripts/resolve-identifiers.py  — invented-reality check: env (incl. shell `$NAME`)/SSM/proto/route refs vs declarations
scripts/verify-run.py           — verification runner; sole writer of the verdict log
scripts/verdict-gate.py         — may this unit be marked Done? (plans-index.py status/validate call it)
scripts/codex-exec.py           — codex headless probe + exec; honest `none <reason>` judge lines
scripts/verify_lib.py           — shared table parser, §10 messages, verified JSONL append, levers()
scripts/finish-table.py         — finish-conditions.md writer: standard rows per phase, Revision + Changelog
scripts/lever-candidates.py     — /closeout: lever candidates → TO-DO.md, second sighting = another scope
scripts/verify-prereqs.sh       — setup.sh step 4: Python + codex checks, warns, always exit 0
scripts/clone-behind.py         — one line when this clone is behind origin/main (/verify, /plan)
scripts/review-mode.py          — /review + /verify mode: flag > AI_SKILLS_REVIEW_MODE > default lean
scripts/harness-scorecard/      — harness scorecard: `pull` homelab logs (MBA only), `run` the baseline tables + Δ, effort trial on a fixed follow-up
scripts/tests/                  — stdlib unittest suite for the scripts (CLAUDE.md §6 Test:)
plans/PLANS-INDEX.md            — local plans tracking ai-skills development
plans/<scope>/                  — active scope folders
plans/archive/                  — completed scopes
plans/TO-DO.md                  — accumulated TODOs (v1.1 items, etc.)
CROSS-REPO.md                   — this trio
ARCHITECTURE.md
CLAUDE.md
```

---

