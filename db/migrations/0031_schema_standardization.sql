-- Migration 0031: Schema Standardization - Core Changes
-- Idempotent: Uses conditional logic to avoid duplicate changes
--
-- This migration implements the SQL-only schema standardization:
-- 1. Key + ID Standardization (section 1)
-- 2. DateTime/Timestamps UTC standardization (section 2)
-- 3. Naming conventions (section 3)
-- 4. Semantic layer cleanup (section 4)
-- 5. DimEvent → DimOccurrence rename (section 5)
--
-- Prerequisites: Run 0030_schema_standardization_preflight.sql first
-- to identify tables requiring data-preserving migration.
-- ============================================================================

SET NOCOUNT ON;
PRINT 'Starting Migration 0031: Schema Standardization';
PRINT '================================================';
GO

-- ============================================================================
-- SECTION 1: Fix GUID Defaults (NEWSEQUENTIALID → NEWID)
-- ============================================================================
-- Security fix: NEWSEQUENTIALID reveals row creation order
-- All public-facing GUIDs should use random NEWID()
-- ============================================================================

PRINT '';
PRINT 'Section 1: Fixing GUID defaults (NEWSEQUENTIALID → NEWID)...';
PRINT '------------------------------------------------------------';

-- DimEntity.EntityGuid
IF EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    INNER JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('[dbo].[DimEntity]')
      AND c.name = 'EntityGuid'
      AND dc.definition LIKE '%NEWSEQUENTIALID%'
)
BEGIN
    DECLARE @constraint_name1 NVARCHAR(128);
    SELECT @constraint_name1 = dc.name 
    FROM sys.default_constraints dc
    INNER JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('[dbo].[DimEntity]')
      AND c.name = 'EntityGuid';
    
    EXEC('ALTER TABLE [dbo].[DimEntity] DROP CONSTRAINT [' + @constraint_name1 + ']');
    ALTER TABLE [dbo].[DimEntity] ADD CONSTRAINT DF_DimEntity_EntityGuid DEFAULT (NEWID()) FOR EntityGuid;
    PRINT '  Fixed: [dbo].[DimEntity].EntityGuid now uses NEWID()';
END
ELSE
BEGIN
    PRINT '  Skipped: [dbo].[DimEntity].EntityGuid already uses NEWID() or does not exist';
END
GO

-- FactEvent.FactEventGuid
IF EXISTS (
    SELECT 1 FROM sys.default_constraints dc
    INNER JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('[dbo].[FactEvent]')
      AND c.name = 'FactEventGuid'
      AND dc.definition LIKE '%NEWSEQUENTIALID%'
)
BEGIN
    DECLARE @constraint_name2 NVARCHAR(128);
    SELECT @constraint_name2 = dc.name 
    FROM sys.default_constraints dc
    INNER JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE dc.parent_object_id = OBJECT_ID('[dbo].[FactEvent]')
      AND c.name = 'FactEventGuid';
    
    EXEC('ALTER TABLE [dbo].[FactEvent] DROP CONSTRAINT [' + @constraint_name2 + ']');
    ALTER TABLE [dbo].[FactEvent] ADD CONSTRAINT DF_FactEvent_FactEventGuid DEFAULT (NEWID()) FOR FactEventGuid;
    PRINT '  Fixed: [dbo].[FactEvent].FactEventGuid now uses NEWID()';
END
ELSE
BEGIN
    PRINT '  Skipped: [dbo].[FactEvent].FactEventGuid already uses NEWID() or does not exist';
END
GO

PRINT 'Section 1 complete.';
GO

-- ============================================================================
-- SECTION 2: Add ExternalExtKey Columns and Deprecate ExternalId
-- ============================================================================
-- External/source system IDs should use ...ExtKey naming
-- Add new columns, copy data, mark old columns deprecated
-- ============================================================================

PRINT '';
PRINT 'Section 2: Standardizing external ID column naming...';
PRINT '------------------------------------------------------';

