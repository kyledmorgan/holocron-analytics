-- Migration 0016: Create sem.PageSignals table
-- Idempotent: Only creates table if it doesn't exist
--
-- Purpose: Stores small extracted cues from pages (minimal content peek).
-- One row per SourcePage (or versioned if needed).
-- Stores:
--   - LeadSentence (first N chars)
--   - InfoboxType (if derivable)
--   - CategoriesJson (top categories)
--   - Flags: IsListPage, IsDisambiguation, HasTimelineMarkers
--   - SignalsJson for extras (section headers sample, etc.)

-- ============================================================================
-- sem.PageSignals table: Cheap extracted cues from pages
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'PageSignals' AND s.name = 'sem'
)
BEGIN
    CREATE TABLE [sem].[PageSignals] (
        page_signals_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        
        -- Link to source page
        source_page_id UNIQUEIDENTIFIER NOT NULL,
        
        -- Content version tracking
        content_hash_sha256 NVARCHAR(64) NULL,
        signals_version INT NOT NULL DEFAULT 1,
        
        -- Extracted signals
        lead_sentence NVARCHAR(1000) NULL,
        infobox_type NVARCHAR(200) NULL,
        categories_json NVARCHAR(MAX) NULL,
        
        -- Boolean flags
        is_list_page BIT NOT NULL DEFAULT 0,
        is_disambiguation BIT NOT NULL DEFAULT 0,
        has_timeline_markers BIT NOT NULL DEFAULT 0,
        has_infobox BIT NOT NULL DEFAULT 0,
        
        -- Extensible signals container
        signals_json NVARCHAR(MAX) NULL,
        
        -- Extraction metadata
        extracted_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        extraction_method NVARCHAR(50) NULL,
        extraction_duration_ms INT NULL,
        
        -- Status
        is_current BIT NOT NULL DEFAULT 1,
        
        CONSTRAINT PK_sem_PageSignals PRIMARY KEY CLUSTERED (page_signals_id),
        CONSTRAINT FK_sem_PageSignals_SourcePage FOREIGN KEY (source_page_id) 
            REFERENCES [sem].[SourcePage](source_page_id)
    );
    PRINT 'Table [sem].[PageSignals] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [sem].[PageSignals] already exists.'
END
GO

-- ============================================================================
-- Indexes for sem.PageSignals
-- ============================================================================

-- Unique index for source_page_id + is_current (ensures one current signals per page)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'UX_sem_PageSignals_SourcePage_Current' 
    AND object_id = OBJECT_ID('[sem].[PageSignals]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_sem_PageSignals_SourcePage_Current
    ON [sem].[PageSignals] (source_page_id)
    WHERE is_current = 1;
    PRINT 'Index [UX_sem_PageSignals_SourcePage_Current] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [UX_sem_PageSignals_SourcePage_Current] already exists.'
END
GO

-- Index for infobox_type lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageSignals_InfoboxType' 
    AND object_id = OBJECT_ID('[sem].[PageSignals]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageSignals_InfoboxType
    ON [sem].[PageSignals] (infobox_type)
    WHERE infobox_type IS NOT NULL;
    PRINT 'Index [IX_sem_PageSignals_InfoboxType] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageSignals_InfoboxType] already exists.'
END
GO

-- Index for flag-based queries (list pages, disambiguation pages)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageSignals_Flags' 
    AND object_id = OBJECT_ID('[sem].[PageSignals]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageSignals_Flags
    ON [sem].[PageSignals] (is_list_page, is_disambiguation, has_timeline_markers, has_infobox)
    WHERE is_current = 1;
    PRINT 'Index [IX_sem_PageSignals_Flags] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageSignals_Flags] already exists.'
END
GO

-- Index for extraction recency
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageSignals_ExtractedUtc' 
    AND object_id = OBJECT_ID('[sem].[PageSignals]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageSignals_ExtractedUtc
    ON [sem].[PageSignals] (extracted_utc DESC);
    PRINT 'Index [IX_sem_PageSignals_ExtractedUtc] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageSignals_ExtractedUtc] already exists.'
END
GO

PRINT 'Migration 0016 completed: sem.PageSignals table and indexes created.'
