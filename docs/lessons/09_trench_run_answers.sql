/******************************************************************************
 * MODULE 09: Trench Run Deep Dive - ANSWER KEY
 * 
 * This file contains solutions for the Trench Run analysis exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Identify the Trench Run Scenes
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
WHERE WorkCode = 'ANH'
  AND SceneNumber BETWEEN 44 AND 54
ORDER BY SceneNumber;
-- Comment: These 11 scenes cover the entire Battle of Yavin trench run.
--          From Gold Squadron's run through the Death Star destruction.

/* VARIATIONS:
   - BETWEEN 44 AND 49                     -- Up to Luke's final run
   - BETWEEN 50 AND 54                     -- The climax only
   - AND SceneType = 'Action'              -- Only action scenes
*/


-- ============================================================================
-- EXERCISE 2: Total Sequence Duration
-- ============================================================================

SELECT
    COUNT(*) AS SceneCount,
    SUM(DurationSec) AS TotalSeconds,
    SUM(DurationSec) / 60.0 AS TotalMinutes,
    MIN(StartSec) AS SequenceStartSec,
    MAX(EndSec) AS SequenceEndSec
FROM learn_scenes
WHERE WorkCode = 'ANH'
  AND SceneNumber BETWEEN 44 AND 54;
-- Comment: The trench run is one of the longest sustained action sequences.

/* VARIATIONS:
   - Add: AVG(DurationSec) AS AvgSceneDuration
   - Compare to total film: / (SELECT SUM(DurationSec) FROM learn_scenes WHERE WorkCode='ANH') * 100
*/


-- ============================================================================
-- EXERCISE 3: Events in the Trench Run
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    EventNumber,
    EventSummary,
    EventType,
    ConfidenceScore
FROM learn_events
WHERE WorkCode = 'ANH'
  AND SceneNumber BETWEEN 44 AND 54
ORDER BY SceneNumber, EventNumber;
-- Comment: This shows the beat-by-beat action of the sequence.
--          Each event is a discrete action or moment.

/* VARIATIONS:
   - AND EventType = 'Combat'              -- Combat events only
   - AND ConfidenceScore >= 0.80           -- High confidence events
   - TOP 30 for a sample
*/


-- ============================================================================
-- EXERCISE 4: Trench Run Participants
-- ============================================================================

SELECT DISTINCT
    ParticipantName,
    ParticipantType
FROM learn_event_participants
WHERE WorkCode = 'ANH'
  AND SceneName IN (
      SELECT SceneName FROM learn_scenes 
      WHERE WorkCode = 'ANH' AND SceneNumber BETWEEN 44 AND 54
  )
ORDER BY ParticipantType, ParticipantName;
-- Comment: Shows everyone involved in the battle: pilots, Vader, etc.

/* VARIATIONS:
   - WHERE ParticipantType = 'Character'   -- Characters only
   - Add: COUNT(*) with GROUP BY           -- Participation count
   - WHERE Importance = 'Primary'          -- Key participants only
*/


-- ============================================================================
-- EXERCISE 5: Primary Actors in the Run
-- ============================================================================

SELECT
    ParticipantName,
    COUNT(*) AS EventAppearances,
    COUNT(DISTINCT SceneName) AS SceneAppearances
FROM learn_event_participants
WHERE WorkCode = 'ANH'
  AND SceneName IN (
      SELECT SceneName FROM learn_scenes 
      WHERE WorkCode = 'ANH' AND SceneNumber BETWEEN 44 AND 54
  )
  AND Importance = 'Primary'
GROUP BY ParticipantName
ORDER BY EventAppearances DESC;
-- Comment: Luke, Vader, and key pilots dominate the primary roles.

/* VARIATIONS:
   - AND Role = 'Actor'                    -- Only when acting
   - HAVING COUNT(*) >= 5                  -- Very active participants
*/


-- ============================================================================
-- EXERCISE 6: Event Types in Battle
-- ============================================================================

SELECT
    EventType,
    COUNT(*) AS EventCount,
    AVG(ConfidenceScore) AS AvgConfidence
FROM learn_events
WHERE WorkCode = 'ANH'
  AND SceneNumber BETWEEN 44 AND 54
GROUP BY EventType
ORDER BY EventCount DESC;
-- Comment: Combat and Movement events dominate the battle sequence.

