/*******************************************************************************
 * VIEW: sem.vw_tech_asset
 *
 * PURPOSE: Canonical semantic view over technology asset models/classes.
 *          Covers ships, weapons, droids, and other tech definitions.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - TechAssetKey: Surrogate key for joins
 *   - TechAssetGuid: Stable external identifier
 *   - ModelName: Human-readable model/class name
 *   - AssetType: Category (Ship, Weapon, Droid, Vehicle, etc.)
 *   - ManufacturerRef: Reference to manufacturer
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_tech_asset
AS
SELECT
    ta.TechAssetKey,
    ta.TechAssetGuid,
    ta.FranchiseKey,
    f.Name                      AS FranchiseName,
    ta.AssetType,
    ta.ModelName,
    ta.ModelNameNormalized,
    ta.ManufacturerRef,
    ta.ManufacturerCode,
    ta.EraRef,
    ta.FirstAppearanceRef,
    ta.TechLevelRef,
    ta.PowerSourceRef,
    ta.MaterialRef,
    ta.SafetyNotes,
    ta.Notes,
    ta.ValidFromUtc
FROM dbo.DimTechAsset ta
INNER JOIN dbo.DimFranchise f
    ON ta.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE ta.IsActive = 1
  AND ta.IsLatest = 1;
