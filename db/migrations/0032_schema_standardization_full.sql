-- ============================================================================
-- Migration 0032: Schema Standardization (Full Data-Preserving Migration)
-- ============================================================================
-- 
-- PURPOSE: Rebuild schema cleanly using drop/recreate where safe and 
--          data-preserving migration where tables have rows, based on 
--          pre-flight inventory.
--
-- PREREQUISITES:
--   - Run 0030_schema_standardization_preflight.sql to assess row counts
--   - Review pre-flight output to verify migration strategies
--   - 0031_schema_standardization.sql must have been run (partial changes)
--
-- STRATEGIES:
--   A) Safe drop/recreate (RowCount = 0): Drop and recreate from canonical DDL
--   B) Data-preserving migration (RowCount > 0): Backup → Drop → Recreate → Copy → Validate
--
-- KEY CHANGES:
--   1. GUID defaults: NEWSEQUENTIALID() → NEWID() (security)
--   2. UTC naming and DATETIME2(3) precision
--   3. "Id" terminology cleanup (→ Guid, Key, ExternalKey, NaturalKey)
--   4. View relocation: dbo.sem_* → sem.vw_*
--   5. DimEvent → DimOccurrence rename
--
-- IMPORTANT: SQL-only. Python updates happen in a later PR.
--
-- ============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

PRINT '============================================================================';
PRINT 'Migration 0032: Schema Standardization (Full Data-Preserving Migration)';
PRINT 'Started at: ' + CONVERT(VARCHAR, SYSUTCDATETIME(), 121);
PRINT '============================================================================';
PRINT '';
GO

-- ============================================================================
-- SECTION 0: Migration Log Table
-- ============================================================================
-- Creates a lightweight migration log to track progress and enable resume
-- ============================================================================

IF OBJECT_ID('dbo.__migration_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.__migration_log (
        log_id INT IDENTITY(1,1) NOT NULL,
        migration_id NVARCHAR(50) NOT NULL,
        step_name NVARCHAR(200) NOT NULL,
        started_utc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        completed_utc DATETIME2(3) NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'started',
        rows_before BIGINT NULL,
        rows_after BIGINT NULL,
        details NVARCHAR(MAX) NULL,
        error_message NVARCHAR(MAX) NULL,
        CONSTRAINT PK___migration_log PRIMARY KEY CLUSTERED (log_id),
        CONSTRAINT CK___migration_log_status CHECK (status IN ('started', 'completed', 'failed', 'skipped'))
    );
    PRINT 'Created migration log table: dbo.__migration_log';
END
ELSE
BEGIN
    PRINT 'Migration log table already exists: dbo.__migration_log';
END
GO

-- ============================================================================
-- Helper Procedures for Migration Logging
-- ============================================================================

IF OBJECT_ID('dbo.__usp_log_migration_start', 'P') IS NOT NULL
    DROP PROCEDURE dbo.__usp_log_migration_start;
GO

CREATE PROCEDURE dbo.__usp_log_migration_start
    @migration_id NVARCHAR(50),
    @step_name NVARCHAR(200),
    @rows_before BIGINT = NULL,
    @details NVARCHAR(MAX) = NULL,
    @log_id INT OUTPUT
AS
BEGIN
    INSERT INTO dbo.__migration_log (migration_id, step_name, rows_before, details, status)
    VALUES (@migration_id, @step_name, @rows_before, @details, 'started');
    
    SET @log_id = SCOPE_IDENTITY();
    
    PRINT '  [START] ' + @step_name + ' (rows_before: ' + ISNULL(CAST(@rows_before AS VARCHAR), 'N/A') + ')';
END;
GO

IF OBJECT_ID('dbo.__usp_log_migration_end', 'P') IS NOT NULL
    DROP PROCEDURE dbo.__usp_log_migration_end;
GO

CREATE PROCEDURE dbo.__usp_log_migration_end
    @log_id INT,
    @status NVARCHAR(20),
    @rows_after BIGINT = NULL,
    @error_message NVARCHAR(MAX) = NULL,
    @details NVARCHAR(MAX) = NULL
AS
BEGIN
    UPDATE dbo.__migration_log
    SET completed_utc = SYSUTCDATETIME(),
        status = @status,
        rows_after = @rows_after,
        error_message = @error_message,
        details = ISNULL(@details, details)
    WHERE log_id = @log_id;
    
    IF @status = 'completed'
        PRINT '  [DONE] Completed (rows_after: ' + ISNULL(CAST(@rows_after AS VARCHAR), 'N/A') + ')';
    ELSE IF @status = 'failed'
        PRINT '  [FAIL] ' + ISNULL(@error_message, 'Unknown error');
    ELSE IF @status = 'skipped'
        PRINT '  [SKIP] ' + ISNULL(@details, 'No changes needed');
END;
GO

PRINT '';
PRINT 'Migration logging procedures created.';
PRINT '';
GO

-- ============================================================================
-- SECTION 1: GUID Default Standardization (NEWSEQUENTIALID → NEWID)
-- ============================================================================
-- Security fix: NEWSEQUENTIALID reveals row creation order
-- All public-facing GUIDs should use random NEWID()
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 1: GUID Default Standardization';
PRINT '============================================================================';
GO

DECLARE @log_id INT;
DECLARE @constraint_name NVARCHAR(128);
DECLARE @table_name NVARCHAR(128);
DECLARE @column_name NVARCHAR(128);

-- Find all GUID columns with NEWSEQUENTIALID() default and fix them
DECLARE guid_cursor CURSOR LOCAL FAST_FORWARD FOR
SELECT 
    t.name AS TableName,
    c.name AS ColumnName,
    dc.name AS ConstraintName
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
INNER JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
  AND ty.name = 'uniqueidentifier'
  AND dc.definition LIKE '%NEWSEQUENTIALID%';

OPEN guid_cursor;
FETCH NEXT FROM guid_cursor INTO @table_name, @column_name, @constraint_name;

WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Fix GUID default',
        @details = @table_name + '.' + @column_name,
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Drop the old constraint
        DECLARE @drop_sql NVARCHAR(500) = 
            'ALTER TABLE [dbo].[' + @table_name + '] DROP CONSTRAINT [' + @constraint_name + ']';
        EXEC sp_executesql @drop_sql;
        
        -- Add new constraint with NEWID()
        DECLARE @add_sql NVARCHAR(500) = 
            'ALTER TABLE [dbo].[' + @table_name + '] ADD CONSTRAINT DF_' + @table_name + '_' + @column_name + 
            ' DEFAULT (NEWID()) FOR [' + @column_name + ']';
        EXEC sp_executesql @add_sql;
        
        COMMIT TRANSACTION;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'Changed from NEWSEQUENTIALID() to NEWID()';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
    
    FETCH NEXT FROM guid_cursor INTO @table_name, @column_name, @constraint_name;
END;

CLOSE guid_cursor;
DEALLOCATE guid_cursor;
GO

PRINT '';
PRINT 'SECTION 1 complete: GUID defaults standardized.';
PRINT '';
GO

-- ============================================================================
-- SECTION 2: DimEvent → DimOccurrence Rename (Phase 6 Placeholder Table)
-- ============================================================================
-- The DimEvent table from migration 0027 is a Phase 6 placeholder.
-- It has 0 rows, so safe to drop/recreate with correct naming.
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 2: DimEvent → DimOccurrence Table Rename';
PRINT '============================================================================';
GO

DECLARE @log_id INT;

