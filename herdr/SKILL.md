---
name: herdr
version: 0.3.0
description: |
  Alex's herdr WORKFLOW layer — the single source of truth for how we drive
  herdr (terminal workspace manager for AI agents) for agent work: naming, the
  model-B worktree-per-scope lifecycle, worker launch + trust handling, the
  default concurrency pane layout, model + account routing, driving the second
  machine (homelab2026) through the two-server view, and the gotchas. Load it
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
  Alex owns tab organization and manual reorg. **One exception:** a `/research`
  pane-mode run opens its own tab (`research <slug> r<k>`, a fresh one per run)
  in the caller's workspace and never closes it; Alex closes it by hand.
- **Pane** = task + seat, set on the PANE:
  `herdr pane rename <pane> "<task> @<seat>"` **plus**
  `herdr pane report-metadata <pane> --source <skill> --display-agent "<task> @<seat>"`
  (without the metadata the sidebar shows the workspace label for every agent).
  Both in one call, read back: `~/Projects/ai-skills/scripts/herdr-pane.sh name <pane> <task> <seat> --source <skill>`.
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
  `git -C <repo> branch -D <branch>` and `git -C <repo> worktree prune`, then
  `~/Projects/ai-skills/scripts/ff-local-trunk.sh <repo>` so the primary checkout's
  trunk carries the merge (fast-forward only; exits 2/3/4 are reported, never forced).
  Never leave a dangling worktree or branch (same discipline as no orphaned WIP).

## 4. Worker launch + trust (autonomous dispatch)

A freshly-created worktree is an unfamiliar directory, so Claude Code shows its
"Is this a project you trust?" dialog on startup and **blocks**. The supervisor
must **NOT** answer it via `send-keys` — you never answer another agent's
permission prompt (the auto-mode classifier blocks it, correctly). Fix it at
**launch**, not with keystrokes:

- **Dispatched workers launch `claude --dangerously-skip-permissions`** — skips
  per-tool prompts, so the worker is non-interactive from the first token.
  🔴 CORRECTION 2026-09-23: it does **not** skip the folder-trust dialog. Under
  Claude Code 2.1.280 a lane launched in an untrusted scratch folder blocked on
  it. Worktree checkouts under `~/.herdr/worktrees/` were all already trusted
  (7/7), so `/concurrency` has not hit it; a new untrusted cwd will. Start
  agents in a pre-trusted folder, as `/research` does with `~/.cache/research-lanes`. **WORKERS ONLY, never the driver.**
  🔴 **Parent trust did not cover a plain `git worktree add` sibling (hit live
  2026-09-29, WellMed 149.2).** `~/Projects/wellmed` was trusted, yet a lane in
  `~/Projects/wellmed/wellmed-cashier.worktrees/fix-…` blocked on the dialog. Before
  launch, pre-trust every worker cwd outside `~/.herdr/worktrees/` (the narrower
  alternative below: load, set, atomic replace, read back) and remove those entries at
  teardown. A worker already at the dialog: `agent send-keys <name> esc` cancels it
  (exits, grants nothing), then pre-trust and re-`agent start` in the same pane. On the
  box the pre-trust edit was refused to an agent session — §6.1.
- Safe here *specifically* because each worker is sandboxed: isolated worktree,
  disjoint touch-set, never pushes/PRs/merges (not `/freeze` — its state is one
  global file; `/concurrency` §10). That is the "no human in the
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
  opens splits its OWN pane **right** at half size (`~/Projects/ai-skills/scripts/herdr-pane.sh helper`)
  — never the herd layout, never a new workspace or tab.

## 6. Model routing table

THE single source of routing truth (verified on this machine 2026-08-23; opus seat re-verified 2026-09-25). New
seats are new rows.

