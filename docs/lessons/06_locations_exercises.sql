/******************************************************************************
 * MODULE 06: Location Hierarchy Explorer
 * 
 * OBJECTIVE: Navigate the location hierarchy (galaxy → region → system → planet → site).
 * 
 * SKILLS PRACTICED:
 *   - Hierarchical data patterns
 *   - Self-referencing relationships
 *   - NULL handling for root nodes
 *   - Geographic filtering
 * 
 * TABLES USED: learn_locations
 * 
 * DIFFICULTY: Intermediate
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Locations
-- ============================================================================
-- GOAL: Preview the locations table to understand the hierarchy.
-- 
-- HINTS:
--   - Look at LocationType and ParentLocation columns
--   - Notice how locations relate to each other
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Location Types
-- ============================================================================
-- GOAL: Find all distinct location types and count locations of each type.
-- 
-- HINTS:
--   - GROUP BY LocationType
--   - Types include Galaxy, Region, System, Planet, Site
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Top-Level Locations
-- ============================================================================
-- GOAL: Find all locations that have no parent (top of hierarchy).
-- 
-- HINTS:
--   - ParentLocation IS NULL indicates root nodes
--   - These are typically galaxies or major regions
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Planets Only
-- ============================================================================
-- GOAL: List all Planet-type locations with their parent (system or region).
-- 
-- HINTS:
--   - Filter on LocationType = 'Planet'
--   - Show LocationName and ParentLocation
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Sites on Tatooine
-- ============================================================================
-- GOAL: Find all Site-type locations whose parent is Tatooine.
-- 
-- HINTS:
--   - LocationType = 'Site' AND ParentLocation = 'Tatooine'
--   - These are specific places on the planet
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Locations with Climate
-- ============================================================================
-- GOAL: List all locations that have climate information.
--       Show location name, type, and climate.
-- 
-- HINTS:
--   - Filter on Climate IS NOT NULL
--   - Order by LocationType
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Desert Worlds
-- ============================================================================
-- GOAL: Find all locations with 'desert' in their terrain description.
-- 
-- HINTS:
--   - Use LIKE on the Terrain column
--   - Case may vary, so consider LOWER()
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Hierarchy Depth
-- ============================================================================
-- GOAL: For each location type, count how many have parents vs. don't.
-- 
-- HINTS:
--   - GROUP BY LocationType
--   - Use CASE to count with/without parent
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Populated Locations
-- ============================================================================
-- GOAL: Find locations with population data.
--       Show location, type, and population reference.
-- 
-- HINTS:
--   - Filter on Population IS NOT NULL
--   - Population is stored as text reference
-- 
-- TABLES: learn_locations

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Location Summary Report
-- ============================================================================
-- GOAL: Create a summary showing:
--       - Each parent location
--       - Count of child locations
--       - Types of children
-- 
-- HINTS:
--   - GROUP BY ParentLocation
--   - COUNT(*) for children
--   - This shows the structure of the hierarchy
-- 
-- TABLES: learn_locations

-- Write your query below:



