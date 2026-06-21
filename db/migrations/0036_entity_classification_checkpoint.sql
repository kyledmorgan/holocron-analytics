-- Migration 0036: Entity classification checkpoint support
-- Adds stored procedures for discovering unclassified entities and
-- checking classification status to support resume/checkpoint runs.
--
-- Idempotent: All CREATE/ALTER statements check for existence first.
-- Additive-only (no drops of existing objects).

-- ============================================================================
-- Stored procedure: dbo.usp_get_unclassified_entities
-- Returns DimEntity rows that lack classification (EntityType IS NULL)
-- and are active/latest. Used by the classify-entities CLI runner.
-- ============================================================================
IF OBJECT_ID('[dbo].[usp_get_unclassified_entities]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [dbo].[usp_get_unclassified_entities];
END
GO

CREATE PROCEDURE [dbo].[usp_get_unclassified_entities]
    @limit INT = 200,
    @fill_missing_only BIT = 0,
    @require_normalization BIT = 0,
    @require_tags BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    -- Base predicate: active latest entities missing classification.
    -- When @fill_missing_only = 1, also include partially classified rows.
    SELECT TOP (@limit)
        e.EntityKey,
        e.EntityGuid,
        e.DisplayName,
        e.EntityType,
        e.DisplayNameNormalized,
        e.SortName,
        e.AliasCsv,
        e.IsLatest,
        e.IsActive,
        e.ExternalKey,
        e.SourcePageId
    FROM [dbo].[DimEntity] e
    WHERE e.IsLatest = 1
      AND e.IsActive = 1
      AND (
          -- Primary: EntityType is missing
          e.EntityType IS NULL
          -- Or: fill-missing-only mode picks up partial rows
          OR (@fill_missing_only = 1 AND (
              e.DisplayNameNormalized IS NULL
              OR e.SortName IS NULL
          ))
          -- Or: require-normalization makes partially normalized rows eligible
          OR (@require_normalization = 1 AND (
              e.DisplayNameNormalized IS NULL
              OR e.SortName IS NULL
          ))
          -- Or: require-tags makes rows without aliases eligible
          OR (@require_tags = 1 AND e.AliasCsv IS NULL)
      )
    ORDER BY e.EntityKey ASC;
END
GO

PRINT 'Stored procedure [dbo].[usp_get_unclassified_entities] created successfully.'
GO

-- ============================================================================
-- Stored procedure: dbo.usp_get_entity_classification_status
-- Returns classification status for a set of entity keys,
-- including their most recent LLM job status if one exists.
-- ============================================================================
IF OBJECT_ID('[dbo].[usp_get_entity_classification_status]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [dbo].[usp_get_entity_classification_status];
END
GO

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
GO

PRINT 'Stored procedure [dbo].[usp_get_entity_classification_status] created successfully.'
GO

PRINT 'Migration 0036 completed: Entity classification checkpoint stored procedures added.'
GO
