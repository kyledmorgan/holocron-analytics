-- Queue summary by status + source_system
CREATE   VIEW [ingest].[vw_WorkItems_QueueSummary]
AS
SELECT
    source_system,
    source_name,
    status,
    variant,
    COUNT(*) AS item_count,
    MIN(created_at) AS oldest_item,
    MAX(created_at) AS newest_item,
    SUM(CASE WHEN attempt > 0 THEN 1 ELSE 0 END) AS items_with_retries,
    MAX(attempt) AS max_retries
FROM [ingest].[work_items]
GROUP BY source_system, source_name, status, variant;
