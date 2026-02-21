/*******************************************************************************
 * MART: mart_location_event_rollup
 *
 * PURPOSE: Location hierarchy with event counts for location explorer.
 *          Shows where events occur with hierarchical context.
 *
 * AUDIENCE: Analysts, learning exercises, location dashboards.
 *
 * KEY COLUMNS:
 *   - LocationKey, LocationName: Location identity
 *   - LocationType: Hierarchy level (Galaxy, Region, System, Planet, Site)
 *   - ParentLocationName: Parent in hierarchy
 *   - EventCount: Number of events at this location
 *
 * DEPENDENCIES: sem_location, sem_event
 ******************************************************************************/
CREATE   VIEW dbo.mart_location_event_rollup
AS
SELECT
    loc.LocationKey,
    loc.LocationGuid,
    loc.EntityKey,
    loc.LocationName,
    loc.LocationNameNormalized,
    loc.LocationType,
    loc.ParentLocationKey,
    loc.ParentLocationName,
    loc.ParentLocationType,
    loc.RegionCode,
    loc.ClimateRef,
    loc.TerrainRef,
    loc.PopulationRef,
    loc.FranchiseKey,
    loc.FranchiseName,
    COALESCE(ev.EventCount, 0) AS EventCount
FROM dbo.sem_location loc
LEFT JOIN (
    SELECT
        e.LocationKey,
        COUNT(*) AS EventCount
    FROM dbo.sem_event e
    WHERE e.LocationKey IS NOT NULL
    GROUP BY e.LocationKey
) ev ON loc.LocationKey = ev.LocationKey;
