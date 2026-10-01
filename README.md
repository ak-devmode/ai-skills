# ai-skills

Custom Claude Code skills for the PMG/Kalpa team. Includes our own skills plus automated setup for [gstack](https://github.com/garrytan/gstack) (Garry Tan's skill suite).

## 1. What's included

### 1.1 Our skills (this repo)

| Skill | Description |
|-------|-------------|
| `/scope` | Task scoping and multi-skill orchestration |
| `/scope-review` | Review a team scope/PRD/plan at the right altitude, in Alex's voice |
| `/plan` | Execute a plan file task by task, with checkpoints; reviews and verifies each unit |
| `/review` | Pre-landing review with codex as the gate (gstack's engine + Kalpa/PMG domain rules); every finding dispositioned |
| `/verify` | Independent verification: a runner executes the finish conditions, a codex judge (Claude fallback) confirms or downgrades, the gate decides Done |
| `/concurrency` | herdr-backed multi-agent dispatch — partition a scope, dispatch lanes to named herdr panes |
| `/research` | Cost-tuned deep research — visible herdr lanes per angle (default) or the background `deep-research-lean` workflow |
| `/herdr` | herdr workflow layer — naming, worktree lifecycle, worker launch, pane layout (referenced by `/concurrency`, `/plan`, `/closeout`) |
| `/prd` | Product Requirements Document generator |
| `/markdown-style` | Structured markdown document creation |
| `/md2docx` | Convert markdown to brand-styled `.docx` (Word/Google Docs); `--bilingual` ID/EN contract mode |
| `/repo-cleanup` | Branch hygiene: classify, prune merged, flag in-flight (current repo) |
| `/repo-cleanup-all` | Alias for `/repo-cleanup --all` — fleet sweep across a GitHub org/user |
| `kalpa-*` | Kalpa-specific skills (`kalpa-context`, `kalpa-coding-standards`, `kalpa-generate-api`, `kalpa-migrate`, `kalpa-satu-sehat-fhir`) |

### 1.2 gstack skills (installed automatically)

gstack adds 25+ skills including `/ship`, `/qa`, `/browse`, `/investigate`, `/retro`, and more. See the [gstack README](https://github.com/garrytan/gstack) for the full list.

## 2. Setup

### 2.1 Quick start

```bash
# Clone this repo
git clone https://github.com/ak-devmode/ai-skills.git ~/Projects/ai-skills

# Run setup (installs both ai-skills + gstack)
cd ~/Projects/ai-skills && ./setup.sh
```

The setup script:
- Symlinks each skill folder from this repo into `~/.claude/skills/`
- Clones [garrytan/gstack](https://github.com/garrytan/gstack) to `~/Projects/gstack` (or pulls latest if already cloned)
- Symlinks gstack into `~/.claude/skills/gstack`
- Runs gstack's own setup script
- Checks the verification prerequisites (Python ≥ 3.9, codex installed and logged in) and
  **warns** with the fix. It never fails the setup (§4.1)

After setup, restart Claude Code and run `/verify --demo`. The whole path, from
`git pull && ./setup.sh` to a finished demo, takes under 5 minutes.

### 2.2 Manual setup

If you prefer to do it by hand:

```bash
# 1. Clone both repos
git clone https://github.com/ak-devmode/ai-skills.git ~/Projects/ai-skills
git clone https://github.com/garrytan/gstack.git ~/Projects/gstack

# 2. Create skills directory
mkdir -p ~/.claude/skills

# 3. Symlink ai-skills
ln -s ~/Projects/ai-skills/scope ~/.claude/skills/scope
ln -s ~/Projects/ai-skills/plan ~/.claude/skills/plan
ln -s ~/Projects/ai-skills/prd ~/.claude/skills/prd
ln -s ~/Projects/ai-skills/markdown-style ~/.claude/skills/markdown-style
# ...one link per top-level skill dir; setup.sh does all of them and arbitrates name
# collisions (ours win the bare name), so prefer it over linking by hand

# 4. Symlink gstack
ln -s ~/Projects/gstack ~/.claude/skills/gstack

# 5. Run gstack setup
cd ~/Projects/gstack && ./setup
```

## 3. Updating

```bash
# Update ai-skills
cd ~/Projects/ai-skills && git pull

# Update gstack
cd ~/Projects/gstack && git pull
```

Or just re-run `./setup.sh` — it pulls gstack automatically.

## 4. Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [Git](https://git-scm.com/)
- [Bun](https://bun.sh/) v1.0+ (required by gstack)
- Python ≥ 3.9 (the verification scripts; stdlib only)
- [codex CLI](https://github.com/openai/codex), logged in: `npm i -g @openai/codex && codex login`.
  It is optional, but without it `/review` and `/verify` run on a Claude fallback and every
  verdict carries a ⚠ marker (§5.3)

### 4.1 What setup checks

`./setup.sh` step 4 runs `scripts/verify-prereqs.sh`, which prints `ok` or `!!` + `fix:`
per prerequisite and always exits 0. The live codex call is left to `/verify --demo`,
because it costs credits on every run.

## 5. Verification — `/review` and `/verify`

### 5.1 What they do

Every phase of a scope that commits code is **reviewed**, and every phase is **verified**,
before it can be marked Done. Both use codex, the other model family, in a fresh
read-only context, so the author's model never grades its own work.

- **`/review`** reviews the phase's exact revision range (`base..HEAD` per repo). Every
  finding gets a stable ID and must be dispositioned: `fixed <sha>` (the commit must
  touch the file or a test beside it, or say how it fixes it) or `rejected <reason>`.
- **`/verify`** runs the phase's rows in the scope's `finish-conditions.md` (commands
  that fail loud), then the codex judge reads that evidence plus git. The judge can
  confirm or **downgrade** a result, never upgrade one. It reports an evidence *rung*
  per check, never a score: 1 said so · 2 pointed at the line · 3 showed the bad case
  can't happen · 4 ran a script that fails loud · 5 reproduced in the running app.
- `/scope` writes the finish table, `/plan` runs both at each phase checkpoint and marks
  Done through the gate, and `/closeout` checks the whole scope.

### 5.2 Reading a verdict

`/verify <N.P>` writes `plans/<scope>/artifacts/verify-<N.P>-report.md`. It leads with the
gate verdict and the judge line, then one row per check (result, rung reached/required,
reason), then findings and lever candidates. Every block names what was expected, what
was found, where, the **cause** (`code` = your change, `environment` = env, network or
credentials, `tooling` = these scripts), and the exact next command.

### 5.3 What each ⚠ in PLANS-INDEX means

| Marker | Means | What to do |
|---|---|---|
| `⚠ verify advisory: N blocked (ids)` | The gate would have blocked, but it is in advisory mode | Read the report; fix, or accept with a reason |
| `⚠ judge: claude-fallback <why>` / `⚠ judge: none <why>` | codex didn't judge, so the verdict is weaker | Set up codex; a later codex verdict clears it |
| `⚠ judge: review <line>` | The review ran on the Claude fallback | Re-review with codex |
| `⚠ verify skipped: <reason>` | Someone ran `/plan … --skip-verify "<reason>"` | Nothing, but it stays visible |
| `⚠ verify failed <ids>` | The scope closed with failing checks (`/closeout`) | The failed checks are in `TO-DO.md` |

### 5.4 Advisory vs blocking

The gate is **advisory** today: a block is reported and marked, and the phase still
closes. After five scopes pass cleanly, it flips to **blocking**, and a block then stops
Done. `/closeout` prints the running count (`clean gated scopes: N/5`). A scope already
in flight when the gate arrived is never asked to verify earlier phases: they are listed
under `**Predates gate:**`.

### 5.5 Skipping

`/plan <N.P> --skip-verify "<reason>"` bypasses the gate for one unit when verification
genuinely cannot run (an env is down). The reason is required, and it goes into the
status header and the index row.

### 5.6 First contact

`/verify --demo` runs a fixture scope with six planted defects and a clean control
(about 2 minutes): the failing verdict names each defect, and the control passes. If
codex isn't set up, the demo says so, and the deterministic half still runs. Contracts:
`templates/verify-contracts.md`.
