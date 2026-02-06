-- Migration 0009: Extended acquisition schema for full HTTP request/response persistence
-- Idempotent: Only modifies tables if columns don't exist
-- 
-- This migration extends the work_items and IngestRecords tables to support:
-- - Variant tracking (RAW vs HTML)
-- - Full response metadata (content_type, content_length, timestamps)
-- - File reference linkage for large payloads
-- - Rank-based prioritization
-- - Efficient queries by source_system and recency

-- ============================================================================
-- Extend work_items table with variant and rank columns
-- ============================================================================

-- Add variant column for RAW/HTML distinction
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'variant'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD variant NVARCHAR(20) NULL;
    PRINT 'Column [variant] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [variant] already exists on [ingest].[work_items].'
END
GO

-- Add rank column for inbound link ranking
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'rank'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD rank INT NULL;
    PRINT 'Column [rank] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [rank] already exists on [ingest].[work_items].'
END
GO

-- Add request_timestamp for when request was initiated
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'request_timestamp'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD request_timestamp DATETIME2 NULL;
    PRINT 'Column [request_timestamp] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [request_timestamp] already exists on [ingest].[work_items].'
END
GO

-- ============================================================================
-- Extend IngestRecords table with additional response metadata
-- ============================================================================

-- Add variant column
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'variant'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD variant NVARCHAR(20) NULL;
    PRINT 'Column [variant] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [variant] already exists on [ingest].[IngestRecords].'
END
GO

-- Add content_type for MIME type
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'content_type'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD content_type NVARCHAR(200) NULL;
    PRINT 'Column [content_type] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [content_type] already exists on [ingest].[IngestRecords].'
END
GO

-- Add content_length for response size
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'content_length'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD content_length BIGINT NULL;
    PRINT 'Column [content_length] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [content_length] already exists on [ingest].[IngestRecords].'
END
GO

-- Add file_path for large payload file references
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'file_path'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD file_path NVARCHAR(2000) NULL;
    PRINT 'Column [file_path] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [file_path] already exists on [ingest].[IngestRecords].'
END
GO

-- Add request_timestamp
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'request_timestamp'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD request_timestamp DATETIME2 NULL;
    PRINT 'Column [request_timestamp] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [request_timestamp] already exists on [ingest].[IngestRecords].'
END
GO

-- Add response_timestamp
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'response_timestamp'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD response_timestamp DATETIME2 NULL;
    PRINT 'Column [response_timestamp] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [response_timestamp] already exists on [ingest].[IngestRecords].'
END
GO

-- Add rank column for tracking inbound link rank
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]') 
    AND name = 'rank'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords] 
    ADD rank INT NULL;
    PRINT 'Column [rank] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [rank] already exists on [ingest].[IngestRecords].'
END
GO

-- ============================================================================
-- Additional indexes for efficient querying
-- ============================================================================

-- Composite index on work_items for variant + source queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_source_variant' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_source_variant 
    ON [ingest].[work_items] (source_system, source_name, variant, status);
    PRINT 'Index [IX_work_items_source_variant] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_source_variant] already exists.'
END
GO

-- Index for recency queries on work_items
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_created_at' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_created_at 
    ON [ingest].[work_items] (created_at DESC);
    PRINT 'Index [IX_work_items_created_at] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_created_at] already exists.'
END
GO

-- Composite index on IngestRecords for variant queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_variant' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_variant 
    ON [ingest].[IngestRecords] (source_system, source_name, resource_id, variant, fetched_at_utc DESC);
    PRINT 'Index [IX_IngestRecords_variant] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_variant] already exists.'
END
GO

-- Index for source system isolation
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_source_system' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_source_system 
    ON [ingest].[IngestRecords] (source_system, source_name, fetched_at_utc DESC);
    PRINT 'Index [IX_IngestRecords_source_system] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_source_system] already exists.'
END
GO

-- Index for file_path lookups (records with file references)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_IngestRecords_file_path' 
    AND object_id = OBJECT_ID('[ingest].[IngestRecords]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_IngestRecords_file_path 
    ON [ingest].[IngestRecords] (file_path)
    WHERE file_path IS NOT NULL;
    PRINT 'Index [IX_IngestRecords_file_path] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_IngestRecords_file_path] already exists.'
END
GO

PRINT 'Migration 0009 completed: Extended acquisition schema created.'