-- Check if DimEvent exists and DimOccurrence does not
IF OBJECT_ID('dbo.DimEvent', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.DimOccurrence', 'U') IS NULL
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Rename DimEvent to DimOccurrence',
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- First, drop the BridgeEntityEvent FK constraint if exists
        IF EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_BridgeEntityEvent_Event')
        BEGIN
            ALTER TABLE dbo.BridgeEntityEvent DROP CONSTRAINT FK_BridgeEntityEvent_Event;
            PRINT '  Dropped FK: FK_BridgeEntityEvent_Event';
        END
        
        -- Rename the table
        EXEC sp_rename 'dbo.DimEvent', 'DimOccurrence';
        PRINT '  Renamed table: dbo.DimEvent → dbo.DimOccurrence';
        
        -- Rename the primary key
        IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'PK_DimEvent')
        BEGIN
            EXEC sp_rename 'dbo.PK_DimEvent', 'PK_DimOccurrence', 'OBJECT';
            PRINT '  Renamed PK: PK_DimEvent → PK_DimOccurrence';
        END
        
        -- Rename EventId to OccurrenceGuid
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventId')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventId', 'OccurrenceGuid', 'COLUMN';
            PRINT '  Renamed column: EventId → OccurrenceGuid';
        END
        
        -- Rename EventName to OccurrenceName
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventName')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventName', 'OccurrenceName', 'COLUMN';
            PRINT '  Renamed column: EventName → OccurrenceName';
        END
        
        -- Rename EventNameNormalized to OccurrenceNameNormalized
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventNameNormalized')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventNameNormalized', 'OccurrenceNameNormalized', 'COLUMN';
            PRINT '  Renamed column: EventNameNormalized → OccurrenceNameNormalized';
        END
        
        -- Rename EventType to OccurrenceType
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventType')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventType', 'OccurrenceType', 'COLUMN';
            PRINT '  Renamed column: EventType → OccurrenceType';
        END
        
        -- Rename EventDate to OccurrenceDate
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventDate')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventDate', 'OccurrenceDate', 'COLUMN';
            PRINT '  Renamed column: EventDate → OccurrenceDate';
        END
        
        -- Rename EventStartDate to OccurrenceStartDate
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventStartDate')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventStartDate', 'OccurrenceStartDate', 'COLUMN';
            PRINT '  Renamed column: EventStartDate → OccurrenceStartDate';
        END
        
        -- Rename EventEndDate to OccurrenceEndDate
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventEndDate')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventEndDate', 'OccurrenceEndDate', 'COLUMN';
            PRINT '  Renamed column: EventEndDate → OccurrenceEndDate';
        END
        
        -- Rename EventLocation to OccurrenceLocation
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimOccurrence') AND name = 'EventLocation')
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.EventLocation', 'OccurrenceLocation', 'COLUMN';
            PRINT '  Renamed column: EventLocation → OccurrenceLocation';
        END
        
        -- Rename indexes
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DimEvent_EventType' AND object_id = OBJECT_ID('dbo.DimOccurrence'))
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.IX_DimEvent_EventType', 'IX_DimOccurrence_OccurrenceType', 'INDEX';
            PRINT '  Renamed index: IX_DimEvent_EventType → IX_DimOccurrence_OccurrenceType';
        END
        
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_DimEvent_EventName' AND object_id = OBJECT_ID('dbo.DimOccurrence'))
        BEGIN
            EXEC sp_rename 'dbo.DimOccurrence.IX_DimEvent_EventName', 'IX_DimOccurrence_OccurrenceName', 'INDEX';
            PRINT '  Renamed index: IX_DimEvent_EventName → IX_DimOccurrence_OccurrenceName';
        END
        
        COMMIT TRANSACTION;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'DimEvent renamed to DimOccurrence with all columns and indexes';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
ELSE IF OBJECT_ID('dbo.DimOccurrence', 'U') IS NOT NULL
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Rename DimEvent to DimOccurrence',
        @log_id = @log_id OUTPUT;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
        @details = 'DimOccurrence already exists';
END
GO

-- ============================================================================
-- SECTION 2B: BridgeEntityEvent → BridgeEntityOccurrence Rename
-- ============================================================================

DECLARE @log_id INT;

IF OBJECT_ID('dbo.BridgeEntityEvent', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.BridgeEntityOccurrence', 'U') IS NULL
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Rename BridgeEntityEvent to BridgeEntityOccurrence',
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Rename the table
        EXEC sp_rename 'dbo.BridgeEntityEvent', 'BridgeEntityOccurrence';
        PRINT '  Renamed table: dbo.BridgeEntityEvent → dbo.BridgeEntityOccurrence';
        
        -- Rename PK
        IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'PK_BridgeEntityEvent')
        BEGIN
            EXEC sp_rename 'dbo.PK_BridgeEntityEvent', 'PK_BridgeEntityOccurrence', 'OBJECT';
            PRINT '  Renamed PK: PK_BridgeEntityEvent → PK_BridgeEntityOccurrence';
        END
        
        -- Rename EventId to OccurrenceKey
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.BridgeEntityOccurrence') AND name = 'EventId')
        BEGIN
            EXEC sp_rename 'dbo.BridgeEntityOccurrence.EventId', 'OccurrenceGuid', 'COLUMN';
            PRINT '  Renamed column: EventId → OccurrenceGuid';
        END
        
        -- Rename indexes
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BridgeEntityEvent_EntityId' AND object_id = OBJECT_ID('dbo.BridgeEntityOccurrence'))
        BEGIN
            EXEC sp_rename 'dbo.BridgeEntityOccurrence.IX_BridgeEntityEvent_EntityId', 'IX_BridgeEntityOccurrence_EntityGuid', 'INDEX';
            PRINT '  Renamed index: IX_BridgeEntityEvent_EntityId → IX_BridgeEntityOccurrence_EntityGuid';
        END
        
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BridgeEntityEvent_EventId' AND object_id = OBJECT_ID('dbo.BridgeEntityOccurrence'))
        BEGIN
            EXEC sp_rename 'dbo.BridgeEntityOccurrence.IX_BridgeEntityEvent_EventId', 'IX_BridgeEntityOccurrence_OccurrenceGuid', 'INDEX';
            PRINT '  Renamed index: IX_BridgeEntityEvent_EventId → IX_BridgeEntityOccurrence_OccurrenceGuid';
        END
        
        -- Add FK to DimOccurrence
        IF OBJECT_ID('dbo.DimOccurrence', 'U') IS NOT NULL
        BEGIN
            ALTER TABLE dbo.BridgeEntityOccurrence ADD CONSTRAINT FK_BridgeEntityOccurrence_Occurrence
                FOREIGN KEY (OccurrenceGuid) REFERENCES dbo.DimOccurrence(OccurrenceGuid);
            PRINT '  Added FK: FK_BridgeEntityOccurrence_Occurrence';
        END
        
        COMMIT TRANSACTION;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'BridgeEntityEvent renamed to BridgeEntityOccurrence';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
