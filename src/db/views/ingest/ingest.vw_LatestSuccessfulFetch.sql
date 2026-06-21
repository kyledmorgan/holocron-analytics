-- Latest successful fetch per resource + variant
CREATE   VIEW [ingest].[vw_LatestSuccessfulFetch]
AS
WITH RankedRecords AS (
    SELECT
        ingest_id,
        source_system,
        source_name,
        resource_type,
        resource_id,
        variant,
        request_uri,
        request_method,
        status_code,
        content_type,
        content_length,
        file_path,
        hash_sha256,
        fetched_at_utc,
        duration_ms,
        error_message,
        error_type,
        work_item_id,
        run_id,
        ROW_NUMBER() OVER (
            PARTITION BY source_system, source_name, resource_type, resource_id, variant
            ORDER BY fetched_at_utc DESC
        ) AS rn
    FROM [ingest].[IngestRecords]
    WHERE status_code >= 200 AND status_code < 300
)
SELECT
    ingest_id,
    source_system,
    source_name,
    resource_type,
    resource_id,
    variant,
    request_uri,
    request_method,
    status_code,
    content_type,
    content_length,
    file_path,
    hash_sha256,
    fetched_at_utc,
    duration_ms,
    error_message,
    error_type,
    work_item_id,
    run_id
FROM RankedRecords
WHERE rn = 1;