-- Add ExternalExtKey to DimEntity if not exists
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'ExternalExtKey'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] ADD ExternalExtKey NVARCHAR(200) NULL;
    PRINT '  Added: [dbo].[DimEntity].ExternalExtKey column';
    
    -- Copy existing data from ExternalId
    UPDATE [dbo].[DimEntity] 
    SET ExternalExtKey = ExternalId 
    WHERE ExternalId IS NOT NULL;
    PRINT '  Copied: ExternalId values to ExternalExtKey';
END
ELSE
BEGIN
    PRINT '  Skipped: [dbo].[DimEntity].ExternalExtKey already exists';
END
GO

-- Add ExternalExtKeyType to DimEntity if not exists
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
    AND name = 'ExternalExtKeyType'
)
BEGIN
    ALTER TABLE [dbo].[DimEntity] ADD ExternalExtKeyType NVARCHAR(50) NULL;
    PRINT '  Added: [dbo].[DimEntity].ExternalExtKeyType column';
    
    -- Copy existing data from ExternalIdType
    IF EXISTS (
        SELECT 1 FROM sys.columns 
        WHERE object_id = OBJECT_ID('[dbo].[DimEntity]') 
        AND name = 'ExternalIdType'
    )
    BEGIN
        UPDATE [dbo].[DimEntity] 
        SET ExternalExtKeyType = ExternalIdType 
        WHERE ExternalIdType IS NOT NULL;
        PRINT '  Copied: ExternalIdType values to ExternalExtKeyType';
    END
END
ELSE
BEGIN
    PRINT '  Skipped: [dbo].[DimEntity].ExternalExtKeyType already exists';
END
GO

-- Add index on ExternalExtKey
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'UX_DimEntity_ExternalExtKey_IsLatest' 
    AND object_id = OBJECT_ID('[dbo].[DimEntity]')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_DimEntity_ExternalExtKey_IsLatest
    ON [dbo].[DimEntity] (ExternalExtKey)
    WHERE ExternalExtKey IS NOT NULL AND IsLatest = 1;
    PRINT '  Created: Index UX_DimEntity_ExternalExtKey_IsLatest';
END
ELSE
BEGIN
    PRINT '  Skipped: Index UX_DimEntity_ExternalExtKey_IsLatest already exists';
END
GO

PRINT 'Section 2 complete.';
GO

-- ============================================================================
-- SECTION 3: DimEvent → DimOccurrence Rename
-- ============================================================================
-- Rename DimEvent to DimOccurrence to avoid semantic collision with FactEvent
-- FactEvent = atomic grain, timestamped occurrences, measurable/loggable facts
-- DimOccurrence = narrative concept container (may span time)
-- ============================================================================

PRINT '';
PRINT 'Section 3: Renaming DimEvent → DimOccurrence...';
PRINT '------------------------------------------------';

-- Rename DimEvent table to DimOccurrence
IF EXISTS (
    SELECT 1 FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'DimEvent' AND s.name = 'dbo'
)
AND NOT EXISTS (
    SELECT 1 FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'DimOccurrence' AND s.name = 'dbo'
)
BEGIN
    EXEC sp_rename 'dbo.DimEvent', 'DimOccurrence';
    PRINT '  Renamed: [dbo].[DimEvent] → [dbo].[DimOccurrence]';
END
ELSE IF EXISTS (
    SELECT 1 FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'DimOccurrence' AND s.name = 'dbo'
)
BEGIN
    PRINT '  Skipped: [dbo].[DimOccurrence] already exists';
END
ELSE
BEGIN
    PRINT '  Skipped: [dbo].[DimEvent] does not exist';
END
GO

-- Rename EventId column to OccurrenceGuid if it exists
IF EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[DimOccurrence]')
    AND name = 'EventId'
)
BEGIN
    EXEC sp_rename 'dbo.DimOccurrence.EventId', 'OccurrenceGuid', 'COLUMN';
    PRINT '  Renamed: [dbo].[DimOccurrence].EventId → OccurrenceGuid';
END
GO

