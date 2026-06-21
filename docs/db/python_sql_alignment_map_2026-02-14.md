# Python / SQL Alignment Map

**Generated:** 2026-02-14  
**Purpose:** Reference mapping from old naming conventions to standardized patterns  
**Status:** Active reconciliation document for Python + SQL updates

---

## 1. Column Renames

### 1.1 External ID Columns

| Table | Old Column | New Column | Python Var | Notes |
|-------|------------|------------|------------|-------|
| `dbo.DimEntity` | `ExternalId` | `ExternalKey` | `external_key` | External source system ID |
| `dbo.DimEntity` | `ExternalIdType` | `ExternalKeyType` | `external_key_type` | Type of external ID |

### 1.2 Batch ID Columns

| Table | Old Column | New Column | Python Var | Notes |
|-------|------------|------------|------------|-------|
| `dbo.DimEntity` | `IngestBatchId` | `IngestBatchKey` | `ingest_batch_key` | Batch tracking |
| `dbo.FactEvent` | `IngestBatchId` | `IngestBatchKey` | `ingest_batch_key` | Batch tracking |
| *(all tables)* | `IngestBatchId` | `IngestBatchKey` | `ingest_batch_key` | Convention |

### 1.3 DimEvent → DimOccurrence Columns

| Old Column | New Column | Python Var | Notes |
|------------|------------|------------|-------|
| `EventId` | `OccurrenceGuid` | `occurrence_guid` | Primary GUID |
| `EventName` | `OccurrenceName` | `occurrence_name` | Display name |
| `EventType` | `OccurrenceType` | `occurrence_type` | Classification |

---

## 2. Table/View Renames

### 2.1 Table Renames

| Old Name | New Name | Python Class | Notes |
|----------|----------|--------------|-------|
| `dbo.DimEvent` | `dbo.DimOccurrence` | `DimOccurrence` | Avoid collision with FactEvent |
| `dbo.BridgeEntityEvent` | `dbo.BridgeEntityOccurrence` | `BridgeEntityOccurrence` | Follow parent |

### 2.2 View Renames (dbo → sem)

| Old Name | New Name | Notes |
|----------|----------|-------|
| `dbo.sem_event` | `sem.vw_event` | Semantic views in sem schema |
| `dbo.sem_character` | `sem.vw_character` | |
| `dbo.sem_species` | `sem.vw_species` | |
| `dbo.sem_organization` | `sem.vw_organization` | |
| `dbo.sem_location` | `sem.vw_location` | |
| `dbo.sem_event_asset` | `sem.vw_event_asset` | |
| `dbo.sem_event_participant` | `sem.vw_event_participant` | |
| `dbo.sem_franchise` | `sem.vw_franchise` | |
| `dbo.sem_work` | `sem.vw_work` | |
| `dbo.sem_scene` | `sem.vw_scene` | |
| `dbo.sem_continuity_frame` | `sem.vw_continuity_frame` | |
| `dbo.sem_tech_asset` | `sem.vw_tech_asset` | |
| `dbo.sem_tech_instance` | `sem.vw_tech_instance` | |
| `dbo.sem_appearance_look` | `sem.vw_appearance_look` | |
| `dbo.sem_claim` | `sem.vw_claim` | |
| `dbo.sem_continuity_issue` | `sem.vw_continuity_issue` | |
| `dbo.sem_issue_claim_link` | `sem.vw_issue_claim_link` | |
| `dbo.vw_TagAssignments` | `sem.vw_tag_assignments` | Tag assignments are semantic |

---

## 3. Data Type Standards

### 3.1 Key Patterns

| Pattern | SQL Type | Python Type | Usage |
|---------|----------|-------------|-------|
| `...Key` | `INT` (dim) / `BIGINT` (fact) | `int` | Internal surrogate keys |
| `...Guid` | `UNIQUEIDENTIFIER` | `uuid.UUID` | Public stable identifiers |
| `...ExtKey` | `INT` / `NVARCHAR` | `int` / `str` | External numeric IDs |
| `...NaturalKey` | `NVARCHAR` | `str` | External text IDs |

### 3.2 Timestamp Patterns

| Pattern | SQL Type | SQL Default | Python Type | Notes |
|---------|----------|-------------|-------------|-------|
| `...Utc` | `DATETIME2(3)` | `SYSUTCDATETIME()` | `datetime` (UTC-aware) | All timestamps |
| `CreatedUtc` | `DATETIME2(3)` | `SYSUTCDATETIME()` | `datetime` | Record creation |
| `UpdatedUtc` | `DATETIME2(3)` | `NULL` | `datetime` / `None` | Last modification |
| `ValidFromUtc` | `DATETIME2(3)` | `SYSUTCDATETIME()` | `datetime` | SCD Type 2 start |
| `ValidToUtc` | `DATETIME2(3)` | `NULL` | `datetime` / `None` | SCD Type 2 end |

### 3.3 GUID Security

