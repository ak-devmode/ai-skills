---
name: cross-repo-init
version: 1.1.0
description: |
  Bootstrap the trio — CROSS-REPO.md, ARCHITECTURE.md, and CLAUDE.md — for a repo so
  /plan and /closeout-extended have the metadata they depend on. CROSS-REPO.md declares
  Pattern Sources (repos this follows patterns from) and Consumers (repos that depend on
  this repo's contracts). ARCHITECTURE.md is a short, agent-load-bearing architecture
  snapshot. CLAUDE.md is the per-repo agent context. Idempotent: re-running on a healthy
  repo produces no diff.

  When an existing CLAUDE.md or ARCHITECTURE.md is present (commonly with the rich
  content living in `.claude/CLAUDE.md` and a thin or stale version at repo root, or
  vice versa), the skill folds them into a single canonical version at root and
  deletes the duplicate — single canonical per repo; old long-form ARCHITECTURE
  versions archive to `archive/<name>-v<version>.md`.

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

**Three outputs per run** at the repo root: `CROSS-REPO.md`, `ARCHITECTURE.md`, and
`CLAUDE.md` (the trio). All three are scaffolded from templates in this skill's
`templates/` directory.

- **If a file is absent:** scaffold from template, auto-detect what can be detected,
  present proposal to user, write on approval.
- **If a file is present:** audit for drift, propose targeted additions / corrections,
  apply on approval. If the file is up-to-date, do nothing — this is the idempotency
  guarantee.

**Assess-first, don't sidecar-by-default.** When an existing CLAUDE.md or
ARCHITECTURE.md is present (commonly with rich content in `.claude/CLAUDE.md` and
stale content at root, or vice versa), the skill READS BOTH, identifies what's
worth preserving, and produces a single canonical file at root with the duplicate
deleted. It does NOT default to writing a parallel sidecar file. See §7.8.

**Long-form archive.** When a repo has a substantial pre-existing architecture
document (e.g., `wellmed-system-architecture.md`) that the new ARCHITECTURE.md
supersedes, agent-critical content is folded inline and the original is moved to
`archive/<name>-v<version>.md` (preserving history without keeping two
co-canonical files). See §7.9.

Drift detection is deterministic-first (grep for stale repo references, missing imports,
broken paths) then LLM-judge on the candidates.

## 2. Step 0 — Detect Current Repo

### 2.1 Identify repo + default branch

```bash
git rev-parse --show-toplevel 2>/dev/null || { echo "ERROR: not a git repo"; exit 1; }
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "(no remote)")
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
CURRENT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current)
echo "REPO_NAME=$REPO_NAME"
echo "REPO_ROOT=$REPO_ROOT"
echo "REMOTE_URL=$REMOTE_URL"
echo "DEFAULT_BRANCH=$DEFAULT_BRANCH"
echo "CURRENT_BRANCH=$CURRENT_BRANCH"
```

Halt with a clear error if not in a git repo.

### 2.2 Branch survey — CRITICAL FOR AUTO-DETECTION ACCURACY

**The checked-out branch is not the truth.** Many teams keep `main` as a
stable release/snapshot branch while real current-state code lives on
`develop` and feature branches. /cross-repo-init's auto-detection MUST
look at the branch that holds current work — not just whatever happens to
be checked out.

```bash
# Enumerate non-stale remote branches with divergence vs default
git -C "$REPO_ROOT" fetch --prune origin 2>/dev/null  # best-effort refresh
git -C "$REPO_ROOT" for-each-ref --format='%(refname:short) %(committerdate:iso-strict)' refs/remotes/origin \
  | grep -vE '/(HEAD|gh-pages)$'
git -C "$REPO_ROOT" rev-list --left-right --count "origin/$DEFAULT_BRANCH...origin/develop" 2>/dev/null || true
```

**Pick the survey branch** (the one auto-detection scans against), using
this cascade:

1. If `CROSS-REPO.md` already exists with a populated `trunk-branch:` field, use that.
2. Else if `origin/develop` exists AND is non-trivially ahead of
   `origin/$DEFAULT_BRANCH` (≥5 commits ahead OR has files the default branch
   doesn't), use `develop`.
3. Else use `$DEFAULT_BRANCH`.

Surface the choice to the user in the Step 0 report, even when no
ambiguity exists:

```
Branch survey:
  Default (origin/HEAD):  $DEFAULT_BRANCH
  Currently checked out:  $CURRENT_BRANCH
  origin/develop:         <exists with N commits ahead of default | does not exist>
  Survey branch chosen:   $SURVEY_BRANCH    (reason: <which step in the cascade>)

Recently-active feature branches (informational only — not scanned by
default; flag any that look like architecture/SDK-restructure work):
  - feat/sdk-restructure-opsi3   (2026-04-21)
  - feature/architecture-adaptation  (2026-04-09)
  - ...
```

If a feature branch name suggests it carries load-bearing architecture
work (`*adapter*`, `*restructure*`, `*architecture*`, `*shared*`, `*sdk*`,
`*infra*`), surface it explicitly and ask the user whether to include it
in the auto-detection scan (numbered inline option).

**All auto-detection in Step 1 (§3.2.3, §3.2.4) and Step 2 (§4.1) MUST
run against `$SURVEY_BRANCH`, not the checked-out branch.** Use
`git ls-tree -r --name-only origin/$SURVEY_BRANCH` for file enumeration
and `git show origin/$SURVEY_BRANCH:<path>` to read content. Do not
`git checkout` — survey without touching the user's working tree.

### 2.3 Drift signal capture

The §6 Drift section in ARCHITECTURE.md (per the template) needs concrete
content. Capture these signals during the survey for use later:

- Components present on `$SURVEY_BRANCH` but absent on `$DEFAULT_BRANCH` (e.g., an `adapter/` directory built on develop, not yet on main).
- ADRs that reference future-state components — flag the future-state ones for the Drift table.
- **Repo state classification** (used by §5.6 stub-repo handling and §7.11):
  - **STUB**: only `README.md` + `.gitignore` (or empty), single branch
    (typically `main`), minimal commit history. No source code.
  - **EMPTY-SERVICE**: skeleton present (cmd/, internal/) but no real
    implementation — branch state matches a recent "service initialized"
    commit.
  - **BUILT**: real codebase with multiple commits, recognizable structure.

If `$SURVEY_BRANCH` and `$DEFAULT_BRANCH` are the same and no Drift
signals surface, render `{{CODE_STATE_DRIFT}}` as:

> "No known drift between target architecture and current code as of {{TIMESTAMP}}."

Else render a table per the kalpa-docs §11 example (link from the
template's HTML comment).

### 2.4 .gitignore audit

```bash
# Check for overbroad markdown ignore rules
grep -nE "^\*\.(md|markdown)\b" "$REPO_ROOT/.gitignore" 2>/dev/null
```

If `*.md` (or `*.markdown`) appears at top level of `.gitignore`, surface
it in the Step 0 report and propose removal. The trio files (CROSS-REPO.md,
ARCHITECTURE.md, CLAUDE.md) and all `docs/` content should be tracked by
default. An `!README.md` exception is a tell that the rule is overbroad —
the right fix is to remove the `*.md` line, not add more exceptions.

Don't silently `git add -f` to bypass the rule — that papers over a real
gitignore problem.

### 2.5 Step 0 report

Surface the cumulative findings to the user before moving to Step 1:

```
Repo bootstrap survey — $REPO_NAME

  Default branch:        $DEFAULT_BRANCH
  Survey branch chosen:  $SURVEY_BRANCH   (cascade reason: ...)
  Currently checked out: $CURRENT_BRANCH

  Repo state:            <STUB | EMPTY-SERVICE | BUILT>
  Drift signals:         <N components on develop missing from main, ...>

  .gitignore audit:      <clean | "*.md rule found (line 50) — propose removal">

  Existing trio:         CROSS-REPO.md=<exists|absent>
                         ARCHITECTURE.md=<exists|absent>  (+ wellmed-system-architecture.md or similar predecessor)
                         CLAUDE.md=<root|.claude/|both|absent>

Proceed with Steps 1-3? (1: yes / 2: ask first)
```

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

3.2.3 Auto-detect Pattern Sources by (against `$SURVEY_BRANCH` per §2.2, not
the checked-out branch):
- Reading `package.json` / `go.mod` / `requirements.txt` for shared-lib imports that
  resolve to other Projects repos. Use `git show origin/$SURVEY_BRANCH:<path>`,
  not `cat`, so the survey is branch-aware.
- Grepping source for explicit cross-repo references (e.g., `wellmed-infrastructure/`
  paths in comments or test fixtures). Use `git grep origin/$SURVEY_BRANCH -- <pattern>`.
- Checking for known PMG/WellMed convention paths in imports.

3.2.4 Auto-detect Consumers by (best effort, branch-aware):
- Grepping sibling repos under `~/Projects/<group>/*` for imports OR webhook URL
  allowlists OR event subscriptions targeting THIS repo's name or contract path.
  For each sibling repo, determine its own `$SURVEY_BRANCH` per the §2.2 cascade
  before scanning — many sibling repos also hold current state on `develop`, not `main`.
- This is approximate — explicitly tell the user the candidate list is best-effort.

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

All file enumeration here runs against `$SURVEY_BRANCH` per §2.2, not the
checked-out branch. Use `git ls-tree -r --name-only origin/$SURVEY_BRANCH` /
`git show origin/$SURVEY_BRANCH:<path>` rather than `ls` / `cat`.

- **Components**: list top-level dirs that contain code (skip `node_modules`, `.git`,
  `dist`, `build`, etc.). For each, peek at the README or first file's docstring for
  a one-line description. If `$SURVEY_BRANCH` has components that `$DEFAULT_BRANCH`
  lacks (or vice versa), capture that gap for §6 Drift.
- **Data Flow**: do NOT auto-generate — leave the placeholder and explicitly ask the
  user. A wrong diagram is worse than a missing one. Note this rule loudly in the
  proposal.
- **Key Decisions**: lift from existing CLAUDE.md if present + scan auto-memory for
  project-relevant decisions (read memory index, filter by repo slug).
- **External Integrations**: scan for SSM parameter names, env var patterns, third-party
  API client imports (xendit, zoho, notion, etc.).
- **Cross-Repo Position**: derive one-line summary from the CROSS-REPO.md just written
  in Step 1.
- **§6 Current Code State vs Target Architecture (Drift)**: assemble from §2.3 signals.
  Each row in the table captures one designed-but-not-built (or
  built-but-not-merged-to-main) component. If no drift surfaced, render as
  the green-check line per §2.3. ADR numbering collisions (two ADRs with the
  same number) are *not* drift content — they go in §3 Key Decisions or §5 ADR
  Index as a known anomaly with a recommended renumbering. (Future polish: a
  separate audit pass for ADR-number collisions across `adrs/*.md` —
  see v1.1 TO-DO.)

### 4.2 Presentation

Use the same numbered-inline-options pattern as 3.2.5. Make it explicit which sections
were auto-detected (high confidence) vs which need user input (low confidence).

### 4.3 Length gate

Before writing, check the proposed content is under 200 lines. **Exception:**
ARCHITECTURE.md for the system-root docs leaf (e.g., kalpa-docs) MAY exceed
200 lines when it is the canonical agent-load-bearing root for an entire
multi-service system; agent-critical content from any long-form predecessor
folds inline here.

When the 200-line gate trips for a normal repo:
- Keep the top-level ARCHITECTURE.md as an index
- Move per-component detail to `docs/architecture/<component>.md`
- Propose this split to user; default to keeping single file under 200 if possible

### 4.4 Long-form predecessor (fold + archive)

If a substantial pre-existing architecture document is present (e.g.,
`wellmed-system-architecture.md` in kalpa-docs), do **not** create a parallel
`ARCHITECTURE.md` next to it. Instead:

1. Read both the predecessor and any draft ARCHITECTURE.md content.
2. Identify agent-critical sections in the predecessor (saga patterns,
   database architecture, tenant installation, code structure rules, etc.).
3. Fold those inline into the new canonical ARCHITECTURE.md (compressed if
   the predecessor is verbose).
4. Move the predecessor to
   `archive/<original-name>-v<version-or-date>.md` via `git mv` (preserves
   history).
5. Update cross-doc references (README.md, plans/PLANS-INDEX.md,
   repo-governance.md, etc.) to point at the new ARCHITECTURE.md
   (canonical) and the archive path (historical).
6. Mention this transformation prominently in the new ARCHITECTURE.md
   preamble.

Non-agent narrative content (history, motivation, changelog) stays in the
archived file; if there's load-bearing non-agent content the team needs,
fold it into README.md instead.

**Single canonical per repo.** Don't keep two architecture docs co-canonical
— one will get stale. The archive is for reference only, not for ongoing
maintenance.

## 5. Step 3 — CLAUDE.md Handling

Same conceptual flow as Steps 1 and 2, with one important wrinkle: CLAUDE.md
commonly lives in **one of two locations** (or both) — at the repo root and
under `.claude/CLAUDE.md`. Many existing repos have rich content in one
location and stale or shallow content in the other.

### 5.1 Check existing state

```bash
[ -f "$REPO_ROOT/CLAUDE.md" ]            && echo "ROOT_EXISTS"
[ -f "$REPO_ROOT/.claude/CLAUDE.md" ]    && echo "CLAUDE_DIR_EXISTS"
```

Possible combinations:
- **Neither exists** → 5.2 scaffold from template at root.
- **Only `CLAUDE.md` (root) exists** → 5.3 audit-and-extend.
- **Only `.claude/CLAUDE.md` exists** → 5.4 fold-up-and-delete (this is
  the most common pattern across wellmed-* code services).
- **Both exist** → 5.5 fold-both-into-root-and-delete-sidecar.

### 5.2 If ABSENT — scaffold

5.2.1 Read template: `<SKILL_DIR>/templates/CLAUDE.md.template`.

5.2.2 Read examples: `<SKILL_DIR>/templates/CLAUDE.md.examples.md` for the
three archetype patterns (Go service / frontend leaf / docs leaf).

5.2.3 Auto-detect what you can (run against `$SURVEY_BRANCH`):
- **What this service is** — derive from README.md head + module name + port.
- **Trunk branch + workflow** — from §2.2 survey + memory pointer to
  `feedback_branch_off_develop.md` if applicable.
- **Build/test/lint** — detect from `Makefile`, `package.json` scripts,
  `go.mod` (Go), `composer.json` (PHP), etc.
- **Architecture decisions** — lift from the just-written ARCHITECTURE.md §4
  + scan auto-memory for repo-relevant decisions.
- **Environment variables** — scan `env.example`, `internal/config/env.go`,
  or equivalent. **Port assignment is authoritative from env.example, NOT
  from any existing .claude/CLAUDE.md** (see §7.10).
- **What NOT to do** — derive from ADRs the repo cites + any "do not"
  callouts in existing docs.
- **Cross-repo position** — one-line summary from CROSS-REPO.md just written.

5.2.4 Present proposal inline (numbered options pattern, same as §3.2.5).

5.2.5 On approval, write `$REPO_ROOT/CLAUDE.md`.

### 5.3 If ONLY ROOT EXISTS — audit-and-extend

5.3.1 Read existing `$REPO_ROOT/CLAUDE.md`.

5.3.2 Identify gaps vs the trio shape — what's missing relative to the
template:
- Archetype declaration (e.g., "Tier-1 internal leaf — saga participant")
- Trunk branch and workflow section
- Cross-repo position pointer to `CROSS-REPO.md`
- Pointer to `ARCHITECTURE.md` for component layout
- Memory pointers (`~/.claude/projects/.../memory/`)

5.3.3 Identify content the existing file ALREADY covers well — preserve those
sections verbatim. **Do not rewrite for rewriting's sake.**

5.3.4 Present a targeted delta proposal:

```
Existing CLAUDE.md is healthy in:
  - §X (Sidekiq/Redis topology)
  - §Y (Feature flags)
  - §Z (Project-specific conventions)

Proposed additions (sections currently missing):
  + §N. Trunk branch and workflow
  + §N+1. Cross-repo position (pointer to CROSS-REPO.md)
  + §N+2. Plans and memory pointers

Inline edits (small corrections):
  - Update port from :50054 to :50053 (env.example is authoritative)

What would you like to do?
  1. Accept all proposed additions and inline edits
  2. Accept additions only (skip inline edits)
  3. Accept inline edits only (skip additions)
  4. Pick specific items (list numbers)
  5. Describe other change
```

5.3.5 On approval, apply edits in-place.

### 5.4 If ONLY .claude/CLAUDE.md EXISTS — fold-up-and-delete

This is the canonical case for wellmed-* code services as of 2026-05. The
rich content (ADRs, ULID rule, env vars, what-not-to-do) lives in
`.claude/CLAUDE.md`; root has nothing.

5.4.1 Read `$REPO_ROOT/.claude/CLAUDE.md`.

5.4.2 Run the §5.2 scaffold flow to draft a root CLAUDE.md, then fold
content from the existing `.claude/CLAUDE.md` into it section-by-section.

5.4.3 The folded root CLAUDE.md should:
- Preserve every load-bearing section from the original
- Add the trio-specific sections (archetype, cross-repo position, plans/
  memory pointers) it didn't have
- Open with a one-paragraph preamble noting the fold + delete of the old
  `.claude/CLAUDE.md`

5.4.4 Present proposal inline. On approval:
1. Write `$REPO_ROOT/CLAUDE.md`.
2. `git rm $REPO_ROOT/.claude/CLAUDE.md` (single canonical).
3. If `.claude/` directory is now empty (no `settings.local.json`, no
   `skills/`, no `logs/`), leave it — it may pick up other Claude Code
   artifacts. Don't `rmdir` it.

### 5.5 If BOTH EXIST — fold-both-into-root-and-delete-sidecar

The hybrid case. Often root is shallow (e.g., language preference + auto-
save rules) while `.claude/CLAUDE.md` has the rich service detail.
Sometimes the inverse (root is rich PMG-customized; sidecar is generic
upstream-inherited).

5.5.1 Read both files.

5.5.2 Identify which is the authoritative source (usually the longer one
with more service-specific content). Note any contradictions for explicit
user resolution.

5.5.3 Present a fold proposal showing what gets kept from each:

```
Root CLAUDE.md (N lines): KEEP sections X, Y (language preference, auto-save rules)
.claude/CLAUDE.md (M lines): KEEP sections A, B, C, D (ADRs, ULID, env vars, what-not-to-do)

Contradictions to resolve (1 found):
  - Port: root says :50053; .claude/ says :50054. env.example says :50054 — adopting that.

Proposed canonical root CLAUDE.md (N+M+trio lines):
  [preview structure]

Action plan:
  1. Write the merged canonical to repo root
  2. Delete .claude/CLAUDE.md (folded; no longer needed)
  3. Keep .claude/ directory (other artifacts may live there)

Approve? (numbered options)
```

5.5.4 On approval: write, delete, done. Single canonical achieved.

### 5.6 If repo is a stub (special case)

If §2.3 identified the repo as stub-only (single README, single main
branch, minimal commit history), produce a **stub CLAUDE.md** instead of
the standard scaffold:

- Lead with a clear STUB warning at the top
- Document the intended role (from ADRs / system architecture if known)
- Instruct future agents: "Do not assume any code exists. Do not fabricate
  implementation."
- Note where the actual work lives (uncommitted local? another branch?
  another team member?)
- Mark "refresh this trio when implementation lands" as the explicit
  follow-up.

See `<SKILL_DIR>/templates/CLAUDE.md.examples.md` for the stub archetype.

## 6. Step 4 — Idempotency Verification

After any write, re-run Steps 1, 2, and 3 read-only. If any reports drift,
something went wrong in the write — halt and tell the user. A healthy
/cross-repo-init run ends with all three files clean and a "no further
changes needed" status.

Also verify post-fold state:
- No `.claude/CLAUDE.md` if it was deleted in §5.4 / §5.5.
- No `wellmed-system-architecture.md` (or similar predecessor) at repo root
  if it was archived in §4.4.

## 7. Step 5 — Report

```
✅ /cross-repo-init complete for <REPO_NAME>

CROSS-REPO.md:   <SCAFFOLDED | UPDATED | HEALTHY (no change)>
  Pattern Sources: <N declared>
  Consumers: <N declared>
  Trunk archetype: <application-trunk | pattern-trunk | leaf | standalone | stub>

ARCHITECTURE.md: <SCAFFOLDED | UPDATED | HEALTHY (no change) | FOLDED-FROM-LONG-FORM>
  Components: <N>
  Lines: <N> / 200 budget  (or "system-root docs leaf — gate waived")
  Long-form archived to: <archive/path or "n/a">
  §6 Drift status: <empty (green check) | N rows>

CLAUDE.md:       <SCAFFOLDED | UPDATED | HEALTHY (no change) | FOLDED-FROM-SIDECAR>
  Location: $REPO_ROOT/CLAUDE.md (canonical)
  Stale .claude/CLAUDE.md: <deleted | absent | retained with reason>

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

7.4a **Always survey the right branch.** The checked-out branch is not the
truth. Pick `$SURVEY_BRANCH` per §2.2 cascade and run ALL auto-detection
against it via `git show` / `git ls-tree`, not `cat` / `ls`. Surface the
branch choice to the user in the Step 0 report so they can correct if
wrong. This rule was added 2026-05-11 after a kalpa-docs dogfood where
the adapter framework lived on `wellmed-infrastructure/develop` (built,
Phase 2 complete) but the checked-out `main` showed only observability
SDK files — auto-detection inferred zero adapter infrastructure when in
fact ~20+ domain adapters existed on develop.

7.4b **Always render §6 Drift.** Every ARCHITECTURE.md gets §6 (Current
Code State vs Target Architecture). If no drift surfaced, render the
green-check line (§2.3). The section's presence is the contract; the
table is empty only when justified.

7.5 **Skip third-party / inactive repos.** If the user invokes this in `~/Projects/gstack`,
`~/Projects/archive`, or any repo without a meaningful contract graph, ask them to
confirm before proceeding. These usually don't need CROSS-REPO.md.

7.6 **Workspace-relative paths in ARCHITECTURE.md Components.** Per /markdown-style §8.8.

7.7 **Templates path resolution.** Templates live at `<SKILL_DIR>/templates/`. The skill
dir is typically `~/Projects/ai-skills/cross-repo-init/` (symlinked into
`~/.claude/skills/cross-repo-init/`). If templates are not found, halt with a clear
message telling the user to check skill installation.

7.8 **Assess-first, don't sidecar-by-default.** When CLAUDE.md or
ARCHITECTURE.md already exists, the skill READS the existing file FIRST,
identifies what's worth preserving and what's missing relative to the trio
shape, and presents a targeted delta proposal — sections to add, inline
edits to apply. The skill does NOT default to writing a parallel sidecar
file (e.g., `CLAUDE.pmg.md` or `.claude/CLAUDE.md` while leaving the
existing root file untouched). Single canonical per repo. The fold
patterns in §5.3 / §5.4 / §5.5 are how this rule is operationalized for
CLAUDE.md; for ARCHITECTURE.md, §4.4 (long-form predecessor) is the
operative path. This rule was added 2026-05-11 after a wellmed-* cascade
revealed that nearly every code service had rich content in
`.claude/CLAUDE.md` and stale/shallow content at root — the right move was
fold-up-and-delete, not sidecar.

7.9 **Single canonical per repo.** Don't keep two architecture docs or
two CLAUDE.md files co-canonical — one will get stale. For long-form
architecture predecessors (e.g., `wellmed-system-architecture.md`),
archive to `archive/<name>-v<version>.md` after folding agent-critical
content into the new canonical. For CLAUDE.md sidecars (e.g.,
`.claude/CLAUDE.md`), delete after folding (no archive needed — CLAUDE.md
versions don't carry historical weight the way long-form ARCH docs do).

7.10 **Authoritative sources for service detail.** Several pieces of
service metadata are easy to get wrong if you trust an existing
`.claude/CLAUDE.md` over the actual code:
- **Ports**: grep `env.example` and any `internal/config/env.go` (or
  language equivalent). If they disagree with a `.claude/CLAUDE.md`,
  trust the env file. (2026-05-11 calibration: multiple wellmed-* repos
  had cashier and pharmacy ports swapped in their `.claude/CLAUDE.md`
  files; env.example was right.)
- **Module path**: grep `go.mod` / `package.json` / `composer.json`. Go
  module paths are case-sensitive and must be lowercase
  (`kalpa-health`, not `Kalpa-Health`) — see
  `memory/feedback_kalpa_health_lowercase.md`.
- **Branch survey**: §2.2 cascade, not the checked-out branch.

7.11 **Stub-repo detection.** If §2.3 surfaces stub-only signals
(repo has only `README.md` + `.gitignore`, only `main` branch, single
commit history, no source code), treat this as a special case:
- Use the stub-trio templates (CLAUDE.md.examples.md "Stub" archetype)
- Mark all three trio files explicitly with "STUB" warnings
- Document the intended role from ADRs / system architecture if known
- Instruct future agents not to fabricate implementation
- Make "refresh this trio when implementation lands" the explicit
  follow-up

Common cause of stub repos: the actual work lives uncommitted on someone's
local machine. Surface this in the trio so future agents understand the gap.

7.12 **`.gitignore *.md` audit.** During Step 0, scan `.gitignore` for any
rule that ignores markdown files broadly (`*.md`, `*.markdown`). If found,
surface it in the Step 0 report and propose removal — the trio files plus
all docs/ content should be tracked by default. (2026-05-11 calibration:
wellmed-backbone's `.gitignore` had `*.md` + `!README.md` rules that
blocked the trio commit until force-added; the rules were removed in a
follow-up commit.)

7.13 **Two-trunk-archetype awareness for WellMed-shaped systems.** Some
codebases have BOTH an **application trunk** (the main app where contracts
terminate) AND a **pattern trunk** (shared library / SDK / adapter
framework where patterns flow from). Example: WellMed = wellmed-backbone
(application trunk) + wellmed-infrastructure (pattern trunk). When
authoring CROSS-REPO.md for either, make the distinction explicit in the
archetype declaration and in §4 Notes — /closeout-extended needs to walk
both edges for full coverage.

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
