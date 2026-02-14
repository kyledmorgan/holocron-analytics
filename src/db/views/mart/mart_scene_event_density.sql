/*******************************************************************************
 * MART: mart_scene_event_density
 * 
 * PURPOSE: Scene-level dashboard with event counts and timing metrics.
 *          Shows event density and duration for scene analysis.
 *
 * AUDIENCE: Analysts, learning exercises, scene breakdown dashboards.
 *
 * KEY COLUMNS:
 *   - SceneKey, SceneName, SceneOrdinal: Scene identity
 *   - WorkTitle, WorkCode: Work context
 *   - DurationSec: Scene duration
 *   - EventCount: Number of events in scene
 *   - EventDensity: Events per minute (if duration known)
 *   - StartSec, EndSec: Timing anchors
 *
 * DEPENDENCIES: sem_scene, sem_event, sem_event_participant
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.mart_scene_event_density
AS
SELECT
    sc.SceneKey,
    sc.SceneGuid,
    sc.WorkKey,
    sc.WorkTitle,
    sc.WorkCode,
    sc.WorkType,
    sc.SceneOrdinal,
    sc.SceneName,
    sc.SceneType,
    sc.StartSec,
    sc.EndSec,
    sc.DurationSec,
    sc.LocationHint,
    sc.FranchiseKey,
    sc.FranchiseName,
    COALESCE(ev.EventCount, 0) AS EventCount,
    /* Events per minute (avoid division by zero) */
    CASE
        WHEN sc.DurationSec > 0
        THEN CAST(COALESCE(ev.EventCount, 0) AS DECIMAL(10,2)) / (sc.DurationSec / 60.0)
        ELSE NULL
    END AS EventsPerMinute,
    ev.MinEventOrdinal,
    ev.MaxEventOrdinal,
    ev.DistinctEventTypes,
    COALESCE(part.DistinctParticipants, 0) AS DistinctParticipants
FROM sem.vw_scene sc
LEFT JOIN (
    SELECT
        e.SceneKey,
        COUNT(*)                       AS EventCount,
        MIN(e.EventOrdinal)            AS MinEventOrdinal,
        MAX(e.EventOrdinal)            AS MaxEventOrdinal,
        COUNT(DISTINCT e.EventTypeKey) AS DistinctEventTypes
    FROM sem.vw_event e
    GROUP BY e.SceneKey
) ev ON sc.SceneKey = ev.SceneKey
LEFT JOIN (
    SELECT
        p.SceneKey,
        COUNT(DISTINCT p.EntityKey) AS DistinctParticipants
    FROM sem.vw_event_participant p
    GROUP BY p.SceneKey
) part ON sc.SceneKey = part.SceneKey;
GO
