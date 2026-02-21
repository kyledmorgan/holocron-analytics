-- Migration 0034: DVO Evidence Bundle Linkage
-- Idempotent: Only adds columns/indexes if they don't exist
--
-- Purpose: Adds nullable EvidenceBundleGuid to DVO fact, bridge, and
-- relationship tables so that LLM-derived records can reference the
-- evidence bundle that influenced their creation.
--
-- Convention: Uses EvidenceBundleGuid (UNIQUEIDENTIFIER) following the
-- project naming standard (see docs/agent/db_policies.md):
--   - ...Guid for public-facing stable identifiers
--   - Never use ...Id suffix
--
-- Nullable because:
--   - Records from manual curation, deterministic loads, or legacy paths
--     continue to use SourceSystem + SourceRef without a bundle
--   - Only LLM-derived records will populate this field
--
-- Tables Modified:
--   - dbo.FactEvent
--   - dbo.FactClaim
--   - dbo.ContinuityIssue
--   - dbo.BridgeEventParticipant
--   - dbo.BridgeEventAsset
--   - dbo.BridgeContinuityIssueClaim
--   - dbo.BridgeEntityRelation

-- ============================================================================
-- 1. dbo.FactEvent — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[FactEvent]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[FactEvent]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[FactEvent].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactEvent_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[FactEvent]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactEvent_EvidenceBundleGuid
    ON [dbo].[FactEvent] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_FactEvent_EvidenceBundleGuid] created.'
END
GO

-- ============================================================================
-- 2. dbo.FactClaim — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[FactClaim]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[FactClaim]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[FactClaim].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactClaim_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[FactClaim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactClaim_EvidenceBundleGuid
    ON [dbo].[FactClaim] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_FactClaim_EvidenceBundleGuid] created.'
END
GO

-- ============================================================================
-- 3. dbo.ContinuityIssue — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[ContinuityIssue]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[ContinuityIssue]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[ContinuityIssue].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ContinuityIssue_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[ContinuityIssue]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_ContinuityIssue_EvidenceBundleGuid
    ON [dbo].[ContinuityIssue] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_ContinuityIssue_EvidenceBundleGuid] created.'
END
GO

-- ============================================================================
-- 4. dbo.BridgeEventParticipant — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[BridgeEventParticipant]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[BridgeEventParticipant]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[BridgeEventParticipant].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_BridgeEventParticipant_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[BridgeEventParticipant]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEventParticipant_EvidenceBundleGuid
    ON [dbo].[BridgeEventParticipant] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_BridgeEventParticipant_EvidenceBundleGuid] created.'
END
GO

-- ============================================================================
-- 5. dbo.BridgeEventAsset — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[BridgeEventAsset]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[BridgeEventAsset]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[BridgeEventAsset].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_BridgeEventAsset_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[BridgeEventAsset]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEventAsset_EvidenceBundleGuid
    ON [dbo].[BridgeEventAsset] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_BridgeEventAsset_EvidenceBundleGuid] created.'
END
GO

-- ============================================================================
-- 6. dbo.BridgeContinuityIssueClaim — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[BridgeContinuityIssueClaim]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[BridgeContinuityIssueClaim]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[BridgeContinuityIssueClaim].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_BridgeContinuityIssueClaim_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[BridgeContinuityIssueClaim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeContinuityIssueClaim_EvidenceBundleGuid
    ON [dbo].[BridgeContinuityIssueClaim] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_BridgeContinuityIssueClaim_EvidenceBundleGuid] created.'
END
GO

-- ============================================================================
-- 7. dbo.BridgeEntityRelation — Add EvidenceBundleGuid
-- ============================================================================
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
    AND name = 'EvidenceBundleGuid'
)
BEGIN
    ALTER TABLE [dbo].[BridgeEntityRelation]
    ADD EvidenceBundleGuid UNIQUEIDENTIFIER NULL;
    PRINT 'Column [EvidenceBundleGuid] added to [dbo].[BridgeEntityRelation].'
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_BridgeEntityRelation_EvidenceBundleGuid'
    AND object_id = OBJECT_ID('[dbo].[BridgeEntityRelation]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_EvidenceBundleGuid
    ON [dbo].[BridgeEntityRelation] (EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
    PRINT 'Index [IX_BridgeEntityRelation_EvidenceBundleGuid] created.'
END
GO

PRINT '=== Migration 0034 complete: DVO evidence bundle linkage applied. ==='
GO
