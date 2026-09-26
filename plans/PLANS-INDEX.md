# Plans Index — ai-skills

Scopes and plans for the ai-skills project (Alex's custom Claude Code skills).
Row shape is enforced by `scripts/plans-index.py`; see `/markdown-style` §11.7 for the
conventions. Table membership follows disk state — a folder under `archive/` belongs in
Completed, a live folder at `plans/` root belongs in Active.

## Active Plans

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 5 | 📝 Draft (2026-09-26) — scoped, 3 phases (5.1–5.3), each exits on gate A | `5-verify-lever/` | **/verify + the verification lever.** Builds /verify, an independent judge from the opposing model family (codex, fresh context) that does its own work from disk, git and runtime, checks that a scope was built as specified and follows the /plan-eng-review test plan, and reports an evidence rung per check rather than a score. Moves /review onto the same codex voice with recorded dispositions for every finding, and targets local maxima: over-built abstractions and names/contracts/paths assumed instead of looked up (a script resolves them). Wires both into /scope, /plan and /closeout so every commit-producing phase is reviewed and verified, with older scopes self-healing; env specifics and the feature map live in the private product test-suite, which becomes its own kalpa-docs program. | Alex |
| 5.1 | 📝 Draft (2026-09-26) | `5-verify-lever/` | Phase 1 — Contracts + deterministic scripts — finish table, verdict + disposition TSVs, feature-map and adapter contracts, resolve-identifiers.py, verdict-gate.py. Gate A. | Alex |
| 5.2 | 📝 Draft (2026-09-26) | `5-verify-lever/` | Phase 2 — /verify skill + /review on codex — dogfood on 5.1 and a live class-A trial on dev clinic_3. Gate A. | Alex |
| 5.3 | 📝 Draft (2026-09-26) | `5-verify-lever/` | Phase 3 — Wiring into /scope, /plan (self-heal), /closeout; ledger-template fix; team rollout. Gate A. | Alex |

## Completed / Archived

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 1 | ✅ Done (2026-05-11) | `archive/closeout-skills/` | Created /closeout, /closeout-extended and /cross-repo-init, and added the Pattern-First Rule plus closeout-prep ledger writes to /plan. Archived manually — this scope predates the ledger feature it introduced, so it had no closeout-prep.md of its own. v1.1 deferred items live in TO-DO.md. | Alex Knecht |
| 4 | ✅ Done (2026-08-30) | `archive/4-herdr-agent-workflow/` | Codifies Alex's herdr agent workflow across the planning skills. Phase 1 collapses /concurrency's clunky dry-run→--dispatch two-step into one inline flow (evaluate-and-bail if parallelism isn't worth it, single [y/N] to proceed), names workers by lane, and amends scope #3. Phase 2 adds the model-B worktree lifecycle — /scope records primary repo+branch, /plan (in a herdr pane) names its agent 'driver' and creates+binds an isolated worktree, /closeout prunes it — plus a CLAUDE.md rule routing execution-parallelism to visible herdr panes. Leaves seams for a friend's bars/diff tool. | Alex |
| 3 | ✅ Done (2026-09-23) — 6.5 met by 2 weeks of production dogfooding (91, 128, 57.3, 137.2); ledger-less closeout | archive/3-concurrency/ | **/concurrency — herdr-backed multi-agent dispatch.** Partitions a scope into a dependency DAG from repo ground truth, dispatches the ready frontier to named herdr panes (worktree per lane, opus/codex/glm seats, cap 5 per tab), supervises by agent state + gate bus. Residuals → TO-DO.md. | Alex Knecht |
| 2 | ✅ Done (2026-09-25) | `archive/2-skills-relook/` | Re-look at all eight core planning skills through the lens of what the current model does natively. Diagnosis was accretion, not model-era mismatch: 3–18% deletion rate across the core, so superseded text survived beside its replacement. Phase 1 audit classified every numbered section; Phase 2 extracted the three deterministic steps that had lost data (scope-number race, index-row leak, plans-dir duplication); Phase 3 fixed eight defects and wired the scripts in. Also fixed the harness layer: kalpa/ was a container dir so 4 of 6 Kalpa skills never registered and `/review` resolved to gstack's. **Revisited 2026-09-23 → closed 2026-09-25 on Opus 5.5:** built the accretion linter (`scripts/lint-skill.py` — growth-from-git, cross-skill-duplicate, memory-citation checks; size demoted to advisory, no splitting to hit a count), moved the fleet to Opus 5.5, fixed contradictions/dead refs/harness-owned text across the core skills, and replaced eight prose procedures with read-back-verified scripts. Fleet lint 13 ISSUE → 0. Kept separate from scope 5 (verify-lever). | Alex Knecht |
| 6 | ✅ Done (2026-09-26) | `archive/6-research-lanes/` | /research pane mode — one visible Sonnet lane per angle in a fresh herdr tab plus an independent verify lane, now the default; live run and interrupt test passed 2026-09-26. | Alex |
