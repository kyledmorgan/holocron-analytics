-- Migration 0006: Create LLM indexes and stored procedures
-- Idempotent: Only creates objects if they don't exist

-- ============================================================================
-- Indexes for llm.job table
-- ============================================================================

-- Primary queue index: status, priority (desc), available_utc, created_utc
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_job_queue' 
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_job_queue 
    ON [llm].[job] (status, priority DESC, available_utc, created_utc)
    INCLUDE (interrogation_key, model_hint, max_attempts, attempt_count);
    PRINT 'Index [IX_llm_job_queue] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_job_queue] already exists.'
END
GO

-- Index for job claiming (locked_by queries)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_job_locked' 
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_job_locked 
    ON [llm].[job] (locked_by, locked_utc)
    WHERE locked_by IS NOT NULL;
    PRINT 'Index [IX_llm_job_locked] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_job_locked] already exists.'
END
GO

-- Index for interrogation_key queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_job_interrogation' 
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_job_interrogation 
    ON [llm].[job] (interrogation_key, status, created_utc DESC);
    PRINT 'Index [IX_llm_job_interrogation] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_job_interrogation] already exists.'
END
GO

-- ============================================================================
-- Indexes for llm.run table
-- ============================================================================

-- Index for job_id lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_run_job' 
    AND object_id = OBJECT_ID('[llm].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_job 
    ON [llm].[run] (job_id, started_utc DESC);
    PRINT 'Index [IX_llm_run_job] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_run_job] already exists.'
END
GO

-- Index for worker queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_run_worker' 
    AND object_id = OBJECT_ID('[llm].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_worker 
    ON [llm].[run] (worker_id, started_utc DESC);
    PRINT 'Index [IX_llm_run_worker] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_run_worker] already exists.'
END
GO

-- Index for status queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_run_status' 
    AND object_id = OBJECT_ID('[llm].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_status 
    ON [llm].[run] (status, started_utc DESC);
    PRINT 'Index [IX_llm_run_status] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_run_status] already exists.'
END
GO

-- ============================================================================
-- Indexes for llm.artifact table
-- ============================================================================

-- Index for run_id lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_artifact_run' 
    AND object_id = OBJECT_ID('[llm].[artifact]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_artifact_run 
    ON [llm].[artifact] (run_id, artifact_type);
    PRINT 'Index [IX_llm_artifact_run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_artifact_run] already exists.'
END
GO

-- Index for artifact_type queries
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_artifact_type' 
    AND object_id = OBJECT_ID('[llm].[artifact]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_artifact_type 
    ON [llm].[artifact] (artifact_type, created_utc DESC);
    PRINT 'Index [IX_llm_artifact_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_artifact_type] already exists.'
END
GO

-- ============================================================================
-- Stored Procedure: llm.usp_claim_next_job
-- Atomically claims the next available job from the queue
-- ============================================================================
IF OBJECT_ID('[llm].[usp_claim_next_job]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_claim_next_job];
END
GO

CREATE PROCEDURE [llm].[usp_claim_next_job]
    @worker_id NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    DECLARE @job_id UNIQUEIDENTIFIER;
    DECLARE @now DATETIME2 = SYSUTCDATETIME();
    
    -- Use READPAST to skip locked rows, UPDLOCK to lock the selected row
    BEGIN TRANSACTION;
    
    SELECT TOP 1 @job_id = job_id
    FROM [llm].[job] WITH (READPAST, UPDLOCK)
    WHERE status = 'NEW'
      AND available_utc <= @now
      AND attempt_count < max_attempts
    ORDER BY priority DESC, available_utc ASC, created_utc ASC;
    
    IF @job_id IS NOT NULL
    BEGIN
        UPDATE [llm].[job]
        SET status = 'RUNNING',
            locked_by = @worker_id,
            locked_utc = @now,
            attempt_count = attempt_count + 1
        WHERE job_id = @job_id;
        
        -- Return the claimed job
        SELECT 
            job_id,
            created_utc,
            status,
            priority,
            interrogation_key,
            input_json,
            evidence_ref_json,
            model_hint,
            max_attempts,
            attempt_count,
            available_utc,
            locked_by,
            locked_utc,
            last_error
        FROM [llm].[job]
        WHERE job_id = @job_id;
    END
    
    COMMIT TRANSACTION;
END
GO

PRINT 'Stored procedure [llm].[usp_claim_next_job] created successfully.'
GO

-- ============================================================================
-- Stored Procedure: llm.usp_complete_job
-- Marks a job as completed (succeeded or failed)
-- ============================================================================
IF OBJECT_ID('[llm].[usp_complete_job]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_complete_job];
END
GO

CREATE PROCEDURE [llm].[usp_complete_job]
    @job_id UNIQUEIDENTIFIER,
    @status VARCHAR(20),
    @error NVARCHAR(MAX) = NULL,
    @backoff_seconds INT = 60
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @now DATETIME2 = SYSUTCDATETIME();
    DECLARE @attempt_count INT;
    DECLARE @max_attempts INT;
    DECLARE @new_status VARCHAR(20) = @status;
    
    -- Get current attempt info
    SELECT @attempt_count = attempt_count, @max_attempts = max_attempts
    FROM [llm].[job]
    WHERE job_id = @job_id;
    
    -- If failed and more attempts allowed, reset to NEW with backoff
    IF @status = 'FAILED' AND @attempt_count < @max_attempts
    BEGIN
        SET @new_status = 'NEW';
        
        UPDATE [llm].[job]
        SET status = @new_status,
            locked_by = NULL,
            locked_utc = NULL,
            last_error = @error,
            available_utc = DATEADD(SECOND, @backoff_seconds * @attempt_count, @now)
        WHERE job_id = @job_id;
    END
    ELSE IF @status = 'FAILED' AND @attempt_count >= @max_attempts
    BEGIN
        -- Deadletter: max attempts exceeded
        SET @new_status = 'DEADLETTER';
        
        UPDATE [llm].[job]
        SET status = @new_status,
            locked_by = NULL,
            locked_utc = NULL,
            last_error = @error
        WHERE job_id = @job_id;
    END
    ELSE
    BEGIN
        -- Success or explicit deadletter
        UPDATE [llm].[job]
        SET status = @new_status,
            locked_by = NULL,
            locked_utc = NULL,
            last_error = CASE WHEN @status = 'SUCCEEDED' THEN NULL ELSE @error END
        WHERE job_id = @job_id;
    END
    
    -- Return the final status
    SELECT @new_status AS final_status;
END
GO

PRINT 'Stored procedure [llm].[usp_complete_job] created successfully.'
GO

-- ============================================================================
-- Stored Procedure: llm.usp_enqueue_job
-- Enqueues a new job to the queue
-- ============================================================================
IF OBJECT_ID('[llm].[usp_enqueue_job]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_enqueue_job];
END
GO

CREATE PROCEDURE [llm].[usp_enqueue_job]
    @priority INT = 100,
    @interrogation_key NVARCHAR(200),
    @input_json NVARCHAR(MAX),
    @evidence_ref_json NVARCHAR(MAX) = NULL,
    @model_hint NVARCHAR(100) = NULL,
    @max_attempts INT = 3
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @job_id UNIQUEIDENTIFIER = NEWID();
    DECLARE @now DATETIME2 = SYSUTCDATETIME();
    
    INSERT INTO [llm].[job] (
        job_id,
        created_utc,
        status,
        priority,
        interrogation_key,
        input_json,
        evidence_ref_json,
        model_hint,
        max_attempts,
        attempt_count,
        available_utc
    )
    VALUES (
        @job_id,
        @now,
        'NEW',
        @priority,
        @interrogation_key,
        @input_json,
        @evidence_ref_json,
        @model_hint,
        @max_attempts,
        0,
        @now
    );
    
    -- Return the created job_id
    SELECT @job_id AS job_id;
END
GO

PRINT 'Stored procedure [llm].[usp_enqueue_job] created successfully.'
GO

-- ============================================================================
-- Stored Procedure: llm.usp_create_run
-- Creates a new run record for a job attempt
-- ============================================================================
IF OBJECT_ID('[llm].[usp_create_run]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_create_run];
END
GO

CREATE PROCEDURE [llm].[usp_create_run]
    @job_id UNIQUEIDENTIFIER,
    @worker_id NVARCHAR(200),
    @ollama_base_url NVARCHAR(500),
    @model_name NVARCHAR(100),
    @model_tag NVARCHAR(100) = NULL,
    @model_digest NVARCHAR(200) = NULL,
    @options_json NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @run_id UNIQUEIDENTIFIER = NEWID();
    
    INSERT INTO [llm].[run] (
        run_id,
        job_id,
        started_utc,
        status,
        worker_id,
        ollama_base_url,
        model_name,
        model_tag,
        model_digest,
        options_json
    )
    VALUES (
        @run_id,
        @job_id,
        SYSUTCDATETIME(),
        'RUNNING',
        @worker_id,
        @ollama_base_url,
        @model_name,
        @model_tag,
        @model_digest,
        @options_json
    );
    
    SELECT @run_id AS run_id;
END
GO

PRINT 'Stored procedure [llm].[usp_create_run] created successfully.'
GO

-- ============================================================================
-- Stored Procedure: llm.usp_complete_run
-- Completes a run with status and metrics
-- ============================================================================
IF OBJECT_ID('[llm].[usp_complete_run]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_complete_run];
END
GO

CREATE PROCEDURE [llm].[usp_complete_run]
    @run_id UNIQUEIDENTIFIER,
    @status VARCHAR(20),
    @metrics_json NVARCHAR(MAX) = NULL,
    @error NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE [llm].[run]
    SET completed_utc = SYSUTCDATETIME(),
        status = @status,
        metrics_json = @metrics_json,
        error = @error
    WHERE run_id = @run_id;
END
GO

PRINT 'Stored procedure [llm].[usp_complete_run] created successfully.'
GO

-- ============================================================================
-- Stored Procedure: llm.usp_create_artifact
-- Records an artifact written to the lake
-- ============================================================================
IF OBJECT_ID('[llm].[usp_create_artifact]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_create_artifact];
END
GO

CREATE PROCEDURE [llm].[usp_create_artifact]
    @run_id UNIQUEIDENTIFIER,
    @artifact_type NVARCHAR(100),
    @lake_uri NVARCHAR(1000),
    @content_sha256 NVARCHAR(64) = NULL,
    @byte_count BIGINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @artifact_id UNIQUEIDENTIFIER = NEWID();
    
    INSERT INTO [llm].[artifact] (
        artifact_id,
        run_id,
        artifact_type,
        content_sha256,
        byte_count,
        lake_uri,
        created_utc
    )
    VALUES (
        @artifact_id,
        @run_id,
        @artifact_type,
        @content_sha256,
        @byte_count,
        @lake_uri,
        SYSUTCDATETIME()
    );
    
    SELECT @artifact_id AS artifact_id;
END
GO

PRINT 'Stored procedure [llm].[usp_create_artifact] created successfully.'
GO
