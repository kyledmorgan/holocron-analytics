/*******************************************************************************
 * VIEW: sem.vw_continuity_frame
 * 
 * PURPOSE: Canonical semantic view over continuity/canon frame definitions.
 *          Provides context for understanding which timeline or canon events
 *          belong to.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - ContinuityFrameKey: Surrogate key for joins
 *   - ContinuityFrameGuid: Stable external identifier
 *   - FrameName: Human-readable frame name
 *   - FrameCode: Short code identifier
 *   - AuthorityType: Type of canonical authority
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW sem.vw_continuity_frame
AS
SELECT
    cf.ContinuityFrameKey,
    cf.ContinuityFrameGuid,
    cf.FranchiseKey,
    f.Name                      AS FranchiseName,
    cf.FrameName,
    cf.FrameCode,
    cf.AuthorityType,
    cf.AuthorityRef,
    cf.PolicySummary,
    cf.EffectiveStartDate,
    cf.EffectiveEndDate,
    cf.Notes,
    cf.ValidFromUtc
FROM dbo.DimContinuityFrame cf
INNER JOIN dbo.DimFranchise f
    ON cf.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE cf.IsActive = 1
  AND cf.IsLatest = 1;
GO
