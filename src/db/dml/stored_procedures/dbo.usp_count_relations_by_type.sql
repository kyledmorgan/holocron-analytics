CREATE PROCEDURE [dbo].[usp_count_relations_by_type]
    @relation_type NVARCHAR(100) = NULL      -- Optional: specific type or all
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        RelationType,
        COUNT(*) AS relation_count,
        SUM(CASE WHEN NeedsReview = 1 THEN 1 ELSE 0 END) AS needs_review_count,
        AVG(Confidence) AS avg_confidence
    FROM [dbo].[BridgeEntityRelation]
    WHERE IsActive = 1
      AND (@relation_type IS NULL OR RelationType = @relation_type)
    GROUP BY RelationType
    ORDER BY relation_count DESC;
END
