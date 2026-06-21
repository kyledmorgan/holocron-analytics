-- Migration 0012: Additive-only updates for content runner acquisition tracking
-- Idempotent: Only adds missing columns/indexes and uses CREATE OR ALTER VIEW
-- NOTE: No destructive statements (no DROP).

USE [Holocron];
GO

-- ============================================================================
-- Extend ingest.work_items with optional timing/diagnostic fields
-- ============================================================================

-- Ensure variant column exists (backfill if 0009 not applied)
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

-- Ensure rank column exists (backfill if 0009 not applied)
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

-- Track request start time (if not already present)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[work_items]')
    AND name = 'request_started_at'
)
BEGIN
    ALTER TABLE [ingest].[work_items]
    ADD request_started_at DATETIME2 NULL;
    PRINT 'Column [request_started_at] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [request_started_at] already exists on [ingest].[work_items].'
END
GO

-- Track request finish time (optional)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[work_items]')
    AND name = 'request_finished_at'
)
BEGIN
    ALTER TABLE [ingest].[work_items]
    ADD request_finished_at DATETIME2 NULL;
    PRINT 'Column [request_finished_at] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [request_finished_at] already exists on [ingest].[work_items].'
END
GO

-- Track last heartbeat per work item (optional)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[work_items]')
    AND name = 'last_heartbeat_at'
)
BEGIN
    ALTER TABLE [ingest].[work_items]
    ADD last_heartbeat_at DATETIME2 NULL;
    PRINT 'Column [last_heartbeat_at] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [last_heartbeat_at] already exists on [ingest].[work_items].'
END
GO

-- Classify errors (optional)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[work_items]')
    AND name = 'error_type'
)
BEGIN
    ALTER TABLE [ingest].[work_items]
    ADD error_type NVARCHAR(200) NULL;
    PRINT 'Column [error_type] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [error_type] already exists on [ingest].[work_items].'
END
GO

-- Link to rank source artifact (optional, reference id or opaque key)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[work_items]')
    AND name = 'rank_source_artifact_id'
)
BEGIN
    ALTER TABLE [ingest].[work_items]
    ADD rank_source_artifact_id NVARCHAR(100) NULL;
    PRINT 'Column [rank_source_artifact_id] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [rank_source_artifact_id] already exists on [ingest].[work_items].'
END
GO

-- ============================================================================
-- Extend ingest.IngestRecords with full request/response capture
-- ============================================================================

-- Ensure variant column exists (backfill if 0009 not applied)
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

-- Ensure content_type column exists
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

-- Ensure content_length column exists
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

-- Ensure file_path column exists for file-backed payloads
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

-- Persist request body (if used)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]')
    AND name = 'request_body'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords]
    ADD request_body NVARCHAR(MAX) NULL;
    PRINT 'Column [request_body] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [request_body] already exists on [ingest].[IngestRecords].'
END
GO

-- Optional binary payload storage for non-text responses
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]')
    AND name = 'response_body_binary'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords]
    ADD response_body_binary VARBINARY(MAX) NULL;
    PRINT 'Column [response_body_binary] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [response_body_binary] already exists on [ingest].[IngestRecords].'
END
GO

-- Classify errors (optional)
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('[ingest].[IngestRecords]')
    AND name = 'error_type'
)
BEGIN
    ALTER TABLE [ingest].[IngestRecords]
    ADD error_type NVARCHAR(200) NULL;
    PRINT 'Column [error_type] added to [ingest].[IngestRecords].'
END
ELSE
BEGIN
    PRINT 'Column [error_type] already exists on [ingest].[IngestRecords].'
END
GO

-- ============================================================================
-- Additional indexes for content runner patterns
-- ============================================================================

-- Fast lookup by source_system + recency (include status + variant)
IF NOT EXISTS (
    SELECT * FROM sys.indexes
    WHERE name = 'IX_work_items_source_created'
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_source_created
    ON [ingest].[work_items] (source_system, created_at DESC)
    INCLUDE (status, variant);
    PRINT 'Index [IX_work_items_source_created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_source_created] already exists.'
END
GO

-- Lookup by resource identity + variant
IF NOT EXISTS (
    SELECT * FROM sys.indexes
    WHERE name = 'IX_work_items_identity_variant'
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_identity_variant
    ON [ingest].[work_items] (source_system, resource_id, variant);
    PRINT 'Index [IX_work_items_identity_variant] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_identity_variant] already exists.'
END
GO

-- ============================================================================
-- Views for recent work, latest successful fetch, and queue summary
-- ============================================================================

-- Recent work items (last 90 days)
CREATE OR ALTER VIEW [ingest].[vw_WorkItems_Recent]
AS
SELECT
    work_item_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    request_uri,
    request_method,
    status,
    priority,
    attempt AS retry_count,
    rank,
    created_at,
    updated_at,
    error_message,
    error_type,
    run_id
FROM [ingest].[work_items]
WHERE created_at >= DATEADD(DAY, -90, SYSUTCDATETIME());
GO

PRINT 'View [ingest].[vw_WorkItems_Recent] created or altered successfully.'
GO

-- Latest successful fetch per resource + variant
CREATE OR ALTER VIEW [ingest].[vw_LatestSuccessfulFetch]
AS
WITH RankedRecords AS (
    SELECT
        ingest_id,
        source_system,
        source_name,
        resource_type,
        resource_id,
        variant,
        request_uri,
        request_method,
        status_code,
        content_type,
        content_length,
        file_path,
        hash_sha256,
        fetched_at_utc,
        duration_ms,
        error_message,
        error_type,
        work_item_id,
        run_id,
        ROW_NUMBER() OVER (
            PARTITION BY source_system, source_name, resource_type, resource_id, variant
            ORDER BY fetched_at_utc DESC
        ) AS rn
    FROM [ingest].[IngestRecords]
    WHERE status_code >= 200 AND status_code < 300
)
SELECT
    ingest_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    request_uri,
    request_method,
    status_code,
    content_type,
    content_length,
    file_path,
    hash_sha256,
    fetched_at_utc,
    duration_ms,
    error_message,
    error_type,
    work_item_id,
    run_id
FROM RankedRecords
WHERE rn = 1;
GO

PRINT 'View [ingest].[vw_LatestSuccessfulFetch] created or altered successfully.'
GO

-- Queue summary by status + source_system
CREATE OR ALTER VIEW [ingest].[vw_WorkItems_QueueSummary]
AS
SELECT
    source_system,
    source_name,
    status,
    variant,
    COUNT(*) AS item_count,
    MIN(created_at) AS oldest_item,
    MAX(created_at) AS newest_item,
    SUM(CASE WHEN attempt > 0 THEN 1 ELSE 0 END) AS items_with_retries,
    MAX(attempt) AS max_retries
FROM [ingest].[work_items]
GROUP BY source_system, source_name, status, variant;
GO

PRINT 'View [ingest].[vw_WorkItems_QueueSummary] created or altered successfully.'
GO

PRINT 'Migration 0012 completed: Content runner acquisition updates applied.'