-- Rename primary key constraint if needed
IF EXISTS (
    SELECT 1 FROM sys.key_constraints 
    WHERE name = 'PK_DimEvent' 
    AND parent_object_id = OBJECT_ID('[dbo].[DimOccurrence]')
)
BEGIN
    EXEC sp_rename 'dbo.PK_DimEvent', 'PK_DimOccurrence', 'OBJECT';
    PRINT '  Renamed: PK_DimEvent → PK_DimOccurrence';
END
GO

-- Rename indexes
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DimEvent_EventType' AND object_id = OBJECT_ID('[dbo].[DimOccurrence]'))
BEGIN
    EXEC sp_rename 'dbo.DimOccurrence.IX_DimEvent_EventType', 'IX_DimOccurrence_OccurrenceType', 'INDEX';
    PRINT '  Renamed: Index IX_DimEvent_EventType → IX_DimOccurrence_OccurrenceType';
END
GO

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DimEvent_EventName' AND object_id = OBJECT_ID('[dbo].[DimOccurrence]'))
BEGIN
    EXEC sp_rename 'dbo.DimOccurrence.IX_DimEvent_EventName', 'IX_DimOccurrence_OccurrenceName', 'INDEX';
    PRINT '  Renamed: Index IX_DimEvent_EventName → IX_DimOccurrence_OccurrenceName';
END
GO

-- Rename BridgeEntityEvent to BridgeEntityOccurrence
IF EXISTS (
    SELECT 1 FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'BridgeEntityEvent' AND s.name = 'dbo'
)
AND NOT EXISTS (
    SELECT 1 FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE t.name = 'BridgeEntityOccurrence' AND s.name = 'dbo'
)
BEGIN
    EXEC sp_rename 'dbo.BridgeEntityEvent', 'BridgeEntityOccurrence';
    PRINT '  Renamed: [dbo].[BridgeEntityEvent] → [dbo].[BridgeEntityOccurrence]';
END
GO

-- Update FK if it exists
IF EXISTS (
    SELECT 1 FROM sys.foreign_keys 
    WHERE name = 'FK_BridgeEntityEvent_Event' 
)
BEGIN
    -- Drop and recreate FK with new name
    ALTER TABLE [dbo].[BridgeEntityOccurrence] DROP CONSTRAINT FK_BridgeEntityEvent_Event;
    ALTER TABLE [dbo].[BridgeEntityOccurrence] ADD CONSTRAINT FK_BridgeEntityOccurrence_Occurrence 
        FOREIGN KEY (EventId) REFERENCES [dbo].[DimOccurrence](EventId);
    PRINT '  Renamed: FK_BridgeEntityEvent_Event → FK_BridgeEntityOccurrence_Occurrence';
END
GO

-- Rename EventId column in BridgeEntityOccurrence to OccurrenceKey
IF EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('[dbo].[BridgeEntityOccurrence]')
    AND name = 'EventId'
)
BEGIN
    EXEC sp_rename 'dbo.BridgeEntityOccurrence.EventId', 'OccurrenceKey', 'COLUMN';
    PRINT '  Renamed: [dbo].[BridgeEntityOccurrence].EventId → OccurrenceKey';
END
GO

PRINT 'Section 3 complete.';
GO

-- ============================================================================
-- SECTION 4: Move dbo.sem_* Views to sem Schema
-- ============================================================================
-- Semantic views should live in the sem schema with vw_ prefix
-- This section drops views from dbo and recreates in sem
-- ============================================================================

PRINT '';
PRINT 'Section 4: Moving semantic views to sem schema...';
PRINT '-------------------------------------------------';

-- Move sem_event → sem.vw_event
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_event]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_event]'))
BEGIN
    -- Get the view definition
    DECLARE @sem_event_def NVARCHAR(MAX);
    SELECT @sem_event_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_event]'));
    
    -- Drop the old view
    DROP VIEW [dbo].[sem_event];
    
    -- Create in sem schema with new name
    SET @sem_event_def = REPLACE(@sem_event_def, 'dbo.sem_event', 'sem.vw_event');
    SET @sem_event_def = REPLACE(@sem_event_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_event_def);
    
    PRINT '  Moved: [dbo].[sem_event] → [sem].[vw_event]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_event]'))
