-- Migration 0002: Create ingest tables
-- Idempotent: Only creates tables if they don't exist

-- ============================================================================
-- work_items table: Manages work queue for ingestion pipeline
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'work_items' AND s.name = 'ingest'
)
BEGIN
    CREATE TABLE [ingest].[work_items] (
        work_item_id NVARCHAR(36) NOT NULL,
        source_system NVARCHAR(100) NOT NULL,
        source_name NVARCHAR(100) NOT NULL,
        resource_type NVARCHAR(100) NOT NULL,
        resource_id NVARCHAR(500) NOT NULL,
        request_uri NVARCHAR(2000) NOT NULL,
        request_method NVARCHAR(10) NOT NULL,
        request_headers NVARCHAR(MAX),
        request_body NVARCHAR(MAX),
        metadata NVARCHAR(MAX),
        priority INT NOT NULL DEFAULT 100,
        status NVARCHAR(20) NOT NULL,
        attempt INT NOT NULL DEFAULT 0,
        run_id NVARCHAR(36),
        discovered_from NVARCHAR(36),
        created_at DATETIME2 NOT NULL,
        updated_at DATETIME2 NOT NULL,
        error_message NVARCHAR(MAX),
        dedupe_key NVARCHAR(800) NOT NULL,
        
        CONSTRAINT PK_work_items PRIMARY KEY CLUSTERED (work_item_id),
        CONSTRAINT CK_work_items_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
        CONSTRAINT CK_work_items_attempt CHECK (attempt >= 0)
    );
    PRINT 'Table [ingest].[work_items] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [ingest].[work_items] already exists.'
END
GO

-- ============================================================================
-- IngestRecords table: Stores raw ingestion data
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'IngestRecords' AND s.name = 'ingest'
)
BEGIN
    CREATE TABLE [ingest].[IngestRecords] (
        ingest_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        source_system NVARCHAR(100) NOT NULL,
        source_name NVARCHAR(100) NOT NULL,
        resource_type NVARCHAR(100) NOT NULL,
        resource_id NVARCHAR(500) NOT NULL,
        request_uri NVARCHAR(2000) NOT NULL,
        request_method NVARCHAR(10) NOT NULL,
        request_headers NVARCHAR(MAX),
        status_code INT NOT NULL,
        response_headers NVARCHAR(MAX),
        payload NVARCHAR(MAX) NOT NULL,
        fetched_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        hash_sha256 NVARCHAR(64),
        run_id UNIQUEIDENTIFIER,
        work_item_id UNIQUEIDENTIFIER,
        attempt INT NOT NULL DEFAULT 1,
        error_message NVARCHAR(MAX),
        duration_ms INT,
        
        CONSTRAINT PK_IngestRecords PRIMARY KEY CLUSTERED (ingest_id),
        CONSTRAINT CK_IngestRecords_StatusCode CHECK (status_code BETWEEN 0 AND 999),
        CONSTRAINT CK_IngestRecords_Attempt CHECK (attempt > 0)
    );
    PRINT 'Table [ingest].[IngestRecords] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [ingest].[IngestRecords] already exists.'
END
GO

-- ============================================================================
-- ingest_runs table: Tracks ingestion run metadata
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'ingest_runs' AND s.name = 'ingest'
)
BEGIN
    CREATE TABLE [ingest].[ingest_runs] (
        run_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        started_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        completed_at DATETIME2,
        status NVARCHAR(20) NOT NULL DEFAULT 'running',
        items_processed INT NOT NULL DEFAULT 0,
        items_succeeded INT NOT NULL DEFAULT 0,
        items_failed INT NOT NULL DEFAULT 0,
        items_discovered INT NOT NULL DEFAULT 0,
        config_hash NVARCHAR(64),
        metadata NVARCHAR(MAX),
        
        CONSTRAINT PK_ingest_runs PRIMARY KEY CLUSTERED (run_id),
        CONSTRAINT CK_ingest_runs_status CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
    );
    PRINT 'Table [ingest].[ingest_runs] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [ingest].[ingest_runs] already exists.'
END
GO

-- ============================================================================
-- seen_resources table: Tracks unique resources seen during ingestion
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'seen_resources' AND s.name = 'ingest'
)
BEGIN
    CREATE TABLE [ingest].[seen_resources] (
        resource_key NVARCHAR(800) NOT NULL,
        source_system NVARCHAR(100) NOT NULL,
        source_name NVARCHAR(100) NOT NULL,
        resource_type NVARCHAR(100) NOT NULL,
        resource_id NVARCHAR(500) NOT NULL,
        first_seen_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        last_seen_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        seen_count INT NOT NULL DEFAULT 1,
        last_run_id UNIQUEIDENTIFIER,
        
        CONSTRAINT PK_seen_resources PRIMARY KEY CLUSTERED (resource_key)
    );
    PRINT 'Table [ingest].[seen_resources] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [ingest].[seen_resources] already exists.'
END
GO
