CREATE PROCEDURE llm.usp_escalate_aged_jobs
    @age_threshold_minutes INT = 60,
    @priority_boost INT = 50,
    @max_priority INT = 300,
    @max_jobs_per_run INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @affected_count INT = 0;

    -- Escalate aged jobs that are still pending
    UPDATE TOP (@max_jobs_per_run) llm.job
    SET
        priority = CASE
            WHEN priority + @priority_boost > @max_priority THEN @max_priority
            ELSE priority + @priority_boost
        END

        --,
        --updated_utc = GETUTCDATE()
    WHERE status = 'NEW'
      AND DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > @age_threshold_minutes
      AND priority < @max_priority;

    SET @affected_count = @@ROWCOUNT;

    -- Return summary
    SELECT
        @affected_count AS jobs_escalated,
        @age_threshold_minutes AS age_threshold_minutes,
        @priority_boost AS priority_boost,
        @max_priority AS max_priority;
END;