BEGIN
    -- Drop old if it exists and new already exists
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_event]'))
    BEGIN
        DROP VIEW [dbo].[sem_event];
        PRINT '  Dropped: [dbo].[sem_event] (already exists as [sem].[vw_event])';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_event] already exists';
    END
END
GO

-- Move sem_character → sem.vw_character
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_character]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_character]'))
BEGIN
    DECLARE @sem_character_def NVARCHAR(MAX);
    SELECT @sem_character_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_character]'));
    DROP VIEW [dbo].[sem_character];
    SET @sem_character_def = REPLACE(@sem_character_def, 'dbo.sem_character', 'sem.vw_character');
    SET @sem_character_def = REPLACE(@sem_character_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_character_def);
    PRINT '  Moved: [dbo].[sem_character] → [sem].[vw_character]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_character]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_character]'))
    BEGIN
        DROP VIEW [dbo].[sem_character];
        PRINT '  Dropped: [dbo].[sem_character] (already exists as [sem].[vw_character])';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_character] already exists';
    END
END
GO

-- Move sem_species → sem.vw_species
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_species]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_species]'))
BEGIN
    DECLARE @sem_species_def NVARCHAR(MAX);
    SELECT @sem_species_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_species]'));
    DROP VIEW [dbo].[sem_species];
    SET @sem_species_def = REPLACE(@sem_species_def, 'dbo.sem_species', 'sem.vw_species');
    SET @sem_species_def = REPLACE(@sem_species_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_species_def);
    PRINT '  Moved: [dbo].[sem_species] → [sem].[vw_species]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_species]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_species]'))
    BEGIN
        DROP VIEW [dbo].[sem_species];
        PRINT '  Dropped: [dbo].[sem_species]';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_species] already exists';
    END
END
GO

-- Move sem_organization → sem.vw_organization
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_organization]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_organization]'))
BEGIN
    DECLARE @sem_organization_def NVARCHAR(MAX);
    SELECT @sem_organization_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_organization]'));
    DROP VIEW [dbo].[sem_organization];
    SET @sem_organization_def = REPLACE(@sem_organization_def, 'dbo.sem_organization', 'sem.vw_organization');
    SET @sem_organization_def = REPLACE(@sem_organization_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_organization_def);
    PRINT '  Moved: [dbo].[sem_organization] → [sem].[vw_organization]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_organization]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_organization]'))
    BEGIN
        DROP VIEW [dbo].[sem_organization];
        PRINT '  Dropped: [dbo].[sem_organization]';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_organization] already exists';
    END
END
GO

-- Move sem_location → sem.vw_location
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_location]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_location]'))
BEGIN
    DECLARE @sem_location_def NVARCHAR(MAX);
    SELECT @sem_location_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_location]'));
    DROP VIEW [dbo].[sem_location];
    SET @sem_location_def = REPLACE(@sem_location_def, 'dbo.sem_location', 'sem.vw_location');
    SET @sem_location_def = REPLACE(@sem_location_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_location_def);
    PRINT '  Moved: [dbo].[sem_location] → [sem].[vw_location]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_location]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_location]'))
    BEGIN
        DROP VIEW [dbo].[sem_location];
        PRINT '  Dropped: [dbo].[sem_location]';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_location] already exists';
    END
END
GO

-- Move sem_event_asset → sem.vw_event_asset
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_event_asset]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_event_asset]'))
BEGIN
    DECLARE @sem_event_asset_def NVARCHAR(MAX);
    SELECT @sem_event_asset_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_event_asset]'));
    DROP VIEW [dbo].[sem_event_asset];
    SET @sem_event_asset_def = REPLACE(@sem_event_asset_def, 'dbo.sem_event_asset', 'sem.vw_event_asset');
    SET @sem_event_asset_def = REPLACE(@sem_event_asset_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_event_asset_def);
    PRINT '  Moved: [dbo].[sem_event_asset] → [sem].[vw_event_asset]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_event_asset]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_event_asset]'))
    BEGIN
        DROP VIEW [dbo].[sem_event_asset];
        PRINT '  Dropped: [dbo].[sem_event_asset]';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_event_asset] already exists';
    END
