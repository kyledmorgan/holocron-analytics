/*******************************************************************************
 * VIEW: sem_claim
 * 
 * PURPOSE: Canonical semantic view over atomic claims/assertions.
 *          Facts asserted about entities with provenance and confidence.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - ClaimKey: Surrogate key for joins
 *   - FactClaimGuid: Stable external identifier
 *   - SubjectName: Entity the claim is about
 *   - Predicate: What is being asserted (e.g., "height", "born_in")
 *   - ObjectValue: The asserted value
 *   - ConfidenceScore: Confidence in the claim (0.0 to 1.0)
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_claim
AS
SELECT
    fc.ClaimKey,
    fc.FactClaimGuid            AS ClaimGuid,
    fc.FranchiseKey,
    f.Name                      AS FranchiseName,
    fc.ContinuityFrameKey,
    cf.FrameName                AS ContinuityFrameName,
    cf.FrameCode                AS ContinuityFrameCode,
    fc.ClaimType,
    fc.SubjectEntityKey,
    e.EntityGuid                AS SubjectEntityGuid,
    e.DisplayName               AS SubjectName,
    e.EntityType                AS SubjectType,
    fc.Predicate,
    fc.ObjectValue,
    fc.ObjectValueType,
    fc.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    fc.SceneKey,
    sc.SceneName,
    fc.ConfidenceScore,
    fc.EvidenceRef,
    fc.ExtractionMethod,
    fc.Notes,
    fc.ValidFromUtc
FROM dbo.FactClaim fc
INNER JOIN dbo.DimFranchise f
    ON fc.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
INNER JOIN dbo.DimContinuityFrame cf
    ON fc.ContinuityFrameKey = cf.ContinuityFrameKey
   AND cf.IsActive = 1
   AND cf.IsLatest = 1
INNER JOIN dbo.DimEntity e
    ON fc.SubjectEntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
LEFT JOIN dbo.DimWork w
    ON fc.WorkKey = w.WorkKey
   AND w.IsActive = 1
   AND w.IsLatest = 1
LEFT JOIN dbo.DimScene sc
    ON fc.SceneKey = sc.SceneKey
   AND sc.IsActive = 1
   AND sc.IsLatest = 1
WHERE fc.IsActive = 1
  AND fc.IsLatest = 1;
GO
