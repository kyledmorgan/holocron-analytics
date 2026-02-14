# Database Templates

Copy-paste templates for tables, views, and migrations in holocron-analytics.

---

## 1. Dimension Table Template

```sql
-- =============================================================================
-- Dim{TableName}: {Brief description}
-- {TableName}Guid provides stable cross-system identity (random GUID).
-- Governance metadata supports versioned rows (SCD Type 2 pattern).
--
-- Key Naming Conventions (see docs/agent/db_policies.md):
--   {TableName}Key = internal surrogate key (INT for dimension)
--   {TableName}Guid = public-facing stable identifier (random UNIQUEIDENTIFIER)
--   ...ExtKey = external source system identifier
-- =============================================================================
CREATE TABLE dbo.Dim{TableName} (
    -- Keys (left)
    {TableName}Key INT IDENTITY(1,1) NOT NULL,
    {TableName}Guid UNIQUEIDENTIFIER NOT NULL 
        CONSTRAINT DF_Dim{TableName}_{TableName}Guid DEFAULT (NEWID()),
    FranchiseKey INT NOT NULL,
    
    -- Business columns (middle)
    {TableName}Name NVARCHAR(200) NOT NULL,
    {TableName}NameNormalized NVARCHAR(200) NULL,
    {TableName}Type NVARCHAR(50) NULL,
    Description NVARCHAR(1000) NULL,
    ExternalExtKey NVARCHAR(200) NULL,
    ExternalExtKeyType NVARCHAR(50) NULL,
    ExternalUrl NVARCHAR(400) NULL,
    Notes NVARCHAR(1000) NULL,
    
    -- Audit columns (right)
    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_Dim{TableName}_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_Dim{TableName}_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_Dim{TableName}_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL 
        CONSTRAINT DF_Dim{TableName}_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL 
        CONSTRAINT DF_Dim{TableName}_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,
    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(MAX) NULL,
    
    -- Constraints
    CONSTRAINT PK_Dim{TableName} PRIMARY KEY CLUSTERED ({TableName}Key),
    CONSTRAINT UQ_Dim{TableName}_{TableName}Guid UNIQUE ({TableName}Guid),
    CONSTRAINT FK_Dim{TableName}_DimFranchise 
        FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

-- Indexes
CREATE INDEX IX_Dim{TableName}_FranchiseKey ON dbo.Dim{TableName}(FranchiseKey);
CREATE INDEX IX_Dim{TableName}_RowHash ON dbo.Dim{TableName}(RowHash);
CREATE UNIQUE INDEX UX_Dim{TableName}_ExternalExtKey_IsLatest
    ON dbo.Dim{TableName}(ExternalExtKey)
    WHERE ExternalExtKey IS NOT NULL AND IsLatest = 1;
GO
```

---

## 2. Fact Table Template

```sql
-- =============================================================================
-- Fact{TableName}: {Brief description}
-- Fact{TableName}Guid provides stable identity (random GUID).
-- Uses BIGINT for high-cardinality fact tables.
-- =============================================================================
CREATE TABLE dbo.Fact{TableName} (
    -- Keys (left)
    {TableName}Key BIGINT IDENTITY(1,1) NOT NULL,
    Fact{TableName}Guid UNIQUEIDENTIFIER NOT NULL 
        CONSTRAINT DF_Fact{TableName}_Fact{TableName}Guid DEFAULT (NEWID()),
    FranchiseKey INT NOT NULL,
    -- Foreign keys to dimensions
    {DimName}Key INT NOT NULL,
    
    -- Degenerate dimensions / measures (middle)
    {TableName}Ordinal INT NOT NULL,
    {MeasureName} DECIMAL(10,4) NULL,
    SummaryShort NVARCHAR(1000) NOT NULL,
    ConfidenceScore DECIMAL(5,4) NOT NULL,
    ExtractionMethod NVARCHAR(20) NOT NULL,
    Notes NVARCHAR(1000) NULL,
    
    -- Audit columns (right)
    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_Fact{TableName}_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_Fact{TableName}_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_Fact{TableName}_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL 
        CONSTRAINT DF_Fact{TableName}_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL 
        CONSTRAINT DF_Fact{TableName}_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,
    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(MAX) NULL,
    
    -- Constraints
    CONSTRAINT PK_Fact{TableName} PRIMARY KEY CLUSTERED ({TableName}Key),
    CONSTRAINT UQ_Fact{TableName}_Fact{TableName}Guid UNIQUE (Fact{TableName}Guid),
    CONSTRAINT FK_Fact{TableName}_DimFranchise 
        FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_Fact{TableName}_Dim{DimName} 
        FOREIGN KEY ({DimName}Key) REFERENCES dbo.Dim{DimName}({DimName}Key)
);

-- Indexes
CREATE INDEX IX_Fact{TableName}_FranchiseKey ON dbo.Fact{TableName}(FranchiseKey);
CREATE INDEX IX_Fact{TableName}_{DimName}Key ON dbo.Fact{TableName}({DimName}Key);
CREATE INDEX IX_Fact{TableName}_RowHash ON dbo.Fact{TableName}(RowHash);
CREATE INDEX IX_Fact{TableName}_IsLatest ON dbo.Fact{TableName}(IsLatest);
GO
```

---

## 3. Bridge Table Template

```sql
-- =============================================================================
-- Bridge{From}To{To}: Many-to-many relationship between {From} and {To}
-- =============================================================================
CREATE TABLE dbo.Bridge{From}{To} (
    -- Keys
    BridgeKey BIGINT IDENTITY(1,1) NOT NULL,
    BridgeGuid UNIQUEIDENTIFIER NOT NULL 
        CONSTRAINT DF_Bridge{From}{To}_BridgeGuid DEFAULT (NEWID()),
    
    -- Endpoints
    {From}Key INT NOT NULL,
    {To}Key INT NOT NULL,
    
    -- Relationship metadata
    RelationType NVARCHAR(100) NOT NULL,
    Confidence DECIMAL(5,4) NULL,
    StartDateRef NVARCHAR(100) NULL,
    EndDateRef NVARCHAR(100) NULL,
    
    -- Provenance
    SourcePageGuid UNIQUEIDENTIFIER NULL,
    RunGuid UNIQUEIDENTIFIER NULL,
    
    -- Audit columns
    CreatedUtc DATETIME2(3) NOT NULL 
        CONSTRAINT DF_Bridge{From}{To}_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_Bridge{From}{To}_IsActive DEFAULT (1),
    NeedsReview BIT NOT NULL CONSTRAINT DF_Bridge{From}{To}_NeedsReview DEFAULT (0),
    
    -- Constraints
    CONSTRAINT PK_Bridge{From}{To} PRIMARY KEY CLUSTERED (BridgeKey),
    CONSTRAINT UQ_Bridge{From}{To}_BridgeGuid UNIQUE (BridgeGuid),
    CONSTRAINT FK_Bridge{From}{To}_{From} 
        FOREIGN KEY ({From}Key) REFERENCES dbo.Dim{From}({From}Key),
    CONSTRAINT FK_Bridge{From}{To}_{To} 
        FOREIGN KEY ({To}Key) REFERENCES dbo.Dim{To}({To}Key)
);

-- Indexes
CREATE INDEX IX_Bridge{From}{To}_{From}Key ON dbo.Bridge{From}{To}({From}Key);
CREATE INDEX IX_Bridge{From}{To}_{To}Key ON dbo.Bridge{From}{To}({To}Key);
CREATE INDEX IX_Bridge{From}{To}_RelationType 
    ON dbo.Bridge{From}{To}(RelationType) WHERE IsActive = 1;
GO
```

---

## 4. Semantic View Template

```sql
-- =============================================================================
-- VIEW: sem.vw_{view_name}
-- 
-- PURPOSE: {Brief description of what this view provides}
--
-- AUDIENCE: {Who uses this view - analysts, downstream marts, learning layer}
--
-- KEY COLUMNS:
--   - {Column1}: {Description}
--   - {Column2}: {Description}
--
-- NOTES: Only returns active, latest version records.
-- =============================================================================
CREATE OR ALTER VIEW sem.vw_{view_name}
AS
SELECT
    t.{PrimaryKey},
    t.{Guid}                    AS {EntityName}Guid,
    t.{ForeignKey},
    ref.Name                    AS {RefTableName}Name,
    
    -- Business columns
    t.{Column1},
    t.{Column2},
    
    -- Audit columns
    t.ValidFromUtc
FROM dbo.{TableName} t
INNER JOIN dbo.{RefTable} ref
    ON t.{ForeignKey} = ref.{RefKey}
   AND ref.IsActive = 1
   AND ref.IsLatest = 1
WHERE t.IsActive = 1
  AND t.IsLatest = 1;
GO
```

---

## 5. Migration Script Template (Data-Preserving)

```sql
-- =============================================================================
-- Migration 0XXX: {Brief description}
-- Idempotent: Uses conditional logic to avoid duplicate changes
--
-- Purpose: {Detailed description of what this migration does}
--
-- Prerequisites: {Any migrations that must run first}
-- =============================================================================

SET NOCOUNT ON;
PRINT 'Starting Migration 0XXX: {Description}';
GO

-- =============================================================================
-- SECTION 1: {Section description}
-- =============================================================================

-- Step 1: Create backup (for populated tables)
IF EXISTS (SELECT 1 FROM [{Schema}].[{TableName}])
   AND NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '{TableName}__bak_YYYYMMDD')
BEGIN
    SELECT * INTO [{Schema}].[{TableName}__bak_YYYYMMDD] 
    FROM [{Schema}].[{TableName}];
    PRINT '  Created backup: [{Schema}].[{TableName}__bak_YYYYMMDD]';
END
GO

-- Step 2: Add new column (if not exists)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[{Schema}].[{TableName}]') 
    AND name = '{NewColumnName}'
)
BEGIN
    ALTER TABLE [{Schema}].[{TableName}] ADD {NewColumnName} {DataType} NULL;
    PRINT '  Added column: {NewColumnName}';
END
GO

-- Step 3: Copy data from old to new column
UPDATE [{Schema}].[{TableName}]
SET {NewColumnName} = {OldColumnName}
WHERE {OldColumnName} IS NOT NULL
  AND {NewColumnName} IS NULL;
PRINT '  Copied data: {OldColumnName} → {NewColumnName}';
GO

-- Step 4: Create index on new column
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'IX_{TableName}_{NewColumnName}' 
    AND object_id = OBJECT_ID('[{Schema}].[{TableName}]')
)
BEGIN
    CREATE INDEX IX_{TableName}_{NewColumnName} 
    ON [{Schema}].[{TableName}]({NewColumnName});
    PRINT '  Created index: IX_{TableName}_{NewColumnName}';
END
GO

-- Step 5: Validate migration
DECLARE @old_count INT, @new_count INT;
SELECT @old_count = COUNT(*) FROM [{Schema}].[{TableName}] WHERE {OldColumnName} IS NOT NULL;
SELECT @new_count = COUNT(*) FROM [{Schema}].[{TableName}] WHERE {NewColumnName} IS NOT NULL;

IF @old_count = @new_count
BEGIN
    PRINT '  Validation passed: ' + CAST(@new_count AS VARCHAR) + ' rows migrated';
END
ELSE
BEGIN
    PRINT '  WARNING: Row count mismatch. Old: ' + CAST(@old_count AS VARCHAR) + ', New: ' + CAST(@new_count AS VARCHAR);
END
GO

PRINT 'Migration 0XXX complete.';
GO
```

---

## 6. Column Rename Migration Template

```sql
-- =============================================================================
-- Migration 0XXX: Rename {OldColumn} → {NewColumn} in {Schema}.{Table}
-- Idempotent: Uses conditional logic to avoid duplicate changes
-- =============================================================================

-- Step 1: Add new column if not exists
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[{Schema}].[{Table}]') 
    AND name = '{NewColumn}'
)
BEGIN
    ALTER TABLE [{Schema}].[{Table}] ADD {NewColumn} {DataType} NULL;
    PRINT 'Added column: {NewColumn}';
END
GO

-- Step 2: Copy data
UPDATE [{Schema}].[{Table}]
SET {NewColumn} = {OldColumn}
WHERE {OldColumn} IS NOT NULL
  AND {NewColumn} IS NULL;
GO

-- Step 3: Drop old index (if exists)
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_{Table}_{OldColumn}')
BEGIN
    DROP INDEX IX_{Table}_{OldColumn} ON [{Schema}].[{Table}];
    PRINT 'Dropped old index: IX_{Table}_{OldColumn}';
END
GO

-- Step 4: Create new index
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_{Table}_{NewColumn}')
BEGIN
    CREATE INDEX IX_{Table}_{NewColumn} ON [{Schema}].[{Table}]({NewColumn});
    PRINT 'Created new index: IX_{Table}_{NewColumn}';
END
GO

-- Step 5: Add deprecation comment to old column
-- Note: Old column kept for compatibility; remove in future migration after Python update
EXEC sys.sp_addextendedproperty 
    @name = N'MS_Description',
    @value = N'DEPRECATED: Use {NewColumn} instead. Will be removed in future release.',
    @level0type = N'SCHEMA', @level0name = '{Schema}',
    @level1type = N'TABLE', @level1name = '{Table}',
    @level2type = N'COLUMN', @level2name = '{OldColumn}';
GO
```

---

## 7. View Move Template (dbo → sem)

```sql
-- =============================================================================
-- Migration 0XXX: Move dbo.sem_{view} → sem.vw_{view}
-- Idempotent: Uses conditional logic to avoid duplicate changes
-- =============================================================================

-- Drop old view if new exists
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_{view}]'))
   AND EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_{view}]'))
BEGIN
    DROP VIEW [dbo].[sem_{view}];
    PRINT 'Dropped: [dbo].[sem_{view}] (new view already exists)';
END
GO

-- Move view if only old exists
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_{view}]'))
   AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_{view}]'))
BEGIN
    -- Get definition, modify, recreate
    DECLARE @def NVARCHAR(MAX);
    SELECT @def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_{view}]'));
    DROP VIEW [dbo].[sem_{view}];
    SET @def = REPLACE(@def, 'dbo.sem_{view}', 'sem.vw_{view}');
    SET @def = REPLACE(@def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@def);
    PRINT 'Moved: [dbo].[sem_{view}] → [sem].[vw_{view}]';
END
GO
```
