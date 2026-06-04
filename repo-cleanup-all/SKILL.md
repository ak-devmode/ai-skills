---
name: repo-cleanup-all
version: 1.0.0
description: |
  Fleet-wide branch hygiene sweep. Thin alias for /repo-cleanup --all — classifies
  and prunes merged branches across every repo in a GitHub org/user. Exists so the
  sweep is autofill-discoverable without remembering the flag.
  Use when asked to "clean up all repos", "sweep the org for stale branches",
  "fleet branch cleanup", or "repo cleanup all".
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - AskUserQuestion
---

# /repo-cleanup-all — Fleet Branch Hygiene Sweep

This skill is an alias. **All logic, config, and safety rules live in
`../repo-cleanup/SKILL.md`** — read that file now and execute it in `--all` mode.

The only behavioral delta:

1. If the user named an owner (e.g. `/repo-cleanup-all kalpa-health`), pass it as
   `--all <owner>`.
2. If not, ask which configured owner to sweep (offer the owners from
   /repo-cleanup §1.1; multi-select allowed — sweep sequentially, one log section
   per repo, restoring the original gh account once at the very end).

Do not duplicate any classification, gating, or safety logic here. If this file
and /repo-cleanup ever disagree, /repo-cleanup wins.