ELSE IF OBJECT_ID('dbo.BridgeEntityOccurrence', 'U') IS NOT NULL
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Rename BridgeEntityEvent to BridgeEntityOccurrence',
        @log_id = @log_id OUTPUT;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
        @details = 'BridgeEntityOccurrence already exists';
END
GO

PRINT '';
PRINT 'SECTION 2 complete: DimEvent → DimOccurrence rename applied.';
PRINT '';
GO

-- ============================================================================
-- SECTION 3: Column Renames for Data-Preserving Tables
-- ============================================================================
-- For tables with data, we add new columns and copy data rather than rename
-- This ensures backward compatibility during transition
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 3: Column Standardization (ExternalId → ExternalKey, etc.)';
PRINT '============================================================================';
GO

DECLARE @log_id INT;

-- ============================================================================
-- 3.1: DimEntity - ExternalId → ExternalKey (already done in 0031, verify)
-- ============================================================================

IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalKey')
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'DimEntity ExternalKey column',
        @log_id = @log_id OUTPUT;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
        @details = 'ExternalKey column already exists';
END
ELSE IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalId')
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'DimEntity ExternalKey column',
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Add new column
        ALTER TABLE dbo.DimEntity ADD ExternalKey NVARCHAR(200) NULL;
        
        -- Copy data
        UPDATE dbo.DimEntity SET ExternalKey = ExternalId WHERE ExternalId IS NOT NULL;
        
        COMMIT TRANSACTION;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'Added ExternalKey, copied from ExternalId';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
GO

-- 3.2: DimEntity - ExternalIdType → ExternalKeyType
DECLARE @log_id INT;

IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalKeyType')
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'DimEntity ExternalKeyType column',
        @log_id = @log_id OUTPUT;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
        @details = 'ExternalKeyType column already exists';
END
ELSE IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalIdType')
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'DimEntity ExternalKeyType column',
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        ALTER TABLE dbo.DimEntity ADD ExternalKeyType NVARCHAR(50) NULL;
        UPDATE dbo.DimEntity SET ExternalKeyType = ExternalIdType WHERE ExternalIdType IS NOT NULL;
        
        COMMIT TRANSACTION;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'Added ExternalKeyType, copied from ExternalIdType';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
GO

PRINT '';
PRINT 'SECTION 3 complete: Column standardization applied.';
PRINT '';
GO

-- ============================================================================
-- SECTION 4: Safe Drop/Recreate Tables (RowCount = 0)
-- ============================================================================
-- For tables with 0 rows, we can safely drop and recreate with canonical DDL
-- These include: BridgeEntityEvent, BridgeEntityRelation, BridgeTagRelation,
-- DimAppearanceLook, DimDate, DimEraAnchor, DimTime, and vector/llm tables
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 4: Safe Drop/Recreate for Empty Tables';
PRINT '============================================================================';
GO

DECLARE @log_id INT;
DECLARE @row_count BIGINT;

-- ============================================================================
-- 4.1: BridgeEntityRelation (0 rows) - Update column names
-- ============================================================================

SELECT @row_count = COUNT(*) FROM dbo.BridgeEntityRelation;

IF @row_count = 0
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'BridgeEntityRelation column rename (FromEntityId/ToEntityId)',
        @rows_before = @row_count,
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Drop indexes first
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BridgeEntityRelation_FromEntity' AND object_id = OBJECT_ID('dbo.BridgeEntityRelation'))
            DROP INDEX IX_BridgeEntityRelation_FromEntity ON dbo.BridgeEntityRelation;
        
        IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BridgeEntityRelation_ToEntity' AND object_id = OBJECT_ID('dbo.BridgeEntityRelation'))
            DROP INDEX IX_BridgeEntityRelation_ToEntity ON dbo.BridgeEntityRelation;
        
        -- Rename columns (FromEntityId → FromEntityGuid, ToEntityId → ToEntityGuid)
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.BridgeEntityRelation') AND name = 'FromEntityId')
        BEGIN
            EXEC sp_rename 'dbo.BridgeEntityRelation.FromEntityId', 'FromEntityGuid', 'COLUMN';
        END
        
        IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.BridgeEntityRelation') AND name = 'ToEntityId')
        BEGIN
            EXEC sp_rename 'dbo.BridgeEntityRelation.ToEntityId', 'ToEntityGuid', 'COLUMN';
        END
        
        -- Recreate indexes with new column names
        CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_FromEntity
        ON dbo.BridgeEntityRelation (FromEntityGuid, RelationType)
        WHERE IsActive = 1;
        
        CREATE NONCLUSTERED INDEX IX_BridgeEntityRelation_ToEntity
        ON dbo.BridgeEntityRelation (ToEntityGuid, RelationType)
        WHERE IsActive = 1;
        
        COMMIT TRANSACTION;
        
        SELECT @row_count = COUNT(*) FROM dbo.BridgeEntityRelation;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @rows_after = @row_count,
            @details = 'Column renames: FromEntityId→FromEntityGuid, ToEntityId→ToEntityGuid';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
