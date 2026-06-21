/*******************************************************************************
 * VIEW: sem.vw_character
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
 * NOTES:
 *   - Only returns active, latest version records.
 *   - Moved from dbo.sem_character as part of schema standardization.
 *   - See docs/agent/db_policies.md for naming conventions.
 ******************************************************************************/
CREATE   VIEW sem.vw_character
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
    e.ExternalKey,
    e.SummaryShort,
    e.IsCanonical,
    c.SpeciesKey,
    species_entity.DisplayName  AS SpeciesName,
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
LEFT JOIN dbo.DimSpecies species_dim
    ON c.SpeciesKey = species_dim.SpeciesKey
   AND species_dim.IsActive = 1
   AND species_dim.IsLatest = 1
LEFT JOIN dbo.DimEntity species_entity
    ON species_dim.EntityKey = species_entity.EntityKey
   AND species_entity.IsActive = 1
   AND species_entity.IsLatest = 1
WHERE c.IsActive = 1
  AND c.IsLatest = 1;
