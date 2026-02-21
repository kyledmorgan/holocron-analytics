CREATE VIEW [sem].[vw_PagesNeedingReview]
AS
SELECT
    sp.source_page_id,
    sp.source_system,
    sp.resource_id,
    sp.variant,
    sp.namespace,
    pc.primary_type,
    pc.confidence_score,
    pc.method AS classification_method,
    pc.rationale,
    pc.needs_review,
    ps.lead_sentence,
    ps.infobox_type,
    pc.created_utc AS classification_utc
FROM [sem].[SourcePage] sp
INNER JOIN [sem].[PageClassification] pc
    ON sp.source_page_id = pc.source_page_id
    AND pc.is_current = 1
LEFT JOIN [sem].[PageSignals] ps
    ON sp.source_page_id = ps.source_page_id
    AND ps.is_current = 1
WHERE sp.is_active = 1
    AND (pc.needs_review = 1 OR pc.confidence_score < 0.70 OR pc.primary_type = 'Unknown');
