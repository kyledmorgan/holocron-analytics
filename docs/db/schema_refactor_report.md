# Schema Refactor Report

**Date:** 2026-02-14  
**Migration:** 0030-0031  
**Scope:** SQL DDL and migration scripts only  

This document summarizes the schema standardization changes to support the next PR (Python reconciliation).

---

## Executive Summary

This refactor standardizes the holocron-analytics database schema to use consistent naming conventions, key patterns, and datetime handling. The changes are implemented as idempotent migration scripts that can be run against existing databases.

### Key Changes

1. **GUID defaults changed** from `NEWSEQUENTIALID()` to `NEWID()` for security
2. **External ID columns renamed** from `ExternalId` to `ExternalExtKey`
3. **DimEvent renamed** to `DimOccurrence` to avoid semantic collision with `FactEvent`
4. **Semantic views moved** from `dbo.sem_*` to `sem.vw_*`
5. **Timestamp standards** enforced: `DATETIME2(3)`, `SYSUTCDATETIME()`, `*Utc` suffix

---

## 1. Object Renames

### 1.1 Table Renames

| Old Name | New Name | Reason |
|----------|----------|--------|
| `dbo.DimEvent` | `dbo.DimOccurrence` | Avoid semantic collision with `FactEvent` |
| `dbo.BridgeEntityEvent` | `dbo.BridgeEntityOccurrence` | Follow parent table rename |

### 1.2 View Renames (Schema Move + Name Change)

| Old Name | New Name | Reason |
|----------|----------|--------|
| `dbo.sem_event` | `sem.vw_event` | Semantic views belong in `sem` schema |
| `dbo.sem_character` | `sem.vw_character` | Semantic views belong in `sem` schema |
| `dbo.sem_species` | `sem.vw_species` | Semantic views belong in `sem` schema |
| `dbo.sem_organization` | `sem.vw_organization` | Semantic views belong in `sem` schema |
| `dbo.sem_location` | `sem.vw_location` | Semantic views belong in `sem` schema |
| `dbo.sem_event_asset` | `sem.vw_event_asset` | Semantic views belong in `sem` schema |
| `dbo.sem_event_participant` | `sem.vw_event_participant` | Semantic views belong in `sem` schema |
| `dbo.sem_franchise` | `sem.vw_franchise` | Semantic views belong in `sem` schema |
| `dbo.sem_work` | `sem.vw_work` | Semantic views belong in `sem` schema |
| `dbo.sem_scene` | `sem.vw_scene` | Semantic views belong in `sem` schema |
| `dbo.sem_continuity_frame` | `sem.vw_continuity_frame` | Semantic views belong in `sem` schema |
| `dbo.sem_tech_asset` | `sem.vw_tech_asset` | Semantic views belong in `sem` schema |
| `dbo.sem_tech_instance` | `sem.vw_tech_instance` | Semantic views belong in `sem` schema |
| `dbo.sem_appearance_look` | `sem.vw_appearance_look` | Semantic views belong in `sem` schema |
| `dbo.sem_claim` | `sem.vw_claim` | Semantic views belong in `sem` schema |
| `dbo.sem_continuity_issue` | `sem.vw_continuity_issue` | Semantic views belong in `sem` schema |
| `dbo.sem_issue_claim_link` | `sem.vw_issue_claim_link` | Semantic views belong in `sem` schema |
| `dbo.vw_TagAssignments` | `sem.vw_tag_assignments` | Tag assignments are semantic |

---

## 2. Column Renames

### 2.1 External ID Columns

| Table | Old Column | New Column | Type | Notes |
|-------|------------|------------|------|-------|
| `dbo.DimEntity` | `ExternalId` | `ExternalExtKey` | `NVARCHAR(200)` | External source system ID |
| `dbo.DimEntity` | `ExternalIdType` | `ExternalExtKeyType` | `NVARCHAR(50)` | Type of external ID |

### 2.2 Batch ID Columns

| Table | Old Column | New Column | Type | Notes |
|-------|------------|------------|------|-------|
| `dbo.DimEntity` | `IngestBatchId` | `IngestBatchKey` | `NVARCHAR(100)` | Batch tracking |
| `dbo.FactEvent` | `IngestBatchId` | `IngestBatchKey` | `NVARCHAR(100)` | Batch tracking |
| *(all tables with IngestBatchId)* | `IngestBatchId` | `IngestBatchKey` | `NVARCHAR(100)` | Convention standardization |

### 2.3 DimEvent → DimOccurrence Columns

| Old Column | New Column | Notes |
|------------|------------|-------|
| `EventId` | `OccurrenceGuid` | Primary GUID |
| `EventName` | `OccurrenceName` | Display name |
| `EventType` | `OccurrenceType` | Type classification |

---

## 3. Data Type Changes

### 3.1 GUID Default Changes

| Table | Column | Old Default | New Default | Reason |
|-------|--------|-------------|-------------|--------|
| `dbo.DimEntity` | `EntityGuid` | `NEWSEQUENTIALID()` | `NEWID()` | Security: sequential reveals row count |
| `dbo.FactEvent` | `FactEventGuid` | `NEWSEQUENTIALID()` | `NEWID()` | Security: sequential reveals row count |

### 3.2 Timestamp Type Standardization

All timestamp columns should use:
- Type: `DATETIME2(3)` (millisecond precision)
- Default: `SYSUTCDATETIME()`
- Suffix: `Utc` (e.g., `CreatedUtc`, `UpdatedUtc`)

---

## 4. Breaking Changes

### 4.1 Column Name Changes

Code referencing these columns must be updated:

| Table | Old Column | New Column | Impact |
|-------|------------|------------|--------|
| `DimEntity` | `ExternalId` | `ExternalExtKey` | Update all SELECTs, INSERTs, stored procs |
| `DimEntity` | `ExternalIdType` | `ExternalExtKeyType` | Update all SELECTs, INSERTs, stored procs |

**Migration strategy:** Both columns exist during transition. Old column kept for compatibility with deprecation notice.

### 4.2 Table/View Name Changes

Code referencing these objects must be updated:

| Old Object | New Object | Impact |
|------------|------------|--------|
| `dbo.DimEvent` | `dbo.DimOccurrence` | Update table references |
| `dbo.sem_*` views | `sem.vw_*` | Update view references |

### 4.3 Mapping Old Names to New Names

```python
# Python column mapping
COLUMN_RENAMES = {
    'ExternalId': 'ExternalExtKey',
    'ExternalIdType': 'ExternalExtKeyType',
    'IngestBatchId': 'IngestBatchKey',
}

# Python view mapping
VIEW_RENAMES = {
    'dbo.sem_event': 'sem.vw_event',
    'dbo.sem_character': 'sem.vw_character',
    # ... etc
}
```

---

## 5. Index Changes

### 5.1 Renamed Indexes

| Old Index | New Index | Table |
|-----------|-----------|-------|
| `UX_DimEntity_ExternalId_IsLatest` | `UX_DimEntity_ExternalExtKey_IsLatest` | `DimEntity` |
| `IX_DimEvent_EventType` | `IX_DimOccurrence_OccurrenceType` | `DimOccurrence` |
| `IX_DimEvent_EventName` | `IX_DimOccurrence_OccurrenceName` | `DimOccurrence` |

### 5.2 New Indexes

| Index | Table | Columns |
|-------|-------|---------|
| `UX_DimEntity_ExternalExtKey_IsLatest` | `DimEntity` | `ExternalExtKey` (filtered) |

---

## 6. Constraint Changes

### 6.1 Renamed Constraints

| Old Constraint | New Constraint | Type |
|----------------|----------------|------|
| `PK_DimEvent` | `PK_DimOccurrence` | Primary Key |
| `FK_BridgeEntityEvent_Event` | `FK_BridgeEntityOccurrence_Occurrence` | Foreign Key |

### 6.2 Modified Default Constraints

