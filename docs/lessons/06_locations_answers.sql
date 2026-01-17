/******************************************************************************
 * MODULE 06: Location Hierarchy Explorer - ANSWER KEY
 * 
 * This file contains solutions for the location hierarchy exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Locations
-- ============================================================================

SELECT TOP 20 *
FROM learn_locations
ORDER BY LocationType, LocationName;
-- Comment: Locations form a hierarchy: Galaxy → Region → System → Planet → Site
--          ParentLocation shows the containing location.

/* VARIATIONS:
   - ORDER BY ParentLocation, LocationName  -- Group by parent
   - WHERE LocationType = 'Planet'          -- Planets only
*/


-- ============================================================================
-- EXERCISE 2: Location Types
-- ============================================================================

SELECT
    LocationType,
    COUNT(*) AS LocationCount
FROM learn_locations
GROUP BY LocationType
ORDER BY 
    CASE LocationType                        -- Custom hierarchy order
        WHEN 'Galaxy' THEN 1
        WHEN 'Region' THEN 2
        WHEN 'System' THEN 3
        WHEN 'Planet' THEN 4
        WHEN 'Site' THEN 5
        ELSE 6
    END;
-- Comment: Location types form levels in the hierarchy.
--          Sites are most specific; galaxies are most general.

/* VARIATIONS:
   - ORDER BY LocationCount DESC            -- By frequency instead
   - WHERE Franchise = 'Star Wars'          -- Specific franchise
*/


-- ============================================================================
-- EXERCISE 3: Top-Level Locations
-- ============================================================================

SELECT
    LocationName,
    LocationType,
    Description
FROM learn_locations
WHERE ParentLocation IS NULL                 -- No parent = root node
ORDER BY LocationType, LocationName;
-- Comment: Root nodes are the top of the hierarchy.
--          Usually galaxies or major unnamed regions.

/* VARIATIONS:
   - AND LocationType = 'Galaxy'            -- Galaxies only
   - AND LocationType = 'Region'            -- Root regions
*/


-- ============================================================================
-- EXERCISE 4: Planets Only
-- ============================================================================

SELECT
    LocationName,
    ParentLocation,
    Climate,
    Terrain,
    Population
FROM learn_locations
WHERE LocationType = 'Planet'
ORDER BY LocationName;
-- Comment: Planets are key locations with environmental data.
--          ParentLocation shows the system or region containing the planet.

/* VARIATIONS:
   - AND Climate IS NOT NULL               -- Planets with known climate
   - AND ParentLocation LIKE '%Outer%'     -- Outer Rim planets
   - ORDER BY ParentLocation, LocationName -- Group by parent
*/


-- ============================================================================
-- EXERCISE 5: Sites on Tatooine
-- ============================================================================

SELECT
    LocationName,
    LocationType,
    Description
FROM learn_locations
WHERE LocationType = 'Site'
  AND ParentLocation = 'Tatooine'
ORDER BY LocationName;
-- Comment: Sites are specific places like cities, buildings, or landmarks.
--          Tatooine has many iconic sites: Mos Eisley, Lars Homestead, etc.

/* VARIATIONS:
   - WHERE ParentLocation = 'Coruscant'    -- Coruscant sites
   - WHERE ParentLocation = 'Naboo'        -- Naboo sites
   - WHERE ParentLocation LIKE '%Death%'   -- Death Star locations
*/


-- ============================================================================
-- EXERCISE 6: Locations with Climate
-- ============================================================================

SELECT
    LocationName,
    LocationType,
    Climate,
    Terrain
FROM learn_locations
WHERE Climate IS NOT NULL
ORDER BY LocationType, LocationName;
-- Comment: Climate data is typically available for planets and moons.

/* VARIATIONS:
   - AND LocationType = 'Planet'           -- Planets only
   - AND Climate LIKE '%hot%'              -- Hot climates
   - AND Climate LIKE '%cold%'             -- Cold climates
*/


-- ============================================================================
-- EXERCISE 7: Desert Worlds
-- ============================================================================

SELECT
    LocationName,
    LocationType,
    Terrain,
    Climate
FROM learn_locations
WHERE LOWER(Terrain) LIKE '%desert%'        -- Case-insensitive search
ORDER BY LocationName;
-- Comment: Desert worlds are common in Star Wars (Tatooine, Jakku).
--          LOWER() ensures case-insensitive matching.

/* VARIATIONS:
   - WHERE Terrain LIKE '%forest%'         -- Forest worlds
   - WHERE Terrain LIKE '%ice%'            -- Ice worlds (Hoth)
   - WHERE Terrain LIKE '%ocean%'          -- Ocean worlds
   - WHERE Terrain LIKE '%city%'           -- Urban worlds (Coruscant)
*/


-- ============================================================================
-- EXERCISE 8: Hierarchy Depth
-- ============================================================================

SELECT
    LocationType,
    SUM(CASE WHEN ParentLocation IS NULL THEN 1 ELSE 0 END) AS RootNodes,
    SUM(CASE WHEN ParentLocation IS NOT NULL THEN 1 ELSE 0 END) AS ChildNodes,
    COUNT(*) AS TotalCount
FROM learn_locations
GROUP BY LocationType
ORDER BY TotalCount DESC;
-- Comment: Shows how many locations of each type are roots vs. children.
--          Galaxies should mostly be roots; Sites should all be children.

/* VARIATIONS:
   - Add: SUM(CASE WHEN ParentLocationType = 'Planet' THEN 1 ELSE 0 END) AS PlanetChildren
   - GROUP BY LocationType, ParentLocationType  -- More detail
*/


-- ============================================================================
-- EXERCISE 9: Populated Locations
-- ============================================================================

SELECT
    LocationName,
    LocationType,
    Population,
    Government
FROM learn_locations
WHERE Population IS NOT NULL
ORDER BY LocationType, LocationName;
-- Comment: Population data is usually available for major planets and sites.
--          Population is stored as text reference (may not be numeric).

/* VARIATIONS:
   - AND LocationType = 'Planet'           -- Planet populations only
   - AND Government IS NOT NULL            -- With known government
   - ORDER BY Population                   -- Alphabetical by pop text
*/


-- ============================================================================
-- EXERCISE 10: Location Summary Report
-- ============================================================================

-- NOTE: STRING_AGG requires SQL Server 2017 or later.
--       See alternative query below for older SQL Server versions.

SELECT
    COALESCE(ParentLocation, '(No Parent)') AS Parent,
    COUNT(*) AS ChildCount,
    STRING_AGG(LocationName, ', ')          -- List children (SQL Server 2017+)
        WITHIN GROUP (ORDER BY LocationName) AS Children
FROM learn_locations
WHERE ParentLocation IS NOT NULL
GROUP BY ParentLocation
ORDER BY ChildCount DESC;
-- Comment: Shows which locations contain the most sub-locations.
--          Planets with many sites are well-detailed in the data.

/* ALTERNATIVE for older SQL Server (without STRING_AGG):
SELECT
    COALESCE(ParentLocation, '(No Parent)') AS Parent,
    COUNT(*) AS ChildCount
FROM learn_locations
WHERE ParentLocation IS NOT NULL
GROUP BY ParentLocation
ORDER BY ChildCount DESC;
*/

/* VARIATIONS:
   - HAVING COUNT(*) >= 3                  -- Only parents with many children
   - WHERE LocationType = 'Site'           -- Only count sites
   - Add: COUNT(DISTINCT LocationType) AS ChildTypes
*/