/* VARIATIONS:
   - Add: EventTypeCode for short codes
   - WHERE EventType LIKE '%Attack%'       -- Attack events specifically
*/


-- ============================================================================
-- EXERCISE 7: Scene-by-Scene Event Counts
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    COUNT(*) AS EventCount
FROM learn_events
WHERE WorkCode = 'ANH'
  AND SceneNumber BETWEEN 44 AND 54
GROUP BY SceneNumber, SceneName
ORDER BY SceneNumber;
-- Comment: Event density shows which scenes have the most action beats.
--          The final run scenes are typically most dense.

/* VARIATIONS:
   - Join with learn_scenes for duration    -- Events per minute
   - HAVING COUNT(*) >= 5                  -- Only dense scenes
*/


-- ============================================================================
-- EXERCISE 8: Vader's Pursuit
-- ============================================================================

SELECT
    SceneName,
    EventSummary,
    Role,
    Importance,
    EventNumber
FROM learn_event_participants ep
WHERE ep.WorkCode = 'ANH'
  AND ep.ParticipantName LIKE '%Vader%'
  AND ep.SceneName IN (
      SELECT SceneName FROM learn_scenes 
      WHERE WorkCode = 'ANH' AND SceneNumber BETWEEN 44 AND 54
  )
ORDER BY 
    (SELECT SceneNumber FROM learn_scenes s WHERE s.SceneName = ep.SceneName AND s.WorkCode = 'ANH'),
    ep.EventNumber;
-- Comment: Tracks Vader's actions through the battle: entering battle,
--          pursuing pilots, targeting Luke.

/* VARIATIONS:
   - AND Role = 'Actor'                    -- Only Vader's actions
   - OR ParticipantName LIKE '%Wingman%'   -- Include Vader's wingmen
*/


-- ============================================================================
-- EXERCISE 9: Luke's Final Run
-- ============================================================================

SELECT
    EventNumber,
    EventSummary,
    EventType,
    ConfidenceScore
FROM learn_events
WHERE WorkCode = 'ANH'
  AND SceneNumber = 49                     -- Luke's Final Run scene
ORDER BY EventNumber;
-- Comment: This is the climactic sequence: Vader pursuing, Han returning,
--          the Force guiding Luke, the torpedo shot.

/* VARIATIONS:
   - SceneNumber = 50                      -- "Use the Force" scene
   - SceneNumber = 53                      -- "Proton Torpedo Shot"
   - SceneNumber = 54                      -- "Death Star Destruction"
*/


-- ============================================================================
-- EXERCISE 10: Trench Run Narrative Summary
-- ============================================================================

-- NOTE: STRING_AGG requires SQL Server 2017 or later.
--       See alternative query below for older SQL Server versions.

SELECT
    e.SceneNumber,
    e.SceneName,
    e.EventNumber,
    e.EventSummary,
    e.EventType,
    STRING_AGG(
        CASE WHEN p.Importance = 'Primary' THEN p.ParticipantName ELSE NULL END, 
        ', '
    ) WITHIN GROUP (ORDER BY p.ParticipantOrdinal) AS PrimaryParticipants
FROM learn_events e
LEFT JOIN learn_event_participants p
    ON e.EventKey = p.EventKey
WHERE e.WorkCode = 'ANH'
  AND e.SceneNumber BETWEEN 44 AND 54
GROUP BY e.SceneNumber, e.SceneName, e.EventNumber, e.EventSummary, e.EventType, e.EventKey
ORDER BY e.SceneNumber, e.EventNumber;
-- Comment: Creates a readable narrative timeline with key participants.
--          STRING_AGG combines participant names into a list.

/* ALTERNATIVE without STRING_AGG (older SQL Server):
SELECT
    e.SceneNumber,
    e.SceneName,
    e.EventNumber,
    e.EventSummary,
    e.EventType,
    p.ParticipantName,
    p.Importance
FROM learn_events e
LEFT JOIN learn_event_participants p
    ON e.EventKey = p.EventKey
    AND p.Importance = 'Primary'
WHERE e.WorkCode = 'ANH'
  AND e.SceneNumber BETWEEN 44 AND 54
ORDER BY e.SceneNumber, e.EventNumber, p.ParticipantOrdinal;
*/

/* VARIATIONS:
   - HAVING COUNT(p.ParticipantName) >= 2  -- Multi-participant events
   - Add: e.ConfidenceScore for data quality
*/
