/******************************************************************************
 * MODULE 05: Asset Lifecycle - ANSWER KEY
 * 
 * This file contains solutions for the asset lifecycle exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Assets
-- ============================================================================

SELECT TOP 20 *
FROM learn_assets
ORDER BY AssetType, AssetName;
-- Comment: Assets are ships, droids, weapons with individual identities.
--          AssetName is the specific instance; ModelName is the class/type.

/* VARIATIONS:
   - WHERE AssetType = 'Ship'              -- Ships only
   - ORDER BY ModelName                    -- Group by model
*/


-- ============================================================================
-- EXERCISE 2: Asset Types
-- ============================================================================

SELECT
    AssetType,
    COUNT(*) AS AssetCount
FROM learn_assets
GROUP BY AssetType
ORDER BY AssetCount DESC;
-- Comment: Shows the distribution of asset types in the database.

/* VARIATIONS:
   - WHERE Status = 'Operational'          -- Only operational assets
   - Add: COUNT(DISTINCT ModelName) AS ModelCount  -- Unique models
*/


-- ============================================================================
-- EXERCISE 3: Ships Only
-- ============================================================================

SELECT
    AssetName,
    ModelName,
    Manufacturer,
    Status,
    LastKnownLocation
FROM learn_assets
WHERE AssetType = 'Ship'
ORDER BY AssetName;
-- Comment: Ships are the most iconic assets in the franchise.
--          Famous ships like the Millennium Falcon appear here.

/* VARIATIONS:
   - AND Status = 'Operational'            -- Flying ships only
   - AND Status = 'Destroyed'              -- Destroyed ships
   - AND Manufacturer LIKE '%Corellian%'   -- Corellian ships
*/


-- ============================================================================
-- EXERCISE 4: Droids by Model
-- ============================================================================

SELECT
    ModelName,
    COUNT(*) AS InstanceCount
FROM learn_assets
WHERE AssetType = 'Droid'
GROUP BY ModelName
ORDER BY InstanceCount DESC, ModelName;
-- Comment: Some droid models have multiple instances (e.g., R2 units).

/* VARIATIONS:
   - AND Status = 'Operational'            -- Working droids
   - HAVING COUNT(*) > 1                   -- Models with multiple units
   - Add: STRING_AGG(AssetName, ', ')      -- List instance names
*/


-- ============================================================================
-- EXERCISE 5: Assets by Status
-- ============================================================================

SELECT
    COALESCE(Status, 'Unknown') AS Status,  -- Handle nulls
    COUNT(*) AS AssetCount
FROM learn_assets
GROUP BY Status
ORDER BY AssetCount DESC;
-- Comment: Status shows current operational state of assets.
--          Common values: Operational, Destroyed, Damaged, Unknown

/* VARIATIONS:
   - WHERE AssetType = 'Ship'              -- Ships only
   - WHERE Status IS NOT NULL              -- Only known statuses
*/


-- ============================================================================
-- EXERCISE 6: Named Ships
-- ============================================================================

SELECT
    AssetName,
    ModelName,
    Manufacturer,
    Status
FROM learn_assets
WHERE AssetType = 'Ship'
  AND AssetName <> ModelName               -- Name differs from model
ORDER BY AssetName;
-- Comment: Named ships have distinct identities beyond their model.
--          The Millennium Falcon is a YT-1300, but has its own name.

/* VARIATIONS:
   - WHERE AssetName LIKE '%Falcon%'       -- Find Falcon
   - WHERE AssetName LIKE '%Star%'         -- Ships with Star in name
   - AND Status = 'Operational'            -- Active named ships
*/


-- ============================================================================
-- EXERCISE 7: Manufacturer Analysis
-- ============================================================================

SELECT
    COALESCE(Manufacturer, 'Unknown') AS Manufacturer,
    COUNT(*) AS AssetCount,
    COUNT(DISTINCT AssetType) AS AssetTypesProduced
FROM learn_assets
GROUP BY Manufacturer
ORDER BY AssetCount DESC;
-- Comment: Major manufacturers produce multiple asset types.

/* VARIATIONS:
   - WHERE AssetType = 'Ship'              -- Ship manufacturers only
   - HAVING COUNT(*) >= 2                  -- Prolific manufacturers
   - Add: STRING_AGG(DISTINCT AssetType, ', ')  -- List types produced
*/


-- ============================================================================
-- EXERCISE 8: Weapons Inventory
-- ============================================================================

SELECT
    AssetName,
    ModelName,
    Status,
    Manufacturer,
    SerialNumber
FROM learn_assets
WHERE AssetType = 'Weapon'
ORDER BY ModelName, AssetName;
-- Comment: Weapons include lightsabers, blasters, and other combat tools.

/* VARIATIONS:
   - WHERE ModelName LIKE '%Lightsaber%'   -- Lightsabers only
   - WHERE ModelName LIKE '%Blaster%'      -- Blasters only
   - AND Status = 'Operational'            -- Working weapons
*/


-- ============================================================================
-- EXERCISE 9: Destroyed Assets
-- ============================================================================

SELECT
    AssetName,
    AssetType,
    ModelName,
    LastKnownLocation,
    Manufacturer
FROM learn_assets
WHERE Status = 'Destroyed'
ORDER BY AssetType, AssetName;
-- Comment: Destroyed assets may have significant story moments.
--          The Death Star is famously destroyed (twice).

/* VARIATIONS:
   - WHERE Status IN ('Destroyed', 'Damaged')  -- All non-operational
   - AND AssetType = 'Ship'                -- Destroyed ships only
   - AND LastKnownLocation IS NOT NULL     -- With known destruction location
*/


-- ============================================================================
-- EXERCISE 10: Asset Summary Report
-- ============================================================================

SELECT
    AssetType,
    COUNT(*) AS TotalAssets,
    SUM(CASE WHEN Status = 'Operational' THEN 1 ELSE 0 END) AS Operational,
    SUM(CASE WHEN Status = 'Destroyed' THEN 1 ELSE 0 END) AS Destroyed,
    SUM(CASE WHEN Status = 'Damaged' THEN 1 ELSE 0 END) AS Damaged,
    SUM(CASE WHEN Status IS NULL OR Status NOT IN ('Operational','Destroyed','Damaged') 
        THEN 1 ELSE 0 END) AS Other
FROM learn_assets
GROUP BY AssetType
ORDER BY TotalAssets DESC;
-- Comment: CASE expressions inside aggregates create conditional counts.
--          This pattern is powerful for creating pivot-style reports.

/* VARIATIONS:
   - Add: CAST(SUM(...) AS FLOAT) / COUNT(*) * 100 AS OperationalPct
   - WHERE Manufacturer IS NOT NULL        -- Only known manufacturers
   - GROUP BY AssetType, Manufacturer      -- Breakdown by both
*/
