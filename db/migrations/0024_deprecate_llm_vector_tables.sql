-- Migration 0024: Deprecate legacy vector tables in llm schema (Phase 2 Cutover)
-- 
-- This migration renames the legacy vector tables in the llm schema to *_legacy
-- to prevent accidental use. The vector schema is now the sole home for:
-- - Chunking for retrieval/embedding
-- - Embedding generation/storage
-- - Retrieval logging / hits
-- - Indexing state
-- - Vector job/run orchestration
--
-- The llm schema remains for chat runtime only:
-- - llm.job, llm.run, llm.artifact
-- - llm.evidence_bundle, llm.evidence_item, llm.run_evidence
--
-- Historical reference: db/legacy_snapshots/llm_vector_subsystem_snapshot.sql
--
-- Idempotent: Only renames tables if they exist with the original name

-- ============================================================================
-- Step 1: Drop foreign key constraints first
-- ============================================================================

-- Drop FK from retrieval_hit to retrieval
IF EXISTS (
    SELECT * FROM sys.foreign_keys 
    WHERE name = 'FK_llm_retrieval_hit_retrieval' 
    AND parent_object_id = OBJECT_ID('[llm].[retrieval_hit]')
)
BEGIN
    ALTER TABLE [llm].[retrieval_hit] DROP CONSTRAINT FK_llm_retrieval_hit_retrieval;
    PRINT 'Dropped constraint FK_llm_retrieval_hit_retrieval.'
END
GO

-- Drop FK from retrieval_hit to chunk
IF EXISTS (
    SELECT * FROM sys.foreign_keys 
    WHERE name = 'FK_llm_retrieval_hit_chunk' 
    AND parent_object_id = OBJECT_ID('[llm].[retrieval_hit]')
)
BEGIN
    ALTER TABLE [llm].[retrieval_hit] DROP CONSTRAINT FK_llm_retrieval_hit_chunk;
    PRINT 'Dropped constraint FK_llm_retrieval_hit_chunk.'
END
GO

-- Drop FK from retrieval to run
IF EXISTS (
    SELECT * FROM sys.foreign_keys 
    WHERE name = 'FK_llm_retrieval_run' 
    AND parent_object_id = OBJECT_ID('[llm].[retrieval]')
)
BEGIN
    ALTER TABLE [llm].[retrieval] DROP CONSTRAINT FK_llm_retrieval_run;
    PRINT 'Dropped constraint FK_llm_retrieval_run.'
END
GO

-- Drop FK from embedding to chunk
IF EXISTS (
    SELECT * FROM sys.foreign_keys 
    WHERE name = 'FK_llm_embedding_chunk' 
    AND parent_object_id = OBJECT_ID('[llm].[embedding]')
)
BEGIN
    ALTER TABLE [llm].[embedding] DROP CONSTRAINT FK_llm_embedding_chunk;
    PRINT 'Dropped constraint FK_llm_embedding_chunk.'
END
GO

-- ============================================================================
-- Step 2: Rename tables to *_legacy
-- ============================================================================

-- Rename llm.retrieval_hit -> llm.retrieval_hit_legacy
IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval_hit' AND s.name = 'llm'
)
BEGIN
    EXEC sp_rename '[llm].[retrieval_hit]', 'retrieval_hit_legacy';
    PRINT 'Renamed [llm].[retrieval_hit] to [llm].[retrieval_hit_legacy].'
END
ELSE IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval_hit_legacy' AND s.name = 'llm'
)
BEGIN
    PRINT 'Table [llm].[retrieval_hit_legacy] already exists (previously renamed).'
END
GO

-- Rename llm.retrieval -> llm.retrieval_legacy
IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval' AND s.name = 'llm'
)
BEGIN
    EXEC sp_rename '[llm].[retrieval]', 'retrieval_legacy';
    PRINT 'Renamed [llm].[retrieval] to [llm].[retrieval_legacy].'
END
ELSE IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval_legacy' AND s.name = 'llm'
)
BEGIN
    PRINT 'Table [llm].[retrieval_legacy] already exists (previously renamed).'
END
GO

-- Rename llm.embedding -> llm.embedding_legacy
IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'embedding' AND s.name = 'llm'
)
BEGIN
    EXEC sp_rename '[llm].[embedding]', 'embedding_legacy';
    PRINT 'Renamed [llm].[embedding] to [llm].[embedding_legacy].'
END
ELSE IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'embedding_legacy' AND s.name = 'llm'
)
BEGIN
    PRINT 'Table [llm].[embedding_legacy] already exists (previously renamed).'
END
GO

-- Rename llm.chunk -> llm.chunk_legacy
IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'chunk' AND s.name = 'llm'
)
BEGIN
    EXEC sp_rename '[llm].[chunk]', 'chunk_legacy';
    PRINT 'Renamed [llm].[chunk] to [llm].[chunk_legacy].'
END
ELSE IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'chunk_legacy' AND s.name = 'llm'
)
BEGIN
    PRINT 'Table [llm].[chunk_legacy] already exists (previously renamed).'
END
GO

-- Rename llm.source_registry -> llm.source_registry_legacy
IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'source_registry' AND s.name = 'llm'
)
BEGIN
    EXEC sp_rename '[llm].[source_registry]', 'source_registry_legacy';
    PRINT 'Renamed [llm].[source_registry] to [llm].[source_registry_legacy].'
END
ELSE IF EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'source_registry_legacy' AND s.name = 'llm'
)
BEGIN
    PRINT 'Table [llm].[source_registry_legacy] already exists (previously renamed).'
END
GO

-- ============================================================================
-- Summary
-- ============================================================================
-- 
-- After this migration:
-- - Legacy vector tables are renamed to *_legacy (blocked from active use)
-- - Chat runtime tables (job, run, artifact, evidence_*) remain unchanged
-- - All vector operations should use the vector.* schema exclusively
--
-- Tables deprecated:
-- - llm.chunk_legacy (was llm.chunk)
-- - llm.embedding_legacy (was llm.embedding)
-- - llm.retrieval_legacy (was llm.retrieval)
-- - llm.retrieval_hit_legacy (was llm.retrieval_hit)
-- - llm.source_registry_legacy (was llm.source_registry)
--
-- Tables preserved (chat runtime):
-- - llm.job
-- - llm.run
-- - llm.artifact
-- - llm.evidence_bundle
-- - llm.evidence_item
-- - llm.run_evidence
--
-- Historical reference:
-- - db/legacy_snapshots/llm_vector_subsystem_snapshot.sql

PRINT '=== Migration 0024 complete: Legacy vector tables deprecated ==='
GO
