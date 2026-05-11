---
name: cross-repo-init
version: 1.0.0
description: |
  Bootstrap CROSS-REPO.md and ARCHITECTURE.md for a repo so /plan and /closeout-extended
  have the metadata they depend on. CROSS-REPO.md declares Pattern Sources (repos this
  follows patterns from) and Consumers (repos that depend on this repo's contracts).
  ARCHITECTURE.md is a short, agent-load-bearing architecture snapshot. Idempotent:
  re-running on a healthy repo produces no diff.

  Use when asked to "cross-repo init", "bootstrap cross-repo", "add CROSS-REPO.md",
  "onboard this repo for closeout", "set up this repo for /closeout-extended", or
  when /plan or /closeout halts asking for CROSS-REPO.md.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# /cross-repo-init — Repo Bootstrap for Closeout Skills

This skill is the on-ramp for the closeout-skills framework. After /cross-repo-init runs
on a repo, /plan reads its CROSS-REPO.md at session start (pattern-first rule), and
/closeout-extended uses it to walk the cross-repo graph.

The skill **never uses AskUserQuestion** — all user interaction is open-ended numbered
inline questions answered by number.

---

## 1. How It Works

Two outputs per run: `CROSS-REPO.md` and `ARCHITECTURE.md` at the repo root. Both are
scaffolded from templates in this skill's `templates/` directory.

- **If a file is absent:** scaffold from template, auto-detect what can be detected,
  present proposal to user, write on approval.
- **If a file is present:** audit for drift against current code state, propose edits,
  apply on approval. If the file is up-to-date, do nothing — this is the idempotency
  guarantee.

Drift detection is deterministic-first (grep for stale repo references, missing imports,
broken paths) then LLM-judge on the candidates.

## 2. Step 0 — Detect Current Repo

```bash
git rev-parse --show-toplevel 2>/dev/null || { echo "ERROR: not a git repo"; exit 1; }
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "(no remote)")
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
echo "REPO_NAME=$REPO_NAME"
echo "REPO_ROOT=$REPO_ROOT"
echo "REMOTE_URL=$REMOTE_URL"
echo "DEFAULT_BRANCH=$DEFAULT_BRANCH"
```

Halt with a clear error if not in a git repo.

## 3. Step 1 — CROSS-REPO.md Handling

### 3.1 Check existing state

```bash
[ -f "$REPO_ROOT/CROSS-REPO.md" ] && echo "EXISTS" || echo "ABSENT"
```

### 3.2 If ABSENT — scaffold and propose

3.2.1 Read template: `~/.claude/skills/cross-repo-init/templates/CROSS-REPO.md.template`
(or wherever the skill is installed — use `$SKILL_DIR` derived from skill invocation).

3.2.2 Read examples: `~/.claude/skills/cross-repo-init/templates/CROSS-REPO.md.examples.md`
for reference patterns.

3.2.3 Auto-detect Pattern Sources by:
- Reading `package.json` / `go.mod` / `requirements.txt` for shared-lib imports that
  resolve to other Projects repos
- Grepping source for explicit cross-repo references (e.g., `wellmed-infrastructure/`
  paths in comments or test fixtures)
- Checking for known PMG/WellMed convention paths in imports

3.2.4 Auto-detect Consumers by (best effort):
- Grepping sibling repos under `~/Projects/<group>/*` for imports OR webhook URL
  allowlists OR event subscriptions targeting THIS repo's name or contract path
- This is approximate — explicitly tell the user the candidate list is best-effort

3.2.5 Present proposal inline:

```
Proposed CROSS-REPO.md for <REPO_NAME>:

PATTERN SOURCES (detected):
  1. wellmed-infrastructure
     - adapters/* — error handling, retries (detected from imports)
     - lib/* — shared utilities (detected from imports)

CONSUMERS (candidates — best-effort grep across ~/Projects):
  2. pmg-chatwoot — references router webhook URL (handlers/router.js:42)
  3. padmacare-wp — references Zoho drip webhook URL (php-plugin-area)

TRAVERSAL CONFIG:
  max-depth-override: 2 (default)
  trunk-branch: develop (detected default)

What would you like to change before writing?
  1. Accept as-is and write file
  2. Remove a Pattern Source (specify which)
  3. Add a Pattern Source (specify repo + paths)
  4. Remove a Consumer (specify which)
  5. Add a Consumer (specify repo + contracts)
  6. Change trunk-branch
  7. Change max-depth-override
  8. Describe other change

Answer by number (multiple OK, e.g. "2 and 5").
```

3.2.6 Loop on user's response until they pick option 1 (accept). Then write
`$REPO_ROOT/CROSS-REPO.md` by substituting placeholders in the template.

### 3.3 If EXISTS — audit for drift

3.3.1 Read existing CROSS-REPO.md.

3.3.2 **Deterministic pass**:
- For each declared Pattern Source: verify the repo directory exists at the expected
  path (`~/Projects/<group>/<repo>` based on naming).
- For each declared Consumer: verify the repo exists.
- Check timestamp footer (`<!-- Last scaffolded/audited by /cross-repo-init: ... -->`)
  for age. Flag if > 90 days old as "potentially stale."

3.3.3 **LLM-judge pass** (only on candidates flagged by 3.3.2):
- For drifted Pattern Sources: re-detect the repo's imports/usage and propose corrections.
- For drifted Consumers: re-grep sibling repos and propose corrections.

3.3.4 If both passes find no drift, output:

```
CROSS-REPO.md is healthy. No changes needed.
```

This is the **idempotency guarantee**: re-run on a healthy repo = zero diff.

3.3.5 If drift is detected, present a numbered diff proposal (same options as 3.2.5
adapted for edit instead of scaffold). Apply on approval.

## 4. Step 2 — ARCHITECTURE.md Handling

Same flow as Step 1, with these differences:

### 4.1 Auto-detection sources

- **Components**: list top-level dirs that contain code (skip `node_modules`, `.git`,
  `dist`, `build`, etc.). For each, peek at the README or first file's docstring for
  a one-line description.
- **Data Flow**: do NOT auto-generate — leave the placeholder and explicitly ask the
  user. A wrong diagram is worse than a missing one. Note this rule loudly in the
  proposal.
- **Key Decisions**: lift from existing CLAUDE.md if present + scan auto-memory for
  project-relevant decisions (read memory index, filter by repo slug).
- **External Integrations**: scan for SSM parameter names, env var patterns, third-party
  API client imports (xendit, zoho, notion, etc.).
- **Cross-Repo Position**: derive one-line summary from the CROSS-REPO.md just written
  in Step 1.

### 4.2 Presentation

Use the same numbered-inline-options pattern as 3.2.5. Make it explicit which sections
were auto-detected (high confidence) vs which need user input (low confidence).

### 4.3 Length gate

Before writing, check the proposed content is under 200 lines. If over, split:
- Keep the top-level ARCHITECTURE.md as an index
- Move per-component detail to `docs/architecture/<component>.md`
- Propose this split to user; default to keeping single file under 200 if possible

## 5. Step 3 — Idempotency Verification

After any write, re-run Steps 1 and 2 read-only. If either reports drift, something
went wrong in the write — halt and tell the user. A healthy /cross-repo-init run ends
with both files clean and a "no further changes needed" status.

## 6. Step 4 — Report

```
✅ /cross-repo-init complete for <REPO_NAME>

CROSS-REPO.md: <SCAFFOLDED | UPDATED | HEALTHY (no change)>
  Pattern Sources: <N declared>
  Consumers: <N declared>

ARCHITECTURE.md: <SCAFFOLDED | UPDATED | HEALTHY (no change)>
  Components: <N>
  Lines: <N> / 200 budget
  Split into docs/architecture/*: <yes | no>

Next: commit these files on the current branch, then this repo is ready
for /plan and /closeout-extended.
```

## 7. Important Behaviors

7.1 **Never use AskUserQuestion.** All interaction is open-ended numbered inline
questions. User answers by number.

7.2 **Idempotent always.** Re-running on a healthy repo produces zero diff and a
"HEALTHY" status. This is non-negotiable — it's the contract /plan and /closeout-extended
depend on.

7.3 **Auto-detection is approximate.** Always tell the user which sections are detected
(high confidence) vs need their input (low confidence). Consumers detection is
especially approximate — it depends on what other repos are checked out locally.

7.4 **Never auto-generate diagrams.** The Data Flow ASCII diagram in ARCHITECTURE.md
requires user input. A wrong diagram is misleading; a placeholder is honest.

7.5 **Skip third-party / inactive repos.** If the user invokes this in `~/Projects/gstack`,
`~/Projects/archive`, or any repo without a meaningful contract graph, ask them to
confirm before proceeding. These usually don't need CROSS-REPO.md.

7.6 **Workspace-relative paths in ARCHITECTURE.md Components.** Per /markdown-style §8.8.

7.7 **Templates path resolution.** Templates live at `<SKILL_DIR>/templates/`. The skill
dir is typically `~/Projects/ai-skills/cross-repo-init/` (symlinked into
`~/.claude/skills/cross-repo-init/`). If templates are not found, halt with a clear
message telling the user to check skill installation.

## 8. First Run Recipe — pmg-integrations (Phase 5 dogfood target)

For the very first dogfood run:

```bash
cd ~/Projects/pmg/pmg-integrations
```

Then invoke /cross-repo-init. Expected behavior:

1. Detects repo: pmg-integrations
2. CROSS-REPO.md absent → scaffolds
3. Auto-detects: wellmed-infrastructure as Pattern Source (from imports in adapters)
4. Auto-detects (best-effort): pmg-chatwoot, padmacare-wp, KP2MI-foreign-workers,
   mcu-status as Consumers (from cross-repo grep)
5. User reviews proposal, accepts or refines
6. Writes CROSS-REPO.md
7. ARCHITECTURE.md absent → scaffolds
8. Auto-detects Components from top-level dirs (handlers, lib, operations, cron, etc.)
9. User fills in Data Flow diagram (skill prompts)
10. Key Decisions lifted from CLAUDE.md + memory
11. External Integrations detected from SSM patterns + client imports
12. User reviews proposal, accepts or refines
13. Writes ARCHITECTURE.md
14. Re-runs idempotency check → both files HEALTHY → report success

Commit on current branch. Repo is now ready for /plan + /closeout flows.

## 9. Known Limitations

- **Consumer detection requires sibling repos to be checked out locally.** If
  `~/Projects/pmg/pmg-chatwoot` isn't cloned, /cross-repo-init won't detect it as a
  Consumer of pmg-integrations. User must add it manually.
- **Data Flow diagram is always user-supplied.** No auto-generation.
- **Best-effort grep for Consumers** may produce false positives (e.g., a comment
  mentioning the repo name doesn't mean it's a real consumer). User reviews and prunes.
- **Templates must exist at `<SKILL_DIR>/templates/`** — symlink setup matters.

## 10. Recovery from Failed Runs

If the skill halts mid-way (e.g., user closed the terminal), nothing is left in a
broken state — files are only written after explicit user approval at the end of each
step. Re-invoking the skill picks up cleanly.

If a file was written but is now wrong, user can:
- Edit it manually
- Or re-invoke /cross-repo-init and use the drift detection to propose corrections
