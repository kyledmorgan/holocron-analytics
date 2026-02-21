CREATE VIEW [dbo].[vw_PromotedEntities]
AS
SELECT
    e.EntityKey,
    e.EntityGuid,
    e.DisplayName,
    e.EntityType,
    e.PromotionState,
    e.PromotionDecisionUtc,
    e.PromotionDecidedBy,
    e.PromotionReason,
    e.PrimaryTypeInferred,
    e.TypeSetJsonInferred,
    e.SourcePageId,
    e.FranchiseKey,
    e.ConfidenceScore,
    e.IsCanonical,
    e.SourceSystem,
    e.SourceRef,
    e.CreatedUtc,
    e.UpdatedUtc
FROM [dbo].[DimEntity] e
WHERE e.IsActive = 1
    AND e.IsLatest = 1
    AND e.PromotionState = 'promoted';
