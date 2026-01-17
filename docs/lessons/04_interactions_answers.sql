/******************************************************************************
 * MODULE 04: Who Met Whom (Interactions) - ANSWER KEY
 * 
 * This file contains solutions for the interaction analysis exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Participant Summary
-- ============================================================================

SELECT TOP 20
    ParticipantName,
    ParticipantType,
    COUNT(*) AS EventCount
FROM learn_event_participants
GROUP BY ParticipantName, ParticipantType
ORDER BY EventCount DESC;
-- Comment: Shows who is most active across all events.
--          Main characters will have highest counts.

/* VARIATIONS:
   - WHERE ParticipantType = 'Character'   -- Characters only
   - WHERE Importance = 'Primary'          -- Only primary appearances
   - HAVING COUNT(*) > 10                  -- Active participants only
*/


-- ============================================================================
-- EXERCISE 2: Role Distribution
-- ============================================================================

SELECT
    ParticipantName,
    Role,
    COUNT(*) AS RoleCount
FROM learn_event_participants
GROUP BY ParticipantName, Role
ORDER BY ParticipantName, RoleCount DESC;
-- Comment: Shows how characters participate in different roles.
--          Heroes might be Actors; villains might be Targets sometimes.

/* VARIATIONS:
   - WHERE ParticipantName LIKE '%Luke%'   -- Focus on one character
   - HAVING COUNT(*) >= 5                  -- Only significant role counts
   - Add: Importance to GROUP BY           -- More detail
*/


-- ============================================================================
-- EXERCISE 3: Event Participation Density
-- ============================================================================

SELECT TOP 10
    EventSummary,
    WorkTitle,
    SceneName,
    COUNT(DISTINCT ParticipantName) AS ParticipantCount
FROM learn_event_participants
GROUP BY EventSummary, WorkTitle, SceneName
ORDER BY ParticipantCount DESC;
-- Comment: Multi-character events are often pivotal moments.
--          Battles and confrontations tend to have many participants.

/* VARIATIONS:
   - WHERE WorkCode = 'ANH'                -- Specific work
   - HAVING COUNT(DISTINCT ParticipantName) >= 4  -- Large gatherings only
   - Add: MIN(Importance) to see mix of primary/secondary
*/


-- ============================================================================
-- EXERCISE 4: Primary Actors
-- ============================================================================

SELECT
    ParticipantName,
    COUNT(*) AS PrimaryActorCount
FROM learn_event_participants
WHERE Importance = 'Primary'
  AND Role = 'Actor'
GROUP BY ParticipantName
ORDER BY PrimaryActorCount DESC;
-- Comment: Primary Actors are the main drivers of events.
--          These are the protagonists and antagonists taking action.

/* VARIATIONS:
   - WHERE Role = 'Target' AND Importance = 'Primary'  -- Primary targets
   - AND WorkCode = 'ANH'                  -- Specific work
   - HAVING COUNT(*) >= 10                 -- Very active actors
*/


-- ============================================================================
-- EXERCISE 5: Scene Co-occurrence
-- ============================================================================

SELECT
    WorkTitle,
    SceneName,
    COUNT(DISTINCT ParticipantName) AS ParticipantCount
FROM learn_event_participants
GROUP BY WorkTitle, SceneName
HAVING COUNT(DISTINCT ParticipantName) >= 3
ORDER BY ParticipantCount DESC, WorkTitle, SceneName;
-- Comment: Scenes with many participants are ensemble moments.
--          Group confrontations, battles, or council meetings.

/* VARIATIONS:
   - HAVING COUNT(DISTINCT ParticipantName) >= 5  -- Larger gatherings
   - WHERE WorkCode = 'ANH'                -- Specific work
   - Add: STRING_AGG(ParticipantName, ', ') to list participants (SQL Server 2017+)
*/


-- ============================================================================
-- EXERCISE 6: Villain Activity
-- ============================================================================

SELECT
    ParticipantName,
    COUNT(*) AS EventCount,
    COUNT(DISTINCT WorkTitle) AS WorkCount
