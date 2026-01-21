-- Migration 0003: Create indexes and additional constraints
-- Idempotent: Only creates indexes if they don't exist

-- ============================================================================
-- Indexes for work_items table
-- ============================================================================

-- Index for queue dequeue operations (status + priority + created_at)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_status' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_status 
    ON [ingest].[work_items] (status, priority, created_at);
    PRINT 'Index [IX_work_items_status] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_status] already exists.'
END
GO

-- Unique index for deduplication
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_dedupe' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX IX_work_items_dedupe 
    ON [ingest].[work_items] (dedupe_key);
    PRINT 'Index [IX_work_items_dedupe] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_dedupe] already exists.'
END
GO

-- Index for run_id queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_run_id' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_run_id 
    ON [ingest].[work_items] (run_id)
    WHERE run_id IS NOT NULL;
    PRINT 'Index [IX_work_items_run_id] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_run_id] already exists.'
END
GO

-- Index for source system queries (useful for re-crawl)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_source' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_source 
    ON [ingest].[work_items] (source_system, source_name);
    PRINT 'Index [IX_work_items_source] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_source] already exists.'
END
GO

-- ============================================================================
-- Indexes for IngestRecords table
-- ============================================================================

-- Index for deduplication lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_Dedupe' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_Dedupe 
    ON [ingest].[IngestRecords] (source_system, source_name, resource_type, resource_id, fetched_at_utc DESC);
    PRINT 'Index [IX_IngestRecords_Dedupe] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_Dedupe] already exists.'
END
GO

-- Index for run tracking
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_RunId' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_RunId 
    ON [ingest].[IngestRecords] (run_id, fetched_at_utc DESC)
    WHERE run_id IS NOT NULL;
    PRINT 'Index [IX_IngestRecords_RunId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_RunId] already exists.'
END
GO

-- Index for work item reference
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_WorkItemId' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_WorkItemId 
    ON [ingest].[IngestRecords] (work_item_id)
    WHERE work_item_id IS NOT NULL;
    PRINT 'Index [IX_IngestRecords_WorkItemId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_WorkItemId] already exists.'
END
GO

-- Index for temporal queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_FetchedAt' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_FetchedAt 
    ON [ingest].[IngestRecords] (fetched_at_utc DESC);
    PRINT 'Index [IX_IngestRecords_FetchedAt] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_FetchedAt] already exists.'
END
GO

-- ============================================================================
-- Indexes for ingest_runs table
-- ============================================================================

-- Index for status and time queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_ingest_runs_status' 
    AND object_id = OBJECT_ID('[ingest].[ingest_runs]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_ingest_runs_status 
    ON [ingest].[ingest_runs] (status, started_at DESC);
    PRINT 'Index [IX_ingest_runs_status] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_ingest_runs_status] already exists.'
END
GO

-- ============================================================================
-- Indexes for seen_resources table
-- ============================================================================

-- Index for source system lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_seen_resources_source' 
    AND object_id = OBJECT_ID('[ingest].[seen_resources]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_seen_resources_source 
    ON [ingest].[seen_resources] (source_system, source_name, resource_type);
    PRINT 'Index [IX_seen_resources_source] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_seen_resources_source] already exists.'
END
GO

-- Index for last_seen_at queries (for stale detection)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_seen_resources_last_seen' 
    AND object_id = OBJECT_ID('[ingest].[seen_resources]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_seen_resources_last_seen 
    ON [ingest].[seen_resources] (last_seen_at DESC);
    PRINT 'Index [IX_seen_resources_last_seen] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_seen_resources_last_seen] already exists.'
END
GO
