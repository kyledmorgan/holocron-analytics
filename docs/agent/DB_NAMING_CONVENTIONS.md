# Database Naming Conventions

This document defines the canonical naming conventions for the holocron-analytics database. All agents and contributors must follow these rules when creating or modifying database objects.

---

## 1. Column Naming

### 1.1 Key Columns

| Pattern | SQL Type | Usage | Example |
|---------|----------|-------|---------|
| `...Key` | `INT` or `BIGINT` | Internal surrogate keys | `EntityKey INT`, `EventKey BIGINT` |
| `...Guid` | `UNIQUEIDENTIFIER` | Public stable identifiers | `EntityGuid UNIQUEIDENTIFIER` |
| `...ExtKey` | `INT` or `NVARCHAR` | External numeric IDs | `WookieepediaExtKey INT` |
| `...NaturalKey` | `NVARCHAR` | External text composite keys | `SourceNaturalKey NVARCHAR(400)` |

**Rules:**
- Dimensions use `INT` for surrogate keys (lower cardinality)
- Facts use `BIGINT` for surrogate keys (high cardinality)
- Never use `...Id` for any column - this pattern is deprecated
- Foreign key columns must match the referenced primary key type

### 1.2 Timestamp Columns

| Pattern | SQL Type | Default | Example |
|---------|----------|---------|---------|
| `...Utc` | `DATETIME2(3)` | `SYSUTCDATETIME()` | `CreatedUtc`, `UpdatedUtc` |

**Standard Timestamp Columns:**
- `CreatedUtc` - Record creation time (always has default)
- `UpdatedUtc` - Last modification time (nullable, no default)
- `ValidFromUtc` - SCD Type 2 validity start
- `ValidToUtc` - SCD Type 2 validity end (nullable)

**Rules:**
- All timestamps must end with `Utc` suffix
- Always use `DATETIME2(3)` (millisecond precision)
- Never use deprecated `DATETIME` type
- Never use `GETDATE()` or `GETUTCDATE()` - use `SYSUTCDATETIME()`

### 1.3 Business Columns

| Type | Convention | Example |
|------|------------|---------|
| Names | PascalCase | `DisplayName`, `SortName` |
| Normalized | `...Normalized` suffix | `DisplayNameNormalized` |
| JSON storage | `...Json` suffix | `AttributesJson`, `MetricsJson` |
| Boolean flags | `Is...` prefix | `IsActive`, `IsLatest` |
| Counts | `...Count` suffix | `AttemptCount` |
| Scores | `...Score` suffix | `ConfidenceScore` |

---

## 2. Table Naming

### 2.1 Core Patterns

| Type | Pattern | Example |
|------|---------|---------|
| Dimensions | `Dim{Entity}` | `DimEntity`, `DimFranchise` |
| Facts | `Fact{Event}` | `FactEvent`, `FactClaim` |
| Bridges | `Bridge{From}{To}` | `BridgeEntityRelation` |
| Staging | `{Source}_{Stage}` | `wookieepedia_raw` |

### 2.2 Schema Ownership

| Schema | Purpose | Table Patterns |
|--------|---------|----------------|
| `dbo` | Core dimensional model | `Dim*`, `Fact*`, `Bridge*` |
| `ingest` | Ingestion pipeline | `work_items`, `IngestRecords` |
| `llm` | LLM processing | `job`, `run`, `artifact` |
| `vector` | Embedding storage | `embedding_space`, `chunk` |
| `sem` | Semantic layer | `SourcePage`, `PageClassification`, views |

---

## 3. View Naming

### 3.1 Semantic Views (sem schema)

| Pattern | Example | Notes |
|---------|---------|-------|
| `sem.vw_{name}` | `sem.vw_event` | User-facing curated views |
| `sem.int_{name}` | `sem.int_staging` | Internal/intermediate views |

**Rules:**
- All semantic views belong in `sem` schema
- Use `vw_` prefix for curated/public views
- Use `int_` prefix for internal processing views
- Never create views with `dbo.sem_*` pattern

### 3.2 Learning Views (dbo schema)

| Pattern | Example | Notes |
|---------|---------|-------|
| `dbo.learn_{name}` | `dbo.learn_events` | Simplified views for SQL learners |

---

## 4. Constraint Naming

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `PK_{Table}` | `PK_DimEntity` |
| Foreign Key | `FK_{Table}_{RefTable}` | `FK_DimEntity_DimFranchise` |
| Unique Constraint | `UQ_{Table}_{Column}` | `UQ_DimEntity_EntityGuid` |
| Check Constraint | `CK_{Table}_{Column}` | `CK_FactEvent_Status` |
| Default Constraint | `DF_{Table}_{Column}` | `DF_DimEntity_CreatedUtc` |

---

## 5. Index Naming

| Type | Pattern | Example |
|------|---------|---------|
| Unique Index | `UX_{Table}_{Columns}` | `UX_DimEntity_ExternalKey_IsLatest` |
| Non-Unique Index | `IX_{Table}_{Columns}` | `IX_DimEntity_FranchiseKey` |
| Clustered Index | Usually same as PK | `PK_DimEntity` |

---

## 6. Anti-Patterns (Avoid)

| ❌ Don't | ✅ Do | Reason |
|----------|-------|--------|
| `EntityId INT` | `EntityKey INT` | `...Id` is deprecated |
| `ExternalId` | `ExternalKey` | Use explicit key suffix |
| `NEWSEQUENTIALID()` | `NEWID()` | Sequential reveals creation order |
| `DATETIME` | `DATETIME2(3)` | Better precision and storage |
| `GETDATE()` | `SYSUTCDATETIME()` | UTC consistency |
| `CreatedOn` | `CreatedUtc` | Clear timezone indication |
| `dbo.sem_event` | `sem.vw_event` | Correct schema placement |

---

## 7. Python Variable Mapping

When writing Python code that interacts with the database:

| SQL Column | Python Variable | Type Hint |
|------------|-----------------|-----------|
| `EntityKey` | `entity_key` | `int` |
| `EntityGuid` | `entity_guid` | `uuid.UUID` |
| `ExternalKey` | `external_key` | `str` |
| `CreatedUtc` | `created_utc` | `datetime` |
| `UpdatedUtc` | `updated_utc` | `Optional[datetime]` |
| `IsActive` | `is_active` | `bool` |
| `AttributesJson` | `attributes_json` | `Optional[str]` |

---

## 8. Migration Guide

When renaming columns to follow conventions:

1. **Add new column** with correct name
2. **Copy data** from old to new column
3. **Create indexes** on new column
4. **Add deprecation notice** to old column
5. **Update Python code** in subsequent PR
6. **Drop old column** after verification period

See [db_templates.md](db_templates.md) for migration script templates.

---

## Quick Reference Card

```
KEYS:
  EntityKey      = INT surrogate (dim) / BIGINT (fact)
  EntityGuid     = UNIQUEIDENTIFIER DEFAULT (NEWID())
  ExternalKey    = External source ID
  
TIMESTAMPS:
  CreatedUtc     = DATETIME2(3) DEFAULT SYSUTCDATETIME()
  UpdatedUtc     = DATETIME2(3) NULL
  
TABLES:
  dbo.Dim*       = Dimensions
  dbo.Fact*      = Facts
  dbo.Bridge*    = Many-to-many
  
VIEWS:
  sem.vw_*       = Semantic curated views
  dbo.learn_*    = Learning/simplified views
```
