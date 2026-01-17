/******************************************************************************
 * MODULE 01: Character Directory & Profiles - ANSWER KEY
 * 
 * This file contains solutions for the character directory exercises.
 * Each solution includes explanatory comments and variation suggestions.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore the Character Table
-- ============================================================================
-- Preview the character table structure and data

SELECT TOP 10 *                   -- Start with TOP to avoid large result sets
FROM learn_characters
ORDER BY CharacterName;           -- Alphabetical order is a good default
-- Comment: Starting with SELECT * helps you learn the available columns.
--          Always use TOP when exploring new tables.

/* VARIATIONS:
   - Try: TOP 20 for more rows
   - Try: ORDER BY CharacterId DESC for different ordering
   - Try: SELECT CharacterName, Species, RoleArchetype for specific columns
*/


-- ============================================================================
-- EXERCISE 2: Find Characters by Species
-- ============================================================================
-- List all Human characters, sorted alphabetically

SELECT
    CharacterName,
    Species,
    Gender,
    RoleArchetype,
    Homeworld
FROM learn_characters
WHERE Species = 'Human'           -- Filter for humans only
ORDER BY CharacterName;           -- Alphabetical sorting
-- Comment: The WHERE clause filters rows before SELECT processes them.

/* VARIATIONS:
   - AND Gender = 'Female'         -- Add gender filter
   - AND RoleArchetype = 'Hero'    -- Only human heroes
   - ORDER BY Homeworld, CharacterName  -- Sort by homeworld first
*/


-- ============================================================================
-- EXERCISE 3: Character Archetypes
-- ============================================================================
-- Find all distinct role archetypes

SELECT DISTINCT RoleArchetype     -- DISTINCT eliminates duplicates
FROM learn_characters
WHERE RoleArchetype IS NOT NULL   -- Exclude nulls for cleaner results
ORDER BY RoleArchetype;
-- Comment: DISTINCT works on the entire selected row; here we only select one column.

/* VARIATIONS:
   - Remove WHERE clause to include NULL as a value
   - Add: SELECT DISTINCT Species for different exploration
   - Add: SELECT DISTINCT Gender for gender values
*/


-- ============================================================================
-- EXERCISE 4: Villains Only
-- ============================================================================
-- List villain characters with key details

SELECT
    CharacterName,
    Species,
    Homeworld
FROM learn_characters
WHERE RoleArchetype = 'Villain'   -- Exact match filter
ORDER BY CharacterName;
-- Comment: String comparisons are case-sensitive in SQL Server by default collation.

/* VARIATIONS:
   - WHERE RoleArchetype IN ('Villain', 'Mastermind')  -- Multiple archetypes
   - WHERE RoleArchetype LIKE '%Villain%'              -- Pattern match
   - Add: Gender, EyeColor for more details
*/


-- ============================================================================
-- EXERCISE 5: Characters from Tatooine
-- ============================================================================
-- Find characters with Tatooine as homeworld

SELECT
    CharacterName,
    Species,
    RoleArchetype,
    BirthYear
FROM learn_characters
WHERE Homeworld = 'Tatooine'      -- Exact match on homeworld
ORDER BY CharacterName;
-- Comment: Homeworld data comes from reference text; may have variations.

/* VARIATIONS:
   - WHERE Homeworld LIKE '%Tatooine%'    -- Catch variations like 'Tatooine desert'
   - WHERE BirthPlace = 'Tatooine'        -- Try birth place instead
   - WHERE Homeworld IN ('Tatooine', 'Alderaan')  -- Multiple planets
*/


-- ============================================================================
-- EXERCISE 6: Name Pattern Search
-- ============================================================================
-- Find characters with 'Skywalker' in their name

SELECT
    CharacterName,
    Species,
    RoleArchetype,
    Homeworld
FROM learn_characters
WHERE CharacterName LIKE '%Skywalker%'  -- % matches any characters
ORDER BY CharacterName;
-- Comment: LIKE with % wildcards is powerful for fuzzy matching.
--          %text% = contains, text% = starts with, %text = ends with

/* VARIATIONS:
   - WHERE CharacterName LIKE 'Luke%'     -- Starts with 'Luke'
   - WHERE CharacterName LIKE '%Solo%'    -- Try: Solo
   - WHERE CharacterName LIKE '%Obi%'     -- Try: Obi-Wan variations
   - WHERE CharacterName LIKE '____ Skywalker'  -- _ matches single character
*/


-- ============================================================================
-- EXERCISE 7: Top 5 by Eye Color
-- ============================================================================
-- First 5 characters with blue eyes

SELECT TOP 5
    CharacterName,
    EyeColor,
    Species,
    RoleArchetype
FROM learn_characters
WHERE EyeColor LIKE '%Blue%'      -- Catches 'Blue', 'Blue-Gray', etc.
ORDER BY CharacterName;
-- Comment: Using LIKE '%Blue%' handles variations in how colors are recorded.

/* VARIATIONS:
   - WHERE EyeColor = 'Blue'              -- Exact match only
   - WHERE EyeColor IN ('Blue', 'Blue-Gray')  -- Explicit list
   - TOP 10 for more results
   - WHERE EyeColor = 'Yellow'            -- Try: Sith eyes
*/


-- ============================================================================
-- EXERCISE 8: Multiple Conditions
-- ============================================================================
-- Female characters who are not Human

SELECT
    CharacterName,
    Species,
    Gender,
    RoleArchetype
FROM learn_characters
WHERE Gender = 'Female'
  AND Species <> 'Human'          -- Not equal to Human
  AND Species IS NOT NULL         -- Exclude unknown species
ORDER BY Species, CharacterName;
-- Comment: AND combines conditions; all must be true.
--          IS NOT NULL is needed because <> doesn't match NULL values.

/* VARIATIONS:
   - Remove: AND Species IS NOT NULL       -- Include unknowns
   - OR Gender = 'Non-binary'              -- Add more genders
   - AND RoleArchetype = 'Leader'          -- Narrow to leaders
*/


-- ============================================================================
-- EXERCISE 9: Canonical Characters Only
-- ============================================================================
-- Canonical characters with known birth years

SELECT
    CharacterName,
    BirthYear,
    Species,
    Homeworld
FROM learn_characters
WHERE IsCanonical = 1             -- 1 = true in bit columns
  AND BirthYear IS NOT NULL       -- Has birth year data
ORDER BY BirthYear, CharacterName;
-- Comment: IsCanonical helps filter to official/confirmed characters.
--          BirthYear is text like '19 BBY' so ORDER BY is alphabetical.

/* VARIATIONS:
   - WHERE IsCanonical = 0                 -- Non-canonical only
   - AND BirthYear LIKE '%BBY%'            -- Before Battle of Yavin only
   - AND BirthYear LIKE '%ABY%'            -- After Battle of Yavin only
*/


-- ============================================================================
-- EXERCISE 10: Character Summary Report
-- ============================================================================
-- Formatted list with null handling

SELECT TOP 10
    CharacterName,
    COALESCE(Species, 'Unknown') AS Species,        -- Replace NULL with 'Unknown'
    COALESCE(Homeworld, 'Unknown') AS Homeworld,
    COALESCE(RoleArchetype, 'Unclassified') AS Archetype
FROM learn_characters
ORDER BY CharacterName;
-- Comment: COALESCE returns the first non-null value from the list.
--          ISNULL(Species, 'Unknown') is an alternative SQL Server function.

/* VARIATIONS:
   - Use ISNULL instead of COALESCE: ISNULL(Species, 'Unknown')
   - Add: CONCAT(CharacterName, ' (', Species, ')') AS FullDescription
   - Add: CASE WHEN Species IS NULL THEN 'Unknown' ELSE Species END AS Species
   - TOP 20 for more results
*/
