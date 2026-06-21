# Database Schema Change Workflow

This document describes the process for making schema changes in holocron-analytics. All agents and contributors must follow this workflow when modifying tables, columns, views, or other database objects.

---

## 1. Before Making Changes

### 1.1 Required Reading

Before proposing any schema change:

1. **Read naming conventions**: [DB_NAMING_CONVENTIONS.md](DB_NAMING_CONVENTIONS.md)
2. **Read review checklist**: [db_review_checklist.md](db_review_checklist.md)
3. **Check existing schema**: [schema_refactor_report.md](../db/schema_refactor_report.md)
4. **Use templates**: [db_templates.md](db_templates.md)

### 1.2 Pre-Change Questions

Ask yourself:

- [ ] Does this change follow naming conventions?
- [ ] Am I using the correct schema (`dbo`, `sem`, `llm`, `vector`, `ingest`)?
- [ ] Will this break existing code or queries?
- [ ] Is there existing data that needs migration?
- [ ] Do I need to update Python code in the same PR?

---

## 2. Types of Schema Changes

### 2.1 Non-Breaking Changes

These can typically be done directly:

| Change Type | Example | Notes |
|-------------|---------|-------|
| Add nullable column | `ALTER TABLE ... ADD NewCol VARCHAR(100) NULL` | No data migration needed |
| Add new table | `CREATE TABLE dbo.NewDim (...)` | Follow templates |
| Add new view | `CREATE VIEW sem.vw_new_view AS ...` | Follow naming |
| Add index | `CREATE INDEX IX_...` | Consider performance |

### 2.2 Breaking Changes

These require migration scripts:

| Change Type | Example | Migration Needed |
|-------------|---------|------------------|
| Rename column | `ExternalId` → `ExternalKey` | Copy data, update indexes |
| Rename table | `DimEvent` → `DimOccurrence` | Update all references |
| Change column type | `INT` → `BIGINT` | May need data copy |
| Drop column | Remove deprecated column | Verify no dependencies |
| Move view | `dbo.sem_*` → `sem.vw_*` | Recreate in new location |

---

## 3. Change Workflow

### 3.1 Step-by-Step Process

```
1. DOCUMENT
   └── What are you changing and why?
   
2. VALIDATE
   └── Run verify_schema_alignment.py (if available)
   └── Check naming conventions
   
3. IMPLEMENT
   └── DDL files (for new objects)
   └── Migration scripts (for changes)
   
4. TEST
   └── Run migration on test database
   └── Verify data integrity
   
5. UPDATE CODE
   └── Python code updates in same or follow-up PR
   
6. REVIEW
   └── Use db_review_checklist.md
   └── Get approval from maintainer
   
7. DEPLOY
   └── Run migration on production
   └── Monitor for issues
```

### 3.2 Migration Script Requirements

Every migration script must:

1. **Be idempotent** - Safe to run multiple times
2. **Include validation** - Verify success
3. **Handle errors gracefully** - Don't leave partial state
4. **Document the change** - Clear comments explaining why

---

## 4. Column Rename Pattern

When renaming a column (e.g., `ExternalId` → `ExternalKey`):

### Step 1: Add New Column
```sql
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'ExternalKey'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] ADD ExternalKey NVARCHAR(200) NULL;
    PRINT 'Added column: ExternalKey';
END
```

### Step 2: Copy Data
```sql
UPDATE [dbo].[DimEntity]
SET ExternalKey = ExternalId
WHERE ExternalId IS NOT NULL
  AND ExternalKey IS NULL;
```

### Step 3: Create New Index
```sql
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_DimEntity_ExternalKey_IsLatest')
BEGIN
    CREATE UNIQUE INDEX UX_DimEntity_ExternalKey_IsLatest
    ON [dbo].[DimEntity](ExternalKey)
    WHERE ExternalKey IS NOT NULL AND IsLatest = 1;
END
```

### Step 4: Add Deprecation Notice
```sql
EXEC sys.sp_addextendedproperty 
    @name = N'MS_Description',
    @value = N'DEPRECATED: Use ExternalKey instead.',
    @level0type = N'SCHEMA', @level0name = 'dbo',
    @level1type = N'TABLE', @level1name = 'DimEntity',
    @level2type = N'COLUMN', @level2name = 'ExternalId';
```

### Step 5: Update Python (Separate PR or Same PR)
```python
# OLD
external_id = row['ExternalId']

# NEW
external_key = row['ExternalKey']
```