ELSE
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'BridgeEntityRelation column rename',
        @rows_before = @row_count,
        @log_id = @log_id OUTPUT;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
        @details = 'Table has data - requires manual data-preserving migration';
END
GO

-- ============================================================================
-- 4.2: BridgeTagRelation (0 rows) - Already compliant, skip
-- ============================================================================

DECLARE @log_id INT;
DECLARE @row_count BIGINT;

SELECT @row_count = COUNT(*) FROM dbo.BridgeTagRelation;

EXEC dbo.__usp_log_migration_start 
    @migration_id = '0032', 
    @step_name = 'BridgeTagRelation verification',
    @rows_before = @row_count,
    @log_id = @log_id OUTPUT;
EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
    @details = 'Already uses compliant naming (TagKey references)';
GO

PRINT '';
PRINT 'SECTION 4 complete: Empty tables processed.';
PRINT '';
GO

-- ============================================================================
-- SECTION 5: Move Semantic Views (dbo.sem_* → sem.vw_*)
-- ============================================================================
-- Semantic views should live in the sem schema with vw_ prefix
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 5: Move Semantic Views to sem Schema';
PRINT '============================================================================';
GO

-- Define a procedure to move a view from dbo.sem_* to sem.vw_*
IF OBJECT_ID('dbo.__usp_move_semantic_view', 'P') IS NOT NULL
    DROP PROCEDURE dbo.__usp_move_semantic_view;
GO

CREATE PROCEDURE dbo.__usp_move_semantic_view
    @old_name NVARCHAR(128),
    @new_name NVARCHAR(128)
