CREATE PROCEDURE llm.usp_get_queue_health_summary
AS
BEGIN
    SET NOCOUNT ON;

    -- Overall queue metrics
    SELECT
        (SELECT COUNT(*) FROM llm.job WHERE status = 'NEW') AS pending_jobs,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'RUNNING') AS running_jobs,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'SUCCEEDED' AND created_utc > DATEADD(HOUR, -24, GETUTCDATE())) AS succeeded_24h,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'FAILED' AND created_utc > DATEADD(HOUR, -24, GETUTCDATE())) AS failed_24h,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'DEADLETTER') AS deadletter_total,
        (SELECT AVG(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) FROM llm.job WHERE status = 'NEW') AS avg_pending_age_minutes,
        (SELECT MAX(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) FROM llm.job WHERE status = 'NEW') AS max_pending_age_minutes,
        (SELECT COUNT(*) FROM llm.job WHERE status = 'NEW' AND DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 60) AS stale_job_count;

    -- Queue health by status
    SELECT * FROM llm.vw_queue_health;

    -- Aged jobs requiring attention
    SELECT TOP 20 * FROM llm.vw_queue_aged_jobs ORDER BY age_minutes DESC;
END;
