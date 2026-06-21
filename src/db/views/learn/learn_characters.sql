/*******************************************************************************
 * LEARN: learn_characters
 * 
 * PURPOSE: Simplified, flat character table for SQL learners.
 *          Minimal joins required - all key information in one place.
 *
 * AUDIENCE: SQL learners in modules 1-2 (basic SELECT, WHERE, ORDER BY).
 *
 * KEY COLUMNS:
 *   - CharacterId: Unique identifier (GUID for user-friendly lookup)
 *   - CharacterName: Display name
 *   - Species, Gender, RoleArchetype: Core attributes for filtering
 *   - Homeworld, BirthPlace: Origin for geography exercises
 *   - Franchise: For multi-franchise filtering
 *
 * NOTES: This is the primary character table for learners.
 *        Use for simple queries without joins.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.learn_characters
AS
SELECT
    c.CharacterGuid             AS CharacterId,
    c.CharacterName,
    c.SortName,
    c.Aliases,
    c.SummaryShort              AS Description,
    c.SpeciesName               AS Species,
    c.Gender,
    c.RoleArchetype,
    c.HomeworldRef              AS Homeworld,
    c.BirthPlaceRef             AS BirthPlace,
    c.BirthRef                  AS BirthYear,
    c.DeathRef                  AS DeathYear,
    c.HeightRef                 AS Height,
    c.EyeColor,
    c.HairColor,
    c.SkinColor,
    c.IsCanonical,
    c.FranchiseName             AS Franchise,
    c.CharacterKey,             -- Include for advanced join exercises
    c.EntityKey                 -- Include for advanced join exercises
FROM sem.vw_character c;
GO
