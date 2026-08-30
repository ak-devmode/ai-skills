# Plans Index — ai-skills

Scopes and plans for the ai-skills project (Alex's custom Claude Code skills).
Row shape is enforced by `scripts/plans-index.py`; see `/markdown-style` §11.7 for the
conventions. Table membership follows disk state — a folder under `archive/` belongs in
Completed, a live folder at `plans/` root belongs in Active.

## Active Plans

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 2 | 🔨 In progress (2026-08-09) | `skills-relook/` | Re-look at all eight core planning skills through the lens of what the current model does natively. Diagnosis was accretion, not model-era mismatch: 3–18% deletion rate across the core, so superseded text survived beside its replacement. Phase 1 audit classified every numbered section; Phase 2 extracted the three deterministic steps that had lost data (scope-number race, index-row leak, plans-dir duplication); Phase 3 fixed eight defects and wired the scripts in. Also fixed the harness layer: kalpa/ was a container dir so 4 of 6 Kalpa skills never registered and `/review` resolved to gstack's. | Alex Knecht |
| 3 | 🔨 In progress (2026-08-23) — 6.1–6.4 done same day, landed to main; remaining: 6.5 dogfood proper on wellmed scope 91 | concurrency/ | **/concurrency — herdr-backed multi-agent dispatch.** The controlled home for no-human-in-the-loop agent trains: partitions a scope's plan surface into a dependency DAG (file/service disjointness + emitter-before-consumer + schema-leads-code edges), dispatches the ready frontier to visible named herdr panes — one git worktree + /freeze per partition — and supervises by agent state (agent wait --until blocked/done), never scrollback. Model routing v1: Opus 4.8 primary / codex GPT-5.6 sol secondary+review / GLM 5.2 via per-pane ANTHROPIC_BASE_URL→OpenRouter env override. Rails: dry-run default, refuse-to-parallelize default, pane cap 2, spawned agents never push/PR, JSONL dispatch log. Gate on 6.1: partitioner over wellmed scope 91 must yield the known answer (dispatch 91.2 only; 91.1 human-gated; rest refused). Dogfood = scope 91 after a staleness refresh. | Alex Knecht |

## Completed / Archived

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 1 | ✅ Done (2026-05-11) | `archive/closeout-skills/` | Created /closeout, /closeout-extended and /cross-repo-init, and added the Pattern-First Rule plus closeout-prep ledger writes to /plan. Archived manually — this scope predates the ledger feature it introduced, so it had no closeout-prep.md of its own. v1.1 deferred items live in TO-DO.md. | Alex Knecht |
| 4 | ✅ Done (2026-08-30) | `archive/4-herdr-agent-workflow/` | Codifies Alex's herdr agent workflow across the planning skills. Phase 1 collapses /concurrency's clunky dry-run→--dispatch two-step into one inline flow (evaluate-and-bail if parallelism isn't worth it, single [y/N] to proceed), names workers by lane, and amends scope #3. Phase 2 adds the model-B worktree lifecycle — /scope records primary repo+branch, /plan (in a herdr pane) names its agent 'driver' and creates+binds an isolated worktree, /closeout prunes it — plus a CLAUDE.md rule routing execution-parallelism to visible herdr panes. Leaves seams for a friend's bars/diff tool. | Alex |
