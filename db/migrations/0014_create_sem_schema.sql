-- Migration 0014: Create sem (semantic) schema
-- Idempotent: Only creates schema if it doesn't exist
--
-- The sem schema contains tables for semantic staging of ingested pages:
-- - SourcePage: Page identity and provenance
-- - PageSignals: Extracted cues and signals from pages
-- - PageClassification: Type inference and lineage

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'sem')
BEGIN
    EXEC('CREATE SCHEMA sem')
    PRINT 'Schema [sem] created successfully.'
END
ELSE
BEGIN
    PRINT 'Schema [sem] already exists.'
END
GO
