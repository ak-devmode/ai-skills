# Herdr Agent Workflow — one-flow dispatch, agent naming, worktree lifecycle
**Project:** ai-skills  **Branch:** `main` (solo repo — direct commits per CROSS-REPO.md)  **Date:** 2026-08-30
**Created by:** Alex
**Scope folder:** `~/Projects/ai-skills/plans/4-herdr-agent-workflow/`
**Source repo(s):** `~/Projects/ai-skills` (skills + global CLAUDE.md)

## Context
Alex is standardizing herdr (terminal workspace manager for AI agents) as the home for `/concurrency` agent trains. Three frictions surfaced while dogfooding: `/concurrency`'s dry-run→`--dispatch` two-step is clunky to enter (used twice, clunky both times); agents render as bare `claude` instead of meaningful names; and scope spaces show no branch/commit status because they're rooted at umbrella dirs, not repos. This scope codifies the fixes across the planning skills so the workflow is the default, not hand-cranked each time. Full background: memory `project_herdr_workflow`.

## Repo Graph
Single-repo task — ai-skills is a "leaf in its own standalone graph" (per its CROSS-REPO.md): a personal Claude Code skills repo, no contract consumers to walk. No cross-repo cascade.

## ADR Alignment
No ADR matches — ai-skills has no ADRs.

## Phases

### Phase 1 — `/concurrency` one-flow + worker naming + amend scope #3
Collapse the dispatch ceremony and fix naming, in the skill that owns them.
- Replace dry-run-default + `--dispatch`-to-execute with a **single flow**: `/concurrency` (a) evaluates parallelism potential and, if the work is basically sequential, **recommends plain `/plan` and bails**; (b) if worthwhile, shows the dispatch plan (lanes · seats · worktrees · freeze paths); (c) asks **once, inline** (`proceed? [y/N]`) and dispatches. Remove the `--dispatch` flag and the re-invocation.
- Keep the **refuse-to-parallelize** default and the pane cap — the veto stays, only the ceremony goes. Consistent with CLAUDE.md: invoking a skill with `Agent` in allowed-tools *is* requesting dispatch.
- **Worker naming:** each dispatched pane's agent named by lane/task (e.g. `57.2 family-id-writeback`) via `herdr agent rename`/`--display-agent`, not left as bare `claude`.
- **Amend scope #3** (`concurrency/`): update its scope.md/progress to record that the `--dispatch` gate is superseded by the inline flow, and that tonight's `_herdr_attach` (OSC 10 on the host Ghostty window) supersedes its old `herd`-alias green-prose fix (that alias was the buggy wrapper, since removed).
- **Gate A (human):** dogfood the new flow on one real dispatch — Alex confirms entering concurrency is now clean before Phase 2 builds on it.

### Phase 2 — Worktree lifecycle + driver naming + CLAUDE.md rule
The cross-skill lifecycle (model B: isolated git worktrees), spanning `/scope` → `/plan` → `/closeout`.
- **`/scope`:** record the scope's **primary repo + intended branch** (new scope.md field), so `/plan` knows what to create.
- **`/plan`:** on invocation inside a herdr pane (`$HERDR_PANE_ID` set), (a) auto-name its own agent **`driver`**; (b) create+bind an isolated worktree — `herdr worktree create --cwd <primary-repo> --branch <b> --base <trunk>` — where the scope's space **is** the worktree-workspace. **Required** when `/concurrency` will run (lane isolation); **optional** for a solo single-driver `/plan`.
- **`/closeout`:** on scope completion, `herdr worktree remove` + prune the branch. (`/repo-cleanup` already does `git worktree prune`.)
- **CLAUDE.md rule:** route **execution** parallelism to visible herdr panes via `/concurrency`; keep in-process subagents for **read-only fan-out** only.
- **Leave clean seams** where the friend's tooling (colored bars + diff) will later attach — but **build the lifecycle now**. The bells/whistles bake in as a follow-up, **not a blocker**.
- **Gate C (review/merge)** — lands as one workflow change; no external wait.

## What Already Exists
- **Scope #3 `concurrency/`** — owns the `/concurrency` machinery: worktree-per-partition (native `herdr worktree`), the `--dispatch` gate (being simplified here), model routing (Opus/codex/GLM), JSONL dispatch log, refuse-to-parallelize + pane-cap rails. Phase 1 **amends** it, not rebuilds.
- **Tonight's herdr config** (done, not part of this scope): `~/.config/herdr/config.toml` theming; `_herdr_attach` in `~/.zshrc`; `jordanhawkes/herdr-metrics` quota plugin; explicit `ui.sidebar.spaces.rows` for branch/commits.
- **`herdr worktree create/open`** proven this session (probe created `wR`, isolated linked worktree, torn down).

## NOT in Scope
- Colored usage bars, a `model` sidebar token, and space-level limit reporting — deferred to the friend's tool or a fork of `jordanhawkes/herdr-metrics` (pane-only, 3 tokens today).
- herdr theming / neutral-pane-fg / quota-panel install — already done tonight outside this scope.
- The `razajamil/herdr-plugin-workspace-manager` tab/pane templating — a candidate for a later scope once the worktree lifecycle lands.

## Skill Sequence
- **Plan Reviews:** `/plan-ceo-review` **YES** (always — catches "should `/concurrency` even work this way?"); `/plan-devex-review` **YES** (this scope *is* developer-experience — the whole point is reducing clunk); `/plan-eng-review` OPTIONAL (skill-logic soundness of the worktree lifecycle); `/plan-design-review` N/A (no UI). Or run `/autoplan` for the combined pass.
- **Implementation Support:** `/investigate` N/A (not a bug); `/document-generate` N/A; browser/design cluster N/A x6 (no UI surface).
- **Review & QA:** `/review` OPTIONAL (skill-md diff); `/qa` N/A; `/browse` N/A.
- **Ship & Post-ship:** `/ship` **N/A** (not in use — promotion is direct-to-main here); `/document-release` OPTIONAL; `/closeout` **YES**; `/retro` OPTIONAL.

## Key Decisions Captured
- **Kill the `--dispatch` two-step** — one inline flow, evaluate-and-bail if concurrency isn't worth it, single `[y/N]`. The dry-run protocol was clunky both times Alex used it.
- **Worktrees required for `/concurrency`, optional on `/plan`** — solo drivers aren't forced into isolation.
- **Agent naming:** `/plan`'s agent → `driver`; `/concurrency` workers → lane/task names.
- **`_herdr_attach` supersedes scope #3's `herd`-alias** green-prose fix — record, don't run both.
- **One new scope** owns this; it **amends** scope #3 in two spots rather than reopening it as the home.
- **Friend's bars/diff tool** lands tonight — leave seams, don't pre-build what it (or a fork) will provide.
