CREATE PROCEDURE [dbo].[usp_batch_insert_entity_relations]
    @relationships_json NVARCHAR(MAX),        -- JSON array of relationship records
    @run_id UNIQUEIDENTIFIER,                 -- LLM run that produced these relationships
    @job_id UNIQUEIDENTIFIER = NULL,          -- Optional job ID for provenance
    @source_page_id UNIQUEIDENTIFIER = NULL,  -- Optional source page ID
    @allow_duplicates BIT = 0                 -- If 0, skip duplicate relationships
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @now DATETIME2 = SYSUTCDATETIME();
    DECLARE @inserted_count INT = 0;
    DECLARE @skipped_count INT = 0;
    DECLARE @error_count INT = 0;
    DECLARE @unresolved_count INT = 0;

    -- Create temp table to hold parsed relationships
    CREATE TABLE #ParsedRelationships (
        row_num INT IDENTITY(1,1),
        from_entity_name NVARCHAR(500),
        to_entity_name NVARCHAR(500),
        relation_type NVARCHAR(100),
        confidence FLOAT,
        start_date NVARCHAR(100),
        end_date NVARCHAR(100),
        work_context_json NVARCHAR(MAX),
        evidence_quote NVARCHAR(MAX),
        bidirectional BIT DEFAULT 0,
        -- Resolved IDs
        from_entity_id UNIQUEIDENTIFIER NULL,
        to_entity_id UNIQUEIDENTIFIER NULL,
        -- Processing status
        processing_status NVARCHAR(20) DEFAULT 'pending', -- pending, inserted, skipped, error, unresolved
        error_message NVARCHAR(500) NULL
    );

    -- Parse JSON into temp table
    BEGIN TRY
        INSERT INTO #ParsedRelationships (
            from_entity_name,
            to_entity_name,
            relation_type,
            confidence,
            start_date,
            end_date,
            work_context_json,
            evidence_quote,
            bidirectional
        )
        SELECT
            -- Normalize: trim whitespace
            LTRIM(RTRIM(JSON_VALUE(j.value, '$.from_entity'))) AS from_entity_name,
            LTRIM(RTRIM(JSON_VALUE(j.value, '$.to_entity'))) AS to_entity_name,
            LTRIM(RTRIM(JSON_VALUE(j.value, '$.relation_type'))) AS relation_type,
            COALESCE(TRY_CAST(JSON_VALUE(j.value, '$.confidence') AS FLOAT), 1.0) AS confidence,
            JSON_VALUE(j.value, '$.start_date') AS start_date,
            JSON_VALUE(j.value, '$.end_date') AS end_date,
            JSON_QUERY(j.value, '$.work_context') AS work_context_json,
            JSON_VALUE(j.value, '$.evidence_quote') AS evidence_quote,
            COALESCE(TRY_CAST(JSON_VALUE(j.value, '$.bidirectional') AS BIT), 0) AS bidirectional
        FROM OPENJSON(@relationships_json) AS j;

    END TRY
    BEGIN CATCH
        -- JSON parsing error
        SELECT
            0 AS inserted_count,
            0 AS skipped_count,
            1 AS error_count,
            0 AS unresolved_count,
            ERROR_MESSAGE() AS error_message,
            'JSON_PARSE_ERROR' AS status;
        RETURN;
    END CATCH

    -- Validate required fields
    UPDATE #ParsedRelationships
    SET processing_status = 'error',
        error_message = 'Missing required field: from_entity'
    WHERE from_entity_name IS NULL OR LEN(from_entity_name) = 0;

    UPDATE #ParsedRelationships
    SET processing_status = 'error',
        error_message = 'Missing required field: to_entity'
    WHERE to_entity_name IS NULL OR LEN(to_entity_name) = 0
      AND processing_status = 'pending';

    UPDATE #ParsedRelationships
    SET processing_status = 'error',
        error_message = 'Missing required field: relation_type'
    WHERE relation_type IS NULL OR LEN(relation_type) = 0
      AND processing_status = 'pending';

    UPDATE #ParsedRelationships
    SET processing_status = 'error',
        error_message = 'from_entity name exceeds maximum length (500 characters)'
    WHERE LEN(from_entity_name) > 500
      AND processing_status = 'pending';

    UPDATE #ParsedRelationships
    SET processing_status = 'error',
        error_message = 'to_entity name exceeds maximum length (500 characters)'
    WHERE LEN(to_entity_name) > 500
      AND processing_status = 'pending';

    UPDATE #ParsedRelationships
    SET processing_status = 'error',
        error_message = 'relation_type exceeds maximum length (100 characters)'
    WHERE LEN(relation_type) > 100
      AND processing_status = 'pending';

    -- Normalize confidence to valid range
    UPDATE #ParsedRelationships
    SET confidence = 0.0
    WHERE confidence < 0.0 AND processing_status = 'pending';

    UPDATE #ParsedRelationships
    SET confidence = 1.0
    WHERE confidence > 1.0 AND processing_status = 'pending';

    -- Resolve from_entity names to entity IDs (case-insensitive)
    UPDATE pr
    SET from_entity_id = e.EntityKey
    FROM #ParsedRelationships pr
    INNER JOIN [dbo].[DimEntity] e
        ON LOWER(pr.from_entity_name) = LOWER(e.DisplayName)
        AND e.IsLatest = 1
        AND e.IsActive = 1
    WHERE pr.processing_status = 'pending';

    -- Resolve to_entity names to entity IDs (case-insensitive)
    UPDATE pr
    SET to_entity_id = e.EntityKey
    FROM #ParsedRelationships pr
    INNER JOIN [dbo].[DimEntity] e
        ON LOWER(pr.to_entity_name) = LOWER(e.DisplayName)
        AND e.IsLatest = 1
        AND e.IsActive = 1
    WHERE pr.processing_status = 'pending';

    -- Mark relationships with unresolved entities
    UPDATE #ParsedRelationships
    SET processing_status = 'unresolved',
        error_message = CASE
            WHEN from_entity_id IS NULL AND to_entity_id IS NULL THEN 'Both from_entity and to_entity not found in DimEntity'
            WHEN from_entity_id IS NULL THEN 'from_entity not found in DimEntity: ' + from_entity_name
            ELSE 'to_entity not found in DimEntity: ' + to_entity_name
        END
    WHERE processing_status = 'pending'
      AND (from_entity_id IS NULL OR to_entity_id IS NULL);

    -- Check for duplicates if @allow_duplicates = 0
    IF @allow_duplicates = 0
    BEGIN
        UPDATE pr
        SET processing_status = 'skipped',
            error_message = 'Duplicate relationship already exists'
        FROM #ParsedRelationships pr
        WHERE pr.processing_status = 'pending'
          AND EXISTS (
              SELECT 1 FROM [dbo].[BridgeEntityRelation] ber
              WHERE ber.FromEntityId = pr.from_entity_id
                AND ber.ToEntityId = pr.to_entity_id
                AND ber.RelationType = pr.relation_type
                AND ber.IsActive = 1
                -- Consider temporal overlap for time-bounded relationships
                AND (
                    (pr.start_date IS NULL AND ber.StartDate IS NULL)
                    OR (pr.start_date = ber.StartDate)
                )
          );
    END

    -- Insert new relationships (only those with resolved entities)
    INSERT INTO [dbo].[BridgeEntityRelation] (
        RelationId,
        FromEntityId,
        ToEntityId,
        RelationType,
        Confidence,
        StartDate,
        EndDate,
        WorkContextJson,
        SourcePageId,
        RunId,
        JobId,
        CreatedUtc,
        IsActive,
        NeedsReview
    )
    SELECT
        NEWID() AS RelationId,
        pr.from_entity_id AS FromEntityId,
        pr.to_entity_id AS ToEntityId,
        pr.relation_type AS RelationType,
        pr.confidence AS Confidence,
        pr.start_date AS StartDate,
        pr.end_date AS EndDate,
        pr.work_context_json AS WorkContextJson,
        @source_page_id AS SourcePageId,
        @run_id AS RunId,
        @job_id AS JobId,
        @now AS CreatedUtc,
        1 AS IsActive,
        CASE WHEN pr.confidence < 0.7 THEN 1 ELSE 0 END AS NeedsReview
    FROM #ParsedRelationships pr
    WHERE pr.processing_status = 'pending';

    SET @inserted_count = @@ROWCOUNT;

    UPDATE #ParsedRelationships
    SET processing_status = 'inserted'
    WHERE processing_status = 'pending';

    -- Count results
    SELECT @skipped_count = COUNT(*)
    FROM #ParsedRelationships
    WHERE processing_status = 'skipped';

    SELECT @error_count = COUNT(*)
    FROM #ParsedRelationships
    WHERE processing_status = 'error';

    SELECT @unresolved_count = COUNT(*)
    FROM #ParsedRelationships
    WHERE processing_status = 'unresolved';

    -- Return results summary
    SELECT
        @inserted_count AS inserted_count,
        @skipped_count AS skipped_count,
        @error_count AS error_count,
        @unresolved_count AS unresolved_count,
        NULL AS error_message,
        'SUCCESS' AS status;

    -- Return details for each processed relationship
    SELECT
        row_num,
        from_entity_name,
        to_entity_name,
        relation_type,
        confidence,
        start_date,
        end_date,
        from_entity_id,
        to_entity_id,
        processing_status,
        error_message
    FROM #ParsedRelationships
    ORDER BY row_num;

    DROP TABLE #ParsedRelationships;
END
