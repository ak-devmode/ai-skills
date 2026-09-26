# Review rules — Kalpa / PMG domain checks

Read by both `/review` executors — the codex gate and the Claude fallback (`review/SKILL.md` §2). Moved verbatim from `review/SKILL.md` §3 (v2.2.0) so the two cannot drift.

**Which groups apply** (from the repo path): WellMed `~/Projects/wellmed/*` → all groups · PMG `~/Projects/pmg/*` → §3.1, §3.5, §3.6, §3.7 (no SATU SEHAT, no ADR-028) · anything else → none (say so; do not invent domain checks).

## 3. Domain checks

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
