# CROSS-REPO.md — ai-skills

<!--
Purpose: declare this repo's place in the multi-repo graph for /plan and
/closeout-extended.

ai-skills is Alex's personal Claude Code skills repo. Its contracts are
SKILL.md frontmatter + template files consumed by Claude Code through
symlinks at `~/.claude/skills/<name>` -> `~/Projects/ai-skills/<name>`.
There is no compile-time or runtime contract graph the way pmg-integrations
or wellmed-infrastructure have one.

Maintenance: re-run /cross-repo-init when:
- A new external repo declares a hard dependency on patterns published here
- The repo gets reorganized (skills moved to subdirectories, etc.)
- A skill is retired/archived
-->

## Archetype

**Leaf in its own standalone graph.** ai-skills is not part of the PMG or
WellMed project graphs — it is a personal skills repo for Alex's Claude
Code installation. /closeout-extended will not traverse to ai-skills from
PMG/WellMed code repos; the relationship is operational (Claude Code reads
skills from this repo via symlinks), not contract-based.

## Trunk branch

- **main** — solo-dev repo (ak-devmode/ai-skills). Commits go direct to
  main per `feedback_branch_workflow.md`. No PR workflow.

## Pattern Sources

<!-- Skills here may follow conventions from each other (e.g. /closeout
     reuses /plan §12 archive logic), but those are intra-repo links — not
     cross-repo Pattern Sources. -->

(none — standalone leaf)

## Consumers

<!-- Claude Code installations consume skills here via symlinks. Not git
     repos under ~/Projects, so /closeout-extended cannot traverse to them. -->

(none in the contract graph — see Operational Consumers below)

### Operational Consumers (non-traversable)

- **`~/.claude/skills/`** — Claude Code's local skill directory. Each
  directory in this repo is symlinked into `~/.claude/skills/<name>`
  (e.g. `~/.claude/skills/plan` -> `~/Projects/ai-skills/plan`). Adding,
  renaming, or removing a skill directory here changes what Claude Code
  can invoke.
- **All projects Alex works in** — every Claude Code session in any repo
  inherits the skills published here. Changes to high-traffic skills
  (`/plan`, `/scope`, `/prd`, `/closeout`, `/markdown-style`) affect work
  across PMG, WellMed, and personal projects.

### Cross-skill reference notes

- **gstack skills** at `~/Projects/gstack/` (upstream `garrytan/gstack`)
  are a separate skills repo also symlinked into `~/.claude/skills/`. Some
  skills in ai-skills follow shared conventions (SKILL.md frontmatter,
  numbered inline questions, allowed-tools enumeration) but ai-skills
  does NOT derive code from gstack — they are independent.
- **kalpa/** subdirectory in this repo holds WellMed/Kalpa-project-specific
  skills (`/coding-standards`, `/generate-api`, `/kalpa-context`,
  `/migrate`, `/review`, `/satu-sehat-fhir`). These are personal-authored
  skills, not derived from kalpa-docs.

## Traversal Config

- max-depth-override: 0    <!-- standalone leaf; /closeout-extended doesn't traverse out -->
- trunk-branch: main

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
