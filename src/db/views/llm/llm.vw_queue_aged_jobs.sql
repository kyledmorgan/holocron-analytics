CREATE VIEW llm.vw_queue_aged_jobs AS
SELECT
    job_id,
    interrogation_key,
    status,
    priority,
    attempt_count,
    max_attempts,
    created_utc,
    DATEDIFF(MINUTE, created_utc, GETUTCDATE()) AS age_minutes,
    CASE
        WHEN DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 1440 THEN 'critical'
        WHEN DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 240 THEN 'warning'
        WHEN DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 60 THEN 'elevated'
        ELSE 'normal'
    END AS age_severity,
    --backoff_until,
    last_error
FROM llm.job
WHERE status IN ('NEW', 'RUNNING')
  AND DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 60;
