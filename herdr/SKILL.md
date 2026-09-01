---
name: herdr
version: 0.1.0
description: |
  Alex's herdr WORKFLOW layer — the single source of truth for how we drive
  herdr (terminal workspace manager for AI agents) for agent work: naming, the
  model-B worktree-per-scope lifecycle, worker launch + trust handling, the
  default concurrency pane layout, model routing, and the gotchas. Load it
  whenever a skill is about to create a herdr worktree-workspace, dispatch a
  worker pane, name an agent, or lay out a herd. Referenced by /concurrency
  (dispatch), /plan (driver + worktree create), and /closeout (worktree
  teardown). `herdr --skill` remains the authority on RAW CLI syntax — this
  skill owns WORKFLOW, not a copy of that. Use when the user says "herd this",
  "set up the worktree", "name the agents", "lay out the panes", or when a
  planning skill reaches a herdr step. Do NOT use to control herdr for a
  one-off pane the user is driving by hand.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# herdr — the workflow layer

Loaded BY other skills (/concurrency, /plan, /closeout) and by Alex directly. It
owns the stable, cross-skill herdr rules so they live in ONE place instead of
drifting across the concurrency skill, the `~/.zshrc` launcher, and memory —
which is the drift the concurrency scope kept re-fixing.

**Boundary — don't over-abstract.** Skill-specific logic stays in its skill: the
DAG partitioner and the dispatch gate are `/concurrency`'s; the scope→plan→
closeout sequencing is those skills'. What lives here is *how to drive herdr
correctly* once a skill has decided *what* to do.

**Raw-CLI authority:** run `herdr --skill` and follow it for pane/workspace/
worktree/agent mechanics (split syntax, IDs, `agent wait`, etc.). This file
never duplicates that — it references it.

## 1. Preconditions (check before driving herdr)

- herdr server answers: `herdr workspace list` exits 0. If not, report and stop —
  **never** `brew services start` on Alex's behalf mid-skill.
- Inside a pane: `test "${HERDR_ENV:-}" = 1`. The socket works from outside, but
  pane-context (`$HERDR_PANE_ID`, `$HERDR_WORKSPACE_ID`) is absent and herdr's
  own guidance is to control from within. If outside, say so and ask first.
- `herdr worktree list` only works from a cwd **inside a git work tree** — it
  errors `not_git_worktree` otherwise. Query worktree state per-workspace
  (`herdr workspace get <id>` / `worktree list` from the repo), not globally.

## 2. Naming — one rule, applied everywhere

herdr's agents sidebar shows the **workspace** label as every row's main header
and the pane's **display-agent** as the subheader. A seat name at the workspace
level therefore *lies* about every other seat in that workspace (learned live: a
codex pane displayed `@opus`). So:

- **Workspace** = the run / scope, never a seat (e.g. `57.3 run`).
- **Tab** = Alex's. This skill and `/concurrency` do **NOT** create or name tabs.
  Alex owns tab organization and manual reorg.
- **Pane** = task + seat, set on the PANE:
  `herdr pane rename <pane> "<task> @<seat>"` **plus**
  `herdr pane report-metadata <pane> --source <skill> --display-agent "<task> @<seat>"`
  (without the metadata the sidebar shows the workspace label for every agent).
