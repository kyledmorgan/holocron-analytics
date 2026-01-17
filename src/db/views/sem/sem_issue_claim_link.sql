/*******************************************************************************
 * VIEW: sem_issue_claim_link
 * 
 * PURPOSE: Canonical semantic view over issue-to-claim relationships.
 *          Links continuity issues to the claims that support or conflict.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - BridgeContinuityIssueClaimKey: Surrogate key
 *   - ContinuityIssueKey: Link to the issue
 *   - ClaimKey: Link to the claim
 *   - Role: How the claim relates (Conflicting, Context, Supporting, ResolutionBasis)
 *   - IssueSummary: Brief issue description
 *   - SubjectName: Entity the claim is about
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_issue_claim_link
AS
SELECT
    icl.BridgeContinuityIssueClaimKey,
    icl.BridgeContinuityIssueClaimGuid AS LinkGuid,
    icl.ContinuityIssueKey,
    ci.ContinuityIssueGuid,
    ci.IssueSummary,
    ci.SeverityLabel,
    ci.Status                   AS IssueStatus,
    icl.ClaimKey,
    fc.FactClaimGuid            AS ClaimGuid,
    e.DisplayName               AS SubjectName,
    fc.Predicate,
    fc.ObjectValue,
    fc.ConfidenceScore          AS ClaimConfidence,
    icl.Role,
    icl.Notes,
    ci.FranchiseKey,
    f.Name                      AS FranchiseName,
    icl.ValidFromUtc
FROM dbo.BridgeContinuityIssueClaim icl
INNER JOIN dbo.ContinuityIssue ci
    ON icl.ContinuityIssueKey = ci.ContinuityIssueKey
   AND ci.IsActive = 1
   AND ci.IsLatest = 1
INNER JOIN dbo.FactClaim fc
    ON icl.ClaimKey = fc.ClaimKey
   AND fc.IsActive = 1
   AND fc.IsLatest = 1
INNER JOIN dbo.DimEntity e
    ON fc.SubjectEntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON ci.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE icl.IsActive = 1
  AND icl.IsLatest = 1;
GO
