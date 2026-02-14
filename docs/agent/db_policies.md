# Database Policies

This document defines the canonical naming conventions, key patterns, datetime standards, and schema ownership rules for the holocron-analytics database.

## 1. Key + ID Standardization

### 1.1 Internal Surrogate Keys (Join Keys)

**Rule:** Internal join keys use `...Key` (NOT `...Id`), with numeric types.

| Table Type | Key Type | Example |
|------------|----------|---------|
| Dimensions (low cardinality) | `INT` | `EntityKey INT NOT NULL` |
| Facts (high cardinality) | `BIGINT` | `EventKey BIGINT NOT NULL` |
| Bridges | `INT` or `BIGINT` | Match the referenced table |

**Implementation Notes:**
- Keys may use `IDENTITY` for sequential generation (internal only)
- FK columns must match PK type (`INT`↔`INT`, `BIGINT`↔`BIGINT`)
- Sequential IDs are acceptable for internal keys (not public identifiers)

### 1.2 Random GUIDs (Public/Stable Identifiers)

**Rule:** Public-facing identifiers use `...Guid` with random UUID generation.

```sql
-- CORRECT
EntityGuid UNIQUEIDENTIFIER NOT NULL DEFAULT (NEWID())

-- WRONG - reveals row creation order (security risk)
EntityGuid UNIQUEIDENTIFIER NOT NULL DEFAULT (NEWSEQUENTIALID())
```

**Usage:**
- Cross-system correlation
- External API responses
- Any identifier visible outside the database

### 1.3 External / Source-System IDs

**Rule:** Never use `...Id` for source system identifiers. Use explicit naming:

| Pattern | Usage | Example |
|---------|-------|---------|
| `...ExtKey` | Numeric external IDs | `WookieepediaExtKey INT NULL` |
| `...NaturalKey` | Text composite keys | `SourceNaturalKey NVARCHAR(400) NOT NULL` |
| `...SourceKey` | Alternative for text keys | `MediaWikiSourceKey NVARCHAR(200) NULL` |

---

## 2. DateTime / Timestamps (UTC, Consistent)

### 2.1 Type Requirements

**Rule:** All timestamps must use `DATETIME2(3)` (or `DATETIME2(7)` if sub-millisecond precision is required).

```sql
-- CORRECT
CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()

-- WRONG - deprecated type, local time ambiguity
CreatedOn DATETIME NOT NULL DEFAULT GETDATE()
```

### 2.2 Naming Convention

**Rule:** All timestamp columns must end with `Utc` suffix.

| Column Name | Purpose |
|-------------|---------|
| `CreatedUtc` | Record creation timestamp |
| `UpdatedUtc` | Last modification timestamp |
| `ValidFromUtc` | SCD Type 2 validity start |
| `ValidToUtc` | SCD Type 2 validity end |
| `LastSeenUtc` | Telemetry/heartbeat timestamps |

### 2.3 Default Values

**Rule:** Use `SYSUTCDATETIME()` for creation timestamps.

```sql
CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
```

**Avoid:**
- `GETDATE()` (local time)
- `GETUTCDATE()` (returns DATETIME, not DATETIME2)
- Ambiguous names like `CreatedOn`, `UpdatedAt`

---

## 3. Naming Conventions (Objects + Columns)

### 3.1 Tables and Views

| Object Type | Convention | Example |
|-------------|------------|---------|
| Schemas | lowercase | `ingest`, `llm`, `vector`, `sem` |
| Dimension tables | PascalCase with `Dim` prefix | `DimEntity`, `DimFranchise` |
| Fact tables | PascalCase with `Fact` prefix | `FactEvent`, `FactClaim` |
| Bridge tables | PascalCase with `Bridge` prefix | `BridgeEntityRelation` |
| Views | `lower_snake_case` with `vw_` prefix | `vw_queue_health`, `vw_current_page` |

### 3.2 Column Naming

**Rule:** Columns use PascalCase.

| Column Type | Pattern | Example |
|-------------|---------|---------|
| Surrogate keys | `...Key` | `EntityKey`, `EventKey` |
| Public GUIDs | `...Guid` | `EntityGuid`, `RunGuid` |
| External keys | `...ExtKey` | `WookieepediaExtKey` |
| Natural keys | `...NaturalKey` | `SourceNaturalKey` |
| Timestamps | `...Utc` | `CreatedUtc`, `UpdatedUtc` |
| JSON columns | `...Json` | `AttributesJson`, `MetricsJson` |

### 3.3 Constraint and Index Naming

| Object Type | Pattern | Example |
|-------------|---------|---------|
| Primary Key | `PK_TableName` | `PK_DimEntity` |
| Foreign Key | `FK_Table_RefTable` | `FK_DimEntity_DimFranchise` |
| Unique Constraint | `UQ_Table_Column` | `UQ_DimEntity_EntityGuid` |
| Unique Index | `UX_Table_Columns` | `UX_DimEntity_ExternalExtKey_IsLatest` |
| Non-Unique Index | `IX_Table_Columns` | `IX_DimEntity_FranchiseKey` |
| Check Constraint | `CK_Table_Column` | `CK_FactEvent_Status` |
| Default Constraint | `DF_Table_Column` | `DF_DimEntity_CreatedUtc` |

---

## 4. Schema Ownership

### 4.1 Schema Purposes

| Schema | Purpose | Table Pattern |
|--------|---------|---------------|
| `dbo` | Core dimensional model | `Dim*`, `Fact*`, `Bridge*` |
| `ingest` | Raw ingestion tables | `work_items`, `IngestRecords`, `ingest_runs` |
| `llm` | LLM chat/interrogation runtime | `job`, `run`, `artifact` |
| `vector` | Embedding/retrieval runtime | `embedding_space`, `chunk`, `embedding` |
| `sem` | Semantic layer | Tables: `SourcePage`, `PageClassification`; Views: `vw_*` |

### 4.2 Semantic Schema Rules

**Rule:** All semantic views belong in the `sem` schema with `vw_` prefix.

```sql
-- CORRECT
sem.vw_current_page_classification
sem.vw_entity_candidates

-- WRONG (old pattern)
dbo.sem_event
dbo.sem_character
```

**Internal vs Curated Distinction (optional):**
- Internal/state tables: `sem.int_*` or no prefix
- Curated views: `sem.vw_*`

---

## 5. Column Ordering (DDL Hygiene)

**Rule:** Order columns logically in DDL:

1. **Keys** (left): Primary key, GUIDs, foreign keys
2. **Business Columns** (middle): Domain-specific data
3. **Audit Columns** (right): Governance and tracking

```sql
CREATE TABLE dbo.DimEntity (
    -- 1. Keys
    EntityKey INT IDENTITY(1,1) NOT NULL,
    EntityGuid UNIQUEIDENTIFIER NOT NULL DEFAULT (NEWID()),
    FranchiseKey INT NOT NULL,
    
    -- 2. Business columns
    EntityType NVARCHAR(50) NOT NULL,
    DisplayName NVARCHAR(200) NOT NULL,
    -- ... more business columns
    
    -- 3. Audit columns
    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL DEFAULT (1),
    IsLatest BIT NOT NULL DEFAULT (1),
    CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedUtc DATETIME2(3) NULL,
    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    AttributesJson NVARCHAR(MAX) NULL,
    
    -- Constraints
    CONSTRAINT PK_DimEntity PRIMARY KEY CLUSTERED (EntityKey)
);
```

---

## 6. Anti-Patterns

### Avoid These Patterns

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `...Id` column names | `...Key`, `...Guid`, `...ExtKey` |
| `NEWSEQUENTIALID()` for public GUIDs | `NEWID()` |
| `DATETIME` type | `DATETIME2(3)` |
| `GETDATE()` for timestamps | `SYSUTCDATETIME()` |
| `dbo.sem_*` views | `sem.vw_*` |
| Timestamps without `Utc` suffix | `CreatedUtc`, `UpdatedUtc` |
| Mixed casing in schema names | `lowercase` only |
| Late-added random columns | Reorder per hygiene rules |

---

## 7. Migration Considerations

When renaming columns or tables:

1. **Add new column** with correct naming
2. **Copy data** from old to new column
3. **Update indexes** to reference new column
4. **Add deprecation comment** to old column
5. **Update Python code** in subsequent PR
6. **Drop old column** after verification period

See [db_templates.md](db_templates.md) for migration script templates.