- **Driver** (a `/plan` session's own agent): `herdr agent rename $HERDR_PANE_ID driver`.
- Auto-name from context when inside a pane via `$HERDR_PANE_ID` / `$HERDR_WORKSPACE_ID`.

## 3. Worktree-per-scope lifecycle (model B)

Isolated git worktree per scope/lane — the default for `/concurrency` (lane
isolation) and opt-in for a solo `/plan`. herdr manages the checkout path under
`~/.herdr/worktrees/<repo>/<branch>`.

- **Create + bind** (the space *is* the worktree-workspace, born that way — do
  NOT create a plain umbrella space and attach a worktree afterward):
  ```
  herdr worktree create --cwd <primary-repo> --base origin/<trunk> \
    --branch <branch> [--label "<name>"] [--no-focus]
  ```
  Trunk: `develop` for wellmed/pmg repos, `main` otherwise.
- The created root pane's cwd is the worktree checkout (not the umbrella) — that
  isolation is the point. Branch + commit status then render in the sidebar
  (repo-bound spaces only; a plain space on a non-repo umbrella dir stays blank).
- **Teardown** (on `/closeout`, after merge):
  `herdr worktree remove --workspace <id>`, then
  `git -C <repo> branch -D <branch>` and `git -C <repo> worktree prune`.
  Never leave a dangling worktree or branch (same discipline as no orphaned WIP).

## 4. Worker launch + trust (autonomous dispatch)

A freshly-created worktree is an unfamiliar directory, so Claude Code shows its
"Is this a project you trust?" dialog on startup and **blocks**. The supervisor
must **NOT** answer it via `send-keys` — you never answer another agent's
permission prompt (the auto-mode classifier blocks it, correctly). Fix it at
**launch**, not with keystrokes:

- **Dispatched workers launch `claude --dangerously-skip-permissions`** — skips
  the trust dialog *and* per-tool prompts, so the worker is non-interactive from
  the first token. **WORKERS ONLY, never the driver.**
- Safe here *specifically* because each worker is sandboxed: isolated worktree,
  `/freeze`d file scope, never pushes/PRs/merges. That is the "no human in the
  loop" threat model; bypass mode matches it. Do not use it for the driver or
  any session working a shared/primary tree.
- **Narrower alternative** (if a worker must still honor tool prompts): pre-trust
  the checkout by setting `hasTrustDialogAccepted: true` on the worktree's entry
  in `~/.claude.json` (`projects["<worktree-path>"]`) *before* launch — trust
  does not inherit from a parent dir. It then still needs a permissive allowlist
  or it stalls on tool prompts instead, so bypass is preferred for trains.

## 5. Default concurrency pane layout

Alex, 2026-08-30 (replaces the old tab-per-scope rule). **NO tabs** — Alex owns
tabs. Since 2026-09-01 his `herdr-new-space` helper (dev-workbench, bound to
prefix+shift+n) pre-builds every manually-created space with tab "work" (this
exact seed layout, driver pane already named `driver`) + tab "shell". Skills
still never create/name tabs — but on dispatch, **check for and REUSE the
seeded standby panes** in the "work" tab before splitting new ones.

```
+-------------+------+------+---
|             |  w1  |  w3  |
|   driver    +------+------+ ...
|  (full ht)  |  w2  |  w4  |
+-------------+------+------+---
    LEFT           workers grow rightward →
```

- Driver in a **full-height LEFT pane**.
- Workers = **half-height panes on the RIGHT**, seeded with 2 placeholders
  (top-right + bottom-right).
- Each further worker adds a half-height pane growing **rightward** (new right
  column, top then bottom half), until Alex manually reorganizes.
- Build it with pane split/move (exact split syntax: `herdr --skill`): first
  worker splits the driver **right**; the second splits that pane **down** (half
  height); later workers add columns to the right, each split **down** into two.
  `--no-focus` on every split so the driver keeps focus. A helper pane a worker
  opens splits its OWN pane **right** at half size — never the herd layout, never
  a new workspace or tab.

## 6. Model routing table

THE single source of routing truth (verified on this machine 2026-08-23). New
seats are new rows.

| Seat | Launch inside pane | Route to it |
|------|-------------------|-------------|
| `opus` | `claude` (global default: Opus 4.8) | judgment, design-adjacent implementation, prod-shaped decisions |
| `codex` | `codex -m gpt-5.6-sol` (headless: `codex exec -m gpt-5.6-sol`) | secondary implementation, independent review passes |
| `glm` | `ANTHROPIC_BASE_URL=https://openrouter.ai/api ANTHROPIC_AUTH_TOKEN=$(security find-generic-password -s openrouter-api-key -w) ANTHROPIC_SMALL_FAST_MODEL=z-ai/glm-5-turbo claude --model z-ai/glm-5.2` | mechanical/bulk: migrations-by-pattern, test scaffolds, sweeps |

Dispatched claude/glm workers append `--dangerously-skip-permissions` (§4).

**Env-leak rule:** provider overrides live ONLY in the seat's launch command,
inline. Secrets resolve from Keychain at spawn — never via herdr `--env`
(persists literals in session state), never `export`ed in the invoking session,
never written to a settings file. A provider swap edits this table's one row.

**GLM launch traps:** base URL is `.../api` NOT `/api/v1` (the SDK appends
`/v1/messages`); bearer only (`ANTHROPIC_AUTH_TOKEN` — setting `ANTHROPIC_API_KEY`
triggers a blocking dialog); "model not found" on a 200-tested key = plumbing,
curl both endpoint styles before touching account settings.

## 7. Gotchas

- **`pane read --source recent` returns empty with no UI client attached** — use
  `--source visible` or `--source detection`. Headless dispatch runs in exactly
  this mode; `recent` is a trap.
- **Green pane prose** = Claude Code text (which carries no color codes) rendering
  in the host window's default foreground (Homebrew green). herdr has NO config
  knob for pane fg — it only *forwards* the host's. Fix: `_herdr_attach` in
  `~/.zshrc` emits OSC 10 `#d8d8d8` on the host Ghostty window before `herdr`
  attaches, so forwarded pane fg is neutral. (Supersedes the removed `herd()`
  alias.) TERM/terminfo makes no difference to content color.
- **Pane content colors are NOT herdr theme tokens** — `theme.custom.*` paints
  chrome (sidebar/borders/status) only. Content color = host-fg / terminfo.
- **herdr is a brew service** (`homebrew.mxcl.herdr`) — survives logout; attach
  by typing `herdr`. Never restart it mid-skill on Alex's behalf.

## 8. Supervision primitives (for reference; owned by the dispatching skill)

- PRIMARY wait is the skill's own done-marker, not a herdr state:
  `herdr agent wait <pane> --until done|blocked`, `herdr notification show`.
- `pane.report_agent` states: `idle | working | blocked | done | unknown`.
  `unknown` is not proof of completion; `blocked` = an approval/question UI.
