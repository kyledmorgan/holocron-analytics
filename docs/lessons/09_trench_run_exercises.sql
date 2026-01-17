/******************************************************************************
 * MODULE 09: Trench Run Deep Dive (Episode IV)
 * 
 * OBJECTIVE: Analyze the iconic Death Star trench run sequence in detail.
 *            Focus on timeline, participants, assets, and sequence ordering.
 * 
 * SKILLS PRACTICED:
 *   - Filtered timeline analysis
 *   - Sequence ordering
 *   - Multi-table correlation
 *   - Narrative-driven queries
 * 
 * TABLES USED: learn_events, learn_event_participants, learn_scenes
 * 
 * SCOPE: A New Hope (ANH), Scenes 44-54 (Gold Squadron through Destruction)
 * 
 * DIFFICULTY: Advanced
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Identify the Trench Run Scenes
-- ============================================================================
-- GOAL: List all scenes that make up the trench run sequence.
--       Show scene numbers, names, and durations.
-- 
-- HINTS:
--   - Filter to WorkCode = 'ANH' and SceneNumber 44-54
--   - Order by scene number for chronological sequence
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Total Sequence Duration
-- ============================================================================
-- GOAL: Calculate the total duration of the trench run sequence.
-- 
-- HINTS:
--   - SUM the DurationSec for the relevant scenes
--   - Convert to minutes for readability
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Events in the Trench Run
-- ============================================================================
-- GOAL: List all events in the trench run sequence, ordered chronologically.
-- 
-- HINTS:
--   - Filter by WorkCode = 'ANH' and SceneNumber range
--   - Order by SceneNumber, then EventNumber
--   - This shows the beat-by-beat sequence
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Trench Run Participants
-- ============================================================================
-- GOAL: Find all participants in trench run events.
--       Who is involved in this sequence?
-- 
-- HINTS:
--   - Filter learn_event_participants by work and scene range
--   - Use DISTINCT to avoid repeating names
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Primary Actors in the Run
-- ============================================================================
-- GOAL: Find who are the Primary importance participants during the trench run.
--       Count their event appearances.
-- 
-- HINTS:
--   - Filter on Importance = 'Primary'
--   - GROUP BY ParticipantName
--   - These are the key figures in the sequence
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Event Types in Battle
-- ============================================================================
-- GOAL: Count events by EventType during the trench run.
--       What kinds of events dominate this sequence?
-- 
-- HINTS:
--   - GROUP BY EventType
--   - Filter to the trench run scenes
--   - Combat and Movement events likely dominate
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Scene-by-Scene Event Counts
-- ============================================================================
-- GOAL: For each trench run scene, count the events.
--       Which scenes are most event-dense?
-- 
-- HINTS:
--   - GROUP BY SceneName (and SceneNumber for ordering)
--   - Order by scene number to show sequence flow
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Vader's Pursuit
-- ============================================================================
-- GOAL: Find all events where Vader participates during the trench run.
--       Track his role and the outcomes.
-- 
-- HINTS:
--   - Filter participants by name containing 'Vader'
--   - Join or correlate with events for context
--   - Show the sequence of Vader's actions
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Luke's Final Run
-- ============================================================================
-- GOAL: Find events specifically from "Luke's Final Run" scene.
--       Show the moment-by-moment sequence.
-- 
-- HINTS:
--   - Filter to the specific scene name or number (49)
--   - Order by EventNumber
--   - This is the climactic torpedo shot scene
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Trench Run Narrative Summary
-- ============================================================================
-- GOAL: Create a timeline showing:
--       - Scene name
--       - Event summary
--       - Primary participants
--       - Order within the sequence
-- 
-- HINTS:
--   - Join events with participants
--   - Filter for Primary importance
--   - Create a readable narrative flow
-- 
-- TABLES: learn_events, learn_event_participants

-- Write your query below:



