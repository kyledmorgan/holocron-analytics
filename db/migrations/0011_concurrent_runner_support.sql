-- Migration 0011: Concurrent runner support with atomic claim/lease semantics
-- Idempotent: Only modifies tables if columns don't exist
-- 
-- This migration adds support for concurrent runners processing work items:
-- - Atomic claim/lease columns on work_items
-- - Worker heartbeat tracking table
-- - Indexes for efficient claim queries

-- ============================================================================
-- Extend work_items table with claim/lease columns
-- ============================================================================

-- Add claimed_by column (worker ID that owns this item)
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'claimed_by'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD claimed_by NVARCHAR(100) NULL;
    PRINT 'Column [claimed_by] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [claimed_by] already exists on [ingest].[work_items].'
END
GO

-- Add claimed_at column (when the item was claimed)
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'claimed_at'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD claimed_at DATETIME2 NULL;
    PRINT 'Column [claimed_at] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [claimed_at] already exists on [ingest].[work_items].'
END
GO

-- Add lease_expires_at column (when the lease expires)
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'lease_expires_at'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD lease_expires_at DATETIME2 NULL;
    PRINT 'Column [lease_expires_at] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [lease_expires_at] already exists on [ingest].[work_items].'
END
GO

-- Add last_error column (for retry visibility)
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'last_error'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD last_error NVARCHAR(MAX) NULL;
    PRINT 'Column [last_error] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [last_error] already exists on [ingest].[work_items].'
END
GO

-- Add next_retry_at column (for backoff scheduling)
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[ingest].[work_items]') 
    AND name = 'next_retry_at'
)
BEGIN
    ALTER TABLE [ingest].[work_items] 
    ADD next_retry_at DATETIME2 NULL;
    PRINT 'Column [next_retry_at] added to [ingest].[work_items].'
END
ELSE
BEGIN
    PRINT 'Column [next_retry_at] already exists on [ingest].[work_items].'
END
GO

-- ============================================================================
-- Create worker_heartbeats table for tracking active workers
-- ============================================================================

IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'worker_heartbeats' AND s.name = 'ingest'
)
BEGIN
    CREATE TABLE [ingest].[worker_heartbeats] (
        worker_id NVARCHAR(100) PRIMARY KEY,
        hostname NVARCHAR(255) NOT NULL,
        pid INT NOT NULL,
        started_at DATETIME2 NOT NULL,
        last_heartbeat_at DATETIME2 NOT NULL,
        items_processed INT NOT NULL DEFAULT 0,
        items_succeeded INT NOT NULL DEFAULT 0,
        items_failed INT NOT NULL DEFAULT 0,
        status NVARCHAR(20) NOT NULL DEFAULT 'active',
        current_work_item_id NVARCHAR(36) NULL
    );
    PRINT 'Table [ingest].[worker_heartbeats] created.'
END
ELSE
BEGIN
    PRINT 'Table [ingest].[worker_heartbeats] already exists.'
END
GO

-- ============================================================================
-- Create run_metrics table for aggregate run tracking
-- ============================================================================

IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'run_metrics' AND s.name = 'ingest'
)
BEGIN
    CREATE TABLE [ingest].[run_metrics] (
        run_id NVARCHAR(36) PRIMARY KEY,
        started_at DATETIME2 NOT NULL,
        ended_at DATETIME2 NULL,
        max_workers INT NOT NULL,
        items_processed INT NOT NULL DEFAULT 0,
        items_succeeded INT NOT NULL DEFAULT 0,
        items_failed INT NOT NULL DEFAULT 0,
        items_discovered INT NOT NULL DEFAULT 0,
        retry_count INT NOT NULL DEFAULT 0,
        backoff_events INT NOT NULL DEFAULT 0,
        status NVARCHAR(20) NOT NULL DEFAULT 'running'
    );
    PRINT 'Table [ingest].[run_metrics] created.'
END
ELSE
BEGIN
    PRINT 'Table [ingest].[run_metrics] already exists.'
END
GO

-- ============================================================================
-- Indexes for concurrent claim queries
-- ============================================================================

-- Index for finding claimable items (pending + eligible for retry)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_claimable' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_claimable 
    ON [ingest].[work_items] (status, next_retry_at, priority, rank DESC, created_at)
    WHERE status IN ('pending', 'in_progress');
    PRINT 'Index [IX_work_items_claimable] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_claimable] already exists.'
END
GO

-- Index for lease expiration recovery
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_lease_expires' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_lease_expires 
    ON [ingest].[work_items] (lease_expires_at, status)
    WHERE status = 'in_progress';
    PRINT 'Index [IX_work_items_lease_expires] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_lease_expires] already exists.'
END
GO

-- Index for worker-specific queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_work_items_claimed_by' 
    AND object_id = OBJECT_ID('[ingest].[work_items]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_work_items_claimed_by 
    ON [ingest].[work_items] (claimed_by, status);
    PRINT 'Index [IX_work_items_claimed_by] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_work_items_claimed_by] already exists.'
END
GO

PRINT 'Migration 0011 completed: Concurrent runner support added.'
