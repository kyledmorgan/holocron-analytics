CREATE VIEW llm.vw_queue_health_by_type AS
SELECT
    interrogation_key,
    status,
    COUNT(*) AS job_count,
    AVG(priority) AS avg_priority,
    AVG(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) AS avg_age_minutes,
    MAX(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) AS max_age_minutes,
    AVG(attempt_count) AS avg_attempts,
    SUM(CASE WHEN attempt_count >= max_attempts THEN 1 ELSE 0 END) AS exhausted_retries
FROM llm.job
GROUP BY interrogation_key, status;
