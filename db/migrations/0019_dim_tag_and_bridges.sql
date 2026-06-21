-- Migration 0019: Create dbo.DimTag and dbo.BridgeTagAssignment tables
-- Idempotent: Only creates tables if they don't exist
--
-- Purpose: A tagging system that can link pages and entities (and later chunks, 
-- claims, events) without committing to rigid facts.
--
-- Tables:
--   - DimTag: Canonical tag definition with TagType and Visibility
--   - BridgeTagAssignment: Many-to-many tag assignments with TargetType + TargetId
--   - BridgeTagRelation: Optional synonyms / broader-narrower / related relationships

-- ============================================================================
-- dbo.DimTag table: Canonical tag definition
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'DimTag' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[DimTag] (
        TagKey INT IDENTITY(1,1) NOT NULL,
        TagGuid UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Tag identity
        TagName NVARCHAR(200) NOT NULL,
        TagNameNormalized NVARCHAR(200) NULL,
        TagType NVARCHAR(50) NOT NULL,
        
        -- Display and categorization
        DisplayName NVARCHAR(200) NULL,
        Description NVARCHAR(1000) NULL,
        SortOrder INT NOT NULL DEFAULT 100,
        
        -- Visibility control
        Visibility NVARCHAR(20) NOT NULL DEFAULT 'public',
        
        -- Color/styling (optional)
        ColorHex NVARCHAR(7) NULL,
        IconRef NVARCHAR(100) NULL,
        
        -- Governance
        IsActive BIT NOT NULL DEFAULT 1,
        IsLatest BIT NOT NULL DEFAULT 1,
        VersionNum INT NOT NULL DEFAULT 1,
        ValidFromUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        ValidToUtc DATETIME2(3) NULL,
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        UpdatedUtc DATETIME2(3) NULL,
        
        -- Source tracking
        SourceSystem NVARCHAR(100) NULL,
        SourceRef NVARCHAR(400) NULL,
        
        CONSTRAINT PK_DimTag PRIMARY KEY CLUSTERED (TagKey),
        CONSTRAINT UQ_DimTag_TagGuid UNIQUE (TagGuid),
        CONSTRAINT CK_DimTag_Visibility CHECK (Visibility IN ('public', 'hidden', 'internal', 'deprecated'))
    );
    PRINT 'Table [dbo].[DimTag] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[DimTag] already exists.'
END
GO

-- Unique constraint on TagType + TagName for active, latest tags
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UX_DimTag_Type_Name_Latest' 
    AND object_id = OBJECT_ID('[dbo].[DimTag]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_DimTag_Type_Name_Latest
    ON [dbo].[DimTag] (TagType, TagName)
    WHERE IsLatest = 1 AND IsActive = 1;
    PRINT 'Index [UX_DimTag_Type_Name_Latest] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [UX_DimTag_Type_Name_Latest] already exists.'
END
GO

-- Index for TagType lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimTag_TagType' 
    AND object_id = OBJECT_ID('[dbo].[DimTag]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimTag_TagType
    ON [dbo].[DimTag] (TagType, Visibility, SortOrder)
    WHERE IsLatest = 1 AND IsActive = 1;
    PRINT 'Index [IX_DimTag_TagType] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimTag_TagType] already exists.'
END
GO

-- Index for Visibility filtering
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimTag_Visibility' 
    AND object_id = OBJECT_ID('[dbo].[DimTag]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimTag_Visibility
    ON [dbo].[DimTag] (Visibility, TagType)
    WHERE IsLatest = 1;
    PRINT 'Index [IX_DimTag_Visibility] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimTag_Visibility] already exists.'
END
GO

-- ============================================================================
-- dbo.BridgeTagAssignment table: Many-to-many tag assignments
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'BridgeTagAssignment' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[BridgeTagAssignment] (
        AssignmentId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Tag reference
        TagKey INT NOT NULL,
        
        -- Target (polymorphic reference)
        TargetType NVARCHAR(50) NOT NULL,
        TargetId NVARCHAR(200) NOT NULL,
        
        -- Assignment metadata
        Weight DECIMAL(5,4) NULL,
        Confidence DECIMAL(5,4) NULL,
        
        -- Source of assignment
        AssignedBy NVARCHAR(100) NULL,
        AssignmentMethod NVARCHAR(50) NOT NULL DEFAULT 'manual',
        
        -- Lineage
        SourcePageId UNIQUEIDENTIFIER NULL,
        ClassificationId UNIQUEIDENTIFIER NULL,
        RunId UNIQUEIDENTIFIER NULL,
        
        -- Timestamps
        AssignedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        
        -- Status
        IsActive BIT NOT NULL DEFAULT 1,
        RemovedUtc DATETIME2(3) NULL,
        RemovedBy NVARCHAR(100) NULL,
        
        CONSTRAINT PK_BridgeTagAssignment PRIMARY KEY CLUSTERED (AssignmentId),
        CONSTRAINT FK_BridgeTagAssignment_Tag FOREIGN KEY (TagKey) 
            REFERENCES [dbo].[DimTag](TagKey),
        CONSTRAINT CK_BridgeTagAssignment_TargetType CHECK (TargetType IN (
            'SourcePage', 'Entity', 'Chunk', 'Claim', 'Event', 'Work', 
            'Character', 'Location', 'Classification', 'Other'
        )),
        CONSTRAINT CK_BridgeTagAssignment_Method CHECK (AssignmentMethod IN (
            'manual', 'rules', 'llm', 'hybrid', 'import', 'system'
        ))
    );
    PRINT 'Table [dbo].[BridgeTagAssignment] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[BridgeTagAssignment] already exists.'
END
GO

-- Unique constraint on TagKey + TargetType + TargetId for active assignments
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UX_BridgeTagAssignment_Tag_Target_Active' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagAssignment]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_BridgeTagAssignment_Tag_Target_Active
    ON [dbo].[BridgeTagAssignment] (TagKey, TargetType, TargetId)
    WHERE IsActive = 1;
    PRINT 'Index [UX_BridgeTagAssignment_Tag_Target_Active] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [UX_BridgeTagAssignment_Tag_Target_Active] already exists.'
END
GO

-- Index for Target lookups (find all tags for a target)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeTagAssignment_Target' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagAssignment]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeTagAssignment_Target
    ON [dbo].[BridgeTagAssignment] (TargetType, TargetId)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeTagAssignment_Target] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeTagAssignment_Target] already exists.'
END
GO

-- Index for TagKey lookups (find all targets with a tag)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeTagAssignment_TagKey' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagAssignment]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeTagAssignment_TagKey
    ON [dbo].[BridgeTagAssignment] (TagKey, TargetType)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeTagAssignment_TagKey] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeTagAssignment_TagKey] already exists.'
END
GO

-- Index for SourcePageId lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeTagAssignment_SourcePageId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagAssignment]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeTagAssignment_SourcePageId
    ON [dbo].[BridgeTagAssignment] (SourcePageId)
    WHERE SourcePageId IS NOT NULL;
    PRINT 'Index [IX_BridgeTagAssignment_SourcePageId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeTagAssignment_SourcePageId] already exists.'
END
GO

-- Index for AssignedUtc (recency)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeTagAssignment_AssignedUtc' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagAssignment]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeTagAssignment_AssignedUtc
    ON [dbo].[BridgeTagAssignment] (AssignedUtc DESC);
    PRINT 'Index [IX_BridgeTagAssignment_AssignedUtc] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeTagAssignment_AssignedUtc] already exists.'
END
GO

-- ============================================================================
-- dbo.BridgeTagRelation table: Tag relationships (synonyms / broader-narrower / related)
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'BridgeTagRelation' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[BridgeTagRelation] (
        RelationId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Tag references
        FromTagKey INT NOT NULL,
        ToTagKey INT NOT NULL,
        
        -- Relationship type
        RelationType NVARCHAR(50) NOT NULL,
        
        -- Direction and weight
        IsBidirectional BIT NOT NULL DEFAULT 0,
        Weight DECIMAL(5,4) NULL,
        
        -- Metadata
        Notes NVARCHAR(500) NULL,
        
        -- Timestamps
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        CreatedBy NVARCHAR(100) NULL,
        
        -- Status
        IsActive BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_BridgeTagRelation PRIMARY KEY CLUSTERED (RelationId),
        CONSTRAINT FK_BridgeTagRelation_FromTag FOREIGN KEY (FromTagKey) 
            REFERENCES [dbo].[DimTag](TagKey),
        CONSTRAINT FK_BridgeTagRelation_ToTag FOREIGN KEY (ToTagKey) 
            REFERENCES [dbo].[DimTag](TagKey),
        CONSTRAINT CK_BridgeTagRelation_Type CHECK (RelationType IN (
            'synonym', 'broader', 'narrower', 'related', 'replaces', 'replaced_by'
        )),
        CONSTRAINT CK_BridgeTagRelation_NotSelf CHECK (FromTagKey <> ToTagKey)
    );
    PRINT 'Table [dbo].[BridgeTagRelation] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[BridgeTagRelation] already exists.'
END
GO

-- Unique constraint on FromTag + ToTag + RelationType for active relations
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UX_BridgeTagRelation_From_To_Type_Active' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagRelation]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_BridgeTagRelation_From_To_Type_Active
    ON [dbo].[BridgeTagRelation] (FromTagKey, ToTagKey, RelationType)
    WHERE IsActive = 1;
    PRINT 'Index [UX_BridgeTagRelation_From_To_Type_Active] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [UX_BridgeTagRelation_From_To_Type_Active] already exists.'
END
GO

-- Index for FromTagKey lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeTagRelation_FromTag' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeTagRelation_FromTag
    ON [dbo].[BridgeTagRelation] (FromTagKey, RelationType)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeTagRelation_FromTag] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeTagRelation_FromTag] already exists.'
END
GO

-- Index for ToTagKey lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeTagRelation_ToTag' 
    AND object_id = OBJECT_ID('[dbo].[BridgeTagRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeTagRelation_ToTag
    ON [dbo].[BridgeTagRelation] (ToTagKey, RelationType)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeTagRelation_ToTag] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeTagRelation_ToTag] already exists.'
END
GO

PRINT 'Migration 0019 completed: DimTag, BridgeTagAssignment, and BridgeTagRelation tables created.'
