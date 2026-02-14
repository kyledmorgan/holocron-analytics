/*******************************************************************************
 * MART: mart_character_appearance_timeline
 * 
 * PURPOSE: Timeline of character appearances across works and scenes.
 *          Shows where and when each character appears.
 *
 * AUDIENCE: Analysts, learning exercises, character journey analysis.
 *
 * KEY COLUMNS:
 *   - CharacterKey, CharacterName: Character identity
 *   - WorkKey, WorkTitle, WorkCode: Work context
 *   - SceneKey, SceneName, SceneOrdinal: Scene context
 *   - LookLabel, LookType: Appearance details
 *   - StartSec, EndSec: Timing within the work
 *
 * DEPENDENCIES: sem_appearance_look, sem_scene
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.mart_character_appearance_timeline
AS
SELECT
    al.CharacterKey,
    al.CharacterGuid,
    al.CharacterName,
    al.WorkKey,
    al.WorkTitle,
    al.WorkCode,
    al.SceneKey,
    al.SceneName,
    al.SceneOrdinal,
    al.LookKey,
    al.LookGuid,
    al.LookLabel,
    al.LookType,
    al.ConditionRef,
    al.IsPrimaryLookInScene,
    al.ConfidenceScore,
    sc.StartSec,
    sc.EndSec,
    sc.DurationSec,
    sc.LocationHint,
    al.FranchiseKey,
    al.FranchiseName
FROM sem.vw_appearance_look al
INNER JOIN sem.vw_scene sc
    ON al.SceneKey = sc.SceneKey;
GO
