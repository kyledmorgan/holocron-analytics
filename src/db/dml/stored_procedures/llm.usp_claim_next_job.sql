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
