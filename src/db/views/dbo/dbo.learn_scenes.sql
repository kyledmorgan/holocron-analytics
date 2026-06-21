/*******************************************************************************
 * LEARN: learn_scenes
 *
 * PURPOSE: Simplified, flat scene table for SQL learners.
 *          Shows scenes with work context for timeline queries.
 *
 * AUDIENCE: SQL learners in modules 1-3 (basic queries, ordering, grouping).
 *
 * KEY COLUMNS:
 *   - SceneId: Unique identifier (GUID for user-friendly lookup)
 *   - SceneName, SceneNumber: Identity and ordering
 *   - SceneType: Category for filtering (Opening, Action, Scene, Ending)
 *   - WorkTitle, WorkCode: Parent work context
 *   - StartSec, EndSec, DurationSec: Timing for analysis
 *   - LocationHint: Approximate location
 *
 * NOTES: This is the primary scene table for learners.
 *        Use for timeline and duration queries.
 ******************************************************************************/
CREATE   VIEW dbo.learn_scenes
AS
SELECT
    sc.SceneGuid                AS SceneId,
    sc.SceneName,
    sc.SceneOrdinal             AS SceneNumber,
    sc.SceneType,
    sc.WorkTitle,
    sc.WorkCode,
    sc.WorkType,
    sc.StartSec,
    sc.EndSec,
    sc.DurationSec,
    sc.LocationHint,
    sc.FranchiseName            AS Franchise,
    sc.SceneKey,                -- Include for advanced join exercises
    sc.WorkKey                  -- Include for advanced join exercises
FROM dbo.sem_scene sc;
