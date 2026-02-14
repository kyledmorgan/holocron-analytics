/*******************************************************************************
 * LEARN: learn_locations
 * 
 * PURPOSE: Simplified location hierarchy table for SQL learners.
 *          Flat view with parent location names for easy filtering.
 *
 * AUDIENCE: SQL learners in modules 6 (location hierarchy queries).
 *
 * KEY COLUMNS:
 *   - LocationId: Unique identifier
 *   - LocationName: Display name
 *   - LocationType: Hierarchy level (Galaxy, Region, System, Planet, Site)
 *   - ParentLocation: Parent location name
 *   - ParentLocationType: Parent's hierarchy level
 *   - Climate, Terrain: Environmental attributes
 *   - Population: Population reference
 *
 * NOTES: This is the primary location table for learners.
 *        Use for geographic hierarchy exploration.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.learn_locations
AS
SELECT
    loc.LocationGuid            AS LocationId,
    loc.LocationName,
    loc.LocationType,
    loc.ParentLocationName      AS ParentLocation,
    loc.ParentLocationType,
    loc.RegionCode,
    loc.ClimateRef              AS Climate,
    loc.TerrainRef              AS Terrain,
    loc.PopulationRef           AS Population,
    loc.GovernmentRef           AS Government,
    loc.SummaryShort            AS Description,
    loc.FranchiseName           AS Franchise,
    loc.LocationKey,            -- Include for advanced join exercises
    loc.ParentLocationKey       -- Include for advanced join exercises
FROM sem.vw_location loc;
GO
