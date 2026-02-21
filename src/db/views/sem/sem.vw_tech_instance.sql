/*******************************************************************************
 * VIEW: sem.vw_tech_instance
 *
 * PURPOSE: Canonical semantic view over specific technology instances.
 *          Individual ships, droids, weapons with their own identity.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - TechInstanceKey: Surrogate key for joins
 *   - TechInstanceGuid: Stable external identifier
 *   - InstanceName: Human-readable name (e.g., "Millennium Falcon")
 *   - ModelName: Base model/class name (e.g., "YT-1300")
 *   - AssetType: Category (Ship, Weapon, Droid, etc.)
 *   - CurrentStatus: Current operational status
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_tech_instance
AS
SELECT
    ti.TechInstanceKey,
    ti.TechInstanceGuid,
    ti.EntityKey,
    e.EntityGuid,
    ti.TechAssetKey,
    ta.TechAssetGuid,
    ti.InstanceName,
    ta.ModelName,
    ta.AssetType,
    ta.ManufacturerRef,
    ti.SerialRef,
    ti.BuildRef,
    ti.CurrentStatus,
    ti.LastKnownLocationRef,
    ti.Notes,
    ta.FranchiseKey,
    f.Name                      AS FranchiseName,
    ti.ValidFromUtc
FROM dbo.DimTechInstance ti
INNER JOIN dbo.DimEntity e
    ON ti.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimTechAsset ta
    ON ti.TechAssetKey = ta.TechAssetKey
   AND ta.IsActive = 1
   AND ta.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON ta.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE ti.IsActive = 1
  AND ti.IsLatest = 1;
