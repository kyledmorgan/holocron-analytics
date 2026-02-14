# Runtime Schema Snapshot (Reference Only)

**Generated:** 2026-02-14  
**Purpose:** Aid future diffing between "what's running" vs "what's scripted"  
**Status:** Template - populate with actual runtime metadata after migrations

---

## How to Generate This Snapshot

Run the following query against your SQL Server instance after applying migrations:

```sql
-- Schema snapshot query
SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLength,
    c.precision AS Precision,
    c.scale AS Scale,
    c.is_nullable AS IsNullable,
    c.column_id AS OrdinalPosition,
    dc.definition AS DefaultValue,
    CASE WHEN pk.column_id IS NOT NULL THEN 'PK' ELSE '' END AS IsPrimaryKey,
    CASE WHEN fk.parent_column_id IS NOT NULL THEN fk_ref.name ELSE '' END AS ForeignKeyRef
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
LEFT JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
LEFT JOIN (
    SELECT ic.object_id, ic.column_id
    FROM sys.indexes i
    INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
    WHERE i.is_primary_key = 1
) pk ON t.object_id = pk.object_id AND c.column_id = pk.column_id
LEFT JOIN sys.foreign_key_columns fk ON t.object_id = fk.parent_object_id AND c.column_id = fk.parent_column_id
LEFT JOIN sys.tables fk_ref ON fk.referenced_object_id = fk_ref.object_id
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
ORDER BY s.name, t.name, c.column_id;
```

---

## Expected Schema After Standardization

### Key Patterns

| Pattern | Usage |
|---------|-------|
| `...Key` | Internal surrogate keys (INT for dims, BIGINT for facts) |
| `...Guid` | Public-facing stable identifiers (UNIQUEIDENTIFIER with NEWID()) |
| `...ExtKey` | External source system numeric IDs |
| `...NaturalKey` | External source system text IDs |
| `...Utc` | All UTC timestamps (DATETIME2(3)) |

### Schema Ownership

| Schema | Contents |
|--------|----------|
| `dbo` | Dim*, Fact*, Bridge* tables |
| `ingest` | work_items, IngestRecords, ingest_runs, seen_resources |
| `llm` | job, run, artifact, evidence_bundle, evidence_item, run_evidence |
| `vector` | embedding_space, job, run, source_registry, chunk, embedding, retrieval, retrieval_hit |
| `sem` | SourcePage, PageSignals, PageClassification + all vw_* views |

### Views Expected in sem Schema

After migration, these views should exist in `sem` schema:

- `sem.vw_event`
- `sem.vw_character`
- `sem.vw_species`
- `sem.vw_organization`
- `sem.vw_location`
- `sem.vw_franchise`
- `sem.vw_work`
- `sem.vw_scene`
- `sem.vw_continuity_frame`
- `sem.vw_tech_asset`
- `sem.vw_tech_instance`
- `sem.vw_appearance_look`
- `sem.vw_claim`
- `sem.vw_continuity_issue`
- `sem.vw_issue_claim_link`
- `sem.vw_event_asset`
- `sem.vw_event_participant`
- `sem.vw_tag_assignments`
- `sem.vw_CurrentPageClassification`
- `sem.vw_PagesByType`
- `sem.vw_PagesNeedingReview`
- `sem.vw_TechnicalPages`
- `sem.vw_EntityCandidates`

### Verification Queries

```sql
-- Verify no dbo.sem_* views remain
SELECT name FROM sys.views 
WHERE schema_id = SCHEMA_ID('dbo') AND name LIKE 'sem_%';
-- Expected: 0 rows

-- Verify semantic views in sem schema
SELECT name FROM sys.views 
WHERE schema_id = SCHEMA_ID('sem');
-- Expected: 20+ rows

-- Verify no NEWSEQUENTIALID() for public GUIDs
SELECT OBJECT_NAME(dc.parent_object_id) AS TableName, c.name AS ColumnName
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
WHERE dc.definition LIKE '%NEWSEQUENTIALID%' AND c.name LIKE '%Guid';
-- Expected: 0 rows

-- Verify ExternalExtKey column exists in DimEntity
SELECT name FROM sys.columns 
WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalExtKey';
-- Expected: 1 row
```

---

## Reconciliation Status

| Check | Status | Notes |
|-------|--------|-------|
| All GUIDs use NEWID() | ✅ Scripted | DDL files updated |
| ExternalId → ExternalExtKey | ✅ Scripted | Migration adds column |
| dbo.sem_* → sem.vw_* | ✅ Scripted | Migration moves views |
| IngestBatchId → IngestBatchKey | ✅ Scripted | DDL files updated |
| DimEvent → DimOccurrence | ✅ Scripted | Migration renames table |

---

## Next Steps

After running the standardization migrations:

1. Execute the snapshot query above
2. Compare against this expected state
3. Document any differences in this file
4. Update Python code to use new names (separate PR)
