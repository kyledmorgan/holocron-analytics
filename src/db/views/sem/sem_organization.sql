/*******************************************************************************
 * VIEW: sem_organization
 * 
 * PURPOSE: Canonical semantic view over organization/faction data.
 *          Flattens organization information with entity context.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - OrganizationKey: Surrogate key for joins
 *   - OrganizationGuid: Stable external identifier
 *   - OrganizationName: Human-readable display name (from entity)
 *   - OrgType: Organization type (Military, Political, etc.)
 *   - Scope: Scope of organization
 *   - AlignmentRef: Light/Dark/Neutral alignment
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_organization
AS
SELECT
    o.OrganizationKey,
    o.OrganizationGuid,
    o.EntityKey,
    e.EntityGuid,
    e.DisplayName               AS OrganizationName,
    e.DisplayNameNormalized     AS OrganizationNameNormalized,
    e.SortName,
    e.SummaryShort,
    o.OrgType,
    o.Scope,
    o.AlignmentRef,
    o.FoundedRef,
    o.DissolvedRef,
    o.HeadquartersRef,
    o.Notes,
    e.FranchiseKey,
    f.Name                      AS FranchiseName,
    o.ValidFromUtc
FROM dbo.DimOrganization o
INNER JOIN dbo.DimEntity e
    ON o.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON e.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE o.IsActive = 1
  AND o.IsLatest = 1;
GO
