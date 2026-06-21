/*******************************************************************************
 * VIEW: sem_continuity_issue
 *
 * PURPOSE: Canonical semantic view over continuity issues/discrepancies.
 *          Records where conflicting or ambiguous information exists.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - ContinuityIssueKey: Surrogate key for joins
 *   - ContinuityIssueGuid: Stable external identifier
 *   - IssueSummary: Brief description of the issue
 *   - IssueTypeName: Category of issue
 *   - SeverityLabel: Issue severity (Low, Med, High, Critical)
 *   - DisputeLevel: How contested this issue is (Low, Med, High)
 *   - Status: Current resolution status
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW dbo.sem_continuity_issue
AS
SELECT
    ci.ContinuityIssueKey,
    ci.ContinuityIssueGuid,
    ci.FranchiseKey,
    f.Name                      AS FranchiseName,
    ci.ContinuityFrameKey,
    cf.FrameName                AS ContinuityFrameName,
    cf.FrameCode                AS ContinuityFrameCode,
    ci.IssueTypeKey,
    it.IssueTypeName,
    it.IssueTypeCode,
    ci.IssueSummary,
    ci.IssueDescription,
    ci.Scope,
    ci.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    ci.SceneKey,
    sc.SceneName,
    ci.SeverityScore,
    ci.SeverityLabel,
    ci.DisputeLevel,
    ci.Status,
    ci.ConfidenceScore,
    ci.Notes,
    ci.ValidFromUtc
FROM dbo.ContinuityIssue ci
INNER JOIN dbo.DimFranchise f
    ON ci.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
INNER JOIN dbo.DimContinuityFrame cf
    ON ci.ContinuityFrameKey = cf.ContinuityFrameKey
   AND cf.IsActive = 1
   AND cf.IsLatest = 1
INNER JOIN dbo.DimIssueType it
    ON ci.IssueTypeKey = it.IssueTypeKey
   AND it.IsActive = 1
   AND it.IsLatest = 1
LEFT JOIN dbo.DimWork w
    ON ci.WorkKey = w.WorkKey
   AND w.IsActive = 1
   AND w.IsLatest = 1
LEFT JOIN dbo.DimScene sc
    ON ci.SceneKey = sc.SceneKey
   AND sc.IsActive = 1
   AND sc.IsLatest = 1
WHERE ci.IsActive = 1
  AND ci.IsLatest = 1;
