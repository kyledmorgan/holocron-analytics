# Database PR Review Checklist

Use this checklist when reviewing PRs that contain SQL DDL, migrations, or schema changes.

---

## Quick Review Checklist

Before approving any SQL PR, verify:

- [ ] No columns named `...Id` (use `...Key`, `...Guid`, `...ExtKey`)
- [ ] All GUIDs use `DEFAULT (NEWID())` not `NEWSEQUENTIALID()`
- [ ] All timestamps use `DATETIME2(3)` with `Utc` suffix
- [ ] All timestamps default to `SYSUTCDATETIME()`
- [ ] Views in `sem` schema use `vw_` prefix
- [ ] Column ordering follows convention (keys → business → audit)
- [ ] Constraint names follow naming convention

---

## Detailed Review Criteria

### 1. Key + ID Naming

| Check | Rule |
|-------|------|
| ✅ | Surrogate keys use `...Key` (not `...Id`) |
| ✅ | INT for dimension keys, BIGINT for fact keys |
| ✅ | Public GUIDs use `...Guid` suffix |
| ✅ | External IDs use `...ExtKey` or `...NaturalKey` |
| ❌ | Never use `...Id` for any column |

**Examples:**
```sql
-- CORRECT
EntityKey INT IDENTITY(1,1) NOT NULL
EntityGuid UNIQUEIDENTIFIER NOT NULL DEFAULT (NEWID())
WookieepediaExtKey INT NULL
SourceNaturalKey NVARCHAR(400) NULL

-- WRONG
EntityId INT NOT NULL          -- Should be EntityKey
external_id NVARCHAR(200) NULL -- Should be ExternalKey
ExtKey NVARCHAR(200) NULL      -- Should be ExternalKey
```

### 2. GUID Defaults

| Check | Rule |
|-------|------|
| ✅ | Use `NEWID()` for all public/stable GUIDs |
| ❌ | Never use `NEWSEQUENTIALID()` for public GUIDs |

**Why:** `NEWSEQUENTIALID()` generates sequential GUIDs that reveal row creation order—a security concern for externally-visible identifiers.

```sql
-- CORRECT (secure - random)
EntityGuid UNIQUEIDENTIFIER NOT NULL DEFAULT (NEWID())

-- WRONG (insecure - sequential)
EntityGuid UNIQUEIDENTIFIER NOT NULL DEFAULT (NEWSEQUENTIALID())
```

### 3. DateTime Standards

| Check | Rule |
|-------|------|
| ✅ | Use `DATETIME2(3)` (or `DATETIME2(7)` for sub-ms) |
| ✅ | Column names end with `Utc` suffix |
| ✅ | Default to `SYSUTCDATETIME()` |
| ❌ | Never use `DATETIME` type |
| ❌ | Never use `GETDATE()` or `GETUTCDATE()` |

```sql
-- CORRECT
CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
UpdatedUtc DATETIME2(3) NULL

-- WRONG
CreatedOn DATETIME NOT NULL DEFAULT GETDATE()
created_at DATETIME2 NOT NULL -- Missing precision, wrong name
```

### 4. Schema Placement

| Check | Rule |
|-------|------|
| ✅ | Semantic views in `sem` schema with `vw_` prefix |
| ✅ | No `dbo.sem_*` views (move to `sem.vw_*`) |
| ✅ | Tables use correct schema for their purpose |

```sql
-- CORRECT
sem.vw_current_page_classification
sem.vw_entity_candidates

-- WRONG
dbo.sem_event              -- Should be sem.vw_event
dbo.vw_semantic_data       -- Should be in sem schema
```

### 5. Column Ordering

| Position | Column Types |
|----------|--------------|
| Left | Primary keys, GUIDs, foreign keys |
| Middle | Business columns (domain data) |
| Right | Audit columns (governance, tracking) |

**Audit columns (right side):**
- `RowHash`
- `IsActive`, `IsLatest`, `VersionNum`
- `ValidFromUtc`, `ValidToUtc`
- `CreatedUtc`, `UpdatedUtc`
- `SourceSystem`, `SourceRef`
- `IngestBatchKey`
- `AttributesJson`

### 6. Constraint Naming

| Object | Pattern | Example |
|--------|---------|---------|
| Primary Key | `PK_TableName` | `PK_DimEntity` |
| Foreign Key | `FK_Table_RefTable` | `FK_DimEntity_DimFranchise` |
| Unique | `UQ_Table_Column` | `UQ_DimEntity_EntityGuid` |
| Index (unique) | `UX_Table_Columns` | `UX_DimEntity_ExternalKey_IsLatest` |
| Index (non-unique) | `IX_Table_Columns` | `IX_DimEntity_FranchiseKey` |
| Check | `CK_Table_Column` | `CK_FactEvent_Status` |
| Default | `DF_Table_Column` | `DF_DimEntity_CreatedUtc` |

---

## Migration-Specific Checks

### For Column Renames

- [ ] New column added (not renamed in place)
- [ ] Data copied from old to new column
- [ ] New indexes created
- [ ] Old indexes dropped or kept for compatibility
- [ ] Deprecation comment added to old column
- [ ] Row count validation included
- [ ] Rollback plan documented (if needed)

### For Table Renames

- [ ] All dependent views updated
- [ ] All dependent stored procedures updated
- [ ] All foreign key constraints updated
- [ ] All indexes renamed
- [ ] Old table name not left as orphan

### For View Moves

- [ ] Old view dropped (or kept for compatibility period)
- [ ] New view created in correct schema
- [ ] View uses `vw_` prefix if in `sem` schema
- [ ] View references use correct aliases

---

## Common Issues to Flag

### Security Issues (Block PR)

1. **Sequential GUIDs for public identifiers**
   - `NEWSEQUENTIALID()` reveals row creation order
   - Fix: Use `NEWID()`

2. **Local time functions**
   - `GETDATE()` uses server local time
   - Fix: Use `SYSUTCDATETIME()`

### Naming Issues (Request Changes)

1. **`...Id` column names**
   - Violates naming convention
   - Fix: Rename to `...Key`, `...Guid`, or `...ExtKey`

2. **Missing `Utc` suffix on timestamps**
   - Creates ambiguity about timezone
   - Fix: Add `Utc` suffix

3. **Wrong schema for semantic views**
   - `dbo.sem_*` views should be `sem.vw_*`
   - Fix: Move to correct schema

### Style Issues (Suggest Changes)

1. **Column ordering**
   - Keys should be leftmost, audit rightmost
   - Suggest: Reorder for consistency

2. **Inconsistent casing**
   - Mix of PascalCase and snake_case
   - Suggest: Use PascalCase for columns

---

## Approval Criteria

**Approve if:**
- All Quick Review items pass
- No security issues
- Naming conventions followed
- Schema placement correct

**Request changes if:**
- Any naming violations
- Wrong GUID default functions
- Datetime type/naming issues
- Wrong schema placement

**Block if:**
- Security vulnerabilities
- Breaking changes without migration plan
- Data loss potential without backup