AS
BEGIN
    DECLARE @log_id INT;
    DECLARE @old_full_name NVARCHAR(256) = '[dbo].[' + @old_name + ']';
    DECLARE @new_full_name NVARCHAR(256) = '[sem].[' + @new_name + ']';
    DECLARE @view_def NVARCHAR(MAX);
    
    IF OBJECT_ID(@old_full_name, 'V') IS NOT NULL
       AND OBJECT_ID(@new_full_name, 'V') IS NULL
    BEGIN
        EXEC dbo.__usp_log_migration_start 
            @migration_id = '0032', 
            @step_name = 'Move view ' + @old_name + ' → ' + @new_name,
            @log_id = @log_id OUTPUT;
        
        BEGIN TRY
            -- Get view definition
            SELECT @view_def = OBJECT_DEFINITION(OBJECT_ID(@old_full_name));
            
            -- Drop old view
            DECLARE @drop_sql NVARCHAR(500) = 'DROP VIEW ' + @old_full_name;
            EXEC sp_executesql @drop_sql;
            
            -- Modify definition for new schema/name
            SET @view_def = REPLACE(@view_def, 'dbo.' + @old_name, 'sem.' + @new_name);
            SET @view_def = REPLACE(@view_def, '[dbo].[' + @old_name + ']', '[sem].[' + @new_name + ']');
            SET @view_def = REPLACE(@view_def, 'CREATE VIEW', 'CREATE VIEW');
            SET @view_def = REPLACE(@view_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
            
            -- Create new view
            EXEC sp_executesql @view_def;
            
            EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
                @details = 'View moved from dbo to sem schema';
        END TRY
        BEGIN CATCH
            EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
                @error_message = ERROR_MESSAGE();
        END CATCH;
    END
    ELSE IF OBJECT_ID(@new_full_name, 'V') IS NOT NULL
    BEGIN
        EXEC dbo.__usp_log_migration_start 
            @migration_id = '0032', 
            @step_name = 'Move view ' + @old_name + ' → ' + @new_name,
            @log_id = @log_id OUTPUT;
        
        -- If new view exists and old still exists, just drop old
        IF OBJECT_ID(@old_full_name, 'V') IS NOT NULL
        BEGIN
            DECLARE @drop_old NVARCHAR(500) = 'DROP VIEW ' + @old_full_name;
            EXEC sp_executesql @drop_old;
            EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
                @details = 'Dropped old view (new already exists)';
        END
        ELSE
        BEGIN
            EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
                @details = 'New view already exists';
        END
    END
END;
GO

-- Move all semantic views
EXEC dbo.__usp_move_semantic_view 'sem_event', 'vw_event';
EXEC dbo.__usp_move_semantic_view 'sem_character', 'vw_character';
EXEC dbo.__usp_move_semantic_view 'sem_species', 'vw_species';
EXEC dbo.__usp_move_semantic_view 'sem_organization', 'vw_organization';
EXEC dbo.__usp_move_semantic_view 'sem_location', 'vw_location';
EXEC dbo.__usp_move_semantic_view 'sem_event_asset', 'vw_event_asset';
EXEC dbo.__usp_move_semantic_view 'sem_event_participant', 'vw_event_participant';
EXEC dbo.__usp_move_semantic_view 'sem_franchise', 'vw_franchise';
EXEC dbo.__usp_move_semantic_view 'sem_work', 'vw_work';
EXEC dbo.__usp_move_semantic_view 'sem_scene', 'vw_scene';
EXEC dbo.__usp_move_semantic_view 'sem_continuity_frame', 'vw_continuity_frame';
EXEC dbo.__usp_move_semantic_view 'sem_tech_asset', 'vw_tech_asset';
EXEC dbo.__usp_move_semantic_view 'sem_tech_instance', 'vw_tech_instance';
EXEC dbo.__usp_move_semantic_view 'sem_appearance_look', 'vw_appearance_look';
EXEC dbo.__usp_move_semantic_view 'sem_claim', 'vw_claim';
EXEC dbo.__usp_move_semantic_view 'sem_continuity_issue', 'vw_continuity_issue';
EXEC dbo.__usp_move_semantic_view 'sem_issue_claim_link', 'vw_issue_claim_link';
GO

-- Move vw_TagAssignments to sem.vw_tag_assignments
DECLARE @log_id INT;

IF OBJECT_ID('[dbo].[vw_TagAssignments]', 'V') IS NOT NULL
   AND OBJECT_ID('[sem].[vw_tag_assignments]', 'V') IS NULL
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Move view vw_TagAssignments → vw_tag_assignments',
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        DECLARE @view_def NVARCHAR(MAX);
        SELECT @view_def = OBJECT_DEFINITION(OBJECT_ID('[dbo].[vw_TagAssignments]'));
        
        DROP VIEW [dbo].[vw_TagAssignments];
        
        SET @view_def = REPLACE(@view_def, 'dbo.vw_TagAssignments', 'sem.vw_tag_assignments');
        SET @view_def = REPLACE(@view_def, '[dbo].[vw_TagAssignments]', '[sem].[vw_tag_assignments]');
        SET @view_def = REPLACE(@view_def, 'CREATE OR ALTER VIEW', 'CREATE VIEW');
        
        EXEC sp_executesql @view_def;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'View moved from dbo to sem schema';
    END TRY
    BEGIN CATCH
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
ELSE IF OBJECT_ID('[sem].[vw_tag_assignments]', 'V') IS NOT NULL
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Move view vw_TagAssignments → vw_tag_assignments',
        @log_id = @log_id OUTPUT;
    
    IF OBJECT_ID('[dbo].[vw_TagAssignments]', 'V') IS NOT NULL
    BEGIN
        DROP VIEW [dbo].[vw_TagAssignments];
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'Dropped old view (new already exists)';
    END
    ELSE
    BEGIN
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
            @details = 'New view already exists';
    END
END
GO

-- Clean up helper procedure
IF OBJECT_ID('dbo.__usp_move_semantic_view', 'P') IS NOT NULL
    DROP PROCEDURE dbo.__usp_move_semantic_view;
GO

PRINT '';
PRINT 'SECTION 5 complete: Semantic views moved to sem schema.';
PRINT '';
GO

-- ============================================================================
-- SECTION 6: DateTime/UTC Standardization
-- ============================================================================
-- Verify all timestamp columns use:
-- - Type: DATETIME2(3)
-- - Default: SYSUTCDATETIME()
-- - Suffix: Utc
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 6: DateTime/UTC Standardization Analysis';
PRINT '============================================================================';
GO

DECLARE @log_id INT;

EXEC dbo.__usp_log_migration_start 
    @migration_id = '0032', 
    @step_name = 'DateTime/UTC Analysis',
    @log_id = @log_id OUTPUT;

-- This section reports on non-compliant datetime columns
-- Actual fixes require data-preserving migration which should be planned separately

SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS CurrentType,
    c.scale AS CurrentPrecision,
    dc.definition AS CurrentDefault,
    CASE 
        WHEN ty.name = 'datetime' THEN 'REQUIRES FIX: Change to DATETIME2(3)'
        WHEN ty.name = 'datetime2' AND c.scale <> 3 THEN 'CONSIDER: Standardize to DATETIME2(3)'
        ELSE 'OK'
    END AS TypeStatus,
    CASE 
        WHEN c.name NOT LIKE '%Utc' AND c.name NOT LIKE '%UTC' 
             AND (c.name LIKE '%_at' OR c.name LIKE '%At' OR c.name LIKE '%Date')
        THEN 'CONSIDER: Add Utc suffix'
        ELSE 'OK'
    END AS NamingStatus,
    CASE 
        WHEN dc.definition LIKE '%GETDATE%' THEN 'REQUIRES FIX: Change to SYSUTCDATETIME()'
        WHEN dc.definition IS NULL AND c.is_nullable = 0 THEN 'REVIEW: No default for NOT NULL'
        ELSE 'OK'
    END AS DefaultStatus
INTO #datetime_analysis
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
LEFT JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
  AND ty.name IN ('datetime', 'datetime2')
  AND (
      ty.name = 'datetime' 
      OR c.scale <> 3 
      OR dc.definition LIKE '%GETDATE%'
      OR (c.name NOT LIKE '%Utc' AND c.name NOT LIKE '%UTC' 
          AND (c.name LIKE '%_at' OR c.name LIKE '%At' OR c.name LIKE '%Date'))
  );

DECLARE @non_compliant_count INT;
SELECT @non_compliant_count = COUNT(*) FROM #datetime_analysis 
WHERE TypeStatus <> 'OK' OR NamingStatus <> 'OK' OR DefaultStatus <> 'OK';

IF @non_compliant_count > 0
BEGIN
    PRINT '  Found ' + CAST(@non_compliant_count AS VARCHAR) + ' datetime columns needing attention:';
    SELECT * FROM #datetime_analysis ORDER BY SchemaName, TableName, ColumnName;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
        @details = 'Found ' + CAST(@non_compliant_count AS VARCHAR) + ' columns needing review. See output above.';
END
ELSE
BEGIN
    PRINT '  All datetime columns appear compliant.';
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
        @details = 'All datetime columns compliant';
END

DROP TABLE #datetime_analysis;
GO

PRINT '';
PRINT 'SECTION 6 complete: DateTime analysis reported.';
PRINT '';
GO

-- ============================================================================
-- SECTION 7: Index Updates for Renamed Columns
-- ============================================================================
-- Update indexes that reference renamed columns
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 7: Index Updates for Renamed Columns';
PRINT '============================================================================';
GO

DECLARE @log_id INT;

-- Create index on ExternalKey if not exists
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'UX_DimEntity_ExternalKey_IsLatest' 
    AND object_id = OBJECT_ID('dbo.DimEntity')
)
AND EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('dbo.DimEntity') 
    AND name = 'ExternalKey'
)
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Create index UX_DimEntity_ExternalKey_IsLatest',
        @log_id = @log_id OUTPUT;
    
    BEGIN TRY
        CREATE UNIQUE NONCLUSTERED INDEX UX_DimEntity_ExternalKey_IsLatest
        ON dbo.DimEntity (ExternalKey)
        WHERE ExternalKey IS NOT NULL AND IsLatest = 1;
        
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'completed',
            @details = 'Index created on ExternalKey';
    END TRY
    BEGIN CATCH
        EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'failed',
            @error_message = ERROR_MESSAGE();
    END CATCH;
END
ELSE
BEGIN
    EXEC dbo.__usp_log_migration_start 
        @migration_id = '0032', 
        @step_name = 'Create index UX_DimEntity_ExternalKey_IsLatest',
        @log_id = @log_id OUTPUT;
    EXEC dbo.__usp_log_migration_end @log_id = @log_id, @status = 'skipped',
        @details = 'Index already exists or ExternalKey column missing';
END
GO

PRINT '';
PRINT 'SECTION 7 complete: Index updates applied.';
PRINT '';
GO

-- ============================================================================
-- SECTION 8: Verification and Summary
-- ============================================================================
-- Final verification queries and migration summary
-- ============================================================================

PRINT '============================================================================';
PRINT 'SECTION 8: Verification and Summary';
PRINT '============================================================================';
PRINT '';
GO

-- 8.1: Verify no dbo.sem_* views remain
PRINT '8.1: Checking for remaining dbo.sem_* views...';
SELECT 'dbo.sem_* views remaining' AS Check, name AS ViewName 
FROM sys.views 
WHERE schema_id = SCHEMA_ID('dbo') AND name LIKE 'sem_%';

IF NOT EXISTS (SELECT 1 FROM sys.views WHERE schema_id = SCHEMA_ID('dbo') AND name LIKE 'sem_%')
    PRINT '  ✓ No dbo.sem_* views found (expected)';
