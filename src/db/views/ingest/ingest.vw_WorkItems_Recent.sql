-- ============================================================================
-- Views for recent work, latest successful fetch, and queue summary
-- ============================================================================

-- Recent work items (last 90 days)
CREATE   VIEW [ingest].[vw_WorkItems_Recent]
AS
SELECT
    work_item_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    request_uri,
    request_method,
    status,
    priority,
    attempt AS retry_count,
    rank,
    created_at,
    updated_at,
    error_message,
    error_type,
    run_id
FROM [ingest].[work_items]
WHERE created_at >= DATEADD(DAY, -90, SYSUTCDATETIME());
