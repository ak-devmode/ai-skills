# Plans Index — ai-skills

Scopes and plans for the ai-skills project (Alex's custom Claude Code skills).
Row shape is enforced by `scripts/plans-index.py`; see `/markdown-style` §11.7 for the
conventions. Table membership follows disk state — a folder under `archive/` belongs in
Completed, a live folder at `plans/` root belongs in Active.

## Active Plans

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 2 | 🔨 In progress (2026-08-09) | `skills-relook/` | Re-look at all eight core planning skills through the lens of what the current model does natively. Diagnosis was accretion, not model-era mismatch: 3–18% deletion rate across the core, so superseded text survived beside its replacement. Phase 1 audit classified every numbered section; Phase 2 extracted the three deterministic steps that had lost data (scope-number race, index-row leak, plans-dir duplication); Phase 3 fixed eight defects and wired the scripts in. Also fixed the harness layer: kalpa/ was a container dir so 4 of 6 Kalpa skills never registered and `/review` resolved to gstack's. | Alex Knecht |
| 5 | 📝 Brief only — placeholder (2026-09-11); NOT scoped. Run /scope when a window opens (post-birth). | 5-verify-lever/ | **/verify + the verification lever.** Two identical misfires (pmg-web scope 64, kalpa-web scope 128) ported design boards as facsimiles and closed on rung-1 evidence; retro: the instruction was not the gap, a verification loop against the source is. Inspired by poteto's pstack (cursor/plugins). Locked: two classes (behavior feature-map / conformance verdict) as separate artifacts; report the evidence rung 1–5, never a score; unit of rigor = feature; driver+verbs in dev-workbench, feature map in the product repo (kalpa-docs for WellMed); /verify as a new top skill with /review untouched; codex judge, Claude fallback, both fresh; lever built on the second sighting of a gap; phase 0 = fail-loud floor at boundaries + operations/ scripts held by lints. gstack /browse verified as the driver. Port-fidelity is dead as a trial — candidates: staging clinic_3 journey, kalpa wire verbs. | Alex |
| 6 | 🔨 In progress (2026-09-23) — 6.1 Tasks 1.0–1.3 done; 1.4 live run pending on Alex | `6-research-lanes/` | Adds a visible pane mode to /research alongside the existing Workflow mode. Each research angle runs as one Sonnet context in its own herdr pane, in a fresh tab per run, plus a separate verify lane that never saw the sources; the Opus driver synthesizes. Lanes fail by state rather than timeout so an interrupt never hangs the driver. Triggered by a 36-agent, 1.7M-token Workflow run on 2026-09-23 that was invisible while it drifted. | Alex |

## Completed / Archived

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 1 | ✅ Done (2026-05-11) | `archive/closeout-skills/` | Created /closeout, /closeout-extended and /cross-repo-init, and added the Pattern-First Rule plus closeout-prep ledger writes to /plan. Archived manually — this scope predates the ledger feature it introduced, so it had no closeout-prep.md of its own. v1.1 deferred items live in TO-DO.md. | Alex Knecht |
| 4 | ✅ Done (2026-08-30) | `archive/4-herdr-agent-workflow/` | Codifies Alex's herdr agent workflow across the planning skills. Phase 1 collapses /concurrency's clunky dry-run→--dispatch two-step into one inline flow (evaluate-and-bail if parallelism isn't worth it, single [y/N] to proceed), names workers by lane, and amends scope #3. Phase 2 adds the model-B worktree lifecycle — /scope records primary repo+branch, /plan (in a herdr pane) names its agent 'driver' and creates+binds an isolated worktree, /closeout prunes it — plus a CLAUDE.md rule routing execution-parallelism to visible herdr panes. Leaves seams for a friend's bars/diff tool. | Alex |
| 3 | ✅ Done (2026-09-23) — 6.5 met by 2 weeks of production dogfooding (91, 128, 57.3, 137.2); ledger-less closeout | archive/3-concurrency/ | **/concurrency — herdr-backed multi-agent dispatch.** Partitions a scope into a dependency DAG from repo ground truth, dispatches the ready frontier to named herdr panes (worktree per lane, opus/codex/glm seats, cap 5 per tab), supervises by agent state + gate bus. Residuals → TO-DO.md. | Alex Knecht |
