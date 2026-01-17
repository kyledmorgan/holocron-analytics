/*******************************************************************************
 * VIEW: sem_species
 * 
 * PURPOSE: Canonical semantic view over species/creature data.
 *          Flattens species information with entity context.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - SpeciesKey: Surrogate key for joins
 *   - SpeciesGuid: Stable external identifier
 *   - SpeciesName: Human-readable display name (from entity)
 *   - Category: Species category
 *   - HomeworldRef: Reference to homeworld
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_species
AS
SELECT
    sp.SpeciesKey,
    sp.SpeciesGuid,
    sp.EntityKey,
    e.EntityGuid,
    e.DisplayName               AS SpeciesName,
    e.DisplayNameNormalized     AS SpeciesNameNormalized,
    e.SortName,
    e.SummaryShort,
    sp.Category,
    sp.HomeworldRef,
    sp.TypicalLifespanRef,
    sp.AverageHeightRef,
    sp.SkinTypesRef,
    sp.LanguageRef,
    sp.DietRef,
    sp.TraitsJson,
    sp.Notes,
    e.FranchiseKey,
    f.Name                      AS FranchiseName,
    sp.ValidFromUtc
FROM dbo.DimSpecies sp
INNER JOIN dbo.DimEntity e
    ON sp.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON e.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE sp.IsActive = 1
  AND sp.IsLatest = 1;
GO