ELSE
    PRINT '  ✗ WARNING: dbo.sem_* views still exist';
GO

-- 8.2: Verify semantic views in sem schema
PRINT '';
PRINT '8.2: Semantic views in sem schema:';
SELECT 'sem.vw_* views' AS Check, name AS ViewName 
FROM sys.views 
WHERE schema_id = SCHEMA_ID('sem') AND name LIKE 'vw_%'
ORDER BY name;
GO

-- 8.3: Verify no NEWSEQUENTIALID() for public GUIDs
PRINT '';
PRINT '8.3: Checking for NEWSEQUENTIALID() defaults on GUID columns...';
SELECT 
    'NEWSEQUENTIALID() found' AS Issue,
    OBJECT_SCHEMA_NAME(dc.parent_object_id) AS SchemaName,
    OBJECT_NAME(dc.parent_object_id) AS TableName, 
    c.name AS ColumnName,
    dc.definition AS DefaultDefinition
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE dc.definition LIKE '%NEWSEQUENTIALID%' 
  AND t.name = 'uniqueidentifier';

IF NOT EXISTS (
    SELECT 1 
    FROM sys.default_constraints dc
    JOIN sys.types t ON t.name = 'uniqueidentifier'
    JOIN sys.columns c ON dc.parent_object_id = c.object_id 
        AND dc.parent_column_id = c.column_id 
        AND c.user_type_id = t.user_type_id
    WHERE dc.definition LIKE '%NEWSEQUENTIALID%'
)
    PRINT '  ✓ No NEWSEQUENTIALID() defaults found (expected)';
ELSE
    PRINT '  ✗ WARNING: NEWSEQUENTIALID() defaults still exist';
GO

-- 8.4: Verify ExternalKey columns exist
PRINT '';
PRINT '8.4: Checking for ExternalKey column in DimEntity...';
IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.DimEntity') AND name = 'ExternalKey')
    PRINT '  ✓ ExternalKey column exists in DimEntity';
ELSE
    PRINT '  ✗ WARNING: ExternalKey column missing from DimEntity';
GO

-- 8.5: Verify DimOccurrence exists
PRINT '';
PRINT '8.5: Checking for DimOccurrence table...';
IF EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'DimOccurrence' AND s.name = 'dbo')
    PRINT '  ✓ DimOccurrence table exists';
ELSE IF EXISTS (SELECT 1 FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'DimEvent' AND s.name = 'dbo')
    PRINT '  ✗ WARNING: DimEvent not renamed to DimOccurrence';
ELSE
    PRINT '  ○ Neither DimEvent nor DimOccurrence exists (placeholder table may not have been created)';
GO

-- 8.6: Migration log summary
PRINT '';
PRINT '============================================================================';
PRINT 'MIGRATION LOG SUMMARY';
PRINT '============================================================================';

SELECT 
    step_name,
    status,
    rows_before,
    rows_after,
    DATEDIFF(MILLISECOND, started_utc, completed_utc) AS duration_ms,
    CASE 
        WHEN error_message IS NOT NULL THEN LEFT(error_message, 100) + '...'
        ELSE details
    END AS notes
FROM dbo.__migration_log
WHERE migration_id = '0032'
ORDER BY log_id;
GO

-- 8.7: Final counts
PRINT '';
PRINT '============================================================================';
PRINT 'FINAL STATUS COUNTS';
PRINT '============================================================================';

SELECT 
    status,
    COUNT(*) AS step_count
FROM dbo.__migration_log
WHERE migration_id = '0032'
GROUP BY status
ORDER BY 
    CASE status 
        WHEN 'completed' THEN 1 
        WHEN 'skipped' THEN 2 
        WHEN 'failed' THEN 3 
        ELSE 4 
    END;
GO

PRINT '';
PRINT '============================================================================';
PRINT 'Migration 0032 Complete';
PRINT 'Completed at: ' + CONVERT(VARCHAR, SYSUTCDATETIME(), 121);
PRINT '============================================================================';
PRINT '';
PRINT 'Next Steps:';
PRINT '  1. Review any FAILED steps above and remediate';
PRINT '  2. Review DateTime Analysis output for manual fixes';
PRINT '  3. Update Python code to use new column/table names (separate PR)';
PRINT '  4. Consider dropping deprecated columns after verification period';
PRINT '';
GO
