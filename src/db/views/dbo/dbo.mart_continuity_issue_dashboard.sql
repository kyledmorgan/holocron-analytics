/*******************************************************************************
 * MART: mart_continuity_issue_dashboard
 *
 * PURPOSE: Continuity issue dashboard with linked claim counts.
 *          For browsing and filtering issues by severity and status.
 *
 * AUDIENCE: Analysts, learning exercises, continuity analysis.
 *
 * KEY COLUMNS:
 *   - ContinuityIssueKey, IssueSummary: Issue identity
 *   - IssueTypeName: Category of issue
 *   - SeverityLabel, SeverityScore: Severity indicators
 *   - DisputeLevel, Status: Resolution state
 *   - LinkedClaimCount: Number of claims associated
 *   - WorkTitle, SceneName: Scope context (if applicable)
 *
 * DEPENDENCIES: sem_continuity_issue, sem_issue_claim_link
 ******************************************************************************/
CREATE   VIEW dbo.mart_continuity_issue_dashboard
AS
SELECT
    ci.ContinuityIssueKey,
    ci.ContinuityIssueGuid,
    ci.FranchiseKey,
    ci.FranchiseName,
    ci.ContinuityFrameKey,
    ci.ContinuityFrameName,
    ci.ContinuityFrameCode,
    ci.IssueTypeKey,
    ci.IssueTypeName,
    ci.IssueTypeCode,
    ci.IssueSummary,
    ci.IssueDescription,
    ci.Scope,
    ci.WorkKey,
    ci.WorkTitle,
    ci.WorkCode,
    ci.SceneKey,
    ci.SceneName,
    ci.SeverityScore,
    ci.SeverityLabel,
    ci.DisputeLevel,
    ci.Status,
    ci.ConfidenceScore,
    COALESCE(lc.LinkedClaimCount, 0)    AS LinkedClaimCount,
    COALESCE(lc.ConflictingClaims, 0)   AS ConflictingClaimCount,
    COALESCE(lc.SupportingClaims, 0)    AS SupportingClaimCount
FROM dbo.sem_continuity_issue ci
LEFT JOIN (
    SELECT
        icl.ContinuityIssueKey,
        COUNT(*)                                        AS LinkedClaimCount,
        SUM(CASE WHEN icl.Role = 'Conflicting' THEN 1 ELSE 0 END) AS ConflictingClaims,
        SUM(CASE WHEN icl.Role = 'Supporting' THEN 1 ELSE 0 END)  AS SupportingClaims
    FROM dbo.sem_issue_claim_link icl
    GROUP BY icl.ContinuityIssueKey
) lc ON ci.ContinuityIssueKey = lc.ContinuityIssueKey;
