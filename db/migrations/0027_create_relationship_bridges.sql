-- Migration 0027: Create relationship bridge tables for Phase 2
-- Idempotent: Only creates tables if they don't exist
--
-- Purpose: Provides entity-to-entity relationship bridge and optional
-- event/work dimension tables for Phase 2 multi-output routing.
--
-- Tables:
--   - BridgeEntityRelation: Core entity-to-entity relationship bridge
--   - DimEvent: Event dimension (battles, treaties, births, deaths)
--   - BridgeEntityEvent: Entity participation in events
--   - DimWork: Creative works dimension (films, TV, novels, comics)
--   - BridgeEntityWork: Entity appearances in works
--
-- Foundation for:
--   - Phase 6: Events/works extraction
--   - Phase 3: Broad coverage routing outputs to multiple tables
--   - Phase 4: Governance and human review of relationship assertions

-- ============================================================================
-- dbo.BridgeEntityRelation table: Entity-to-Entity relationships
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'BridgeEntityRelation' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[BridgeEntityRelation] (
        RelationId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Endpoints (FK to DimEntity)
        FromEntityId UNIQUEIDENTIFIER NOT NULL,
        ToEntityId UNIQUEIDENTIFIER NOT NULL,
        
        -- Relationship type (open-ended string taxonomy)
        RelationType NVARCHAR(100) NOT NULL,
        
        -- Confidence score
        Confidence DECIMAL(5,4) NULL,
        
        -- Temporal bounds (optional, fuzzy dates allowed)
        StartDate NVARCHAR(100) NULL,
        EndDate NVARCHAR(100) NULL,
        
        -- Work context anchoring (JSON array of work references or direct FK)
        WorkContextJson NVARCHAR(MAX) NULL,
        
        -- Provenance tracking
        SourcePageId UNIQUEIDENTIFIER NULL,
        RunId UNIQUEIDENTIFIER NULL,
        JobId UNIQUEIDENTIFIER NULL,
        
        -- Timestamps
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        ModifiedUtc DATETIME2(3) NULL,
        
        -- Status and governance
        IsActive BIT NOT NULL DEFAULT 1,
        NeedsReview BIT NOT NULL DEFAULT 0,
        ReviewedUtc DATETIME2(3) NULL,
        ReviewedBy NVARCHAR(100) NULL,
        
        CONSTRAINT PK_BridgeEntityRelation PRIMARY KEY CLUSTERED (RelationId),
        -- Note: FK constraints to DimEntity would be added if DimEntity uses UNIQUEIDENTIFIER as PK
        -- For now, we use soft references since DimEntity.EntityId may be INT or UNIQUEIDENTIFIER
        -- depending on the existing schema. Verify and add FKs as appropriate.
    );
    PRINT 'Table [dbo].[BridgeEntityRelation] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[BridgeEntityRelation] already exists.'
END
GO

-- Index for finding relationships by relation type
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityRelation_RelationType' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_RelationType
    ON [dbo].[BridgeEntityRelation] (RelationType)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityRelation_RelationType] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityRelation_RelationType] already exists.'
END
GO

-- Index for finding all relationships for an entity (from endpoint)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityRelation_FromEntity' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_FromEntity
    ON [dbo].[BridgeEntityRelation] (FromEntityId, RelationType)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityRelation_FromEntity] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityRelation_FromEntity] already exists.'
END
GO

-- Index for finding all relationships for an entity (to endpoint)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityRelation_ToEntity' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_ToEntity
    ON [dbo].[BridgeEntityRelation] (ToEntityId, RelationType)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityRelation_ToEntity] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityRelation_ToEntity] already exists.'
END
GO

-- Index for finding relationships from a specific extraction run
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityRelation_RunId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_RunId
    ON [dbo].[BridgeEntityRelation] (RunId)
    WHERE RunId IS NOT NULL;
    PRINT 'Index [IX_BridgeEntityRelation_RunId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityRelation_RunId] already exists.'
END
GO

-- Index for finding relationships from a specific source page
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityRelation_SourcePageId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_SourcePageId
    ON [dbo].[BridgeEntityRelation] (SourcePageId)
    WHERE SourcePageId IS NOT NULL;
    PRINT 'Index [IX_BridgeEntityRelation_SourcePageId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityRelation_SourcePageId] already exists.'
END
GO

-- Index for reviewing relationships (governance)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityRelation_NeedsReview' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_NeedsReview
    ON [dbo].[BridgeEntityRelation] (NeedsReview, Confidence)
    WHERE IsActive = 1 AND NeedsReview = 1;
    PRINT 'Index [IX_BridgeEntityRelation_NeedsReview] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityRelation_NeedsReview] already exists.'
END
GO

-- ============================================================================
-- dbo.DimEvent table: Event dimension (battles, treaties, births, deaths)
-- Deferred implementation - placeholder structure for Phase 6
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'DimEvent' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[DimEvent] (
        EventId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Event identity
        EventName NVARCHAR(500) NOT NULL,
        EventNameNormalized NVARCHAR(500) NULL,
        
        -- Event classification (open-ended type taxonomy)
        EventType NVARCHAR(100) NULL,
        
        -- Temporal information (fuzzy dates allowed)
        EventDate NVARCHAR(100) NULL,
        EventStartDate NVARCHAR(100) NULL,
        EventEndDate NVARCHAR(100) NULL,
        
        -- Location (text or FK reference)
        EventLocation NVARCHAR(500) NULL,
        LocationEntityId UNIQUEIDENTIFIER NULL,
        
        -- Description
        Description NVARCHAR(MAX) NULL,
        
        -- Provenance
        SourcePageId UNIQUEIDENTIFIER NULL,
        RunId UNIQUEIDENTIFIER NULL,
        
        -- Confidence
        Confidence DECIMAL(5,4) NULL,
        
        -- Timestamps
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        ModifiedUtc DATETIME2(3) NULL,
        
        -- Status
        IsActive BIT NOT NULL DEFAULT 1,
        IsLatest BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_DimEvent PRIMARY KEY CLUSTERED (EventId)
    );
    PRINT 'Table [dbo].[DimEvent] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[DimEvent] already exists.'
END
GO

-- Index for event type lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimEvent_EventType' 
    AND object_id = OBJECT_ID('[dbo].[DimEvent]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimEvent_EventType
    ON [dbo].[DimEvent] (EventType)
    WHERE IsActive = 1 AND IsLatest = 1;
    PRINT 'Index [IX_DimEvent_EventType] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimEvent_EventType] already exists.'
END
GO

-- Index for event name lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimEvent_EventName' 
    AND object_id = OBJECT_ID('[dbo].[DimEvent]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimEvent_EventName
    ON [dbo].[DimEvent] (EventName)
    WHERE IsActive = 1 AND IsLatest = 1;
    PRINT 'Index [IX_DimEvent_EventName] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimEvent_EventName] already exists.'
END
GO

-- ============================================================================
-- dbo.BridgeEntityEvent table: Entity participation in events
-- Deferred implementation - placeholder structure for Phase 6
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'BridgeEntityEvent' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[BridgeEntityEvent] (
        BridgeId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- References
        EntityId UNIQUEIDENTIFIER NOT NULL,
        EventId UNIQUEIDENTIFIER NOT NULL,
        
        -- Participation details (open-ended role taxonomy)
        ParticipationRole NVARCHAR(100) NULL,
        
        -- Confidence
        Confidence DECIMAL(5,4) NULL,
        
        -- Provenance
        SourcePageId UNIQUEIDENTIFIER NULL,
        RunId UNIQUEIDENTIFIER NULL,
        
        -- Timestamps
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        
        -- Status
        IsActive BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_BridgeEntityEvent PRIMARY KEY CLUSTERED (BridgeId),
        CONSTRAINT FK_BridgeEntityEvent_Event FOREIGN KEY (EventId) 
            REFERENCES [dbo].[DimEvent](EventId)
    );
    PRINT 'Table [dbo].[BridgeEntityEvent] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[BridgeEntityEvent] already exists.'
END
GO

-- Index for entity lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityEvent_EntityId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityEvent]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityEvent_EntityId
    ON [dbo].[BridgeEntityEvent] (EntityId)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityEvent_EntityId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityEvent_EntityId] already exists.'
END
GO

-- Index for event lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityEvent_EventId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityEvent]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityEvent_EventId
    ON [dbo].[BridgeEntityEvent] (EventId)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityEvent_EventId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityEvent_EventId] already exists.'
END
GO

-- ============================================================================
-- dbo.DimWork table: Creative works dimension (films, TV, novels, comics)
-- Deferred implementation - placeholder structure for Phase 6
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'DimWork' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[DimWork] (
        WorkId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Work identity
        WorkName NVARCHAR(500) NOT NULL,
        WorkNameNormalized NVARCHAR(500) NULL,
        
        -- Work classification (open-ended type taxonomy)
        WorkType NVARCHAR(100) NULL,
        WorkMedium NVARCHAR(100) NULL,
        
        -- Canon status
        CanonStatus NVARCHAR(50) NULL,
        
        -- Release information (fuzzy dates allowed)
        ReleaseDate NVARCHAR(100) NULL,
        
        -- Description
        Description NVARCHAR(MAX) NULL,
        
        -- Provenance
        SourcePageId UNIQUEIDENTIFIER NULL,
        RunId UNIQUEIDENTIFIER NULL,
        
        -- Confidence
        Confidence DECIMAL(5,4) NULL,
        
        -- Timestamps
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        ModifiedUtc DATETIME2(3) NULL,
        
        -- Status
        IsActive BIT NOT NULL DEFAULT 1,
        IsLatest BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_DimWork PRIMARY KEY CLUSTERED (WorkId)
    );
    PRINT 'Table [dbo].[DimWork] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[DimWork] already exists.'
END
GO

-- Index for work type lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimWork_WorkType' 
    AND object_id = OBJECT_ID('[dbo].[DimWork]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimWork_WorkType
    ON [dbo].[DimWork] (WorkType, WorkMedium)
    WHERE IsActive = 1 AND IsLatest = 1;
    PRINT 'Index [IX_DimWork_WorkType] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimWork_WorkType] already exists.'
END
GO

-- Index for work name lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimWork_WorkName' 
    AND object_id = OBJECT_ID('[dbo].[DimWork]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimWork_WorkName
    ON [dbo].[DimWork] (WorkName)
    WHERE IsActive = 1 AND IsLatest = 1;
    PRINT 'Index [IX_DimWork_WorkName] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimWork_WorkName] already exists.'
END
GO

-- ============================================================================
-- dbo.BridgeEntityWork table: Entity appearances in works
-- Deferred implementation - placeholder structure for Phase 6
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'BridgeEntityWork' AND s.name = 'dbo'
)
BEGIN
    CREATE TABLE [dbo].[BridgeEntityWork] (
        BridgeId UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- References
        EntityId UNIQUEIDENTIFIER NOT NULL,
        WorkId UNIQUEIDENTIFIER NOT NULL,
        
        -- Appearance details (open-ended type taxonomy)
        AppearanceType NVARCHAR(100) NULL,
        
        -- Confidence
        Confidence DECIMAL(5,4) NULL,
        
        -- Provenance
        SourcePageId UNIQUEIDENTIFIER NULL,
        RunId UNIQUEIDENTIFIER NULL,
        
        -- Timestamps
        CreatedUtc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        
        -- Status
        IsActive BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_BridgeEntityWork PRIMARY KEY CLUSTERED (BridgeId),
        CONSTRAINT FK_BridgeEntityWork_Work FOREIGN KEY (WorkId) 
            REFERENCES [dbo].[DimWork](WorkId)
    );
    PRINT 'Table [dbo].[BridgeEntityWork] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [dbo].[BridgeEntityWork] already exists.'
END
GO

-- Index for entity lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityWork_EntityId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityWork]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityWork_EntityId
    ON [dbo].[BridgeEntityWork] (EntityId)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityWork_EntityId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityWork_EntityId] already exists.'
END
GO

-- Index for work lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_BridgeEntityWork_WorkId' 
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityWork]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityWork_WorkId
    ON [dbo].[BridgeEntityWork] (WorkId)
    WHERE IsActive = 1;
    PRINT 'Index [IX_BridgeEntityWork_WorkId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_BridgeEntityWork_WorkId] already exists.'
END
GO

PRINT 'Migration 0027 completed: Relationship bridge tables created for Phase 2.'
GO
