/******************************************************************************
 * MODULE 10: Duel of the Fates Deep Dive - ANSWER KEY
 * 
 * This file contains solutions for the Duel of the Fates analysis exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Identify the Duel Scenes
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    SceneType,
    DurationSec,
    StartSec,
    EndSec,
    LocationHint
FROM learn_scenes
WHERE WorkCode = 'TPM'
  AND SceneNumber BETWEEN 27 AND 44
ORDER BY SceneNumber;
-- Comment: These 18 scenes cover the entire Duel of the Fates sequence.
--          From the doors opening to reveal Maul through Qui-Gon's death.

/* VARIATIONS:
   - BETWEEN 27 AND 35                     -- Up to barriers
   - BETWEEN 36 AND 44                     -- Climax and resolution
   - AND SceneType = 'Action'              -- Only action scenes
*/


-- ============================================================================
-- EXERCISE 2: Duel Sequence Overview
-- ============================================================================

-- Scene summary
SELECT
    'Scenes' AS Metric,
    COUNT(*) AS Value
FROM learn_scenes
WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44
UNION ALL
SELECT
    'Duration (sec)',
    SUM(DurationSec)
FROM learn_scenes
WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44
UNION ALL
SELECT
    'Events',
    COUNT(*)
FROM learn_events
WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44;
-- Comment: The Duel of the Fates is one of the longest sequences in the prequels.

/* SINGLE QUERY VERSION:
SELECT
    (SELECT COUNT(*) FROM learn_scenes WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44) AS Scenes,
    (SELECT SUM(DurationSec) FROM learn_scenes WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44) AS DurationSec,
    (SELECT COUNT(*) FROM learn_events WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44) AS Events;
*/


-- ============================================================================
-- EXERCISE 3: The Three Duelists
-- ============================================================================

SELECT
    ParticipantName,
    COUNT(*) AS EventAppearances,
    COUNT(DISTINCT SceneName) AS SceneAppearances,
    SUM(CASE WHEN Role = 'Actor' THEN 1 ELSE 0 END) AS AsActor,
    SUM(CASE WHEN Role = 'Target' THEN 1 ELSE 0 END) AS AsTarget
FROM learn_event_participants
WHERE WorkCode = 'TPM'
  AND SceneName IN (
      SELECT SceneName FROM learn_scenes 
      WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44
  )
  AND (
      ParticipantName LIKE '%Qui-Gon%'
      OR ParticipantName LIKE '%Obi%Wan%'
      OR ParticipantName LIKE '%Maul%'
  )
GROUP BY ParticipantName
ORDER BY EventAppearances DESC;
-- Comment: Tracks how each duelist participates across the sequence.
--          Actor = attacking; Target = being attacked.

/* VARIATIONS:
   - AND Importance = 'Primary'            -- Primary roles only
   - Add: AVG(ParticipationScore)          -- Average importance
*/


-- ============================================================================
-- EXERCISE 4: Scene-by-Scene Breakdown
-- ============================================================================

SELECT
    s.SceneNumber,
    s.SceneName,
    s.DurationSec,
    COALESCE(e.EventCount, 0) AS EventCount,
    CASE 
        WHEN s.DurationSec > 0 THEN CAST(COALESCE(e.EventCount, 0) AS FLOAT) / (s.DurationSec / 60.0)
        ELSE NULL 
    END AS EventsPerMinute
FROM learn_scenes s
LEFT JOIN (
    SELECT SceneKey, COUNT(*) AS EventCount
    FROM learn_events
    WHERE WorkCode = 'TPM' AND SceneNumber BETWEEN 27 AND 44
    GROUP BY SceneKey
) e ON s.SceneKey = e.SceneKey
WHERE s.WorkCode = 'TPM'
  AND s.SceneNumber BETWEEN 27 AND 44
ORDER BY s.SceneNumber;
-- Comment: Shows event density per scene - high density = intense action.

/* VARIATIONS:
   - HAVING EventCount >= 3                -- Only event-dense scenes
   - Add: SceneType for categorization
*/


-- ============================================================================
-- EXERCISE 5: Combat Events
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    EventNumber,
    EventSummary,
    EventType,
    ConfidenceScore
FROM learn_events
WHERE WorkCode = 'TPM'
  AND SceneNumber BETWEEN 27 AND 44
  AND (EventType LIKE '%Combat%' OR EventType LIKE '%Attack%' OR EventType LIKE '%Duel%')
ORDER BY SceneNumber, EventNumber;
-- Comment: Combat events show the physical action of the lightsaber duel.

/* VARIATIONS:
   - OR EventType LIKE '%Force%'           -- Include Force uses
   - AND ConfidenceScore >= 0.80           -- High confidence only
*/


-- ============================================================================
-- EXERCISE 6: The Laser Gate Separation
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    SceneType,
    DurationSec,
    LocationHint
FROM learn_scenes
WHERE WorkCode = 'TPM'
  AND (
      SceneName LIKE '%Barrier%'
      OR SceneName LIKE '%Gate%'
      OR SceneName LIKE '%Separated%'
      OR SceneName LIKE '%Laser%'
      OR SceneNumber BETWEEN 32 AND 35
  )
ORDER BY SceneNumber;
-- Comment: The laser gates create the dramatic separation that leads to tragedy.
--          Obi-Wan is blocked while Qui-Gon fights Maul alone.

/* VARIATIONS:
   - SceneNumber = 33                      -- "Separated by Barriers" specifically
   - SceneNumber = 34                      -- "Qui-Gon Meditates"
*/


-- ============================================================================
-- EXERCISE 7: Qui-Gon's Last Stand
-- ============================================================================

SELECT
    SceneName,
    EventNumber,
    EventSummary,
    EventType
FROM learn_events
WHERE WorkCode = 'TPM'
  AND SceneNumber IN (36, 37)              -- Qui-Gon vs Maul, Qui-Gon Struck Down
ORDER BY SceneNumber, EventNumber;
-- Comment: These are the tragic scenes where Qui-Gon falls to Maul.
--          The melting pit chamber is the final battleground for Qui-Gon.

/* VARIATIONS:
   - JOIN with participants to see Qui-Gon's actions
   - AND EventType LIKE '%Injury%'         -- The fatal blow
*/


-- ============================================================================
-- EXERCISE 8: Obi-Wan's Revenge
-- ============================================================================

SELECT
    e.SceneNumber,
    e.SceneName,
    e.EventNumber,
    e.EventSummary,
    e.EventType,
    p.ParticipantName,
    p.Role
FROM learn_events e
LEFT JOIN learn_event_participants p
    ON e.EventKey = p.EventKey
    AND p.ParticipantName LIKE '%Obi%'
WHERE e.WorkCode = 'TPM'
  AND e.SceneNumber BETWEEN 39 AND 43
ORDER BY e.SceneNumber, e.EventNumber;
-- Comment: Obi-Wan's furious attack after witnessing Qui-Gon's death.
--          From initial attack through his disarming and final victory.

/* VARIATIONS:
   - AND p.Role = 'Actor'                  -- Only Obi-Wan's actions
   - Add Maul's participation              -- Both duelists
*/


-- ============================================================================
-- EXERCISE 9: Key Moments Timeline
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    CASE
        WHEN SceneName LIKE '%Doors%' OR SceneName LIKE '%Revealed%' THEN 'ACT 1: Maul Appears'
        WHEN SceneName LIKE '%Initial%' OR SceneName LIKE '%Three-Way%' THEN 'ACT 1: Initial Combat'
        WHEN SceneName LIKE '%Barrier%' OR SceneName LIKE '%Separated%' THEN 'ACT 2: Separation'
        WHEN SceneName LIKE '%Qui-Gon%Maul%' THEN 'ACT 2: Qui-Gon Alone'
        WHEN SceneName LIKE '%Struck%' THEN 'TURNING POINT: Qui-Gon Falls'
        WHEN SceneName LIKE '%Obi-Wan%Attack%' THEN 'ACT 3: Obi-Wan Attacks'
        WHEN SceneName LIKE '%Disarmed%' OR SceneName LIKE '%Hanging%' THEN 'ACT 3: Obi-Wan in Peril'
        WHEN SceneName LIKE '%Maul%Severed%' OR SceneName LIKE '%Falls%' THEN 'CLIMAX: Maul Defeated'
        WHEN SceneName LIKE '%Last Words%' THEN 'RESOLUTION: Qui-Gon Dies'
        ELSE 'Other'
    END AS NarrativeBeat,
    DurationSec
FROM learn_scenes
WHERE WorkCode = 'TPM'
  AND SceneNumber BETWEEN 27 AND 44
ORDER BY SceneNumber;
-- Comment: Maps scenes to classical narrative structure.
--          The duel follows a three-act structure with clear turning points.

/* VARIATIONS:
   - GROUP BY NarrativeBeat                -- Summarize by act
   - Add: SUM(DurationSec)                 -- Duration per act
*/


-- ============================================================================
-- EXERCISE 10: Complete Duel Narrative
-- ============================================================================

-- NOTE: STRING_AGG requires SQL Server 2017 or later.
--       See alternative query below for older SQL Server versions.

SELECT
    s.SceneNumber,
    s.SceneName,
    e.EventNumber,
    e.EventSummary,
    e.EventType,
    STRING_AGG(
        CASE WHEN p.Importance = 'Primary' THEN p.ParticipantName ELSE NULL END,
        ', '
    ) WITHIN GROUP (ORDER BY p.ParticipantOrdinal) AS PrimaryParticipants
FROM learn_scenes s
INNER JOIN learn_events e ON s.SceneKey = e.SceneKey
LEFT JOIN learn_event_participants p ON e.EventKey = p.EventKey
WHERE s.WorkCode = 'TPM'
  AND s.SceneNumber BETWEEN 27 AND 44
GROUP BY s.SceneNumber, s.SceneName, e.EventNumber, e.EventSummary, e.EventType, e.EventKey
ORDER BY s.SceneNumber, e.EventNumber;
-- Comment: Complete narrative flow with participants.
--          This creates a readable story of the duel.

/* ALTERNATIVE without STRING_AGG:
SELECT
    s.SceneNumber,
    s.SceneName,
    e.EventNumber,
    e.EventSummary,
    e.EventType,
    p.ParticipantName,
    p.Role
FROM learn_scenes s
INNER JOIN learn_events e ON s.SceneKey = e.SceneKey
LEFT JOIN learn_event_participants p 
    ON e.EventKey = p.EventKey
    AND p.Importance = 'Primary'
WHERE s.WorkCode = 'TPM'
  AND s.SceneNumber BETWEEN 27 AND 44
ORDER BY s.SceneNumber, e.EventNumber, p.ParticipantOrdinal;
*/

/* VARIATIONS:
   - WHERE p.ParticipantName LIKE '%Qui%' OR p.ParticipantName LIKE '%Obi%' OR p.ParticipantName LIKE '%Maul%'
   - Add: e.ConfidenceScore for data quality
   - HAVING COUNT(p.ParticipantName) >= 2  -- Multi-participant events
*/
