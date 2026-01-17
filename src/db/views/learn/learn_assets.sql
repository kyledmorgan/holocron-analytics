/*******************************************************************************
 * LEARN: learn_assets
 * 
 * PURPOSE: Simplified technology asset table for SQL learners.
 *          Covers ships, droids, weapons - both models and instances.
 *
 * AUDIENCE: SQL learners in modules 5-6 (asset lifecycle queries).
 *
 * KEY COLUMNS:
 *   - AssetId: Unique identifier for the instance
 *   - AssetName: Individual name (e.g., "Millennium Falcon")
 *   - ModelName: Base model (e.g., "YT-1300")
 *   - AssetType: Category (Ship, Droid, Weapon, Vehicle)
 *   - Manufacturer: Who made it
 *   - Status: Current operational status
 *   - LastKnownLocation: Where it was last seen
 *
 * NOTES: This is the primary asset table for learners.
 *        Use for asset tracking and lifecycle queries.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.learn_assets
AS
SELECT
    ti.TechInstanceGuid         AS AssetId,
    ti.InstanceName             AS AssetName,
    ti.ModelName,
    ti.AssetType,
    ti.ManufacturerRef          AS Manufacturer,
    ti.SerialRef                AS SerialNumber,
    ti.CurrentStatus            AS Status,
    ti.LastKnownLocationRef     AS LastKnownLocation,
    ti.BuildRef                 AS BuildInfo,
    ti.FranchiseName            AS Franchise,
    ti.TechInstanceKey,         -- Include for advanced join exercises
    ti.TechAssetKey             -- Include for advanced join exercises
FROM dbo.sem_tech_instance ti;
GO
