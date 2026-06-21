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
