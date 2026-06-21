CREATE PROCEDURE [dbo].[usp_get_entity_classification_status]
    @limit INT = 200
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@limit)
        e.EntityKey,
        e.EntityGuid,
        e.DisplayName,
        e.EntityType,
        e.IsLatest,
        e.IsActive,
        j.job_id       AS LastJobId,
        j.status        AS LastJobStatus,
        j.attempt_count AS LastJobAttemptCount,
        j.last_error    AS LastJobError,
        CASE
            WHEN e.EntityType IS NOT NULL AND e.IsLatest = 1 AND e.IsActive = 1
                THEN 'classified'
            WHEN j.status = 'RUNNING'
                THEN 'in_progress'
            WHEN j.status IN ('FAILED', 'DEADLETTER')
                THEN 'failed'
            WHEN j.status = 'SUCCEEDED'
                THEN 'succeeded'
            WHEN j.status = 'NEW'
                THEN 'pending'
            ELSE 'unprocessed'
        END AS ClassificationState
    FROM [dbo].[DimEntity] e
    LEFT JOIN [llm].[job] j
        ON j.dedupe_key = CONCAT('entity_classify:', CAST(e.EntityKey AS NVARCHAR))
    WHERE e.IsLatest = 1
      AND e.IsActive = 1
    ORDER BY e.EntityKey ASC;
END
