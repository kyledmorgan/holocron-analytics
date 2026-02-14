/*******************************************************************************
 * LEARN: learn_continuity_issues
 * 
 * PURPOSE: Simplified continuity issue table for SQL learners.
 *          Flat view of canon conflicts and ambiguities.
 *
 * AUDIENCE: SQL learners in modules 8 (continuity analysis).
 *
 * KEY COLUMNS:
 *   - IssueId: Unique identifier
 *   - IssueSummary: Brief description of the issue
 *   - IssueType: Category of the issue
 *   - Severity: Severity label (Low, Med, High, Critical)
 *   - SeverityScore: Numeric severity (1-10)
 *   - DisputeLevel: How contested (Low, Med, High)
 *   - Status: Resolution status (Open, Explained, Retconned, etc.)
 *   - WorkTitle, SceneName: Scope context (if applicable)
 *
 * NOTES: This is the primary continuity issue table for learners.
 *        Use for severity filtering and status analysis.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.learn_continuity_issues
AS
SELECT
    ci.ContinuityIssueGuid      AS IssueId,
    ci.IssueSummary,
    ci.IssueDescription         AS Description,
    ci.IssueTypeName            AS IssueType,
    ci.IssueTypeCode,
    ci.SeverityLabel            AS Severity,
    ci.SeverityScore,
    ci.DisputeLevel,
    ci.Status,
    ci.Scope,
    ci.WorkTitle,
    ci.WorkCode,
    ci.SceneName,
    ci.ConfidenceScore,
    ci.ContinuityFrameName      AS ContinuityFrame,
    ci.FranchiseName            AS Franchise,
    ci.ContinuityIssueKey       -- Include for advanced join exercises
FROM sem.vw_continuity_issue ci;
GO
