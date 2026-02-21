CREATE PROCEDURE [dbo].[usp_get_entities_by_type]
    @entity_type NVARCHAR(100),
    @promotion_state NVARCHAR(30) = NULL,  -- Optional filter by promotion state
    @run_id UNIQUEIDENTIFIER = NULL,       -- Optional filter by run
    @limit INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@limit)
        --EntityId,
        DisplayName,
        EntityType,
        PrimaryTypeInferred,
        TypeSetJsonInferred,
        PromotionState,
        AdjudicationRunId,
        SourcePageId,
        CreatedUtc
        --ModifiedUtc
    FROM [dbo].[DimEntity]
    WHERE LOWER(EntityType) = LOWER(@entity_type)
      AND IsLatest = 1
      AND IsActive = 1
      AND (@promotion_state IS NULL OR PromotionState = @promotion_state)
      AND (@run_id IS NULL OR AdjudicationRunId = @run_id)
    ORDER BY CreatedUtc DESC;
END
