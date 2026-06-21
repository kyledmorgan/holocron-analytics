CREATE VIEW [dbo].[vw_StagedEntities]
AS
SELECT
    e.EntityKey,
    e.EntityGuid,
    e.DisplayName,
    e.EntityType,
    e.PromotionState,
    e.PrimaryTypeInferred,
    e.TypeSetJsonInferred,
    e.SourcePageId,
    e.ConfidenceScore,
    e.SourceSystem,
    e.SourceRef,
    e.CreatedUtc,
    sp.resource_id AS PageTitle,
    sp.namespace AS PageNamespace,
    sp.continuity_hint AS PageContinuity,
    pc.confidence_score AS ClassificationConfidence,
    pc.rationale AS ClassificationRationale
FROM [dbo].[DimEntity] e
LEFT JOIN [sem].[SourcePage] sp ON e.SourcePageId = sp.source_page_id
LEFT JOIN [sem].[PageClassification] pc
    ON sp.source_page_id = pc.source_page_id
    AND pc.is_current = 1
WHERE e.IsActive = 1
    AND e.IsLatest = 1
    AND e.PromotionState IN ('staged', 'candidate');
