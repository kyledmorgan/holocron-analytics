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
