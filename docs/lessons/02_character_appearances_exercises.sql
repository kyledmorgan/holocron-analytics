/******************************************************************************
 * MODULE 02: Character Appearances
 * 
 * OBJECTIVE: Learn where and when characters appear across works and scenes.
 * 
 * SKILLS PRACTICED:
 *   - JOINs (introduction)
 *   - Filtering across multiple tables
 *   - Ordering by multiple columns
 *   - Working with timeline data
 * 
 * TABLES USED: learn_characters, learn_scenes, learn_event_participants
 * 
 * DIFFICULTY: Beginner-Intermediate (introduces joins)
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Preview Participant Data
-- ============================================================================
-- GOAL: Explore the event participants table to see who appears in events.
-- 
-- HINTS:
--   - Start with SELECT TOP 10 *
--   - Notice the ParticipantName, Role, and Event columns
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Find Luke's Appearances
-- ============================================================================
-- GOAL: List all events where Luke Skywalker participates.
--       Show the work, scene, and his role in each event.
-- 
-- HINTS:
--   - Filter on ParticipantName
--   - Use LIKE if you're not sure of exact name format
--   - Order by WorkTitle and EventNumber
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Appearances by Work
-- ============================================================================
-- GOAL: Count how many event participations exist for each work.
-- 
-- HINTS:
--   - Use GROUP BY to aggregate
--   - Use COUNT(*) to count rows
--   - Order by count descending
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Primary Participants Only
-- ============================================================================
-- GOAL: List all 'Primary' importance participants from 'A New Hope'.
-- 
-- HINTS:
--   - Filter on Importance = 'Primary'
--   - Filter on WorkTitle (use LIKE for flexibility)
--   - Show distinct participant names
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Scene Timeline
-- ============================================================================
-- GOAL: List all scenes from 'A New Hope' in chronological order.
--       Show scene number, name, type, and duration.
-- 
-- HINTS:
--   - Use the learn_scenes table
--   - Filter by WorkCode or WorkTitle
--   - Order by SceneNumber
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Action Scenes
-- ============================================================================
-- GOAL: Find all 'Action' type scenes across all works.
--       Show work title, scene name, and duration.
-- 
-- HINTS:
--   - Filter on SceneType
--   - Order by WorkTitle, then SceneNumber
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Longest Scenes
-- ============================================================================
-- GOAL: Find the 10 longest scenes (by DurationSec) across all works.
-- 
-- HINTS:
--   - Use TOP 10
--   - Order by DurationSec DESC
--   - Handle NULL durations
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Roles in Events
-- ============================================================================
-- GOAL: Find all distinct roles that participants can have in events.
-- 
-- HINTS:
--   - Use DISTINCT on the Role column
--   - Think about what each role means (Actor, Target, Observer, etc.)
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Darth Vader's Confrontations
-- ============================================================================
-- GOAL: List all events where Darth Vader participates as an 'Actor'.
--       Show the scene name, event summary, and work title.
-- 
-- HINTS:
--   - Filter on ParticipantName containing 'Vader'
--   - Filter on Role = 'Actor'
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Multi-Participant Events
-- ============================================================================
-- GOAL: Count how many participants are in each event.
--       Show events with 3 or more participants.
-- 
-- HINTS:
--   - GROUP BY EventId (or EventSummary)
--   - Use HAVING to filter after grouping
--   - COUNT(*) for participant count
-- 
-- TABLES: learn_event_participants

-- Write your query below:



