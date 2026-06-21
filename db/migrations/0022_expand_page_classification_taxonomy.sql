-- Migration 0022: Expand page classification taxonomy and add WorkMedia metadata
-- Idempotent: Only adds columns if they don't exist
--
-- Purpose: Expand PrimaryType taxonomy to reduce Unknown classifications
-- and add second-layer WorkMedia metadata (work_medium, canon_context).
--
-- New PrimaryType values supported:
--   - Droid (named droids or droid model lines)
--   - VehicleCraft (starships, starfighters, vehicles with specs)
--   - ObjectItem (weapons, gear, armor, apparel)
--   - ReferenceMeta (lists, timelines, disambiguation pages)
--   - ObjectArtifact (legacy: general objects)
--   - Unknown (replaces "Other")
--
-- Removed/consolidated types:
--   - Technology/Vehicle/Weapon merged into VehicleCraft/ObjectItem/ObjectArtifact
--   - MetaReference renamed to ReferenceMeta
--   - Other renamed to Unknown
--
-- New columns on sem.PageClassification:
--   - work_medium: Medium type for WorkMedia pages (film/tv/game/book/comic/etc.)
--   - canon_context: Canon context for WorkMedia pages (canon/legends/both/unknown)

-- ============================================================================
-- Add work_medium column to sem.PageClassification
-- ============================================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageClassification]') 
    AND name = 'work_medium'
)
BEGIN
    ALTER TABLE [sem].[PageClassification]
    ADD work_medium NVARCHAR(20) NULL;
    PRINT 'Column [work_medium] added to sem.PageClassification.'
END
ELSE
BEGIN
    PRINT 'Column [work_medium] already exists on sem.PageClassification.'
END
GO

-- Add CHECK constraint for work_medium enum values
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints 
    WHERE name = 'CK_sem_PageClassification_WorkMedium'
    AND parent_object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    ALTER TABLE [sem].[PageClassification]
    ADD CONSTRAINT CK_sem_PageClassification_WorkMedium 
    CHECK (work_medium IN (
        'film', 'tv', 'game', 'book', 'comic', 'reference', 
        'episode', 'short', 'other', 'unknown'
    ) OR work_medium IS NULL);
    PRINT 'CHECK constraint [CK_sem_PageClassification_WorkMedium] created successfully.'
END
ELSE
BEGIN
    PRINT 'CHECK constraint [CK_sem_PageClassification_WorkMedium] already exists.'
END
GO

-- ============================================================================
-- Add canon_context column to sem.PageClassification
-- ============================================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[sem].[PageClassification]') 
    AND name = 'canon_context'
)
BEGIN
    ALTER TABLE [sem].[PageClassification]
    ADD canon_context NVARCHAR(20) NULL;
    PRINT 'Column [canon_context] added to sem.PageClassification.'
END
ELSE
BEGIN
    PRINT 'Column [canon_context] already exists on sem.PageClassification.'
END
GO

-- Add CHECK constraint for canon_context enum values
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints 
    WHERE name = 'CK_sem_PageClassification_CanonContext'
    AND parent_object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    ALTER TABLE [sem].[PageClassification]
    ADD CONSTRAINT CK_sem_PageClassification_CanonContext 
    CHECK (canon_context IN ('canon', 'legends', 'both', 'unknown') OR canon_context IS NULL);
    PRINT 'CHECK constraint [CK_sem_PageClassification_CanonContext] created successfully.'
END
ELSE
BEGIN
    PRINT 'CHECK constraint [CK_sem_PageClassification_CanonContext] already exists.'
END
GO

-- ============================================================================
-- Add indexes for WorkMedia filtering
-- ============================================================================

-- Index for work_medium lookups (for WorkMedia analysis)
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_WorkMedium' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_WorkMedium
    ON [sem].[PageClassification] (work_medium, canon_context)
    WHERE is_current = 1 AND work_medium IS NOT NULL;
    PRINT 'Index [IX_sem_PageClassification_WorkMedium] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_WorkMedium] already exists.'
END
GO

-- Index for canon_context lookups
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_sem_PageClassification_CanonContext' 
    AND object_id = OBJECT_ID('[sem].[PageClassification]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_sem_PageClassification_CanonContext
    ON [sem].[PageClassification] (canon_context, primary_type)
    WHERE is_current = 1 AND canon_context IS NOT NULL;
    PRINT 'Index [IX_sem_PageClassification_CanonContext] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_sem_PageClassification_CanonContext] already exists.'
END
GO

-- ============================================================================
-- Documentation: PrimaryType taxonomy updates
-- ============================================================================

-- The primary_type column already exists as NVARCHAR(100) and can accommodate
-- the new type names without schema changes. The following types are now supported:
--
-- Core entity types:
--   - PersonCharacter: Sentient individuals with biography
--   - Droid: Named droids or droid model lines (NEW)
--   - Species: Biological species or sentient groups
--
-- Places and structures:
--   - LocationPlace: Planets, cities, bases, facilities
--
-- Objects and technology:
--   - VehicleCraft: Starships, starfighters, vehicles with specs (NEW)
--   - ObjectItem: Weapons, gear, armor, clothing, physical items (NEW)
--   - ObjectArtifact: Legacy general objects (kept for compatibility)
--
-- Organizations and concepts:
--   - Organization: Governments, militaries, orders, corporations
--   - Concept: Abstract ideas, systems, philosophies
--
-- Events and time:
--   - EventConflict: Battles, wars, raids, missions
--   - TimePeriod: Eras, ages, periods
--
-- Media and content:
--   - WorkMedia: Films, episodes, novels, comics, games
--
-- Meta and reference:
--   - ReferenceMeta: Lists, timelines, disambiguation pages (renamed from MetaReference)
--   - TechnicalSitePage: Wiki infrastructure pages
--
-- Unknown:
--   - Unknown: Pages that don't fit any category (renamed from Other)
--
-- The application code (Python enums, JSON schemas, prompts) has been updated
-- to use these new types. No data migration is needed as this is additive.

PRINT 'Migration 0022 completed: PrimaryType taxonomy expanded and WorkMedia metadata columns added.'
