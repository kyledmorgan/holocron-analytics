/*******************************************************************************
 * VIEW: sem.vw_scene
 *
 * PURPOSE: Canonical semantic view over scene subdivisions within works.
 *          Flattens scene information with work and franchise context.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - SceneKey: Surrogate key for joins
 *   - SceneGuid: Stable external identifier
 *   - SceneName: Human-readable scene name
 *   - SceneOrdinal: Scene order within the work
 *   - SceneType: Category (Opening, Action, Scene, Ending, Credits)
 *   - StartSec/EndSec/DurationSec: Timing information
 *   - WorkTitle: Parent work title
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_scene
AS
SELECT
    s.SceneKey,
    s.SceneGuid,
    s.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    w.WorkType,
    s.SceneOrdinal,
    s.SceneName,
    s.SceneType,
    s.StartSec,
    s.EndSec,
    s.DurationSec,
    s.LocationHint,
    s.Notes,
    s.ValidFromUtc,
    w.FranchiseKey,
    f.Name                      AS FranchiseName
FROM dbo.DimScene s
INNER JOIN dbo.DimWork w
    ON s.WorkKey = w.WorkKey
   AND w.IsActive = 1
   AND w.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON w.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE s.IsActive = 1
  AND s.IsLatest = 1;
