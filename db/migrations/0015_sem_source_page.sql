-- Migration 0015: Create sem.SourcePage table
-- Idempotent: Only creates table if it doesn't exist
--
-- Purpose: Represents a "page/article" identity derived from ingest + registry.
-- Bridges to:
--   - Latest fetch: ingest.IngestRecords.ingest_id
--   - Optional indexing: llm.source_registry.source_id
-- Captures source system, resource ID (title), variant, namespace, continuity hint,
-- content hash, and timestamps.

-- ============================================================================
-- sem.SourcePage table: Page identity and provenance
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'SourcePage' AND s.name = 'sem'
)
BEGIN
    CREATE TABLE [sem].[SourcePage] (
        source_page_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Identity fields
        source_system NVARCHAR(100) NOT NULL,
        resource_id NVARCHAR(500) NOT NULL,
        variant NVARCHAR(20) NULL,
        
        -- Parsed metadata
        namespace NVARCHAR(100) NULL,
        continuity_hint NVARCHAR(50) NULL,
        
        -- Content tracking
        content_hash_sha256 NVARCHAR(64) NULL,
        
        -- Links to other systems
        latest_ingest_id UNIQUEIDENTIFIER NULL,
        source_registry_id NVARCHAR(256) NULL,
        
        -- Timestamps
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        -- Status
        is_active BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_sem_SourcePage PRIMARY KEY CLUSTERED (source_page_id)
    );
    PRINT 'Table [sem].[SourcePage] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [sem].[SourcePage] already exists.'
END
GO

-- ============================================================================
-- Indexes for sem.SourcePage
-- ============================================================================

-- Unique index for source_system + resource_id + variant (business key)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UX_sem_SourcePage_SourceSystem_ResourceId_Variant' 
    AND object_id = OBJECT_ID('[sem].[SourcePage]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_sem_SourcePage_SourceSystem_ResourceId_Variant
    ON [sem].[SourcePage] (source_system, resource_id, variant)
    WHERE is_active = 1;
    PRINT 'Index [UX_sem_SourcePage_SourceSystem_ResourceId_Variant] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [UX_sem_SourcePage_SourceSystem_ResourceId_Variant] already exists.'
END
GO

-- Index for namespace lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_SourcePage_Namespace' 
    AND object_id = OBJECT_ID('[sem].[SourcePage]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_SourcePage_Namespace
    ON [sem].[SourcePage] (namespace, source_system);
    PRINT 'Index [IX_sem_SourcePage_Namespace] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_SourcePage_Namespace] already exists.'
END
GO

-- Index for continuity_hint lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_SourcePage_ContinuityHint' 
    AND object_id = OBJECT_ID('[sem].[SourcePage]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_SourcePage_ContinuityHint
    ON [sem].[SourcePage] (continuity_hint, source_system);
    PRINT 'Index [IX_sem_SourcePage_ContinuityHint] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_SourcePage_ContinuityHint] already exists.'
END
GO

-- Index for content hash lookups (deduplication)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_SourcePage_ContentHash' 
    AND object_id = OBJECT_ID('[sem].[SourcePage]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_SourcePage_ContentHash
    ON [sem].[SourcePage] (content_hash_sha256)
    WHERE content_hash_sha256 IS NOT NULL;
    PRINT 'Index [IX_sem_SourcePage_ContentHash] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_SourcePage_ContentHash] already exists.'
END
GO

-- Index for latest_ingest_id FK lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_SourcePage_LatestIngestId' 
    AND object_id = OBJECT_ID('[sem].[SourcePage]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_SourcePage_LatestIngestId
    ON [sem].[SourcePage] (latest_ingest_id)
    WHERE latest_ingest_id IS NOT NULL;
    PRINT 'Index [IX_sem_SourcePage_LatestIngestId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_SourcePage_LatestIngestId] already exists.'
END
GO

-- Index for updated_utc (recency queries)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_SourcePage_UpdatedUtc' 
    AND object_id = OBJECT_ID('[sem].[SourcePage]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_SourcePage_UpdatedUtc
    ON [sem].[SourcePage] (updated_utc DESC);
    PRINT 'Index [IX_sem_SourcePage_UpdatedUtc] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_SourcePage_UpdatedUtc] already exists.'
END
GO

PRINT 'Migration 0015 completed: sem.SourcePage table and indexes created.'
