---
name: review
version: 2.0.0
description: |
  Pre-landing code review in two passes: gstack's review engine for generic
  correctness, security, and diff quality, then a Kalpa/PMG domain pass that a
  generic reviewer cannot know about — SATU SEHAT + FHIR, ADR conformance, table
  write-ownership, tenant isolation, PHI/credential leakage, and the stack-specific
  footguns. Findings from both passes merge into one ranked report.

  Use when asked to "review", "review this PR", "review the diff", "pre-landing
  review", "check my diff before merge", or before opening any PR. Also invoked by
  /scope's skill checklist (Review & QA) and as /plan's pre-merge gate.

  Runs both passes by default. `--kalpa-only` skips the gstack engine when you want
  the fast domain check; `--engine-only` skips the domain pass for non-Kalpa repos.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# /review — Two-Pass Pre-Landing Review

Supersedes the old `kalpa/review` skill, which was invisible: it lived in a
container directory with no `SKILL.md`, so it never registered, and the bare name
`/review` resolved to gstack's. This skill takes the name and uses both.

**Reuse, don't reimplement.** gstack's review engine is ~1,850 lines with its own
specialists, checklists, and triage. This skill never duplicates any of it — Pass 1
reads that skill and follows it. Pass 2 is the layer gstack structurally cannot
have, because it depends on ADRs and production history that live in Alex's repos.

---

## 1. Resolve Scope and Project

1.1 **Review target**, in priority order: an explicit argument (PR number, branch,
path, or `staged`) → the current branch's diff against its trunk → the working-tree
diff. Never review a bare `HEAD` when a branch diff is available; the branch diff is
what lands.

1.2 **Project**, from the repo path — this selects which Pass 2 groups apply:

| Path | Project | Pass 2 |
|---|---|---|
| `~/Projects/wellmed/*` | WellMed / Kalpa | all groups |
| `~/Projects/pmg/*` | PMG | groups 3.1, 3.5, 3.6, 3.7 (no SATU SEHAT, no ADR-028) |
| anything else | generic | Pass 2 skipped — say so, don't invent domain checks |

1.3 **Read the project's own canon before reviewing** — per `/plan` §1.1, probing to
discover what a doc records is a defect. Repo `CLAUDE.md` (conventions, build/test,
gotchas), `ARCHITECTURE.md`, and for WellMed the ADR index at `kalpa-docs/adrs/`.
These decide what "correct" means here; a finding that contradicts an accepted ADR
is a finding about the ADR, and must say so.

---

## 2. Pass 1 — gstack Review Engine

2.1 Read `~/.claude/skills/gstack/review/SKILL.md` and execute it against the
resolved target. That path is the gstack repo root symlink, which is stable
regardless of which skill owns the bare `/review` name — do not reach for
`~/.claude/skills/review`, which is this skill.

2.2 Skip Pass 1 entirely on `--kalpa-only`. Note the skip in the report header —
never let a domain-only run read as a full review.

2.3 **One deviation from the engine's interaction style:** render every decision as
numbered inline options answered by number. `AskUserQuestion` is banned in
ai-skills-authored skills (`ai-skills/CLAUDE.md` §3.2), and this skill owns the
invocation.

2.4 Capture the engine's findings for the merge in §4. Do not re-rank them yet.

---

## 3. Pass 2 — Kalpa / PMG Domain Checks

Each group below is a class of defect that has actually shipped. Check only what the
diff touches — a group with no surface in the diff is reported as `n/a`, not as
passing. Cite `file:line` for every finding.

### 3.1 Secrets and PHI in logs

The recurring shape is a log line that is correct in structure and catastrophic in
content. Check every added or modified log/print/trace statement for: credentials in
a connection string (`amqp://user:pass@host`, DSNs), request bodies echoed from an
upstream, patient identifiers (NIK, IHS ID, names, DOB), and full auth payloads.

**Do not assume a sibling service redacts.** Redaction is per-service, and at least
one WellMed service logs a full broker URL with password at Info level while its
siblings redact. A new service copying a sibling's logger inherits nothing.

### 3.2 SATU SEHAT and FHIR (WellMed only)

- Every patient-data path carries **NIK**; IHS ID resolution has a miss path that
  fails closed, not silently.
- **ICD-10 codes, never ranges.** A range where a code belongs is a validation
  rejection at the gateway, not a local error — it is the single largest cause of
  rejected bundles.
- Bundle structure matches the resource profiles; bundle size within limits.
- **Environment is explicit.** Staging is `api-satusehat-stg.kemkes.go.id`; a
  hardcoded prod host in a non-prod path is a finding.
