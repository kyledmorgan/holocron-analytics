-- Migration 0018: Add promotion and inferred type columns to dbo.DimEntity
-- Idempotent: Only adds columns if they don't exist
-- Additive-only (no drops)
--
-- Purpose: Add promotion/adjudication state and semantic staging outputs to DimEntity.
-- Columns added:
--   - PromotionState: staged | candidate | adjudicated | promoted | suppressed | merged
--   - PromotionDecisionUtc: When the promotion decision was made
--   - PromotionDecidedBy: Who made the promotion decision
--   - PromotionReason: Reason for the promotion decision
--   - SourcePageId: FK to sem.SourcePage
--   - PrimaryTypeInferred: Inferred primary type from page classification
--   - TypeSetJsonInferred: Inferred type set (multi-label with weights)
--   - AdjudicationRunId: FK to llm.run for adjudication lineage

-- ============================================================================
-- Add PromotionState column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'PromotionState'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD PromotionState NVARCHAR(30) NOT NULL DEFAULT 'staged';
    PRINT 'Column [PromotionState] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [PromotionState] already exists on [dbo].[DimEntity].'
END
GO

-- Add check constraint for PromotionState values
IF NOT EXISTS (
    SELECT * FROM sys.check_constraints 
    WHERE name = 'CK_DimEntity_PromotionState' 
    AND parent_object_id = OBJECT_ID('[dbo].[DimEntity]')
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD CONSTRAINT CK_DimEntity_PromotionState 
    CHECK (PromotionState IN ('staged', 'candidate', 'adjudicated', 'promoted', 'suppressed', 'merged'));
    PRINT 'Constraint [CK_DimEntity_PromotionState] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Constraint [CK_DimEntity_PromotionState] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add PromotionDecisionUtc column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'PromotionDecisionUtc'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD PromotionDecisionUtc DATETIME2 NULL;
    PRINT 'Column [PromotionDecisionUtc] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [PromotionDecisionUtc] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add PromotionDecidedBy column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'PromotionDecidedBy'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD PromotionDecidedBy NVARCHAR(100) NULL;
    PRINT 'Column [PromotionDecidedBy] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [PromotionDecidedBy] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add PromotionReason column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'PromotionReason'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD PromotionReason NVARCHAR(500) NULL;
    PRINT 'Column [PromotionReason] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [PromotionReason] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add SourcePageId column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'SourcePageId'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD SourcePageId UNIQUEIDENTIFIER NULL;
    PRINT 'Column [SourcePageId] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [SourcePageId] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add PrimaryTypeInferred column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'PrimaryTypeInferred'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD PrimaryTypeInferred NVARCHAR(100) NULL;
    PRINT 'Column [PrimaryTypeInferred] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [PrimaryTypeInferred] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add TypeSetJsonInferred column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'TypeSetJsonInferred'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD TypeSetJsonInferred NVARCHAR(MAX) NULL;
    PRINT 'Column [TypeSetJsonInferred] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [TypeSetJsonInferred] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Add AdjudicationRunId column
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'AdjudicationRunId'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] 
    ADD AdjudicationRunId UNIQUEIDENTIFIER NULL;
    PRINT 'Column [AdjudicationRunId] added to [dbo].[DimEntity].'
END
ELSE
BEGIN
    PRINT 'Column [AdjudicationRunId] already exists on [dbo].[DimEntity].'
END
GO

-- ============================================================================
-- Indexes for new columns
-- ============================================================================

-- Index for PromotionState lookups (filtering by promotion state)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimEntity_PromotionState' 
    AND object_id = OBJECT_ID('[dbo].[DimEntity]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimEntity_PromotionState
    ON [dbo].[DimEntity] (PromotionState)
    WHERE IsLatest = 1;
    PRINT 'Index [IX_DimEntity_PromotionState] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimEntity_PromotionState] already exists.'
END
GO

-- Index for SourcePageId FK lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimEntity_SourcePageId' 
    AND object_id = OBJECT_ID('[dbo].[DimEntity]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimEntity_SourcePageId
    ON [dbo].[DimEntity] (SourcePageId)
    WHERE SourcePageId IS NOT NULL;
    PRINT 'Index [IX_DimEntity_SourcePageId] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimEntity_SourcePageId] already exists.'
END
GO

-- Index for PrimaryTypeInferred lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimEntity_PrimaryTypeInferred' 
    AND object_id = OBJECT_ID('[dbo].[DimEntity]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimEntity_PrimaryTypeInferred
    ON [dbo].[DimEntity] (PrimaryTypeInferred)
    WHERE PrimaryTypeInferred IS NOT NULL AND IsLatest = 1;
    PRINT 'Index [IX_DimEntity_PrimaryTypeInferred] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimEntity_PrimaryTypeInferred] already exists.'
END
GO

-- Index for promoted entities (commonly used downstream filter)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_DimEntity_Promoted' 
    AND object_id = OBJECT_ID('[dbo].[DimEntity]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimEntity_Promoted
    ON [dbo].[DimEntity] (EntityType, DisplayName)
    WHERE PromotionState = 'promoted' AND IsLatest = 1 AND IsActive = 1;
    PRINT 'Index [IX_DimEntity_Promoted] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_DimEntity_Promoted] already exists.'
END
GO

PRINT 'Migration 0018 completed: Promotion and inferred type columns added to DimEntity.'