FROM learn_event_participants
WHERE ParticipantName LIKE '%Vader%'
   OR ParticipantName LIKE '%Palpatine%'
   OR ParticipantName LIKE '%Maul%'        -- Include Darth Maul
GROUP BY ParticipantName
ORDER BY EventCount DESC;
-- Comment: Tracking villain activity across the saga.

/* VARIATIONS:
   - OR ParticipantName LIKE '%Sith%'      -- Any Sith
   - OR ParticipantName LIKE '%Empire%'    -- Empire as organization
   - AND Role = 'Actor'                    -- Only when acting
*/


-- ============================================================================
-- EXERCISE 7: Target Analysis
-- ============================================================================

SELECT
    ParticipantName,
    ParticipantType,
    COUNT(*) AS TargetCount
FROM learn_event_participants
WHERE Role = 'Target'
GROUP BY ParticipantName, ParticipantType
ORDER BY TargetCount DESC;
-- Comment: Characters frequently targeted may be in danger
--          or central to conflict.

/* VARIATIONS:
   - WHERE Importance = 'Primary'          -- Major targeting events
   - AND WorkCode = 'ANH'                  -- Specific work
   - HAVING COUNT(*) >= 3                  -- Frequently targeted
*/


-- ============================================================================
-- EXERCISE 8: Cross-Work Appearances
-- ============================================================================

SELECT
    ParticipantName,
    COUNT(DISTINCT WorkTitle) AS WorkCount,
    COUNT(*) AS TotalAppearances
FROM learn_event_participants
GROUP BY ParticipantName
HAVING COUNT(DISTINCT WorkTitle) >= 2
ORDER BY WorkCount DESC, TotalAppearances DESC;
-- Comment: Characters appearing in multiple works are saga regulars.
--          These are the recurring characters across the franchise.

/* VARIATIONS:
   - HAVING COUNT(DISTINCT WorkTitle) >= 3  -- Very recurring characters
   - WHERE ParticipantType = 'Character'   -- Characters only
   - Add: STRING_AGG(DISTINCT WorkCode, ', ') to list works (SQL Server 2017+)
*/


-- ============================================================================
-- EXERCISE 9: Scene Dominance
-- ============================================================================

SELECT
    ParticipantName,
    COUNT(DISTINCT SceneName) AS SceneCount,
    COUNT(*) AS EventCount
FROM learn_event_participants
GROUP BY ParticipantName
ORDER BY SceneCount DESC;
-- Comment: Scene count shows breadth of presence;
--          event count shows depth of involvement.

/* VARIATIONS:
   - WHERE WorkCode = 'ANH'                -- One work only
   - HAVING COUNT(DISTINCT SceneName) >= 10  -- Major presence
   - Add ratio: CAST(EventCount AS FLOAT) / SceneCount AS EventsPerScene
*/


-- ============================================================================
-- EXERCISE 10: Interaction Partners
-- ============================================================================

-- Find everyone who appeared in events with Luke Skywalker
SELECT DISTINCT
    p2.ParticipantName,
    p2.ParticipantType,
    COUNT(*) AS SharedEventCount
FROM learn_event_participants p2
WHERE p2.EventId IN (
    -- Subquery: Find events where Luke appears
    SELECT p1.EventId
    FROM learn_event_participants p1
    WHERE p1.ParticipantName LIKE '%Luke%Skywalker%'
)
  AND p2.ParticipantName NOT LIKE '%Luke%Skywalker%'  -- Exclude Luke himself
GROUP BY p2.ParticipantName, p2.ParticipantType
ORDER BY SharedEventCount DESC;
-- Comment: This finds Luke's "interaction partners" - characters
--          who were present in the same events.

/* VARIATIONS:
   - Change 'Luke%Skywalker' to '%Vader%'  -- Vader's partners
   - Change 'Luke%Skywalker' to '%Obi%Wan%'  -- Obi-Wan's partners
   - Add: AND p2.Importance = 'Primary'    -- Only major co-participants
   - HAVING COUNT(*) >= 3                  -- Frequent partners only
*/
