/*******************************************************************************
 * MART: mart_character_profile
 * 
 * PURPOSE: Character profile mart for browsing and filtering characters.
 *          Enriched with species, appearance count, and event participation stats.
 *
 * AUDIENCE: Analysts, learning exercises, character directory dashboards.
 *
 * KEY COLUMNS:
 *   - CharacterKey, CharacterGuid, CharacterName: Identity
 *   - SpeciesName, Gender, RoleArchetype: Core attributes
 *   - HomeworldRef, BirthRef: Origin information
 *   - EventParticipationCount: Number of events participated in
 *   - AppearanceCount: Number of distinct scene appearances
 *
 * DEPENDENCIES: sem_character, sem_event_participant, sem_appearance_look
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.mart_character_profile
AS
SELECT
    c.CharacterKey,
    c.CharacterGuid,
    c.EntityKey,
    c.EntityGuid,
    c.CharacterName,
    c.CharacterNameNormalized,
    c.SortName,
    c.Aliases,
    c.SummaryShort,
    c.SpeciesKey,
    c.SpeciesName,
    c.Gender,
    c.Pronouns,
    c.RoleArchetype,
    c.BirthRef,
    c.DeathRef,
    c.BirthPlaceRef,
    c.HomeworldRef,
    c.HeightRef,
    c.EyeColor,
    c.HairColor,
    c.SkinColor,
    c.IsCanonical,
    c.FranchiseKey,
    c.FranchiseName,
    COALESCE(ep.EventParticipationCount, 0) AS EventParticipationCount,
    COALESCE(al.AppearanceCount, 0)         AS AppearanceCount
FROM sem.vw_character c
LEFT JOIN (
    SELECT
        p.EntityKey,
        COUNT(*) AS EventParticipationCount
    FROM sem.vw_event_participant p
    GROUP BY p.EntityKey
) ep ON c.EntityKey = ep.EntityKey
LEFT JOIN (
    SELECT
        al.CharacterKey,
        COUNT(*) AS AppearanceCount
    FROM sem.vw_appearance_look al
    GROUP BY al.CharacterKey
) al ON c.CharacterKey = al.CharacterKey;
GO
