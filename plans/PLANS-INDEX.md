# Plans Index — ai-skills

Scopes and plans for the ai-skills project (Alex's custom Claude Code skills).
Row shape is enforced by `scripts/plans-index.py`; see `/markdown-style` §11.7 for the
conventions. Table membership follows disk state — a folder under `archive/` belongs in
Completed, a live folder at `plans/` root belongs in Active.

## Active Plans

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 2 | 🔨 In progress (2026-08-09) | `skills-relook/` | Re-look at all eight core planning skills through the lens of what the current model does natively. Diagnosis was accretion, not model-era mismatch: 3–18% deletion rate across the core, so superseded text survived beside its replacement. Phase 1 audit classified every numbered section; Phase 2 extracted the three deterministic steps that had lost data (scope-number race, index-row leak, plans-dir duplication); Phase 3 fixed eight defects and wired the scripts in. Also fixed the harness layer: kalpa/ was a container dir so 4 of 6 Kalpa skills never registered and `/review` resolved to gstack's. | Alex Knecht |

## Completed / Archived

| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
| 1 | ✅ Done (2026-05-11) | `archive/closeout-skills/` | Created /closeout, /closeout-extended and /cross-repo-init, and added the Pattern-First Rule plus closeout-prep ledger writes to /plan. Archived manually — this scope predates the ledger feature it introduced, so it had no closeout-prep.md of its own. v1.1 deferred items live in TO-DO.md. | Alex Knecht |
