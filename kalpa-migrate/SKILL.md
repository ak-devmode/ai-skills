---
name: kalpa-migrate
description: "Generate a Prisma database migration with safety checks, rollback plan, and WellMed conventions."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# Generate Database Migration

Create a Prisma migration with proper safety checks and rollback plan.

## Arguments
- `$ARGUMENTS` - Description of the schema change (e.g., "add appointment status enum" or "add index on patient.nik")

## Process

1. **Analyze the change request**
   - Determine affected tables
   - Identify potential data migration needs
   - Check for breaking changes

2. **Update Prisma schema** (`prisma/schema.prisma`)
   - Make the schema changes
   - Add appropriate `@map` for snake_case column names
   - Include `@@index` for frequently queried fields

3. **Generate migration**
   ```bash
   pnpm prisma migrate dev --name {descriptive_name} --create-only
   ```

4. **Review generated SQL**
   - Check for destructive operations
   - Add data backfill if needed
   - Ensure indexes are created concurrently for large tables

5. **Create rollback script**
   - Place in `prisma/rollbacks/{migration_name}.sql`
   - Test rollback doesn't lose data

## Safety Rules

### Always
- Use `CREATE INDEX CONCURRENTLY` for production indexes
- Add `NOT NULL` with a `DEFAULT` first, then remove default
- Wrap data migrations in transactions
- Test on staging with production-like data volume

### Never
- Drop columns without 2-week deprecation period
- Rename tables (create new + migrate + drop old)
- Add `NOT NULL` to existing columns without default
- Run migrations during peak hours (9AM-6PM WIB)

## Template

```sql
-- Migration: {name}
-- Description: {description}
-- Author: {author}
-- Date: {date}

-- Safety check: Ensure no active transactions on affected tables
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
  AND query LIKE '%{table_name}%';

-- Main migration
BEGIN;

{migration_sql}

COMMIT;
```

## Rollback Template

```sql
-- Rollback: {name}
-- Review data implications before running

BEGIN;

{rollback_sql}

COMMIT;
```
