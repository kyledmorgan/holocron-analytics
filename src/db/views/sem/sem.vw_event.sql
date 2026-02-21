/*******************************************************************************
 * VIEW: sem_event
 *
 * PURPOSE: Canonical semantic view over events.
 *          Flattens event information with context from work, scene, location,
 *          event type, continuity frame, and era.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - EventKey: Surrogate key for joins
 *   - FactEventGuid: Stable external identifier
 *   - EventOrdinal: Order within the scene
 *   - EventTypeName: Type of event (Combat, Movement, Dialogue, etc.)
 *   - SummaryShort: Brief event description
 *   - ConfidenceScore: Confidence in the event data (0.0 to 1.0)
 *   - WorkTitle, SceneName: Context for where the event occurs
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_event
AS
SELECT
    ev.EventKey,
    ev.FactEventGuid            AS EventGuid,
    ev.FranchiseKey,
    f.Name                      AS FranchiseName,
    ev.ContinuityFrameKey,
    cf.FrameName                AS ContinuityFrameName,
    cf.FrameCode                AS ContinuityFrameCode,
    ev.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    ev.SceneKey,
    sc.SceneName,
    sc.SceneOrdinal,
    ev.ParentEventKey,
    ev.EventOrdinal,
    ev.EventTypeKey,
    et.EventTypeName,
    et.EventTypeCode,
    et.VerbClass,
    et.VerbLemma,
    ev.LocationKey,
    le.DisplayName              AS LocationName,
    ev.StartSec,
    ev.EndSec,
    ev.EraKey,
    era.EraName,
    era.EraCode,
    ev.UniverseYearMin,
    ev.UniverseYearMax,
    ev.DateKey,
    ev.TimeKey,
    ev.EventTimestampUtc,
    ev.SummaryShort,
    ev.SummaryNormalized,
    ev.ConfidenceScore,
    ev.ExtractionMethod,
    ev.Notes,
    ev.ValidFromUtc
FROM dbo.FactEvent ev
INNER JOIN dbo.DimFranchise f
    ON ev.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
INNER JOIN dbo.DimContinuityFrame cf
    ON ev.ContinuityFrameKey = cf.ContinuityFrameKey
   AND cf.IsActive = 1
   AND cf.IsLatest = 1
INNER JOIN dbo.DimWork w
    ON ev.WorkKey = w.WorkKey
   AND w.IsActive = 1
   AND w.IsLatest = 1
INNER JOIN dbo.DimScene sc
    ON ev.SceneKey = sc.SceneKey
   AND sc.IsActive = 1
   AND sc.IsLatest = 1
INNER JOIN dbo.DimEventType et
    ON ev.EventTypeKey = et.EventTypeKey
   AND et.IsActive = 1
   AND et.IsLatest = 1
LEFT JOIN dbo.DimLocation loc
    ON ev.LocationKey = loc.LocationKey
   AND loc.IsActive = 1
   AND loc.IsLatest = 1
LEFT JOIN dbo.DimEntity le
    ON loc.EntityKey = le.EntityKey
   AND le.IsActive = 1
   AND le.IsLatest = 1
LEFT JOIN dbo.DimEra era
    ON ev.EraKey = era.EraKey
   AND era.IsActive = 1
   AND era.IsLatest = 1
WHERE ev.IsActive = 1
  AND ev.IsLatest = 1;