| Seat | Launch inside pane | Route to it |
|------|-------------------|-------------|
| `opus` | worker: `CLAUDE_CODE_DISABLE_1M_CONTEXT=1 claude --model opus` (Opus 5.5, 200k). Driver only: bare `claude` (`opus[1m]`) | judgment, design-adjacent implementation, prod-shaped decisions |
| `sonnet` | `CLAUDE_CODE_DISABLE_1M_CONTEXT=1 claude --model sonnet` (Sonnet 5.5, 200k) | **default for mechanical lanes**: apply a known pattern across a module, sweeps, test scaffolds, migrations-by-pattern |
| `codex` | `codex -m gpt-5.6-sol` (headless: `codex exec -m gpt-5.6-sol`) | secondary implementation, independent review passes; bills OpenAI, not Claude limits |
| `glm` | `ANTHROPIC_BASE_URL=https://openrouter.ai/api ANTHROPIC_AUTH_TOKEN=$(security find-generic-password -s openrouter-api-key -w) ANTHROPIC_SMALL_FAST_MODEL=z-ai/glm-5-turbo claude --model z-ai/glm-5.2` | mechanical/bulk when both Claude accounts are low on headroom (bills OpenRouter) |

Dispatched claude/glm workers append `--dangerously-skip-permissions` (§4). The token rules
in §6.2 apply to every worker.

**Account-aware launch.** Two accounts per seat — `alex` (alex@work) and `int`
(integrations) — on both machines (dev-workbench `config/accounts/accounts.tsv`). A
worker for a placed lane launches through the account launcher instead of the bare
CLI: `claude-<account>` for `opus`, `codex-<account> -m gpt-5.6-sol` for `codex`
(e.g. `claude-int --dangerously-skip-permissions`). The launchers exist on both
machines and work from non-interactive shells; the machine's default account runs with
its real dirs, the other with its own login and shared config. `glm` bills OpenRouter,
not an account, so it keeps its row unchanged. Which account and machine a lane gets is
`/concurrency` §5.1's call (`scripts/placement.py`); this table only says how to start it.

### 6.1 Two machines — the two-server view (herdr 0.9)

homelab2026 is a saved herdr machine (`herdr machine list`); its spaces show in the
MBA's sidebar beside the local ones. Driving it from the MBA:

- **Every command for a box pane carries `herdr --machine homelab2026 …`**, discovery
  and every later call alike. Without it the command hits the local server, even while
  the TUI has the box selected. Never combine it with `--session` / `--remote`.
- **Ids are per server.** The box has its own `w1:p1` and its own agent names: read
  them from that server's JSON, never reuse a local id, and never `--current`.
- **Worktrees on the box:** `herdr --machine homelab2026 worktree create --cwd
  ~/Projects/<repo> --base <base> --branch <b> --no-focus` — `<base>` is the commit
  `placement.py check-base` passed, named so the box can resolve it: `origin/<trunk>`
  for a fresh lane, the pushed `origin/<branch>` or a SHA on origin when the lane needs
  more; remote paths must be `~/`-relative or absolute. Fetch the box's clone first, quoted so `~` expands on
  the box (`ssh homelab2026 'git -C ~/Projects/<repo> fetch -q origin'`); it never sees a
  commit that is not on origin.
- **Trust on the box (one observation, 2026-10-03, dev-workbench):** the first herdr
  worktree lane stopped at Claude Code's folder-trust dialog, and pre-trusting through
  the box's `~/.claude.json` (§4) was refused to the agent session as self-modification,
  so Alex answered it in the pane. A second herdr worktree of the same repo then opened
  with no dialog. Assume one approval per repo only for herdr-created worktrees; expect
  the dialog again for a new repo or a plain `git worktree add` path (§4).
