/*******************************************************************************
 * MART: mart_trench_run_events
 *
 * PURPOSE: Deep dive mart for the Trench Run sequence (Episode IV).
 *          Pre-filtered to ONLY include trench-run related scenes.
 *          Excludes control room cutaways - focuses on flight sequence.
 *
 * AUDIENCE: Analysts, learning exercises, Trench Run deep dive module.
 *
 * KEY COLUMNS:
 *   - EventKey, EventGuid: Event identity
 *   - SceneName, SceneOrdinal, EventOrdinal: Sequence position
 *   - EventTypeName, SummaryShort: What happened
 *   - LocationName: Where in the trench run
 *   - TimelineOrdinal: For sorting
 *
 * SCOPE: WorkCode = 'ANH' AND SceneOrdinal BETWEEN 44 AND 54
 *        (Gold Squadron Trench Run through Death Star Destruction)
 *
 * DEPENDENCIES: sem_event, sem_scene
 ******************************************************************************/
CREATE   VIEW dbo.mart_trench_run_events
AS
SELECT
    e.EventKey,
    e.EventGuid,
    e.FranchiseKey,
    e.FranchiseName,
    e.ContinuityFrameKey,
    e.ContinuityFrameName,
    e.WorkKey,
    e.WorkTitle,
    e.WorkCode,
    e.SceneKey,
    e.SceneName,
    e.SceneOrdinal,
    e.EventOrdinal,
    /* Timeline ordering within the sequence */
    ((e.SceneOrdinal - 44) * 1000 + e.EventOrdinal) AS SequenceOrdinal,
    e.EventTypeKey,
    e.EventTypeName,
    e.EventTypeCode,
    e.VerbClass,
    e.LocationKey,
    e.LocationName,
    e.StartSec,
    e.EndSec,
    e.SummaryShort,
    e.ConfidenceScore,
    e.ExtractionMethod
FROM dbo.sem_event e
WHERE e.WorkCode = 'ANH'
  AND e.SceneOrdinal >= 44     -- Gold Squadron Trench Run
  AND e.SceneOrdinal <= 54;    -- Death Star Destruction
