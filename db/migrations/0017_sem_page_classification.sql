-- Migration 0017: Create sem.PageClassification table
-- Idempotent: Only creates table if it doesn't exist
--
-- Purpose: Stores type inference and lineage for pages.
-- Many rows over time per SourcePage (taxonomy_version + run lineage).
-- Stores:
--   - PrimaryType (e.g., PersonCharacter / LocationPlace / WorkMedia / EventConflict / 
--                  Concept / MetaReference / TechnicalSitePage / TimePeriod)
--   - TypeSetJson (multi-label with weights)
--   - ConfidenceScore
--   - Method (rules/llm/hybrid)
--   - ModelName/PromptVersion
--   - RunId (FK to llm.run)
--   - EvidenceJson (explainability + used signals)

-- ============================================================================
-- sem.PageClassification table: Type inference and lineage
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'PageClassification' AND s.name = 'sem'
)
BEGIN
    CREATE TABLE [sem].[PageClassification] (
        page_classification_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Link to source page
        source_page_id UNIQUEIDENTIFIER NOT NULL,
        
        -- Classification taxonomy
        taxonomy_version NVARCHAR(20) NOT NULL DEFAULT 'v1',
        
        -- Primary classification result
        primary_type NVARCHAR(100) NOT NULL,
        type_set_json NVARCHAR(MAX) NULL,
        confidence_score DECIMAL(5,4) NULL,
        
        -- Classification method
        method NVARCHAR(20) NOT NULL,
        model_name NVARCHAR(100) NULL,
        prompt_version NVARCHAR(50) NULL,
        
        -- Lineage to LLM run (if applicable)
        run_id UNIQUEIDENTIFIER NULL,
        
        -- Explainability
        evidence_json NVARCHAR(MAX) NULL,
        rationale NVARCHAR(2000) NULL,
        
        -- Review flags
        needs_review BIT NOT NULL DEFAULT 0,
        review_notes NVARCHAR(1000) NULL,
        
        -- Tag suggestions from classification
        suggested_tags_json NVARCHAR(MAX) NULL,
        
        -- Timestamps
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        -- Status
        is_current BIT NOT NULL DEFAULT 1,
        superseded_by_id UNIQUEIDENTIFIER NULL,
        
        CONSTRAINT PK_sem_PageClassification PRIMARY KEY CLUSTERED (page_classification_id),
        CONSTRAINT FK_sem_PageClassification_SourcePage FOREIGN KEY (source_page_id) 
            REFERENCES [sem].[SourcePage](source_page_id),
        CONSTRAINT CK_sem_PageClassification_Method CHECK (method IN ('rules', 'llm', 'hybrid', 'manual'))
    );
    PRINT 'Table [sem].[PageClassification] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [sem].[PageClassification] already exists.'
END
GO

-- ============================================================================
-- Indexes for sem.PageClassification
-- ============================================================================

-- Index for source_page_id + taxonomy_version + created_utc (main lookup pattern)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_SourcePage_Taxonomy_Created' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_SourcePage_Taxonomy_Created
    ON [sem].[PageClassification] (source_page_id, taxonomy_version, created_utc DESC);
    PRINT 'Index [IX_sem_PageClassification_SourcePage_Taxonomy_Created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_SourcePage_Taxonomy_Created] already exists.'
END
GO

-- Unique index for current classification per source page
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UX_sem_PageClassification_SourcePage_Current' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_sem_PageClassification_SourcePage_Current
    ON [sem].[PageClassification] (source_page_id)
    WHERE is_current = 1;
    PRINT 'Index [UX_sem_PageClassification_SourcePage_Current] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [UX_sem_PageClassification_SourcePage_Current] already exists.'
END
GO

-- Index for primary_type lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_PrimaryType' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_PrimaryType
    ON [sem].[PageClassification] (primary_type, confidence_score DESC)
    WHERE is_current = 1;
    PRINT 'Index [IX_sem_PageClassification_PrimaryType] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_PrimaryType] already exists.'
END
GO

-- Index for method lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_Method' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_Method
    ON [sem].[PageClassification] (method, created_utc DESC);
    PRINT 'Index [IX_sem_PageClassification_Method] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_Method] already exists.'
END
GO

-- Index for needs_review queue
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_NeedsReview' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_NeedsReview
    ON [sem].[PageClassification] (needs_review, confidence_score ASC)
    WHERE is_current = 1 AND needs_review = 1;
    PRINT 'Index [IX_sem_PageClassification_NeedsReview] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_NeedsReview] already exists.'
END
GO

-- Index for run_id FK lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_RunId' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_RunId
    ON [sem].[PageClassification] (run_id)
    WHERE run_id IS NOT NULL;
    PRINT 'Index [IX_sem_PageClassification_RunId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_RunId] already exists.'
END
GO

PRINT 'Migration 0017 completed: sem.PageClassification table and indexes created.'
