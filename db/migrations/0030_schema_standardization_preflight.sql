-- Migration 0030: Schema Standardization Pre-Flight Checks
-- Purpose: Row count inventory and schema analysis before standardization migration
--
-- Run this script BEFORE executing the standardization migration to:
-- 1. Identify tables that are safe to drop/recreate (0 rows)
-- 2. Identify tables that require data-preserving migration (rows > 0)
--
-- Output: Row counts for all base tables by schema/table
-- ============================================================================

-- ============================================================================
-- SECTION 1: Row Count Inventory
-- ============================================================================
-- This query returns row counts for all tables to determine migration strategy
-- Tables with 0 rows: safe to drop and recreate
-- Tables with rows > 0: require data-preserving migration
-- ============================================================================

SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    SUM(p.rows) AS RowCount,
    CASE 
        WHEN SUM(p.rows) = 0 THEN 'Safe to drop/recreate'
        ELSE 'Requires data-preserving migration'
    END AS MigrationStrategy
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
GROUP BY s.name, t.name
ORDER BY s.name, t.name;
GO

-- ============================================================================
-- SECTION 2: Column Inventory - Identify ...Id Columns Needing Rename
-- ============================================================================
-- Lists all columns ending in 'Id' that should be renamed according to standards:
-- - Internal surrogate keys: ...Key (INT or BIGINT)
-- - Public/stable identifiers: ...Guid (UNIQUEIDENTIFIER)
-- - External/source system IDs: ...ExtKey or ...NaturalKey
-- ============================================================================

SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable,
    CASE 
        WHEN c.name LIKE '%Id' AND ty.name = 'uniqueidentifier' THEN 'Rename to ...Guid'
        WHEN c.name LIKE '%Id' AND ty.name IN ('int', 'bigint') AND c.name NOT LIKE '%ExtKey' THEN 'Rename to ...Key or ...ExtKey'
        WHEN c.name LIKE '%Id' AND ty.name IN ('nvarchar', 'varchar') THEN 'Rename to ...NaturalKey or ...ExtKey'
        ELSE 'Review required'
    END AS RecommendedAction
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
  AND c.name LIKE '%Id'
  AND c.name NOT LIKE '%Guid'
  AND c.name NOT LIKE '%Key'
ORDER BY s.name, t.name, c.name;
GO

-- ============================================================================
-- SECTION 3: GUID Default Analysis
-- ============================================================================
-- Identifies GUID columns using NEWSEQUENTIALID() that should use NEWID()
-- NEWSEQUENTIALID() reveals row creation order - security concern for public IDs
-- ============================================================================

SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    dc.definition AS DefaultDefinition,
    CASE 
        WHEN dc.definition LIKE '%NEWSEQUENTIALID%' THEN 'CHANGE to NEWID() - security concern'
        WHEN dc.definition LIKE '%NEWID%' THEN 'OK - random GUID'
        ELSE 'Review required'
    END AS RecommendedAction
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
LEFT JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
  AND ty.name = 'uniqueidentifier'
  AND dc.definition IS NOT NULL
ORDER BY s.name, t.name, c.name;
GO

-- ============================================================================
-- SECTION 4: DateTime Column Analysis
-- ============================================================================
-- Identifies datetime columns that should be standardized:
-- - DATETIME should become DATETIME2(3)
-- - Should use SYSUTCDATETIME() for UTC timestamps
-- - Should end with 'Utc' suffix
-- ============================================================================

SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.scale AS Precision,
    dc.definition AS DefaultDefinition,
    CASE 
        WHEN ty.name = 'datetime' THEN 'CHANGE to DATETIME2(3)'
        WHEN ty.name = 'datetime2' AND c.scale <> 3 THEN 'Consider DATETIME2(3) precision'
        ELSE 'OK'
    END AS TypeAction,
    CASE 
        WHEN c.name NOT LIKE '%Utc' AND c.name NOT LIKE '%UTC' AND c.name LIKE '%At%' THEN 'RENAME to include Utc suffix'
        WHEN c.name NOT LIKE '%Utc' AND c.name NOT LIKE '%UTC' AND c.name LIKE '%Date%' THEN 'RENAME to include Utc suffix'
        ELSE 'OK'
    END AS NamingAction
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
LEFT JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id
WHERE s.name IN ('dbo', 'ingest', 'llm', 'vector', 'sem')
  AND ty.name IN ('datetime', 'datetime2')
ORDER BY s.name, t.name, c.name;
GO

-- ============================================================================
-- SECTION 5: View Inventory - dbo.sem_* Views to Move
-- ============================================================================
-- Lists views in dbo schema with sem_ prefix that should move to sem schema
-- ============================================================================

SELECT 
    s.name AS CurrentSchema,
    v.name AS ViewName,
    'sem' AS TargetSchema,
    REPLACE(v.name, 'sem_', 'vw_') AS NewViewName,
    'DROP and recreate in sem schema' AS RequiredAction
FROM sys.views v
INNER JOIN sys.schemas s ON v.schema_id = s.schema_id
WHERE s.name = 'dbo'
  AND v.name LIKE 'sem_%'
ORDER BY v.name;
GO

-- ============================================================================
-- SECTION 6: DimEvent Collision Check
-- ============================================================================
-- Check for DimEvent table that needs rename to DimOccurrence
-- ============================================================================

SELECT 
    s.name AS SchemaName,
    t.name AS TableName,
    'DimOccurrence' AS RecommendedNewName,
    'Rename to avoid collision with FactEvent semantic meaning' AS Reason
FROM sys.tables t
INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE t.name = 'DimEvent'
ORDER BY s.name;
GO

-- ============================================================================
-- End of Pre-Flight Script
-- ============================================================================
PRINT 'Pre-flight analysis complete. Review results above before running migration.'
PRINT 'Tables with row count > 0 require data-preserving migration pattern.'
PRINT 'See db/migrations/README.md for migration strategy documentation.'
GO
