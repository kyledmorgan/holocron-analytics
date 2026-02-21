CREATE PROCEDURE [dbo].[usp_count_entities_by_type]
    @entity_type NVARCHAR(100) = NULL      -- Optional: specific type or all
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        EntityType,
        PromotionState,
        COUNT(*) AS entity_count
    FROM [dbo].[DimEntity]
    WHERE IsLatest = 1
      AND IsActive = 1
      AND (@entity_type IS NULL OR LOWER(EntityType) = LOWER(@entity_type))
    GROUP BY EntityType, PromotionState
    ORDER BY EntityType, PromotionState;
END
