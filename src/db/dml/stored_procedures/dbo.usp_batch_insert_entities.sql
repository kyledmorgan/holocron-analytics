CREATE PROCEDURE [dbo].[usp_batch_insert_entities]
    @entities_json NVARCHAR(MAX),         -- JSON array of entity records
    @run_id UNIQUEIDENTIFIER,             -- LLM run that produced these entities
    @job_id UNIQUEIDENTIFIER = NULL,      -- Optional job ID for provenance
    @source_page_id UNIQUEIDENTIFIER = NULL, -- Optional source page ID
    @batch_mode NVARCHAR(20) = 'staged'   -- 'staged' (default), 'candidate', 'promoted'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @now DATETIME2 = SYSUTCDATETIME();
    DECLARE @inserted_count INT = 0;
    DECLARE @updated_count INT = 0;
    DECLARE @skipped_count INT = 0;
    DECLARE @error_count INT = 0;

    -- Validate batch_mode
    IF @batch_mode NOT IN ('staged', 'candidate', 'promoted')
    BEGIN
        SET @batch_mode = 'staged';
    END

    -- Create temp table to hold parsed entities
    CREATE TABLE #ParsedEntities (
        row_num INT IDENTITY(1,1),
        entity_name NVARCHAR(500),
        entity_type NVARCHAR(100),
        confidence FLOAT,
        attributes_json NVARCHAR(MAX),
        evidence_quote NVARCHAR(MAX),
        aliases_json NVARCHAR(MAX),
        processing_status NVARCHAR(20) DEFAULT 'pending', -- pending, inserted, updated, skipped, error
        existing_entity_id UNIQUEIDENTIFIER NULL,
        error_message NVARCHAR(500) NULL
    );

    -- Parse JSON into temp table
    BEGIN TRY
        INSERT INTO #ParsedEntities (
            entity_name,
            entity_type,
            confidence,
            attributes_json,
            evidence_quote,
            aliases_json
        )
        SELECT
            -- Normalize: trim whitespace
            LTRIM(RTRIM(JSON_VALUE(j.value, '$.name'))) AS entity_name,
            LTRIM(RTRIM(JSON_VALUE(j.value, '$.type'))) AS entity_type,
            COALESCE(TRY_CAST(JSON_VALUE(j.value, '$.confidence') AS FLOAT), 1.0) AS confidence,
            JSON_QUERY(j.value, '$.attributes') AS attributes_json,
            JSON_VALUE(j.value, '$.evidence_quote') AS evidence_quote,
            JSON_QUERY(j.value, '$.aliases') AS aliases_json
        FROM OPENJSON(@entities_json) AS j;

    END TRY
    BEGIN CATCH
        -- JSON parsing error
        SELECT
            0 AS inserted_count,
            0 AS updated_count,
            0 AS skipped_count,
            1 AS error_count,
            ERROR_MESSAGE() AS error_message,
            'JSON_PARSE_ERROR' AS status;
        RETURN;
    END CATCH

    -- Skip rows with invalid data
    UPDATE #ParsedEntities
    SET processing_status = 'error',
        error_message = 'Missing required field: name'
    WHERE entity_name IS NULL OR LEN(entity_name) = 0;

    UPDATE #ParsedEntities
    SET processing_status = 'error',
        error_message = 'Missing required field: type'
    WHERE entity_type IS NULL OR LEN(entity_type) = 0
      AND processing_status = 'pending';

    UPDATE #ParsedEntities
    SET processing_status = 'error',
        error_message = 'Name exceeds maximum length (500 characters)'
    WHERE LEN(entity_name) > 500
      AND processing_status = 'pending';

    -- Normalize confidence to valid range
    UPDATE #ParsedEntities
    SET confidence = 0.0
    WHERE confidence < 0.0 AND processing_status = 'pending';

    UPDATE #ParsedEntities
    SET confidence = 1.0
    WHERE confidence > 1.0 AND processing_status = 'pending';

    -- Check for existing entities (case-insensitive match on name + type)
    UPDATE pe
    SET existing_entity_id = e.EntityId
    FROM #ParsedEntities pe
    INNER JOIN [dbo].[DimEntity] e
        ON LOWER(pe.entity_name) = LOWER(e.DisplayName)
        AND LOWER(pe.entity_type) = LOWER(e.EntityType)
        AND e.IsLatest = 1
    WHERE pe.processing_status = 'pending';

    -- Process updates for existing entities
    -- (Update TypeSetJsonInferred, AdjudicationRunId if newer confidence)
    UPDATE e
    SET
        TypeSetJsonInferred = COALESCE(pe.attributes_json, e.TypeSetJsonInferred),
        AdjudicationRunId = @run_id,
        ModifiedUtc = @now
    FROM [dbo].[DimEntity] e
    INNER JOIN #ParsedEntities pe
        ON pe.existing_entity_id = e.EntityId
    WHERE pe.processing_status = 'pending'
      AND pe.existing_entity_id IS NOT NULL;

    SET @updated_count = @@ROWCOUNT;

    UPDATE #ParsedEntities
    SET processing_status = 'updated'
    WHERE existing_entity_id IS NOT NULL
      AND processing_status = 'pending';

    -- Insert new entities
    INSERT INTO [dbo].[DimEntity] (
        EntityId,
        DisplayName,
        EntityType,
        TypeSetJsonInferred,
        PrimaryTypeInferred,
        PromotionState,
        AdjudicationRunId,
        SourcePageId,
        IsLatest,
        IsActive,
        CreatedUtc,
        ModifiedUtc
    )
    SELECT
        NEWID() AS EntityId,
        pe.entity_name AS DisplayName,
        pe.entity_type AS EntityType,
        pe.attributes_json AS TypeSetJsonInferred,
        pe.entity_type AS PrimaryTypeInferred,
        @batch_mode AS PromotionState,
        @run_id AS AdjudicationRunId,
        @source_page_id AS SourcePageId,
        1 AS IsLatest,
        1 AS IsActive,
        @now AS CreatedUtc,
        @now AS ModifiedUtc
    FROM #ParsedEntities pe
    WHERE pe.processing_status = 'pending'
      AND pe.existing_entity_id IS NULL;

    SET @inserted_count = @@ROWCOUNT;

    UPDATE #ParsedEntities
    SET processing_status = 'inserted'
    WHERE existing_entity_id IS NULL
      AND processing_status = 'pending';

    -- Count errors
    SELECT @error_count = COUNT(*)
    FROM #ParsedEntities
    WHERE processing_status = 'error';

    -- Return results summary
    SELECT
        @inserted_count AS inserted_count,
        @updated_count AS updated_count,
        @skipped_count AS skipped_count,
        @error_count AS error_count,
        NULL AS error_message,
        'SUCCESS' AS status;

    -- Return details for each processed entity
    SELECT
        row_num,
        entity_name,
        entity_type,
        confidence,
        processing_status,
        existing_entity_id,
        error_message
    FROM #ParsedEntities
    ORDER BY row_num;

    DROP TABLE #ParsedEntities;
END