- OAuth tokens expire in 1 hour — any new client has refresh, and refresh is
  single-flight if it can be called concurrently.

### 3.3 Table write-ownership (WellMed, ADR-028)

Any migration, DDL, `AutoMigrate`, ORM model change, or new write path: confirm the
writing service is the table's declared owner. A write that crosses an owner
boundary is an ADR-028 amendment, not a code change — flag it as a design finding
and name the ADR.

For a table defined in two repos, confirm the definitions stayed column-identical.
A drift between dual-defined tables is silent until it isn't.

### 3.4 Canonical record placement (WellMed, ADR-018)

New clinical records land in the canonical home the ADR names, not wherever the
touching service is convenient. Writing a canonical record into the wrong service is
cheap now and a migration later.

### 3.5 Tenant and workspace isolation

Every query on shared tables filters by the tenant discriminator the schema
actually populates. Check the column is non-NULL in practice before trusting it as a
filter — a filter on a universally-NULL column returns zero rows with no error,
which reads as "no data" rather than "broken query."

### 3.6 Stack footguns

| Check | Why |
|---|---|
| Go module paths lowercase | Paths are case-sensitive; mixed case breaks import resolution |
| No ORM full-struct `Save()` on app-generated IDs | Zeroes `created_at` on rows whose ID was not DB-assigned |
| Status enum casing matches the repo convention | UPPERCASE or Title, never lowercase |
| Timezone handling matches the current phase of the offset migration | The FE and the DB disagree mid-migration; a write that assumes the end state shifts every displayed time |
| Parameterized queries | Kept only because a raw-SQL builder is the one place it still happens |

### 3.7 Contract cascade

If the diff touches a `.proto`, schema, OpenAPI spec, or event payload: name every
consumer that must regenerate or update, and confirm each is either in this change
or explicitly deferred with a named follow-up. A contract change whose consumers are
unlisted is incomplete, not done.

### 3.8 Test and doc surface

New behavior has a test; a bug fix has a regression test that fails without the fix.
If the change alters something the repo `CLAUDE.md` or `ARCHITECTURE.md` states,
the doc edit is part of this change.

---

## 4. Merge and Report

4.1 Merge both passes into one ranked list. Deduplicate: when the engine and the
domain pass find the same defect, keep the domain finding — it carries the ADR or
production context that makes it actionable — and note the engine agreed.

4.2 Rank by consequence, not by pass or category:

```
  BLOCKING    ships a defect: data loss, PHI/credential exposure, contract break,
              owner-boundary violation, rejected-bundle cause
  SHOULD FIX  correctness or maintainability cost that survives the merge
  NOTE        judgment calls, style, and things worth knowing but not fixing here
```

4.3 Output:

```
/review — {repo} @ {branch}  ({N} files, +{added}/-{removed})
Passes: gstack engine {✓|SKIPPED} · Kalpa domain {✓|SKIPPED|n/a — generic repo}

BLOCKING ({n})
  1. {file:line} — {defect}. {consequence}. {fix}

SHOULD FIX ({n})
  2. {file:line} — {defect} → {fix}

NOTE ({n})
  3. {file:line} — {observation}

Checked and clear: {group list}
Not applicable: {group list, each with the one-word reason}

Verdict: {SHIP | SHIP AFTER BLOCKING | DO NOT SHIP} — {one sentence}
```

4.4 **`Not applicable` is not `clear`.** A group with no surface in the diff and a
group verified clean are different results, and collapsing them is how a review
overstates its coverage. Same reason `/closeout` says "HEALED (ledger-less)" rather
than "HEALED."

---

## 5. Behaviors

5.1 **Never commit, never push, never open the PR.** This skill reports. Landing is
`git`, by hand, after the user reads the verdict.

5.2 **Never fix in-band by default.** Findings are reported with the fix named, not
applied — the diff under review must stay the diff that was written. On an explicit
"fix them" (or `--fix`), apply them and re-report, splitting fixed from
not-fixed.

5.3 **Cite `file:line` or don't raise it.** An uncitable finding is a hunch, and a
reviewer's hunch costs more attention than it saves.

5.4 **A finding against an accepted ADR is a finding about the ADR.** Say which ADR,
and route it as a design decision rather than a code fix.

5.5 **Numbered inline questions only.** Never `AskUserQuestion` — including inside
the Pass 1 invocation (§2.3).

5.6 **Report the cost when it's high.** Pass 1 loads a large engine. If the user
asked for a quick look, say that `--kalpa-only` exists rather than silently
spending the context.