- **Naming a box pane:** `scripts/herdr-pane.sh name <pane> <task> <seat> --machine
  homelab2026` (§2 — the same two calls, against the box's server).
- **Routing rule.** A lane goes to the box only when its base is on origin
  (`placement.py check-base`); its branch comes back to the MBA by `placement.py
  fetch-back` (git fetch over ssh), never by a worker push. Usage headroom, job size and
  Alex's plans decide the rest (`/concurrency` §5.1).
- A failed `--machine` call does not prove nothing happened on the box: read its state
  (`herdr --machine homelab2026 workspace list`) before retrying a mutation.
- The box does not publish its own usage block (dev-workbench ENG-2); the MBA's block
  already merges both machines.

### 6.2 Worker token budget

Measured 2026-10-05: 78% of a weekly Claude limit went in ~45h. The `fe-fail-loud`
lanes each ran 500–1,300 turns as one Opus `[1m]` session at a 200–300k median
context. Cache reads, which re-read the whole context every turn, were ~67% of the
weighted spend; output was negligible. Context size × turn count is the bill, so:

- **Workers never run a 1M window.** A 200k window auto-compacts; a 1M window lets a
  lane carry 500k of stale history into every turn. The model alias does not cap it:
  under Claude Code 2.1.288, `--model opus`, `--model claude-opus-5-5` and `--model
  sonnet` all report a 1,000,000 window, and `CLAUDE_CODE_AUTO_COMPACT_WINDOW` does not
  change it. `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`, inline before the launcher, does
  (reads back 200,000 in `--output-format json` `modelUsage.contextWindow`). Only the
  driver keeps 1M.
- **One unit per session.** A brief covers one coherent unit. A lane with several
  units gets a fresh worker per unit, handed off through commits and the hand-back
  file, never a re-prompt of the same session. Fix writers and review panes are
  fresh sessions too (`/concurrency` §7.3).
- **Pick the cheapest seat that can do it.** Pattern work goes to `sonnet`; `opus`
  only when the lane needs judgment. When Claude headroom is low, push mechanical
  lanes to `codex` or `glm`, which bill elsewhere.
- **Small tool output.** Bash output was 83% of tool-result bytes. Every brief
  carries the output rule in `/concurrency` §6 step 3.

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
  attaches, so forwarded pane fg is neutral. TERM/terminfo makes no difference to
  content color; the zshrc `HERDR_ENV`→TERM/TERMINFO block is for TUI
  correctness (export TERMINFO before TERM) — suspect it if a TUI misbehaves.
- **Pane content colors are NOT herdr theme tokens** — `theme.custom.*` paints
  chrome (sidebar/borders/status) only. Content color = host-fg / terminfo.
- **herdr is a brew service** (`homebrew.mxcl.herdr`) — survives logout; attach
  by typing `herdr`. Never restart it mid-skill on Alex's behalf.
- **`herdr worktree create --cwd <repo>` leaves an idle base-repo space behind**
  (a `<repo> (main)` shell) that a later pane move does not consume. Close it
  after the move (verified live 2026-08-24).
- **A role in the workspace label makes a phantom agent.** Name the workspace for
  the run/scope number only, never a role: a space named `128 driver` shows every
  pane in it, workers included, as a second "driver" (hit live 2026-08-24).
  Roles belong on panes (§2).
- **A fresh tab's panes are not shells yet.** `agent start` straight after
  `tab create` / `pane split` can fail `agent_pane_busy` ("not an available shell")
  while zsh is still starting. Retry `agent start` into the **same** pane id, and do not
  split again (5 of 8 on 2026-09-29).
- **`agent prompt` right after `agent start` can paste without submitting.** The
  text sits in the input box and the agent stays `idle` (8 of 13 lanes on
  2026-09-29). After prompting, wait a few seconds; any worker still `idle` gets
  `agent send-keys <name> enter`. That submits our own prompt; it does not answer a
  permission dialog.
- **Machine capacity is the real pane cap for build-heavy lanes.** 13 Opus lanes
  all running Go lint and test baselines at once drove the 10-core MacBook Air to
  load ~100 (RAM fine, CPU saturated) and made it sluggish for Alex (2026-09-29).
  For CPU-bound lanes (Go/Node builds, DB suites), dispatch **≤ ~6 at once** on the
  MBA and queue the rest, or stagger the starts. If a herd is already out, renice the
  worker trees instead of killing them, because their later builds inherit the
  priority. Walk the descendants of every `claude --dangerously-skip-permissions` pid
  and `setpriority(+10)`. Do it in Python: a zsh loop over an unsplit pid list spins.

## 8. Supervision primitives (for reference; owned by the dispatching skill)

- PRIMARY wait is the skill's own done-marker, not a herdr state:
  `herdr pane wait-output <pane> --match "<marker>"`. `agent wait --until done`
  hangs on codex (it reports `idle`); use `--until blocked` for alerts only.
- `pane.report_agent` states: `idle | working | blocked | done | unknown`.
  `unknown` is not proof of completion; `blocked` = an approval/question UI.
