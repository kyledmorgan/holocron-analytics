CREATE VIEW llm.vw_queue_summary_by_priority AS
SELECT
    CASE
        WHEN priority >= 200 THEN 'urgent (200+)'
        WHEN priority >= 100 THEN 'normal (100-199)'
        WHEN priority >= 50 THEN 'backfill (50-99)'
        ELSE 'low (<50)'
    END AS priority_band,
    status,
    COUNT(*) AS job_count,
    AVG(DATEDIFF(MINUTE, created_utc, GETUTCDATE())) AS avg_age_minutes
FROM llm.job
GROUP BY
    CASE
        WHEN priority >= 200 THEN 'urgent (200+)'
        WHEN priority >= 100 THEN 'normal (100-199)'
        WHEN priority >= 50 THEN 'backfill (50-99)'
        ELSE 'low (<50)'
    END,
    status;
