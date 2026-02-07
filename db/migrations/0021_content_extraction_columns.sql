-- Migration 0021: Add content extraction columns to sem.PageSignals
-- and descriptor_sentence column to sem.PageClassification
-- Idempotent: Only adds columns if they don't exist
--
-- Purpose: Support improved content extraction with bounded excerpts
-- and LLM-generated descriptor sentences.
--
-- New columns on sem.PageSignals:
--   - content_format_detected: wikitext/html/unknown
--   - content_start_strategy: triple_quote/first_paragraph/mw_parser_output/fallback
--   - content_start_offset: int (char offset where content starts)
--   - lead_excerpt_text: the bounded excerpt used for LLM classification
--   - lead_excerpt_len: length of the excerpt
--
-- New column on sem.PageClassification:
--   - descriptor_sentence: LLM-generated single sentence descriptor (<= 50 words)

-- ============================================================================
-- Add columns to sem.PageSignals
-- ============================================================================

-- content_format_detected: wikitext/html/unknown
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageSignals]') 
    AND name = 'content_format_detected'
)
BEGIN
    ALTER TABLE [sem].[PageSignals]
    ADD content_format_detected NVARCHAR(20) NULL;
    PRINT 'Column [content_format_detected] added to sem.PageSignals.'
END
ELSE
BEGIN
    PRINT 'Column [content_format_detected] already exists on sem.PageSignals.'
END
GO

-- content_start_strategy: triple_quote/first_paragraph/mw_parser_output/fallback
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageSignals]') 
    AND name = 'content_start_strategy'
)
BEGIN
    ALTER TABLE [sem].[PageSignals]
    ADD content_start_strategy NVARCHAR(50) NULL;
    PRINT 'Column [content_start_strategy] added to sem.PageSignals.'
END
ELSE
BEGIN
    PRINT 'Column [content_start_strategy] already exists on sem.PageSignals.'
END
GO

-- content_start_offset: int (char offset where content starts)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageSignals]') 
    AND name = 'content_start_offset'
)
BEGIN
    ALTER TABLE [sem].[PageSignals]
    ADD content_start_offset INT NULL;
    PRINT 'Column [content_start_offset] added to sem.PageSignals.'
END
ELSE
BEGIN
    PRINT 'Column [content_start_offset] already exists on sem.PageSignals.'
END
GO

-- lead_excerpt_text: the bounded excerpt used for LLM classification
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageSignals]') 
    AND name = 'lead_excerpt_text'
)
BEGIN
    ALTER TABLE [sem].[PageSignals]
    ADD lead_excerpt_text NVARCHAR(MAX) NULL;
    PRINT 'Column [lead_excerpt_text] added to sem.PageSignals.'
END
ELSE
BEGIN
    PRINT 'Column [lead_excerpt_text] already exists on sem.PageSignals.'
END
GO

-- lead_excerpt_len: length of the excerpt
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageSignals]') 
    AND name = 'lead_excerpt_len'
)
BEGIN
    ALTER TABLE [sem].[PageSignals]
    ADD lead_excerpt_len INT NULL;
    PRINT 'Column [lead_excerpt_len] added to sem.PageSignals.'
END
ELSE
BEGIN
    PRINT 'Column [lead_excerpt_len] already exists on sem.PageSignals.'
END
GO

-- lead_excerpt_hash: SHA256 hash of the excerpt for deduplication
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageSignals]') 
    AND name = 'lead_excerpt_hash'
)
BEGIN
    ALTER TABLE [sem].[PageSignals]
    ADD lead_excerpt_hash NVARCHAR(64) NULL;
    PRINT 'Column [lead_excerpt_hash] added to sem.PageSignals.'
END
ELSE
BEGIN
    PRINT 'Column [lead_excerpt_hash] already exists on sem.PageSignals.'
END
GO

-- ============================================================================
-- Add descriptor_sentence column to sem.PageClassification
-- ============================================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageClassification]') 
    AND name = 'descriptor_sentence'
)
BEGIN
    ALTER TABLE [sem].[PageClassification]
    ADD descriptor_sentence NVARCHAR(400) NULL;
    PRINT 'Column [descriptor_sentence] added to sem.PageClassification.'
END
ELSE
BEGIN
    PRINT 'Column [descriptor_sentence] already exists on sem.PageClassification.'
END
GO

-- ============================================================================
-- Add index for content format queries
-- ============================================================================

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageSignals_ContentFormat' 
    AND object_id = OBJECT_ID('[sem].[PageSignals]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageSignals_ContentFormat
    ON [sem].[PageSignals] (content_format_detected, content_start_strategy)
    WHERE is_current = 1 AND content_format_detected IS NOT NULL;
    PRINT 'Index [IX_sem_PageSignals_ContentFormat] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageSignals_ContentFormat] already exists.'
END
GO

PRINT 'Migration 0021 completed: Content extraction columns added.'
