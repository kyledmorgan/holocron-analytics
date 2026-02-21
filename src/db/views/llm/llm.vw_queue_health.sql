CREATE VIEW llm.vw_queue_health AS
SELECT
    status,
    COUNT(*) AS job_count,
    AVG(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) AS avg_age_minutes,
    MIN(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) AS min_age_minutes,
    MAX(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) AS max_age_minutes,
    SUM(CASE WHEN DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 60 THEN 1 ELSE 0 END) AS jobs_over_1h,
    SUM(CASE WHEN DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 240 THEN 1 ELSE 0 END) AS jobs_over_4h,
    SUM(CASE WHEN DATEDIFF(MINUTE, created_utc, GETUTCDATE()) > 1440 THEN 1 ELSE 0 END) AS jobs_over_24h
FROM llm.job
GROUP BY status;
