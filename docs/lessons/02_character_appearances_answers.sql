/******************************************************************************
 * MODULE 02: Character Appearances - ANSWER KEY
 * 
 * This file contains solutions for the character appearances exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Preview Participant Data
-- ============================================================================

SELECT TOP 10 *
FROM learn_event_participants
ORDER BY WorkTitle, SceneName, EventNumber;
-- Comment: This table links participants to events with role information.
--          Each row is one participant's involvement in one event.

/* VARIATIONS:
   - ORDER BY ParticipantName           -- Group by character
   - WHERE Importance = 'Primary'       -- Only main participants
*/


-- ============================================================================
-- EXERCISE 2: Find Luke's Appearances
-- ============================================================================

SELECT
    WorkTitle,
    SceneName,
    EventSummary,
    Role,
    Importance
FROM learn_event_participants
WHERE ParticipantName LIKE '%Luke%Skywalker%'  -- Flexible pattern matching
ORDER BY WorkTitle, EventNumber;
-- Comment: Using LIKE handles variations in name formatting.

/* VARIATIONS:
   - WHERE ParticipantName = 'Luke Skywalker'  -- Exact match
   - AND Role = 'Actor'                        -- Only where Luke acts
   - AND Importance = 'Primary'                -- Only major appearances
*/


-- ============================================================================
-- EXERCISE 3: Appearances by Work
-- ============================================================================

SELECT
    WorkTitle,
    COUNT(*) AS ParticipationCount           -- Count all participations
FROM learn_event_participants
GROUP BY WorkTitle                           -- Group by work
ORDER BY ParticipationCount DESC;            -- Most participations first
-- Comment: GROUP BY aggregates rows; COUNT(*) counts rows in each group.

/* VARIATIONS:
   - GROUP BY WorkCode                        -- Use code instead of title
   - HAVING COUNT(*) > 50                     -- Only works with many events
   - Add: WorkCode in SELECT and GROUP BY
*/


-- ============================================================================
-- EXERCISE 4: Primary Participants Only
-- ============================================================================

SELECT DISTINCT
    ParticipantName,
    ParticipantType
FROM learn_event_participants
WHERE Importance = 'Primary'
  AND WorkTitle LIKE '%New Hope%'            -- Flexible title match
ORDER BY ParticipantName;
-- Comment: DISTINCT removes duplicates so each character appears once.

/* VARIATIONS:
   - WHERE WorkCode = 'ANH'                  -- Exact work code match
   - AND ParticipantType = 'Character'       -- Only characters, not orgs
   - Remove DISTINCT to see every appearance
*/


-- ============================================================================
-- EXERCISE 5: Scene Timeline
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    SceneType,
    DurationSec,
    StartSec,
    EndSec
FROM learn_scenes
WHERE WorkCode = 'ANH'                       -- A New Hope work code
ORDER BY SceneNumber;
-- Comment: SceneNumber gives the chronological order within a work.

/* VARIATIONS:
   - WHERE WorkTitle LIKE '%New Hope%'       -- Title match instead
   - WHERE WorkCode = 'TPM'                  -- Try: The Phantom Menace
   - AND SceneType = 'Action'                -- Only action scenes
*/


-- ============================================================================
-- EXERCISE 6: Action Scenes
-- ============================================================================

SELECT
    WorkTitle,
    SceneName,
    SceneNumber,
    DurationSec,
    LocationHint
FROM learn_scenes
WHERE SceneType = 'Action'
ORDER BY WorkTitle, SceneNumber;
-- Comment: SceneType categorizes scenes by their primary purpose.

/* VARIATIONS:
   - WHERE SceneType IN ('Action', 'Opening')  -- Multiple types
   - AND DurationSec > 200                     -- Long action scenes only
   - WHERE SceneType = 'Ending'                -- Try: ending scenes
*/


-- ============================================================================
-- EXERCISE 7: Longest Scenes
-- ============================================================================

SELECT TOP 10
    WorkTitle,
    SceneName,
    SceneType,
    DurationSec,
    LocationHint
FROM learn_scenes
WHERE DurationSec IS NOT NULL                -- Exclude scenes without duration
ORDER BY DurationSec DESC;
-- Comment: TOP with ORDER BY DESC gives highest values first.

/* VARIATIONS:
   - TOP 20                                  -- More results
   - ORDER BY DurationSec ASC                -- Shortest scenes instead
   - AND SceneType = 'Action'                -- Longest action scenes
*/


-- ============================================================================
-- EXERCISE 8: Roles in Events
-- ============================================================================

SELECT DISTINCT Role                         -- Unique role values
FROM learn_event_participants
WHERE Role IS NOT NULL
ORDER BY Role;
-- Comment: Common roles include Actor (does something), Target (affected by action),
--          Observer (witnesses), etc.

/* VARIATIONS:
   - SELECT DISTINCT Importance              -- Try: importance levels
   - SELECT DISTINCT ParticipantType         -- Try: participant types
   - Add: COUNT(*) with GROUP BY Role        -- Count by role
*/


-- ============================================================================
-- EXERCISE 9: Darth Vader's Confrontations
-- ============================================================================

SELECT
    SceneName,
    EventSummary,
    WorkTitle,
    Role,
    Importance
FROM learn_event_participants
WHERE ParticipantName LIKE '%Vader%'         -- Matches 'Darth Vader'
  AND Role = 'Actor'                         -- Vader is the actor
ORDER BY WorkTitle, EventNumber;
-- Comment: Actor role means Vader is doing something in the event.

/* VARIATIONS:
   - AND Role = 'Target'                     -- Where Vader is the target
   - OR Role = 'Target'                      -- Either actor or target
   - AND Importance = 'Primary'              -- Only major confrontations
   - WHERE ParticipantName LIKE '%Obi%'      -- Try: Obi-Wan instead
*/


-- ============================================================================
-- EXERCISE 10: Multi-Participant Events
-- ============================================================================

SELECT
    EventSummary,
    WorkTitle,
    SceneName,
    COUNT(*) AS ParticipantCount             -- Count participants
FROM learn_event_participants
GROUP BY EventSummary, WorkTitle, SceneName  -- Group by event
HAVING COUNT(*) >= 3                         -- Filter to 3+ participants
ORDER BY ParticipantCount DESC, EventSummary;
-- Comment: HAVING filters after GROUP BY; WHERE filters before GROUP BY.

/* VARIATIONS:
   - HAVING COUNT(*) >= 5                    -- Larger group events
   - AND WorkCode = 'ANH'                    -- Specific work only
   - GROUP BY EventId                        -- More precise grouping
*/