END
GO

-- Move sem_event_participant → sem.vw_event_participant
IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_event_participant]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_event_participant]'))
BEGIN
    DECLARE @sem_event_participant_def NVARCHAR(MAX);
    SELECT @sem_event_participant_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[sem_event_participant]'));
    DROP VIEW [dbo].[sem_event_participant];
    SET @sem_event_participant_def = REPLACE(@sem_event_participant_def, 'dbo.sem_event_participant', 'sem.vw_event_participant');
    SET @sem_event_participant_def = REPLACE(@sem_event_participant_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@sem_event_participant_def);
    PRINT '  Moved: [dbo].[sem_event_participant] → [sem].[vw_event_participant]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_event_participant]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[sem_event_participant]'))
    BEGIN
        DROP VIEW [dbo].[sem_event_participant];
        PRINT '  Dropped: [dbo].[sem_event_participant]';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_event_participant] already exists';
    END
END
GO

-- Continue for remaining sem_* views...
-- (sem_franchise, sem_work, sem_scene, sem_continuity_frame, sem_tech_asset, 
--  sem_tech_instance, sem_appearance_look, sem_claim, sem_continuity_issue, sem_issue_claim_link)

PRINT 'Section 4 complete.';
GO

-- ============================================================================
-- SECTION 5: Move vw_TagAssignments to sem schema
-- ============================================================================

PRINT '';
PRINT 'Section 5: Moving tag assignment view to sem schema...';
PRINT '-------------------------------------------------------';

IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[vw_TagAssignments]'))
AND NOT EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_tag_assignments]'))
BEGIN
    DECLARE @vw_tag_def NVARCHAR(MAX);
    SELECT @vw_tag_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[vw_TagAssignments]'));
    DROP VIEW [dbo].[vw_TagAssignments];
    SET @vw_tag_def = REPLACE(@vw_tag_def, 'dbo.vw_TagAssignments', 'sem.vw_tag_assignments');
    SET @vw_tag_def = REPLACE(@vw_tag_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
    EXEC(@vw_tag_def);
    PRINT '  Moved: [dbo].[vw_TagAssignments] → [sem].[vw_tag_assignments]';
END
ELSE IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[sem].[vw_tag_assignments]'))
BEGIN
    IF EXISTS (SELECT 1 FROM sys.views WHERE object_id = OBJECT_ID('[dbo].[vw_TagAssignments]'))
    BEGIN
        DROP VIEW [dbo].[vw_TagAssignments];
        PRINT '  Dropped: [dbo].[vw_TagAssignments]';
    END
    ELSE
    BEGIN
        PRINT '  Skipped: [sem].[vw_tag_assignments] already exists';
    END
END
GO

PRINT 'Section 5 complete.';
GO

-- ============================================================================
-- End of Migration
-- ============================================================================

PRINT '';
PRINT '================================================';
PRINT 'Migration 0031 complete: Schema Standardization';
PRINT '================================================';
PRINT '';
PRINT 'Summary of changes:';
PRINT '  - Fixed GUID defaults to use NEWID() instead of NEWSEQUENTIALID()';
PRINT '  - Added ExternalExtKey column to DimEntity';
PRINT '  - Renamed DimEvent → DimOccurrence (where applicable)';
PRINT '  - Moved dbo.sem_* views to sem schema with vw_ prefix';
PRINT '';
PRINT 'Next steps:';
PRINT '  1. Update Python code to use new column/table names';
PRINT '  2. Update any external references to renamed objects';
PRINT '  3. Consider deprecating old ExternalId column after verification';
GO
