# Migration 0032: Schema Standardization Guide

**Date:** 2026-02-14  
**Migration:** 0032_schema_standardization_full.sql  
**Scope:** SQL DDL only (Python updates in separate PR)

---

## Overview

Migration 0032 implements comprehensive schema standardization based on the pre-flight inventory analysis. It uses two migration strategies:

1. **Safe drop/recreate** for tables with 0 rows
2. **Data-preserving migration** for tables with existing data

---

## Prerequisites

Before running this migration:

1. **Run pre-flight analysis:**
   ```sql
   -- Execute to assess current state
   :r db/migrations/0030_schema_standardization_preflight.sql
   ```

2. **Verify migration 0031 has been run:**
   ```sql
   SELECT * FROM dbo.__migration_log WHERE migration_id = '0031';
   ```

3. **Back up the database** (recommended for production):
   ```sql
   BACKUP DATABASE holocron TO DISK = '/backups/holocron_pre_0032.bak';
   ```

---

## How to Run

### Development Environment

```bash
# Using sqlcmd
sqlcmd -S localhost -d holocron -i db/migrations/0032_schema_standardization_full.sql -o migration_0032_output.txt

# Or using Azure Data Studio / SSMS
# Open the file and execute (F5)
```

### Production Environment

1. Schedule maintenance window
2. Notify stakeholders
3. Execute migration script
4. Verify output
5. Monitor application logs

---

## Migration Sections

| Section | Description | Strategy |
|---------|-------------|----------|
| 0 | Migration log table creation | Setup |
| 1 | GUID defaults (NEWSEQUENTIALID → NEWID) | In-place update |
| 2 | DimEvent → DimOccurrence rename | Rename (0 rows) |
| 3 | Column standardization (ExternalId → ExternalKey) | Add column + copy |
| 4 | Empty tables (BridgeEntityRelation, etc.) | Drop/recreate |
| 5 | Semantic views (dbo.sem_* → sem.vw_*) | Drop + recreate |
| 6 | DateTime/UTC analysis | Report only |
| 7 | Index updates | Create/update |
| 8 | Verification and summary | Validation |

---

## Expected Output

After successful execution, you should see:

```
============================================================================
FINAL STATUS COUNTS
============================================================================
status      step_count
----------- -----------
completed   XX
skipped     XX
failed      0

============================================================================
Migration 0032 Complete
============================================================================
```

### Verification Queries

```sql
-- Verify no dbo.sem_* views remain
SELECT name FROM sys.views 
WHERE schema_id = SCHEMA_ID('dbo') AND name LIKE 'sem_%';
-- Expected: 0 rows

-- Verify semantic views in sem schema
SELECT name FROM sys.views 
WHERE schema_id = SCHEMA_ID('sem') AND name LIKE 'vw_%';
-- Expected: 15+ rows

-- Verify no NEWSEQUENTIALID() for public GUIDs
SELECT OBJECT_NAME(dc.parent_object_id) AS TableName, c.name AS ColumnName
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
WHERE dc.definition LIKE '%NEWSEQUENTIALID%' AND c.name LIKE '%Guid';
-- Expected: 0 rows

-- Verify ExternalKey column exists
SELECT name FROM sys.columns 
WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalKey';
-- Expected: 1 row
```

---

## Rollback Procedure

If rollback is needed:

### Partial Rollback (column renames)
```sql
-- ExternalKey → ExternalId (if needed)
IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalKey')
BEGIN
    ALTER TABLE dbo.DimEntity DROP COLUMN ExternalKey;
END
```

### Full Rollback
Restore from backup taken before migration.

---

## Post-Migration Tasks

1. **Review migration log:**
   ```sql
   SELECT * FROM dbo.__migration_log WHERE migration_id = '0032' ORDER BY log_id;
   ```

2. **Address any failed steps:**
   - Check error messages in migration log
   - Run manual remediation as needed

3. **Update Python code (separate PR):**
   - Update column references: `ExternalId` → `ExternalKey`
   - Update view references: `dbo.sem_*` → `sem.vw_*`
   - Update table references: `DimEvent` → `DimOccurrence`

4. **Consider deprecation timeline:**
   - Old columns can be dropped after Python code update
   - Recommended: 2-week verification period

---

## Paste Execution Summary Here

After running the migration, paste the final output below for documentation:

```
[PASTE MIGRATION OUTPUT HERE]
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Resolution |
|-------|-------|------------|
| "Cannot rename column, referenced by constraint" | FK/index references | Drop constraints first, then rename |
| "View definition could not be parsed" | Complex view syntax | Manually recreate view in sem schema |
| "Timeout during execution" | Large table scan | Increase command timeout, run in batches |

### Getting Help

- Review migration log: `SELECT * FROM dbo.__migration_log`
- Check SQL Server error log
- Contact DBA team for production issues

---

## Related Documentation

- [db_policies.md](../agent/db_policies.md) - Naming conventions
- [schema_refactor_report.md](schema_refactor_report.md) - Full refactor details
- [python_sql_alignment_map](python_sql_alignment_map_2026-02-14.md) - Python/SQL mapping
