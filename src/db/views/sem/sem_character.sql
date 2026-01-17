/*******************************************************************************
 * VIEW: sem_character
 * 
 * PURPOSE: Canonical semantic view over character data.
 *          Flattens character information with entity and species context.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - CharacterKey: Surrogate key for joins
 *   - CharacterGuid: Stable external identifier
 *   - CharacterName: Human-readable display name (from entity)
 *   - SpeciesName: Species display name
 *   - Gender, RoleArchetype: Character attributes
 *   - EntityKey: Link to base entity record
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_character
AS
SELECT
    c.CharacterKey,
    c.CharacterGuid,
    c.EntityKey,
    e.EntityGuid,
    e.DisplayName               AS CharacterName,
    e.DisplayNameNormalized     AS CharacterNameNormalized,
    e.SortName,
    e.AliasCsv                  AS Aliases,
    e.ExternalId,
    e.SummaryShort,
    e.IsCanonical,
    c.SpeciesKey,
    sp.DisplayName              AS SpeciesName,
    c.Gender,
    c.Pronouns,
    c.BirthRef,
    c.DeathRef,
    c.BirthPlaceRef,
    c.HomeworldRef,
    c.HeightRef,
    c.MassRef,
    c.EyeColor,
    c.HairColor,
    c.SkinColor,
    c.DistinguishingMarks,
    c.RoleArchetype,
    c.Notes,
    e.FranchiseKey,
    f.Name                      AS FranchiseName,
    c.ValidFromUtc
FROM dbo.DimCharacter c
INNER JOIN dbo.DimEntity e
    ON c.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON e.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
LEFT JOIN dbo.DimSpecies spc
    ON c.SpeciesKey = spc.SpeciesKey
   AND spc.IsActive = 1
   AND spc.IsLatest = 1
LEFT JOIN dbo.DimEntity sp
    ON spc.EntityKey = sp.EntityKey
   AND sp.IsActive = 1
   AND sp.IsLatest = 1
WHERE c.IsActive = 1
  AND c.IsLatest = 1;
GO
