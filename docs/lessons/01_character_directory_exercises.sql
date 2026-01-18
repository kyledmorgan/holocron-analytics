/******************************************************************************
 * MODULE 01: Character Directory & Profiles
 * 
 * OBJECTIVE: Learn to browse and filter character data using basic SQL.
 * 
 * SKILLS PRACTICED:
 *   - SELECT specific columns
 *   - WHERE clause filtering
 *   - ORDER BY for sorting
 *   - TOP for limiting results
 *   - DISTINCT for unique values
 *   - LIKE for pattern matching
 * 
 * TABLES USED: learn_characters
 * 
 * DIFFICULTY: Beginner (no joins required)
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore the Character Table
-- ============================================================================
-- GOAL: Preview what data is available in the character table.
-- 
-- HINTS:
--   - Use SELECT * to see all columns
--   - Use TOP to limit rows returned
--   - Look at the column names to understand what's available
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Find Characters by Species
-- ============================================================================
-- GOAL: List all Human characters, sorted alphabetically by name.
-- 
-- HINTS:
--   - Filter on the Species column
--   - Use ORDER BY to sort
--   - Think about which columns to include in output
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Character Archetypes
-- ============================================================================
-- GOAL: Find all distinct role archetypes (Hero, Villain, etc.) in the data.
-- 
-- HINTS:
--   - Use DISTINCT to get unique values
--   - You only need one column
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Villains Only
-- ============================================================================
-- GOAL: List all characters with the 'Villain' archetype.
--       Show their name, species, and homeworld.
-- 
-- HINTS:
--   - Filter on RoleArchetype
--   - Select specific columns (not *)
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Characters from Tatooine
-- ============================================================================
-- GOAL: Find all characters whose homeworld is Tatooine.
--       Order by name.
-- 
-- HINTS:
--   - Filter on the Homeworld column
--   - Remember: column values are case-sensitive in some databases
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Name Pattern Search
-- ============================================================================
-- GOAL: Find all characters whose name contains 'Skywalker'.
-- 
-- HINTS:
--   - Use LIKE with wildcard characters (%)
--   - Pattern: '%Skywalker%' matches anywhere in the string
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Top 5 by Eye Color
-- ============================================================================
-- GOAL: List the first 5 characters with blue eyes, ordered by name.
-- 
-- HINTS:
--   - Combine TOP, WHERE, and ORDER BY
--   - Eye color might have variations (Blue, Blue-Gray, etc.)
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Multiple Conditions
-- ============================================================================
-- GOAL: Find all female characters who are not Human.
--       Show name, species, gender, and archetype.
-- 
-- HINTS:
--   - Use AND to combine conditions
--   - Use <> or != for "not equal"
--   - Handle NULL species values (some characters have unknown species)
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Canonical Characters Only
-- ============================================================================
-- GOAL: List all canonical characters (IsCanonical = 1) who have a known
--       birth year, ordered by birth year.
-- 
-- HINTS:
--   - Filter on IsCanonical column (1 = true, 0 = false)
--   - Use IS NOT NULL to check for non-null values
--   - BirthYear is stored as text (e.g., '19 BBY')
-- 
-- TABLES: learn_characters

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Character Summary Report
-- ============================================================================
-- GOAL: Create a formatted list of the top 10 characters showing:
--       Name, Species (or 'Unknown' if null), Homeworld, and Archetype
--       Ordered by name.
-- 
-- HINTS:
--   - Use COALESCE or ISNULL to handle nulls
--   - Example: COALESCE(Species, 'Unknown') AS Species
--   - Think about readable column aliases
-- 
-- TABLES: learn_characters

-- Write your query below:



