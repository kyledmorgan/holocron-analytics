/******************************************************************************
 * MODULE 08: Continuity Issues & Claims - ANSWER KEY
 * 
 * This file contains solutions for the continuity analysis exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Continuity Issues
-- ============================================================================

SELECT TOP 20 *
FROM learn_continuity_issues
ORDER BY SeverityScore DESC, IssueSummary;
-- Comment: Continuity issues track canon conflicts and ambiguities.
--          Severity and DisputeLevel indicate how serious and contested.

/* VARIATIONS:
   - WHERE Status = 'Open'                 -- Unresolved issues only
   - ORDER BY Status, Severity             -- Group by status
*/


-- ============================================================================
-- EXERCISE 2: Issues by Severity
-- ============================================================================

SELECT
    Severity,
    COUNT(*) AS IssueCount,
    AVG(SeverityScore) AS AvgScore
FROM learn_continuity_issues
GROUP BY Severity
ORDER BY AvgScore DESC;
-- Comment: Severity labels map to numeric scores for ranking.

/* VARIATIONS:
   - Add: CASE to order by severity level properly
   - WHERE Status = 'Open'                 -- Only unresolved
   - Add: COUNT(DISTINCT IssueType)        -- Types per severity
*/


-- ============================================================================
-- EXERCISE 3: High Severity Issues
-- ============================================================================

SELECT
    IssueSummary,
    IssueType,
    Severity,
    SeverityScore,
    DisputeLevel,
    Status
FROM learn_continuity_issues
WHERE Severity IN ('High', 'Critical')
ORDER BY SeverityScore DESC, DisputeLevel DESC;
-- Comment: High severity issues are major canon problems.
--          Combined with high dispute means very controversial.

/* VARIATIONS:
   - AND Status = 'Open'                   -- Unresolved high severity
   - AND DisputeLevel = 'High'             -- Also highly disputed
   - WHERE SeverityScore >= 7              -- Numeric threshold
*/


-- ============================================================================
-- EXERCISE 4: Issue Status Analysis
-- ============================================================================

SELECT
    Status,
    COUNT(*) AS IssueCount,
    CAST(COUNT(*) AS FLOAT) / (SELECT COUNT(*) FROM learn_continuity_issues) * 100 
        AS PercentOfTotal
FROM learn_continuity_issues
GROUP BY Status
ORDER BY IssueCount DESC;
-- Comment: Status shows resolution state of issues.
--          Open = unresolved, Explained = addressed, Retconned = changed in canon.

/* VARIATIONS:
   - Add: AVG(SeverityScore) per status    -- Severity by status
   - HAVING COUNT(*) > 1                   -- Only common statuses
*/


-- ============================================================================
-- EXERCISE 5: Issues by Work
-- ============================================================================

SELECT
    COALESCE(WorkTitle, '(Franchise-wide)') AS Work,
    WorkCode,
    COUNT(*) AS IssueCount,
    AVG(SeverityScore) AS AvgSeverity
FROM learn_continuity_issues
GROUP BY WorkTitle, WorkCode
ORDER BY IssueCount DESC;
-- Comment: Some issues span multiple works or the whole franchise.
--          NULL WorkTitle means not scoped to a specific work.

/* VARIATIONS:
   - WHERE WorkTitle IS NOT NULL           -- Only work-specific issues
   - AND Severity = 'High'                 -- High severity by work
   - HAVING COUNT(*) >= 2                  -- Works with multiple issues
*/


-- ============================================================================
-- EXERCISE 6: Explore Claims
-- ============================================================================

SELECT TOP 20 *
FROM learn_claims
ORDER BY SubjectName, Predicate;
-- Comment: Claims are atomic assertions: "Subject has Predicate = Value"
--          Example: "Luke Skywalker" "height" "1.72 m"

/* VARIATIONS:
   - WHERE SubjectName LIKE '%Luke%'       -- Claims about Luke
   - ORDER BY ConfidenceScore DESC         -- Highest confidence first
*/


-- ============================================================================
-- EXERCISE 7: Claims by Subject
-- ============================================================================

SELECT
    SubjectName,
    SubjectType,
    COUNT(*) AS ClaimCount,
    AVG(ConfidenceScore) AS AvgConfidence
FROM learn_claims
GROUP BY SubjectName, SubjectType
ORDER BY ClaimCount DESC;
-- Comment: Characters with many claims are well-documented.
--          Low confidence claims may indicate uncertainty or disputes.

/* VARIATIONS:
   - WHERE SubjectType = 'Character'       -- Characters only
   - HAVING AVG(ConfidenceScore) < 0.80    -- Subjects with uncertain claims
   - AND COUNT(*) >= 5                     -- Well-documented subjects
*/


-- ============================================================================
-- EXERCISE 8: Low Confidence Claims
-- ============================================================================

SELECT
    SubjectName,
    Predicate,
    Value,
    ConfidenceScore,
    ExtractionMethod,
    SourceWork
FROM learn_claims
WHERE ConfidenceScore < 0.70
ORDER BY ConfidenceScore ASC, SubjectName;
-- Comment: Low confidence claims may need verification.
--          AI-extracted claims sometimes have lower confidence.

/* VARIATIONS:
   - WHERE ConfidenceScore < 0.50          -- Very low confidence
   - AND ExtractionMethod = 'AI'           -- AI-extracted only
   - AND SourceWork IS NULL                -- No specific source
*/


-- ============================================================================
-- EXERCISE 9: Claim Types
-- ============================================================================

SELECT
    ClaimType,
    COUNT(*) AS ClaimCount,
    AVG(ConfidenceScore) AS AvgConfidence,
    MIN(ConfidenceScore) AS MinConfidence,
    MAX(ConfidenceScore) AS MaxConfidence
FROM learn_claims
GROUP BY ClaimType
ORDER BY ClaimCount DESC;
-- Comment: Claim types categorize the nature of the assertion.
--          Attribute = property of entity, Relationship = link to another entity.

/* VARIATIONS:
   - WHERE ConfidenceScore >= 0.80         -- Only high confidence
   - Add: COUNT(DISTINCT SubjectName)      -- Subjects per type
   - HAVING AVG(ConfidenceScore) > 0.75    -- Reliable claim types
*/


-- ============================================================================
-- EXERCISE 10: Disputed Topics
-- ============================================================================

SELECT
    IssueSummary,
    Description,
    IssueType,
    Severity,
    SeverityScore,
    DisputeLevel,
    Status,
    WorkTitle,
    SceneName,
    ContinuityFrame
FROM learn_continuity_issues
WHERE DisputeLevel = 'High'
ORDER BY SeverityScore DESC;
-- Comment: High dispute issues are the most debated in the fan community.
--          These often involve character motivations or timeline conflicts.

/* VARIATIONS:
   - AND Severity IN ('High', 'Critical')  -- High dispute AND severity
   - AND Status = 'Open'                   -- Unresolved disputes
   - AND WorkTitle IS NOT NULL             -- Work-specific disputes
*/
