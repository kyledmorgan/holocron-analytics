# SQL Style Guide

This document defines the SQL coding style for holocron-analytics. All agents and contributors must follow these guidelines when writing SQL DDL, queries, views, and stored procedures.

---

## 1. General Formatting

### 1.1 Keywords

- Use UPPERCASE for SQL keywords
- Use PascalCase for column names, table names, and constraint names
- Use lowercase for schema names

```sql
-- CORRECT
SELECT EntityKey, EntityGuid, DisplayName
FROM dbo.DimEntity
WHERE IsActive = 1 AND IsLatest = 1;

-- WRONG
select entityKey, entityGuid, displayName
from DBO.dimEntity
where isActive = 1;
```

### 1.2 Indentation

- Use 4 spaces for indentation (not tabs)
- Align major clauses (SELECT, FROM, WHERE, etc.) at the same level
- Indent continuation lines within clauses

```sql
SELECT
    e.EntityKey,
    e.EntityGuid,
    e.DisplayName,
    f.FranchiseName
FROM dbo.DimEntity e
INNER JOIN dbo.DimFranchise f
    ON e.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
WHERE e.IsActive = 1
  AND e.IsLatest = 1
ORDER BY e.DisplayName;
```

### 1.3 Line Length

- Keep lines under 120 characters
- Break long expressions across multiple lines
- Align operators and commas for readability

---

## 2. SELECT Statements

### 2.1 Column Lists

- List columns vertically for readability
- Put commas at the end of lines (not beginning)
- Include aliases for calculated columns

```sql
-- CORRECT
SELECT
    EntityKey,
    EntityGuid,
    DisplayName,
    UPPER(DisplayName) AS DisplayNameUpper,
    COUNT(*) AS RecordCount
FROM dbo.DimEntity
GROUP BY EntityKey, EntityGuid, DisplayName;

-- WRONG (comma-first style)
SELECT
    EntityKey
   ,EntityGuid
   ,DisplayName
FROM dbo.DimEntity;
```

### 2.2 Table Aliases

- Use short, meaningful aliases (1-3 characters)
- Be consistent with alias naming across queries
- Always use aliases when joining multiple tables

```sql
-- Standard aliases
FROM dbo.DimEntity e          -- e for Entity
INNER JOIN dbo.DimFranchise f -- f for Franchise
INNER JOIN dbo.FactEvent fe   -- fe for FactEvent
INNER JOIN sem.SourcePage sp  -- sp for SourcePage
```

---

## 3. JOIN Syntax

### 3.1 Explicit JOINs

- Always use explicit JOIN syntax (never comma-style)
- Put join conditions on separate lines
- Use AND alignment for multiple join conditions

```sql
-- CORRECT
FROM dbo.DimEntity e
INNER JOIN dbo.DimFranchise f
    ON e.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
LEFT OUTER JOIN dbo.DimSpecies sp
    ON e.SpeciesKey = sp.SpeciesKey

-- WRONG (comma-style join)
FROM dbo.DimEntity e, dbo.DimFranchise f
WHERE e.FranchiseKey = f.FranchiseKey
```

### 3.2 Join Type Preferences

| Preferred | Alternative | Notes |
|-----------|-------------|-------|
| `INNER JOIN` | `JOIN` | Be explicit |
| `LEFT OUTER JOIN` | `LEFT JOIN` | Be explicit |
| `CROSS APPLY` | (subquery) | For lateral joins |

---

## 4. WHERE Clauses

### 4.1 Condition Formatting

- Start each condition on a new line
- Align AND/OR operators
- Use parentheses for clarity with complex conditions

```sql
WHERE e.IsActive = 1
  AND e.IsLatest = 1
  AND (
      e.EntityType = 'Character'
      OR e.EntityType = 'Organization'
  )
  AND e.CreatedUtc >= '2026-01-01';
```

### 4.2 Standard Filters

Always include these filters for dimensional tables:

```sql
WHERE t.IsActive = 1
  AND t.IsLatest = 1
```

---

## 5. DDL Statements

### 5.1 CREATE TABLE Structure

Order columns consistently:

1. **Keys** (primary key, GUIDs, foreign keys)
2. **Business columns** (domain data)
3. **Audit columns** (governance, tracking)
4. **Constraints** (at the end)

```sql
CREATE TABLE dbo.DimEntity (
    -- Keys
    EntityKey INT IDENTITY(1,1) NOT NULL,
    EntityGuid UNIQUEIDENTIFIER NOT NULL 
        CONSTRAINT DF_DimEntity_EntityGuid DEFAULT (NEWID()),
    FranchiseKey INT NOT NULL,
    
    -- Business columns
    DisplayName NVARCHAR(200) NOT NULL,
    EntityType NVARCHAR(50) NOT NULL,
    
    -- Audit columns
    IsActive BIT NOT NULL CONSTRAINT DF_DimEntity_IsActive DEFAULT (1),
    CreatedUtc DATETIME2(3) NOT NULL 
        CONSTRAINT DF_DimEntity_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    
    -- Constraints
    CONSTRAINT PK_DimEntity PRIMARY KEY CLUSTERED (EntityKey),
    CONSTRAINT FK_DimEntity_Franchise 
        FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);
```