### Step 6: Drop Old Column (Later, After Verification)
```sql
-- Only after confirming all code uses new column
ALTER TABLE [dbo].[DimEntity] DROP COLUMN ExternalId;
```

---

## 5. Table Rename Pattern

When renaming a table (e.g., `DimEvent` → `DimOccurrence`):

### Step 1: Rename Table
```sql
EXEC sp_rename 'dbo.DimEvent', 'DimOccurrence';
```

### Step 2: Rename Primary Key
```sql
EXEC sp_rename 'dbo.PK_DimEvent', 'PK_DimOccurrence', 'OBJECT';
```

### Step 3: Rename Indexes
```sql
EXEC sp_rename 'dbo.DimOccurrence.IX_DimEvent_Type', 'IX_DimOccurrence_Type', 'INDEX';
```

### Step 4: Update Foreign Keys
```sql
ALTER TABLE [dbo].[BridgeEntityEvent] DROP CONSTRAINT FK_BridgeEntityEvent_Event;
ALTER TABLE [dbo].[BridgeEntityEvent] ADD CONSTRAINT FK_BridgeEntityOccurrence_Occurrence
    FOREIGN KEY (OccurrenceKey) REFERENCES [dbo].[DimOccurrence](OccurrenceKey);
```

### Step 5: Update Views
Update all views that reference the old table name.

---

## 6. View Move Pattern

When moving a view (e.g., `dbo.sem_event` → `sem.vw_event`):

### Step 1: Get View Definition
```sql
DECLARE @def NVARCHAR(MAX);
SELECT @def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_event]'));
```

### Step 2: Drop Old View
```sql
DROP VIEW [dbo].[sem_event];
```

### Step 3: Create New View
```sql
SET @def = REPLACE(@def, 'dbo.sem_event', 'sem.vw_event');
EXEC(@def);
```

---

## 7. Testing Changes

### 7.1 Pre-Migration Testing

```bash
# Backup database
# Run migration on test instance
# Verify data integrity
# Run Python tests
```

### 7.2 Post-Migration Verification

```sql
-- Verify row counts match
SELECT COUNT(*) FROM [dbo].[Table] WHERE OldColumn IS NOT NULL;
SELECT COUNT(*) FROM [dbo].[Table] WHERE NewColumn IS NOT NULL;

-- Verify constraints exist
SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('[dbo].[Table]');

-- Verify data integrity
SELECT TOP 100 OldColumn, NewColumn FROM [dbo].[Table]
WHERE OldColumn <> NewColumn OR (OldColumn IS NULL XOR NewColumn IS NULL);
```

---

## 8. Documentation Requirements

Every schema change must update:

1. **DDL file** (if adding/modifying table): `src/db/ddl/`
2. **DML file** (if adding/modifying stored procedure, function, or trigger): `src/db/dml/`
3. **View file** (if adding/modifying view): `src/db/views/{schema}/`
4. **Migration script** (if changing existing object): `db/migrations/`
5. **Schema documentation** (if significant change): `docs/db/`
6. **Agent documentation** (if new patterns): `docs/agent/`

> **Important:** Both the migration script AND the canonical definition file must be updated.
> See [SQL_SYNC_POLICY.md](SQL_SYNC_POLICY.md) for the full synchronization policy.

---

## 9. Rollback Planning

Before running any migration:

1. **Document the rollback steps** - How to undo the change
2. **Create backup** (for tables with data)
3. **Test rollback** on test environment
4. **Have a plan** for partial failures

---

## Quick Reference

```
WORKFLOW:
  1. Read conventions
  2. Design change
  3. Write migration (idempotent)
  4. Update canonical definition (ddl/ dml/ views/)
  5. Test on local
  6. Update Python (same or follow-up PR)
  7. Review with checklist
  8. Deploy
  
MIGRATION FILES:
  db/migrations/XXXX_description.sql
  
DDL FILES (tables, schemas, types):
  src/db/ddl/{layer}/{NNN}_{TableName}.sql

DML FILES (stored procedures, functions, triggers):
  src/db/dml/stored_procedures/{schema}.{name}.sql
  src/db/dml/functions/{schema}.{name}.sql
  src/db/dml/triggers/{schema}.{name}.sql

VIEW FILES:
  src/db/views/{schema}/{schema}.{name}.sql
  
VERIFICATION:
  scripts/verify_schema_alignment.py

EXTRACTION & RECONCILIATION:
  scripts/db/extract_sql_objects.py --extract --reconcile --verbose

SYNC POLICY:
  docs/agent/SQL_SYNC_POLICY.md
```
