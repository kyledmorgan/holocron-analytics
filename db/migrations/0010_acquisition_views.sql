-- Migration 0010: Acquisition views for common consumption patterns
-- Idempotent: Drops and recreates views
-- 
-- This migration creates views for efficient querying:
-- - Recent work items (last 90 days)
-- - Latest successful fetch per resource + variant
-- - Pending/failed work items with retry counts
-- - Resources with both RAW and HTML variants present
-- - Per-source system isolation

-- ============================================================================
-- View: Recent work items (last 90 days) - Hot working set
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_recent_work_items]'))
BEGIN
    DROP VIEW [ingest].[vw_recent_work_items];
END
GO

CREATE VIEW [ingest].[vw_recent_work_items]
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
    attempt,
    rank,
    created_at,
    updated_at,
    error_message,
    run_id
FROM [ingest].[work_items]
WHERE created_at >= DATEADD(DAY, -90, SYSUTCDATETIME());
GO

PRINT 'View [ingest].[vw_recent_work_items] created successfully.'
GO

-- ============================================================================
-- View: Archive/older work items (older than 90 days)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_archive_work_items]'))
BEGIN
    DROP VIEW [ingest].[vw_archive_work_items];
END
GO

CREATE VIEW [ingest].[vw_archive_work_items]
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
    attempt,
    rank,
    created_at,
    updated_at,
    error_message,
    run_id
FROM [ingest].[work_items]
WHERE created_at < DATEADD(DAY, -90, SYSUTCDATETIME());
GO

PRINT 'View [ingest].[vw_archive_work_items] created successfully.'
GO

-- ============================================================================
-- View: Pending and failed work items with retry info
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_pending_failed_work_items]'))
BEGIN
    DROP VIEW [ingest].[vw_pending_failed_work_items];
END
GO

CREATE VIEW [ingest].[vw_pending_failed_work_items]
AS
SELECT 
    work_item_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    request_uri,
    status,
    priority,
    attempt AS retry_count,
    rank,
    created_at,
    updated_at,
    error_message,
    run_id,
    CASE 
        WHEN status = 'pending' THEN 'ready'
        WHEN status = 'in_progress' THEN 'running'
        WHEN status = 'failed' AND attempt < 3 THEN 'retry_eligible'
        ELSE 'max_retries_exceeded'
    END AS retry_status
FROM [ingest].[work_items]
WHERE status IN ('pending', 'in_progress', 'failed');
GO

PRINT 'View [ingest].[vw_pending_failed_work_items] created successfully.'
GO

-- ============================================================================
-- View: Latest successful fetch per resource + variant
-- Uses ROW_NUMBER() to get only the most recent successful record
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_latest_successful_fetch]'))
BEGIN
    DROP VIEW [ingest].[vw_latest_successful_fetch];
END
GO

CREATE VIEW [ingest].[vw_latest_successful_fetch]
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
        status_code,
        content_type,
        content_length,
        file_path,
        hash_sha256,
        fetched_at_utc,
        duration_ms,
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
    status_code,
    content_type,
    content_length,
    file_path,
    hash_sha256,
    fetched_at_utc,
    duration_ms,
    work_item_id,
    run_id
FROM RankedRecords
WHERE rn = 1;
GO

PRINT 'View [ingest].[vw_latest_successful_fetch] created successfully.'
GO

-- ============================================================================
-- View: Recent successful fetches (last 90 days)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_recent_ingest_records]'))
BEGIN
    DROP VIEW [ingest].[vw_recent_ingest_records];
END
GO

CREATE VIEW [ingest].[vw_recent_ingest_records]
AS
SELECT 
    ingest_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    request_uri,
    status_code,
    content_type,
    content_length,
    file_path,
    hash_sha256,
    fetched_at_utc,
    duration_ms,
    error_message,
    work_item_id,
    run_id,
    attempt
FROM [ingest].[IngestRecords]
WHERE fetched_at_utc >= DATEADD(DAY, -90, SYSUTCDATETIME());
GO

PRINT 'View [ingest].[vw_recent_ingest_records] created successfully.'
GO

-- ============================================================================
-- View: Resources with both RAW and HTML variants successfully fetched
-- Useful for checking completeness of dual-variant acquisition
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_resources_with_both_variants]'))
BEGIN
    DROP VIEW [ingest].[vw_resources_with_both_variants];
END
GO

CREATE VIEW [ingest].[vw_resources_with_both_variants]
AS
WITH LatestRaw AS (
    SELECT 
        source_system,
        source_name,
        resource_type,
        resource_id,
        ingest_id AS raw_ingest_id,
        fetched_at_utc AS raw_fetched_at,
        status_code AS raw_status_code,
        file_path AS raw_file_path,
        content_length AS raw_content_length,
        ROW_NUMBER() OVER (
            PARTITION BY source_system, source_name, resource_type, resource_id
            ORDER BY fetched_at_utc DESC
        ) AS rn
    FROM [ingest].[IngestRecords]
    WHERE variant = 'raw' AND status_code >= 200 AND status_code < 300
),
LatestHtml AS (
    SELECT 
        source_system,
        source_name,
        resource_type,
        resource_id,
        ingest_id AS html_ingest_id,
        fetched_at_utc AS html_fetched_at,
        status_code AS html_status_code,
        file_path AS html_file_path,
        content_length AS html_content_length,
        ROW_NUMBER() OVER (
            PARTITION BY source_system, source_name, resource_type, resource_id
            ORDER BY fetched_at_utc DESC
        ) AS rn
    FROM [ingest].[IngestRecords]
    WHERE variant = 'html' AND status_code >= 200 AND status_code < 300
)
SELECT 
    r.source_system,
    r.source_name,
    r.resource_type,
    r.resource_id,
    r.raw_ingest_id,
    r.raw_fetched_at,
    r.raw_status_code,
    r.raw_file_path,
    r.raw_content_length,
    h.html_ingest_id,
    h.html_fetched_at,
    h.html_status_code,
    h.html_file_path,
    h.html_content_length,
    CASE 
        WHEN r.raw_fetched_at > h.html_fetched_at THEN r.raw_fetched_at
        ELSE h.html_fetched_at
    END AS latest_fetch_at
FROM LatestRaw r
INNER JOIN LatestHtml h 
    ON r.source_system = h.source_system
    AND r.source_name = h.source_name
    AND r.resource_type = h.resource_type
    AND r.resource_id = h.resource_id
WHERE r.rn = 1 AND h.rn = 1;
GO

PRINT 'View [ingest].[vw_resources_with_both_variants] created successfully.'
GO

-- ============================================================================
-- View: Response payload availability (DB stored vs file reference)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_payload_availability]'))
BEGIN
    DROP VIEW [ingest].[vw_payload_availability];
END
GO

CREATE VIEW [ingest].[vw_payload_availability]
AS
SELECT 
    ingest_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    fetched_at_utc,
    CASE 
        WHEN file_path IS NOT NULL THEN 'file_reference'
        WHEN payload IS NOT NULL AND LEN(payload) > 0 THEN 'db_stored'
        ELSE 'no_payload'
    END AS storage_type,
    file_path,
    content_length,
    content_type,
    hash_sha256
FROM [ingest].[IngestRecords];
GO

PRINT 'View [ingest].[vw_payload_availability] created successfully.'
GO

-- ============================================================================
-- View: Work item queue summary by source system
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[ingest].[vw_queue_summary_by_source]'))
BEGIN
    DROP VIEW [ingest].[vw_queue_summary_by_source];
END
GO

CREATE VIEW [ingest].[vw_queue_summary_by_source]
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

PRINT 'View [ingest].[vw_queue_summary_by_source] created successfully.'
GO

PRINT 'Migration 0010 completed: Acquisition views created.'
