-- Create IngestRecords table for storing raw ingestion data
-- This table stores JSON blobs with minimal metadata for tracking and deduplication

IF OBJECT_ID('ingest.IngestRecords', 'U') IS NOT NULL
    DROP TABLE ingest.IngestRecords;
GO

CREATE TABLE ingest.IngestRecords (
    -- Primary key
    ingest_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    
    -- Source identification
    source_system NVARCHAR(100) NOT NULL,  -- e.g., 'mediawiki', 'http_scrape'
    source_name NVARCHAR(100) NOT NULL,    -- e.g., 'wikipedia', 'wookieepedia'
    resource_type NVARCHAR(100) NOT NULL,  -- e.g., 'page', 'category', 'revision'
    resource_id NVARCHAR(500) NOT NULL,    -- Remote ID/title/URL key
    
    -- Request metadata
    request_uri NVARCHAR(2000) NOT NULL,
    request_method NVARCHAR(10) NOT NULL,  -- GET, POST, etc.
    request_headers NVARCHAR(MAX),         -- JSON
    
    -- Response metadata
    status_code INT NOT NULL,
    response_headers NVARCHAR(MAX),        -- JSON
    
    -- Payload (the actual data)
    payload NVARCHAR(MAX) NOT NULL,        -- JSON blob
    
    -- Tracking metadata
    fetched_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    hash_sha256 NVARCHAR(64),              -- For change detection
    run_id UNIQUEIDENTIFIER,               -- Batch run grouping
    work_item_id UNIQUEIDENTIFIER,         -- Reference to work item
    attempt INT NOT NULL DEFAULT 1,        -- Retry attempt number
    error_message NVARCHAR(MAX),           -- Error if failed
    duration_ms INT,                       -- Request duration
    
    -- Constraints
    CONSTRAINT PK_IngestRecords PRIMARY KEY CLUSTERED (ingest_id),
    CONSTRAINT CK_IngestRecords_StatusCode CHECK (status_code BETWEEN 0 AND 999),
    CONSTRAINT CK_IngestRecords_Attempt CHECK (attempt > 0)
);
GO

-- Index for deduplication lookups
CREATE NONCLUSTERED INDEX IX_IngestRecords_Dedupe 
    ON ingest.IngestRecords (source_system, source_name, resource_type, resource_id, fetched_at_utc DESC);
GO

-- Index for run tracking
CREATE NONCLUSTERED INDEX IX_IngestRecords_RunId 
    ON ingest.IngestRecords (run_id, fetched_at_utc DESC)
    WHERE run_id IS NOT NULL;
GO

-- Index for work item reference
CREATE NONCLUSTERED INDEX IX_IngestRecords_WorkItemId 
    ON ingest.IngestRecords (work_item_id)
    WHERE work_item_id IS NOT NULL;
GO

-- Index for temporal queries
CREATE NONCLUSTERED INDEX IX_IngestRecords_FetchedAt 
    ON ingest.IngestRecords (fetched_at_utc DESC);
GO
