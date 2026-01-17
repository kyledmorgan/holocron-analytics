/*******************************************************************************
 * VIEW: sem_location
 * 
 * PURPOSE: Canonical semantic view over location data with hierarchy.
 *          Flattens location information with entity and parent location context.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - LocationKey: Surrogate key for joins
 *   - LocationGuid: Stable external identifier
 *   - LocationName: Human-readable display name (from entity)
 *   - LocationType: Type (Galaxy, Region, System, Planet, Site)
 *   - ParentLocationKey: Key to parent location for hierarchy traversal
 *   - ParentLocationName: Parent location display name
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_location
AS
SELECT
    loc.LocationKey,
    loc.LocationGuid,
    loc.EntityKey,
    e.EntityGuid,
    e.DisplayName               AS LocationName,
    e.DisplayNameNormalized     AS LocationNameNormalized,
    e.SortName,
    e.SummaryShort,
    loc.LocationType,
    loc.ParentLocationKey,
    pe.DisplayName              AS ParentLocationName,
    ploc.LocationType           AS ParentLocationType,
    loc.RegionCode,
    loc.LatitudeRef,
    loc.LongitudeRef,
    loc.ClimateRef,
    loc.TerrainRef,
    loc.PopulationRef,
    loc.GovernmentRef,
    loc.Notes,
    e.FranchiseKey,
    f.Name                      AS FranchiseName,
    loc.ValidFromUtc
FROM dbo.DimLocation loc
INNER JOIN dbo.DimEntity e
    ON loc.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON e.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
LEFT JOIN dbo.DimLocation ploc
    ON loc.ParentLocationKey = ploc.LocationKey
   AND ploc.IsActive = 1
   AND ploc.IsLatest = 1
LEFT JOIN dbo.DimEntity pe
    ON ploc.EntityKey = pe.EntityKey
   AND pe.IsActive = 1
   AND pe.IsLatest = 1
WHERE loc.IsActive = 1
  AND loc.IsLatest = 1;
GO
