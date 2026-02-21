-- Migration 0035: SQL-First Artifact Content Storage
-- Idempotent: Only adds columns/constraints if they don't exist
--
-- Purpose: Extends the LLM artifact and evidence tables so that the literal
-- content of every artifact (request, response, prompt, evidence, run_meta)
-- is persisted in SQL — making SQL the system of record. The data lake
-- remains optional/additive for debugging and portability.
--
-- Tables Modified:
--   - llm.artifact: Add content column, storage flags, make lake_uri nullable
--   - llm.evidence_bundle: Add bundle_json for full evidence bundle content
--   - llm.evidence_item: Add content for evidence item text
--
-- Design Principle: SQL is the authoritative store. The lake is additive.
-- A run can be fully reconstructed from SQL alone without the lake.

-- ============================================================================
-- 1. llm.artifact — Add literal content column + storage mode flags
-- ============================================================================

-- 1a. content: The literal artifact payload (JSON text or plain text)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[artifact]')
    AND name = 'content'
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ADD content NVARCHAR(MAX) NULL;
    PRINT 'Column [content] added to [llm].[artifact].'
END
GO

-- 1b. stored_in_sql: Flag indicating content is stored in SQL
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[artifact]')
    AND name = 'stored_in_sql'
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ADD stored_in_sql BIT NOT NULL
        CONSTRAINT DF_llm_artifact_stored_in_sql DEFAULT 0;
    PRINT 'Column [stored_in_sql] added to [llm].[artifact].'
END
GO

-- 1c. mirrored_to_lake: Flag indicating content is also in the lake
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[artifact]')
    AND name = 'mirrored_to_lake'
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ADD mirrored_to_lake BIT NOT NULL
        CONSTRAINT DF_llm_artifact_mirrored_to_lake DEFAULT 0;
    PRINT 'Column [mirrored_to_lake] added to [llm].[artifact].'
END
GO

-- 1d. Make lake_uri nullable (SQL-first means lake is optional)
-- We must drop/recreate the NOT NULL constraint if it exists.
-- Check current nullability and alter if needed.
IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[artifact]')
    AND name = 'lake_uri'
    AND is_nullable = 0
)
BEGIN
    ALTER TABLE [llm].[artifact]
    ALTER COLUMN lake_uri NVARCHAR(1000) NULL;
    PRINT 'Column [lake_uri] on [llm].[artifact] changed to nullable.'
END
GO

-- 1e. Index on content_sha256 for dedupe-by-hash queries
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_artifact_content_sha256'
    AND object_id = OBJECT_ID('[llm].[artifact]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_artifact_content_sha256
    ON [llm].[artifact] (content_sha256)
    WHERE content_sha256 IS NOT NULL;
    PRINT 'Index [IX_llm_artifact_content_sha256] created.'
END
GO

-- 1f. Backfill stored_in_sql = 0 and mirrored_to_lake = 1 for existing rows
-- (all existing artifacts were lake-only)
UPDATE [llm].[artifact]
SET stored_in_sql = 0,
    mirrored_to_lake = 1
WHERE stored_in_sql = 0
  AND mirrored_to_lake = 0
  AND lake_uri IS NOT NULL;
PRINT 'Backfilled storage flags for existing artifacts.'
GO

-- ============================================================================
-- 2. llm.evidence_bundle — Add full bundle JSON content
-- ============================================================================

-- 2a. bundle_json: The complete evidence.json content stored in SQL
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'bundle_json'
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ADD bundle_json NVARCHAR(MAX) NULL;
    PRINT 'Column [bundle_json] added to [llm].[evidence_bundle].'
END
GO

-- 2b. Make lake_uri nullable on evidence_bundle (SQL-first)
IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_bundle]')
    AND name = 'lake_uri'
    AND is_nullable = 0
)
BEGIN
    ALTER TABLE [llm].[evidence_bundle]
    ALTER COLUMN lake_uri NVARCHAR(1000) NULL;
    PRINT 'Column [lake_uri] on [llm].[evidence_bundle] changed to nullable.'
END
GO

-- ============================================================================
-- 3. llm.evidence_item — Add literal content column
-- ============================================================================

-- 3a. content: The actual evidence item text/content stored in SQL
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[llm].[evidence_item]')
    AND name = 'content'
)
BEGIN
    ALTER TABLE [llm].[evidence_item]
    ADD content NVARCHAR(MAX) NULL;
    PRINT 'Column [content] added to [llm].[evidence_item].'
END
GO

-- 3b. Make lake_uri nullable on evidence_item (already nullable per 0007)
-- Verify: lake_uri on evidence_item is already NULL-able in 0007, no change needed.

-- ============================================================================
-- 4. Update usp_create_artifact to accept content + storage flags
-- ============================================================================
IF OBJECT_ID('[llm].[usp_create_artifact]', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [llm].[usp_create_artifact];
END
GO

CREATE PROCEDURE [llm].[usp_create_artifact]
    @run_id UNIQUEIDENTIFIER,
    @artifact_type NVARCHAR(100),
    @lake_uri NVARCHAR(1000) = NULL,
    @content_sha256 NVARCHAR(64) = NULL,
    @byte_count BIGINT = NULL,
    @content NVARCHAR(MAX) = NULL,
    @content_mime_type NVARCHAR(100) = NULL,
    @stored_in_sql BIT = 0,
    @mirrored_to_lake BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @artifact_id UNIQUEIDENTIFIER = NEWID();

    INSERT INTO [llm].[artifact] (
        artifact_id,
        run_id,
        artifact_type,
        content_sha256,
        byte_count,
        lake_uri,
        content,
        content_mime_type,
        stored_in_sql,
        mirrored_to_lake,
        created_utc
    )
    VALUES (
        @artifact_id,
        @run_id,
        @artifact_type,
        @content_sha256,
        @byte_count,
        @lake_uri,
        @content,
        @content_mime_type,
        @stored_in_sql,
        @mirrored_to_lake,
        SYSUTCDATETIME()
    );

    SELECT @artifact_id AS artifact_id;
END
GO

PRINT 'Stored procedure [llm].[usp_create_artifact] updated with content + storage flags.'
GO

PRINT '=== Migration 0035 complete: SQL-first artifact content storage applied. ==='
GO
