/*******************************************************************************
 * MART: mart_event_timeline
 * 
 * PURPOSE: Chronological event timeline with full context.
 *          Ordered by work, scene, and event ordinal for proper sequencing.
 *
 * AUDIENCE: Analysts, learning exercises, event explorer dashboards.
 *
 * KEY COLUMNS:
 *   - EventKey, EventGuid: Event identity
 *   - WorkTitle, WorkCode, SceneName, SceneOrdinal: Context
 *   - EventOrdinal: Order within scene
 *   - EventTypeName: Event category
 *   - SummaryShort: Event description
 *   - ConfidenceScore: Data quality indicator
 *   - TimelineOrdinal: Computed global ordering for easy sorting
 *
 * DEPENDENCIES: sem_event
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.mart_event_timeline
AS
SELECT
    e.EventKey,
    e.EventGuid,
    e.FranchiseKey,
    e.FranchiseName,
    e.ContinuityFrameKey,
    e.ContinuityFrameName,
    e.ContinuityFrameCode,
    e.WorkKey,
    e.WorkTitle,
    e.WorkCode,
    e.SceneKey,
    e.SceneName,
    e.SceneOrdinal,
    e.EventOrdinal,
    /* Computed timeline ordering: scene ordinal * 1000 + event ordinal */
    (e.SceneOrdinal * 1000 + e.EventOrdinal) AS TimelineOrdinal,
    e.EventTypeKey,
    e.EventTypeName,
    e.EventTypeCode,
    e.VerbClass,
    e.LocationKey,
    e.LocationName,
    e.StartSec,
    e.EndSec,
    e.EraKey,
    e.EraName,
    e.EraCode,
    e.UniverseYearMin,
    e.UniverseYearMax,
    e.SummaryShort,
    e.SummaryNormalized,
    e.ConfidenceScore,
    e.ExtractionMethod,
    e.Notes
FROM dbo.sem_event e;
GO
