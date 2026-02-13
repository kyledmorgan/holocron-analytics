-- Migration 0025: Add job-level idempotency to llm.job
-- Adds dedupe_key column and unique constraint for preventing duplicate job enqueueing
-- Idempotent: Only creates column/constraint if they don't exist

-- ============================================================================
-- Add dedupe_key column to llm.job
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[llm].[job]') 
    AND name = 'dedupe_key'
)
BEGIN
    ALTER TABLE [llm].[job] 
    ADD dedupe_key NVARCHAR(500) NULL;
    PRINT 'Column [dedupe_key] added to [llm].[job].'
END
ELSE
BEGIN
    PRINT 'Column [dedupe_key] already exists in [llm].[job].'
END
GO

-- ============================================================================
-- Add unique constraint for idempotency
-- The constraint is on (interrogation_key, dedupe_key) where dedupe_key is not null
-- This allows jobs without dedupe_key but prevents duplicates when dedupe_key is set
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UQ_llm_job_dedupe' 
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UQ_llm_job_dedupe 
    ON [llm].[job] (interrogation_key, dedupe_key)
    WHERE dedupe_key IS NOT NULL;
    PRINT 'Unique index [UQ_llm_job_dedupe] created successfully.'
END
ELSE
BEGIN
    PRINT 'Unique index [UQ_llm_job_dedupe] already exists.'
END
GO

-- ============================================================================
-- Add index on dedupe_key for lookups
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_job_dedupe_key' 
    AND object_id = OBJECT_ID('[llm].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_job_dedupe_key 
    ON [llm].[job] (dedupe_key)
    WHERE dedupe_key IS NOT NULL;
    PRINT 'Index [IX_llm_job_dedupe_key] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_job_dedupe_key] already exists.'
END
GO

-- ============================================================================
-- Update stored procedure: llm.usp_enqueue_job
-- Add dedupe_key parameter and idempotent insert logic
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
    @max_attempts INT = 3,
    @dedupe_key NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @job_id UNIQUEIDENTIFIER;
    DECLARE @now DATETIME2 = SYSUTCDATETIME();
    DECLARE @existing_status VARCHAR(20);
    
    -- If dedupe_key is provided, check for existing job
    IF @dedupe_key IS NOT NULL
    BEGIN
        SELECT @job_id = job_id, @existing_status = status
        FROM [llm].[job]
        WHERE interrogation_key = @interrogation_key 
          AND dedupe_key = @dedupe_key;
        
        -- If job exists and is not terminal, return existing job_id
        IF @job_id IS NOT NULL
        BEGIN
            -- Log that we found a duplicate (for observability)
            -- Return existing job_id without inserting
            SELECT @job_id AS job_id, 1 AS is_duplicate, @existing_status AS existing_status;
            RETURN;
        END
    END
    
    -- Generate new job_id and insert
    SET @job_id = NEWID();
    
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
        available_utc,
        dedupe_key
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
        @now,
        @dedupe_key
    );
    
    -- Return the created job_id
    SELECT @job_id AS job_id, 0 AS is_duplicate, NULL AS existing_status;
END
GO

PRINT 'Stored procedure [llm].[usp_enqueue_job] updated with dedupe_key support.'
GO

-- ============================================================================
-- Add stored procedure: llm.usp_enqueue_job_idempotent
-- Wrapper for explicit idempotent enqueueing
-- ============================================================================
IF OBJECT_ID('[llm].[usp_enqueue_job_idempotent]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_enqueue_job_idempotent];
END
GO

CREATE PROCEDURE [llm].[usp_enqueue_job_idempotent]
    @interrogation_key NVARCHAR(200),
    @dedupe_key NVARCHAR(500),
    @input_json NVARCHAR(MAX),
    @evidence_ref_json NVARCHAR(MAX) = NULL,
    @model_hint NVARCHAR(100) = NULL,
    @priority INT = 100,
    @max_attempts INT = 3
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Validate dedupe_key is provided
    IF @dedupe_key IS NULL OR LEN(LTRIM(RTRIM(@dedupe_key))) = 0
    BEGIN
        RAISERROR('dedupe_key is required for idempotent job enqueue', 16, 1);
        RETURN;
    END
    
    -- Call the standard enqueue with dedupe_key
    EXEC [llm].[usp_enqueue_job]
        @priority = @priority,
        @interrogation_key = @interrogation_key,
        @input_json = @input_json,
        @evidence_ref_json = @evidence_ref_json,
        @model_hint = @model_hint,
        @max_attempts = @max_attempts,
        @dedupe_key = @dedupe_key;
END
GO

PRINT 'Stored procedure [llm].[usp_enqueue_job_idempotent] created successfully.'
GO

-- ============================================================================
-- Add stored procedure: llm.usp_get_job_by_dedupe_key
-- Lookup a job by its dedupe key
-- ============================================================================
IF OBJECT_ID('[llm].[usp_get_job_by_dedupe_key]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_get_job_by_dedupe_key];
END
GO

CREATE PROCEDURE [llm].[usp_get_job_by_dedupe_key]
    @interrogation_key NVARCHAR(200),
    @dedupe_key NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;
    
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
        last_error,
        dedupe_key
    FROM [llm].[job]
    WHERE interrogation_key = @interrogation_key 
      AND dedupe_key = @dedupe_key;
END
GO

PRINT 'Stored procedure [llm].[usp_get_job_by_dedupe_key] created successfully.'
GO
