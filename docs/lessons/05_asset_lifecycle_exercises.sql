/******************************************************************************
 * MODULE 05: Asset Lifecycle
 * 
 * OBJECTIVE: Track technology assets (ships, droids, weapons) through events.
 * 
 * SKILLS PRACTICED:
 *   - Filtering on asset types
 *   - Tracking status changes
 *   - Lifecycle patterns (used, damaged, destroyed)
 *   - JOIN patterns (optional)
 * 
 * TABLES USED: learn_assets, learn_events, learn_event_participants
 * 
 * DIFFICULTY: Intermediate
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Assets
-- ============================================================================
-- GOAL: Preview the assets table to understand available data.
-- 
-- HINTS:
--   - Look at AssetType, ModelName, Status columns
--   - Assets include ships, droids, weapons
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Asset Types
-- ============================================================================
-- GOAL: Find all distinct asset types and count assets of each type.
-- 
-- HINTS:
--   - GROUP BY AssetType
--   - COUNT(*) for count
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Ships Only
-- ============================================================================
-- GOAL: List all Ship assets with their model names and status.
-- 
-- HINTS:
--   - Filter on AssetType = 'Ship'
--   - Show AssetName, ModelName, Status
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Droids by Model
-- ============================================================================
-- GOAL: Find all Droid assets, grouped by model.
--       Count how many instances of each model exist.
-- 
-- HINTS:
--   - Filter on AssetType = 'Droid'
--   - GROUP BY ModelName
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Assets by Status
-- ============================================================================
-- GOAL: Count assets by their current status.
--       How many are Operational vs Destroyed?
-- 
-- HINTS:
--   - GROUP BY Status
--   - Handle NULL status values
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Named Ships
-- ============================================================================
-- GOAL: Find ships that have unique names (not just model designations).
--       Examples: Millennium Falcon, Tantive IV
-- 
-- HINTS:
--   - Filter on AssetType = 'Ship'
--   - AssetName is the unique instance name
--   - Look for interesting names
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Manufacturer Analysis
-- ============================================================================
-- GOAL: Count assets by manufacturer.
--       Which manufacturers have the most assets?
-- 
-- HINTS:
--   - GROUP BY Manufacturer
--   - Handle NULL manufacturers
--   - Order by count DESC
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Weapons Inventory
-- ============================================================================
-- GOAL: List all Weapon assets with their details.
--       Include name, model, and status.
-- 
-- HINTS:
--   - Filter on AssetType = 'Weapon'
--   - Order by ModelName
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Destroyed Assets
-- ============================================================================
-- GOAL: Find all assets with Status = 'Destroyed'.
--       Show asset name, type, model, and last known location.
-- 
-- HINTS:
--   - Filter on Status
--   - LastKnownLocation shows where it was destroyed
-- 
-- TABLES: learn_assets

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Asset Summary Report
-- ============================================================================
-- GOAL: Create a summary showing:
--       - Asset type
--       - Total count
--       - Count of operational assets
--       - Count of destroyed assets
-- 
-- HINTS:
--   - GROUP BY AssetType
--   - Use CASE expressions inside COUNT or SUM
--   - SUM(CASE WHEN Status = 'Operational' THEN 1 ELSE 0 END)
-- 
-- TABLES: learn_assets

-- Write your query below:



