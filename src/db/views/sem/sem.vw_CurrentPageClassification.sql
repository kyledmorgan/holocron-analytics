CREATE VIEW [sem].[vw_CurrentPageClassification]
AS
SELECT
    sp.source_page_id,
    sp.source_system,
    sp.resource_id,
    sp.variant,
    sp.namespace,
    sp.continuity_hint,
    sp.content_hash_sha256,
    sp.latest_ingest_id,
    sp.created_utc AS page_created_utc,
    sp.updated_utc AS page_updated_utc,

    -- Classification
    pc.page_classification_id,
    pc.taxonomy_version,
    pc.primary_type,
    pc.type_set_json,
    pc.confidence_score,
    pc.method AS classification_method,
    pc.model_name,
    pc.run_id AS classification_run_id,
    pc.rationale,
    pc.needs_review,
    pc.suggested_tags_json,
    pc.created_utc AS classification_utc,

    -- Signals (if available)
    ps.page_signals_id,
    ps.lead_sentence,
    ps.infobox_type,
    ps.categories_json,
    ps.is_list_page,
    ps.is_disambiguation,
    ps.has_timeline_markers,
    ps.has_infobox,
    ps.extracted_utc AS signals_extracted_utc

FROM [sem].[SourcePage] sp
LEFT JOIN [sem].[PageClassification] pc
    ON sp.source_page_id = pc.source_page_id
    AND pc.is_current = 1
LEFT JOIN [sem].[PageSignals] ps
    ON sp.source_page_id = ps.source_page_id
    AND ps.is_current = 1
WHERE sp.is_active = 1;
