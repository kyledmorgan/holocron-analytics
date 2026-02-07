-- Migration 0020: Create semantic staging views
-- Idempotent: Drops and recreates views
--
-- These views provide convenient access to semantic staging data:
-- - Current page classifications with signals
-- - Entities ready for promotion
-- - Tag assignments for source pages

-- ============================================================================
-- View: Current page classification with source page and signals
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_CurrentPageClassification]'))
BEGIN
    DROP VIEW [sem].[vw_CurrentPageClassification];
END
GO

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
GO

PRINT 'View [sem].[vw_CurrentPageClassification] created successfully.'
GO

-- ============================================================================
-- View: Pages by classification type
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_PagesByType]'))
BEGIN
    DROP VIEW [sem].[vw_PagesByType];
END
GO

CREATE VIEW [sem].[vw_PagesByType]
AS
SELECT
    pc.primary_type,
    pc.taxonomy_version,
    COUNT(*) AS page_count,
    AVG(CAST(pc.confidence_score AS FLOAT)) AS avg_confidence,
    SUM(CASE WHEN pc.needs_review = 1 THEN 1 ELSE 0 END) AS needs_review_count,
    SUM(CASE WHEN pc.method = 'rules' THEN 1 ELSE 0 END) AS rules_count,
    SUM(CASE WHEN pc.method = 'llm' THEN 1 ELSE 0 END) AS llm_count,
    SUM(CASE WHEN pc.method = 'hybrid' THEN 1 ELSE 0 END) AS hybrid_count
FROM [sem].[PageClassification] pc
INNER JOIN [sem].[SourcePage] sp 
    ON pc.source_page_id = sp.source_page_id
    AND sp.is_active = 1
WHERE pc.is_current = 1
GROUP BY pc.primary_type, pc.taxonomy_version;
GO

PRINT 'View [sem].[vw_PagesByType] created successfully.'
GO

-- ============================================================================
-- View: Pages needing review (low confidence or flagged)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_PagesNeedingReview]'))
BEGIN
    DROP VIEW [sem].[vw_PagesNeedingReview];
END
GO

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
GO

PRINT 'View [sem].[vw_PagesNeedingReview] created successfully.'
GO

-- ============================================================================
-- View: Technical/suppressed pages (excluded from promotion)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_TechnicalPages]'))
BEGIN
    DROP VIEW [sem].[vw_TechnicalPages];
END
GO

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
GO

PRINT 'View [sem].[vw_TechnicalPages] created successfully.'
GO

-- ============================================================================
-- View: Entity candidates (high confidence, promotable types)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_EntityCandidates]'))
BEGIN
    DROP VIEW [sem].[vw_EntityCandidates];
END
GO

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
GO

PRINT 'View [sem].[vw_EntityCandidates] created successfully.'
GO

-- ============================================================================
-- View: Promoted entities (DimEntity with promotion tracking)
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[vw_PromotedEntities]'))
BEGIN
    DROP VIEW [dbo].[vw_PromotedEntities];
END
GO

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
GO

PRINT 'View [dbo].[vw_PromotedEntities] created successfully.'
GO

-- ============================================================================
-- View: Staged entities awaiting promotion
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[vw_StagedEntities]'))
BEGIN
    DROP VIEW [dbo].[vw_StagedEntities];
END
GO

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
GO

PRINT 'View [dbo].[vw_StagedEntities] created successfully.'
GO

-- ============================================================================
-- View: Tag assignments with tag details
-- ============================================================================
IF EXISTS (SELECT * FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[vw_TagAssignments]'))
BEGIN
    DROP VIEW [dbo].[vw_TagAssignments];
END
GO

CREATE VIEW [dbo].[vw_TagAssignments]
AS
SELECT
    ta.AssignmentId,
    t.TagKey,
    t.TagType,
    t.TagName,
    t.DisplayName AS TagDisplayName,
    t.Visibility AS TagVisibility,
    ta.TargetType,
    ta.TargetId,
    ta.Weight,
    ta.Confidence,
    ta.AssignmentMethod,
    ta.AssignedUtc
FROM [dbo].[BridgeTagAssignment] ta
INNER JOIN [dbo].[DimTag] t ON ta.TagKey = t.TagKey
WHERE ta.IsActive = 1
    AND t.IsActive = 1
    AND t.IsLatest = 1;
GO

PRINT 'View [dbo].[vw_TagAssignments] created successfully.'
GO

PRINT 'Migration 0020 completed: Semantic staging views created.'
