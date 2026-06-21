/*******************************************************************************
 * VIEW: sem_franchise
 *
 * PURPOSE: Canonical semantic view over franchise/universe data.
 *          Provides a clean, stable query surface for franchise information.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - FranchiseKey: Surrogate key for joins
 *   - FranchiseGuid: Stable external identifier
 *   - FranchiseName: Human-readable franchise name
 *   - UniverseCode: Short code identifier (e.g., 'SW' for Star Wars)
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW dbo.sem_franchise
AS
SELECT
    f.FranchiseKey,
    f.FranchiseGuid,
    f.Name                      AS FranchiseName,
    f.UniverseCode,
    f.FranchiseGroup,
    f.OwnerOrRightsHolder,
    f.DefaultContinuityFrame,
    f.Notes,
    f.ValidFromUtc
FROM dbo.DimFranchise f
WHERE f.IsActive = 1
  AND f.IsLatest = 1;
