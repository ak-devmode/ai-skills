# Scope 9 — notes export (verifier fixture)

## 4.1 Phase 1 — export (unit 9.9)
- `notes.export.export_text()` returns every note, newline-joined.
- The export bucket is read from `NOTES_EXPORT_BUCKET`, as declared in `.env.example`.
- Keep it simple: one function. No plugin system, registry or exporter abstraction — there
  is exactly one export format and no second one planned.
- Document the export in `CHANGELOG.md` under `## Unreleased`.
