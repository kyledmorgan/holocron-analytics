/*******************************************************************************
 * VIEW: sem_appearance_look
 * 
 * PURPOSE: Canonical semantic view over character appearance looks.
 *          Tracks how characters appear visually in specific scenes.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - LookKey: Surrogate key for joins
 *   - LookGuid: Stable external identifier
 *   - CharacterName: Character being depicted
 *   - LookLabel: Description of the look
 *   - LookType: Type of appearance (Costume, Makeup, etc.)
 *   - WorkTitle, SceneName: Context for where the look appears
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.sem_appearance_look
AS
SELECT
    al.LookKey,
    al.LookGuid,
    al.CharacterKey,
    c.CharacterGuid,
    e.DisplayName               AS CharacterName,
    al.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    al.SceneKey,
    sc.SceneName,
    sc.SceneOrdinal,
    al.LookLabel,
    al.LookType,
    al.PrimaryColorRef,
    al.SecondaryColorRef,
    al.MaterialRef,
    al.InsigniaRef,
    al.HairStyle,
    al.HairColor,
    al.FacialHair,
    al.MakeupOrMarkingsRef,
    al.ConditionRef,
    al.AccessoriesRef,
    al.ConfidenceScore,
    al.IsPrimaryLookInScene,
    al.EvidenceRef,
    al.Notes,
    w.FranchiseKey,
    f.Name                      AS FranchiseName,
    al.ValidFromUtc
FROM dbo.DimAppearanceLook al
INNER JOIN dbo.DimCharacter c
    ON al.CharacterKey = c.CharacterKey
   AND c.IsActive = 1
   AND c.IsLatest = 1
INNER JOIN dbo.DimEntity e
    ON c.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimWork w
    ON al.WorkKey = w.WorkKey
   AND w.IsActive = 1
   AND w.IsLatest = 1
INNER JOIN dbo.DimScene sc
    ON al.SceneKey = sc.SceneKey
   AND sc.IsActive = 1
   AND sc.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON w.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE al.IsActive = 1
  AND al.IsLatest = 1;
GO