| Pattern | Correct Default | Incorrect Default | Notes |
|---------|-----------------|-------------------|-------|
| `...Guid` | `NEWID()` | `NEWSEQUENTIALID()` | Sequential reveals creation order |

---

## 4. Python Code Search Patterns

Use these grep patterns to find code needing updates:

```bash
# Find old external ID references
grep -rn "ExternalId" src/
grep -rn "external_id" src/
grep -rn "IngestBatchId" src/
grep -rn "ingest_batch_id" src/

# Find old table references  
grep -rn "DimEvent\b" src/
grep -rn "BridgeEntityEvent" src/

# Find old view references
grep -rn "dbo\.sem_" src/
grep -rn "sem_event" src/

# Find potential datetime issues
grep -rn "datetime\.now()" src/  # Should use datetime.now(timezone.utc)
grep -rn "GETDATE()" src/        # Should use SYSUTCDATETIME()
```

---

## 5. Python Variable Naming Conventions

### 5.1 Database Column → Python Variable

| Database Column | Python Variable | Type Hint |
|----------------|-----------------|-----------|
| `EntityKey` | `entity_key` | `int` |
| `EntityGuid` | `entity_guid` | `uuid.UUID` |
| `ExternalKey` | `external_key` | `str` |
| `ExternalKeyType` | `external_key_type` | `str` |
| `IngestBatchKey` | `ingest_batch_key` | `str` |
| `CreatedUtc` | `created_utc` | `datetime` |
| `UpdatedUtc` | `updated_utc` | `Optional[datetime]` |

### 5.2 Python to SQL Parameter Binding

```python
# Correct UUID binding for pyodbc
cursor.execute(
    "INSERT INTO dbo.DimEntity (EntityGuid, ...) VALUES (?, ...)",
    (str(entity_guid), ...)  # Convert UUID to string for pyodbc
)

# Correct UTC datetime binding
from datetime import datetime, timezone
now_utc = datetime.now(timezone.utc)
cursor.execute(
    "INSERT INTO ... (CreatedUtc) VALUES (?)",
    (now_utc,)  # pyodbc handles timezone-aware datetime
)
```

---

## 6. Schema Ownership

| Schema | Python Module | Tables/Objects |
|--------|---------------|----------------|
| `dbo` | `src/db/` | Dim*, Fact*, Bridge* |
| `ingest` | `src/ingest/` | work_items, IngestRecords, ingest_runs |
| `llm` | `src/llm/` | job, run, artifact, evidence_bundle |
| `vector` | `src/vector/` | embedding_space, chunk, embedding |
| `sem` | `src/semantic/` | SourcePage, PageClassification, vw_* views |

---

## 7. Verification Queries

After applying changes, run these to verify alignment:

```sql
-- Verify no deprecated column names remain
SELECT OBJECT_NAME(object_id) AS TableName, name AS ColumnName
FROM sys.columns
WHERE name IN ('ExternalId', 'ExternalIdType', 'IngestBatchId')
  AND object_id IN (SELECT object_id FROM sys.tables);

-- Verify no dbo.sem_* views remain
SELECT name FROM sys.views 
WHERE schema_id = SCHEMA_ID('dbo') AND name LIKE 'sem_%';

-- Verify semantic views exist in sem schema
SELECT name FROM sys.views 
WHERE schema_id = SCHEMA_ID('sem') AND name LIKE 'vw_%';

-- Verify no NEWSEQUENTIALID() for public GUIDs
SELECT OBJECT_NAME(dc.parent_object_id) AS TableName, c.name AS ColumnName
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id 
  AND dc.parent_column_id = c.column_id
WHERE dc.definition LIKE '%NEWSEQUENTIALID%' AND c.name LIKE '%Guid';
```

---

## 8. Files Updated in This PR

| File | Changes |
|------|---------|
| `docs/db/python_sql_alignment_map_2026-02-14.md` | Created this document |
| `scripts/verify_schema_alignment.py` | Schema drift detection script |
| `docs/agent/DB_NAMING_CONVENTIONS.md` | Consolidated naming rules |
| `docs/agent/DB_SCHEMA_CHANGE_WORKFLOW.md` | Schema change process |

---

## Appendix: Quick Reference Card

```
NAMING PATTERNS:
  ...Key       = Internal surrogate (INT/BIGINT)
  ...Guid      = Public identifier (UNIQUEIDENTIFIER + NEWID())
  ...ExtKey    = External numeric ID
  ...NaturalKey = External text ID
  ...Utc       = UTC timestamp (DATETIME2(3) + SYSUTCDATETIME())

SCHEMAS:
  dbo    = Dim*, Fact*, Bridge* tables
  ingest = Work queue tables
  llm    = LLM job/run tables
  vector = Embedding tables
  sem    = Semantic views (vw_*)

ANTI-PATTERNS:
  ❌ ...Id columns
  ❌ NEWSEQUENTIALID() for public GUIDs
  ❌ DATETIME type
  ❌ dbo.sem_* views
```
