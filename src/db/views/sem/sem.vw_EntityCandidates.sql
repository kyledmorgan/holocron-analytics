CREATE VIEW [sem].[vw_EntityCandidates]
AS
SELECT
    sp.source_page_id,
    sp.source_system,
    sp.resource_id,
    sp.variant,
    sp.namespace,
    sp.continuity_hint,
    pc.primary_type,
    pc.type_set_json,
    pc.confidence_score,
    pc.method AS classification_method,
    pc.rationale,
    pc.suggested_tags_json,
    ps.lead_sentence,
    ps.infobox_type,
    ps.categories_json,
    pc.created_utc AS classification_utc
FROM [sem].[SourcePage] sp
INNER JOIN [sem].[PageClassification] pc
    ON sp.source_page_id = pc.source_page_id
    AND pc.is_current = 1
LEFT JOIN [sem].[PageSignals] ps
    ON sp.source_page_id = ps.source_page_id
    AND ps.is_current = 1
WHERE sp.is_active = 1
    AND pc.needs_review = 0
    AND pc.confidence_score >= 0.75
    AND pc.primary_type NOT IN ('TechnicalSitePage', 'MetaReference', 'Unknown');