| Constraint | Old Definition | New Definition |
|------------|----------------|----------------|
| `DF_DimEntity_EntityGuid` | `NEWSEQUENTIALID()` | `NEWID()` |
| `DF_FactEvent_FactEventGuid` | `NEWSEQUENTIALID()` | `NEWID()` |

---

## 7. Runtime Reconciliation Findings

### 7.1 DDL vs Runtime Comparison

After running migrations, the repo DDL should match runtime. Known differences to resolve:

| Object | DDL State | Runtime State | Resolution |
|--------|-----------|---------------|------------|
| `dbo.DimEntity.ExternalId` | Deprecated | May exist | Keep during transition |
| `dbo.DimEntity.ExternalExtKey` | Added | May not exist | Migration adds it |
| `dbo.sem_*` views | Dropped | May exist | Migration moves to `sem.vw_*` |

### 7.2 Recommended Verification Queries

After running migrations, verify with:

```sql
-- Verify no dbo.sem_* views remain
SELECT name FROM sys.views WHERE schema_id = SCHEMA_ID('dbo') AND name LIKE 'sem_%';
-- Expected: 0 rows

-- Verify semantic views exist in sem schema
SELECT name FROM sys.views WHERE schema_id = SCHEMA_ID('sem') AND name LIKE 'vw_%';
-- Expected: 15+ rows

-- Verify GUID defaults
SELECT t.name, c.name, dc.definition
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
WHERE c.name LIKE '%Guid' AND dc.definition LIKE '%NEWSEQUENTIALID%';
-- Expected: 0 rows (no sequential GUIDs)
```

---

## 8. Migration Files

| Migration | Description |
|-----------|-------------|
| `0030_schema_standardization_preflight.sql` | Pre-flight checks and row counts |
| `0031_schema_standardization.sql` | Main standardization migration |

### Migration Execution Order

1. Run `0030_schema_standardization_preflight.sql` to assess current state
2. Review output and identify tables with data
3. Run `0031_schema_standardization.sql` to apply changes
4. Verify with reconciliation queries above

---

## 9. Next Steps (Python Reconciliation)

The following Python files need updates in the next PR:

### 9.1 Database Access Code

- Update column references: `ExternalId` → `ExternalExtKey`
- Update view references: `dbo.sem_*` → `sem.vw_*`
- Update table references: `DimEvent` → `DimOccurrence`

### 9.2 ORM/Model Updates

- Update column mappings in SQLAlchemy models (if used)
- Update Pydantic models for schema validation
- Update any column name constants

### 9.3 Files to Review

```
src/db/
src/llm/storage/
src/vector/store.py
src/ingest/
```

---

## 10. Documentation Updates

The following documentation was created/updated:

| Document | Purpose |
|----------|---------|
| `docs/agent/README.md` | Agent entry point |
| `docs/agent/db_policies.md` | Canonical naming/key/datetime rules |
| `docs/agent/db_templates.md` | Copy-paste templates |
| `docs/agent/db_review_checklist.md` | PR review checklist |
| `docs/db/schema_refactor_report.md` | This document |

---

## Appendix A: Full Column Rename Reference

### All `...Id` → `...Key/Guid/ExtKey` Changes

| Table | Old Column | New Column | Reason |
|-------|------------|------------|--------|
| `dbo.DimEntity` | `ExternalId` | `ExternalExtKey` | External source ID |
| `dbo.DimEntity` | `ExternalIdType` | `ExternalExtKeyType` | Type qualifier |
| `dbo.DimEntity` | `IngestBatchId` | `IngestBatchKey` | Batch reference |
| `dbo.FactEvent` | `IngestBatchId` | `IngestBatchKey` | Batch reference |
| `dbo.DimOccurrence` | `EventId` | `OccurrenceGuid` | Table renamed |

### Columns Kept (Already Compliant)

| Table | Column | Reason |
|-------|--------|--------|
| `dbo.DimEntity` | `EntityKey` | Correct pattern |
| `dbo.DimEntity` | `EntityGuid` | Correct pattern |
| `dbo.FactEvent` | `EventKey` | Correct pattern |
| `dbo.FactEvent` | `FactEventGuid` | Correct pattern |
