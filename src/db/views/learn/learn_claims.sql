/*******************************************************************************
 * LEARN: learn_claims
 * 
 * PURPOSE: Simplified claims table for SQL learners.
 *          Atomic assertions about entities with evidence.
 *
 * AUDIENCE: SQL learners in modules 8 (claims and continuity analysis).
 *
 * KEY COLUMNS:
 *   - ClaimId: Unique identifier
 *   - SubjectName: Entity the claim is about
 *   - SubjectType: Type of entity (Character, Location, etc.)
 *   - Predicate: What is being asserted (e.g., "height", "born_in")
 *   - Value: The asserted value
 *   - ValueType: Type of value (String, Number, Date, EntityRef)
 *   - ConfidenceScore: Confidence in the claim (0.0 to 1.0)
 *   - Source: Where the claim comes from (WorkTitle)
 *
 * NOTES: This is the primary claims table for learners.
 *        Use for fact-checking and evidence analysis.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.learn_claims
AS
SELECT
    c.ClaimGuid                 AS ClaimId,
    c.SubjectName,
    c.SubjectType,
    c.ClaimType,
    c.Predicate,
    c.ObjectValue               AS Value,
    c.ObjectValueType           AS ValueType,
    c.ConfidenceScore,
    c.EvidenceRef               AS Evidence,
    c.ExtractionMethod,
    c.WorkTitle                 AS SourceWork,
    c.WorkCode                  AS SourceWorkCode,
    c.SceneName                 AS SourceScene,
    c.ContinuityFrameName       AS ContinuityFrame,
    c.FranchiseName             AS Franchise,
    c.ClaimKey                  -- Include for advanced join exercises
FROM sem.vw_claim c;
GO
