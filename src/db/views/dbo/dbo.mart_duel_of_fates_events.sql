/*******************************************************************************
 * MART: mart_duel_of_fates_events
 *
 * PURPOSE: Deep dive mart for the Duel of the Fates sequence (Episode I).
 *          Pre-filtered to the lightsaber duel: door reveal to Maul's defeat.
 *
 * AUDIENCE: Analysts, learning exercises, Duel of the Fates deep dive module.
 *
 * KEY COLUMNS:
 *   - EventKey, EventGuid: Event identity
 *   - SceneName, SceneOrdinal, EventOrdinal: Sequence position
 *   - EventTypeName, SummaryShort: What happened
 *   - LocationName: Where in the generator complex
 *   - SequenceOrdinal: For sorting within the duel
 *
 * SCOPE: WorkCode = 'TPM' AND SceneOrdinal BETWEEN 27 AND 44
 *        (Doors Open - Maul Revealed through Qui-Gon's Last Words)
 *
 * DEPENDENCIES: sem_event, sem_scene
 ******************************************************************************/
CREATE   VIEW dbo.mart_duel_of_fates_events
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
    ((e.SceneOrdinal - 27) * 1000 + e.EventOrdinal) AS SequenceOrdinal,
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
WHERE e.WorkCode = 'TPM'
  AND e.SceneOrdinal >= 27     -- Doors Open - Maul Revealed
  AND e.SceneOrdinal <= 44;    -- Qui-Gon's Last Words