### 5.2 Data Types

| Use | Don't Use | Notes |
|-----|-----------|-------|
| `INT` | `INTEGER` | Shorter, standard |
| `BIGINT` | `BIGINTEGER` | For high-cardinality facts |
| `NVARCHAR(n)` | `VARCHAR(n)` | Unicode support |
| `DATETIME2(3)` | `DATETIME` | Better precision |
| `UNIQUEIDENTIFIER` | `CHAR(36)` | Native GUID |
| `BIT` | `TINYINT` | For booleans |
| `DECIMAL(p,s)` | `FLOAT` | Exact numeric |

### 5.3 Constraint Syntax

Put long constraints on multiple lines:

```sql
CONSTRAINT DF_DimEntity_EntityGuid DEFAULT (NEWID()),
CONSTRAINT FK_DimEntity_Franchise 
    FOREIGN KEY (FranchiseKey) 
    REFERENCES dbo.DimFranchise(FranchiseKey),
```

---

## 6. Views

### 6.1 View Header Comment

Always include a header comment:

```sql
/*******************************************************************************
 * VIEW: sem.vw_entity
 * 
 * PURPOSE: Flattened entity view with franchise context.
 *
 * AUDIENCE: Analysts, downstream marts.
 *
 * KEY COLUMNS:
 *   - EntityGuid: Stable public identifier
 *   - DisplayName: Entity name for display
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW sem.vw_entity
AS
SELECT ...
```

### 6.2 View Body

- Use meaningful column aliases
- Filter to active/latest records
- Include necessary joins for denormalization

---

## 7. Stored Procedures

### 7.1 Procedure Header

```sql
/*******************************************************************************
 * PROCEDURE: llm.usp_claim_next_job
 * 
 * PURPOSE: Atomically claim the next available job from the queue.
 *
 * PARAMETERS:
 *   @worker_id NVARCHAR(100) - Worker claiming the job
 *
 * RETURNS: Claimed job details or empty result set
 *
 * USAGE: EXEC llm.usp_claim_next_job @worker_id = 'worker-1'
 ******************************************************************************/
```

### 7.2 Parameter Naming

- Use `@snake_case` for parameters
- Prefix output parameters with `@out_`
- Match column names where applicable

```sql
CREATE PROCEDURE llm.usp_claim_next_job
    @worker_id NVARCHAR(100),
    @out_job_id UNIQUEIDENTIFIER OUTPUT
AS
BEGIN
    ...
END;
```

---

## 8. Comments

### 8.1 Block Comments

Use for headers and section dividers:

```sql
/*******************************************************************************
 * SECTION: Entity Lookups
 ******************************************************************************/
```

### 8.2 Inline Comments

Use `--` for single-line comments:

```sql
-- Filter to active records only
WHERE IsActive = 1
  AND IsLatest = 1  -- SCD Type 2 pattern
```

---

## 9. Security Considerations

### 9.1 Parameterization

Always use parameterized queries:

```sql
-- CORRECT
EXEC sp_executesql N'SELECT * FROM dbo.DimEntity WHERE EntityKey = @key', 
    N'@key INT', @key = @input_key;

-- WRONG (SQL injection risk)
SET @sql = 'SELECT * FROM dbo.DimEntity WHERE EntityKey = ' + CAST(@input_key AS VARCHAR);
EXEC(@sql);
```

### 9.2 Dynamic SQL

If dynamic SQL is required:

1. Validate all inputs
2. Use `QUOTENAME()` for identifiers
3. Use parameters for values
4. Document why dynamic SQL is needed

---

## 10. Performance Guidelines

### 10.1 Index Hints

- Avoid index hints unless absolutely necessary
- Document why hint is needed if used
- Review hints during schema changes

### 10.2 Common Patterns

```sql
-- Use EXISTS instead of IN for subqueries
WHERE EXISTS (SELECT 1 FROM dbo.Related r WHERE r.ParentKey = t.Key)

-- Use OPTION (RECOMPILE) for parameter-sensitive queries
SELECT ... WHERE Col = @param OPTION (RECOMPILE);

-- Use NOLOCK only when explicitly acceptable (read uncommitted)
SELECT ... FROM dbo.Table WITH (NOLOCK)  -- CAUTION: dirty reads
```

---

## Quick Reference

```
FORMATTING:
  - UPPERCASE keywords
  - PascalCase names
  - 4-space indentation
  - Commas at end of lines
  
JOINS:
  - Explicit INNER/LEFT OUTER JOIN
  - Conditions on separate lines
  - Align AND operators

DDL ORDER:
  1. Keys
  2. Business columns
  3. Audit columns
  4. Constraints
  
STANDARD TYPES:
  - INT / BIGINT for keys
  - UNIQUEIDENTIFIER for GUIDs
  - NVARCHAR(n) for text
  - DATETIME2(3) for timestamps
  - DECIMAL(p,s) for numbers
```
