CREATE VIEW [sem].[vw_TechnicalPages]
AS
SELECT
    sp.source_page_id,
    sp.source_system,
    sp.resource_id,
    sp.namespace,
    pc.primary_type,
    pc.confidence_score,
    pc.rationale,
    pc.created_utc AS classification_utc
FROM [sem].[SourcePage] sp
INNER JOIN [sem].[PageClassification] pc
    ON sp.source_page_id = pc.source_page_id
    AND pc.is_current = 1
WHERE sp.is_active = 1
    AND pc.primary_type IN ('TechnicalSitePage', 'MetaReference');
