/******************************************************************************
 * MODULE 10: Duel of the Fates Deep Dive (Episode I)
 * 
 * OBJECTIVE: Analyze the iconic lightsaber duel sequence in The Phantom Menace.
 *            From door reveal to Maul's defeat - the complete duel narrative.
 * 
 * SKILLS PRACTICED:
 *   - Sequence analysis
 *   - Character tracking through scenes
 *   - Force use events
 *   - Narrative beat identification
 * 
 * TABLES USED: learn_events, learn_event_participants, learn_scenes
 * 
 * SCOPE: The Phantom Menace (TPM), Scenes 27-44 (Maul Revealed to Qui-Gon's Last Words)
 * 
 * DIFFICULTY: Advanced
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Identify the Duel Scenes
-- ============================================================================
-- GOAL: List all scenes that make up the Duel of the Fates sequence.
--       Show scene numbers, names, and durations.
-- 
-- HINTS:
--   - Filter to WorkCode = 'TPM' and SceneNumber 27-44
--   - Order by scene number for chronological sequence
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Duel Sequence Overview
-- ============================================================================
-- GOAL: Calculate the total duration and event count for the duel.
-- 
-- HINTS:
--   - SUM duration from scenes
--   - COUNT events from events table
--   - This is a lengthy sequence spanning many scenes
-- 
-- TABLES: learn_scenes, learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: The Three Duelists
-- ============================================================================
-- GOAL: Track appearances of Qui-Gon, Obi-Wan, and Maul through the sequence.
--       Count their event participations.
-- 
-- HINTS:
--   - Filter participants by name patterns
--   - GROUP BY ParticipantName
--   - These are the three main combatants
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Scene-by-Scene Breakdown
-- ============================================================================
-- GOAL: For each scene in the duel, show:
--       - Scene name
--       - Event count
--       - Duration
-- 
-- HINTS:
--   - Join or correlate scenes with events
--   - GROUP BY scene
-- 
-- TABLES: learn_scenes, learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Combat Events
-- ============================================================================
-- GOAL: Find all combat-type events in the duel sequence.
--       Show the beat-by-beat action.
-- 
-- HINTS:
--   - Filter by EventType containing 'Combat' or 'Attack'
--   - Order chronologically
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: The Laser Gate Separation
-- ============================================================================
-- GOAL: Find scenes related to the laser gate barriers.
--       This is where Qui-Gon gets separated from Obi-Wan.
-- 
-- HINTS:
--   - Look for scene names containing 'Barrier', 'Gate', or 'Separated'
--   - Scenes 32-35 approximately
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Qui-Gon's Last Stand
-- ============================================================================
-- GOAL: Find events from scenes where Qui-Gon fights Maul alone.
--       Track the tragic conclusion.
-- 
-- HINTS:
--   - Scenes 36-37 cover Qui-Gon vs Maul alone and his defeat
--   - Filter events by these scenes
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Obi-Wan's Revenge
-- ============================================================================
-- GOAL: Find events from Obi-Wan's attack on Maul after Qui-Gon falls.
--       The "angry Obi-Wan" sequence.
-- 
-- HINTS:
--   - Scenes 39-43 cover Obi-Wan's fight and victory
--   - Filter events and participants
-- 
-- TABLES: learn_events, learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Key Moments Timeline
-- ============================================================================
-- GOAL: Identify the key narrative beats of the duel:
--       - Doors open
--       - Initial confrontation
--       - Separation by barriers
--       - Qui-Gon struck down
--       - Obi-Wan's fury
--       - Maul's defeat
-- 
-- HINTS:
--   - Use scene names to identify key moments
--   - Create a summary timeline
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Complete Duel Narrative
-- ============================================================================
-- GOAL: Create a narrative view of the entire duel showing:
--       - Scene progression
--       - Key events
--       - Primary participants
--       - The story flow
-- 
-- HINTS:
--   - Join scenes, events, and participants
--   - Order by scene and event number
--   - Focus on Primary importance participants
-- 
-- TABLES: learn_scenes, learn_events, learn_event_participants

-- Write your query below:



