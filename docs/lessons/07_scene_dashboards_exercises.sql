/******************************************************************************
 * MODULE 07: Scene Breakdown Dashboards
 * 
 * OBJECTIVE: Analyze scenes by duration, event density, and type.
 * 
 * SKILLS PRACTICED:
 *   - Aggregation functions (COUNT, SUM, AVG, MIN, MAX)
 *   - Arithmetic in SQL
 *   - Grouping and filtering groups
 *   - Dashboard-style queries
 * 
 * TABLES USED: learn_scenes, learn_events
 * 
 * DIFFICULTY: Intermediate
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Scene Overview
-- ============================================================================
-- GOAL: Get a summary of scene data by work.
--       Count scenes, total duration, average duration per work.
-- 
-- HINTS:
--   - GROUP BY WorkTitle
--   - Use COUNT, SUM, AVG on DurationSec
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Scene Type Distribution
-- ============================================================================
-- GOAL: Count scenes by SceneType across all works.
-- 
-- HINTS:
--   - GROUP BY SceneType
--   - What types exist? (Opening, Action, Scene, Ending, Credits)
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Longest Scenes per Work
-- ============================================================================
-- GOAL: Find the longest scene in each work.
-- 
-- HINTS:
--   - GROUP BY WorkTitle
--   - MAX(DurationSec)
--   - Need to also get the scene name (more complex)
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Scene Timing Analysis
-- ============================================================================
-- GOAL: For A New Hope, show each scene's position in the film.
--       Include start time, end time, and percentage through the film.
-- 
-- HINTS:
--   - Filter to WorkCode = 'ANH'
--   - Calculate position as StartSec / MAX(EndSec) * 100
--   - This requires a subquery or window function
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Event Density by Scene
-- ============================================================================
-- GOAL: Count events per scene for A New Hope.
--       Which scenes have the most events?
-- 
-- HINTS:
--   - Use learn_events table
--   - GROUP BY SceneName (and WorkCode filter)
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Action Scene Analysis
-- ============================================================================
-- GOAL: Find all Action scenes and their average event count.
-- 
-- HINTS:
--   - Join or correlate learn_scenes with learn_events
--   - Filter scenes where SceneType = 'Action'
-- 
-- TABLES: learn_scenes, learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Scene Duration Brackets
-- ============================================================================
-- GOAL: Categorize scenes into duration brackets:
--       - Short: < 60 seconds
--       - Medium: 60-180 seconds  
--       - Long: > 180 seconds
--       Count scenes in each bracket.
-- 
-- HINTS:
--   - Use CASE expression to create categories
--   - GROUP BY the CASE expression
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Opening vs Ending
-- ============================================================================
-- GOAL: Compare Opening and Ending scenes across works.
--       Show average duration for each type.
-- 
-- HINTS:
--   - Filter to SceneType IN ('Opening', 'Ending', 'Credits')
--   - GROUP BY SceneType
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Work Duration Calculation
-- ============================================================================
-- GOAL: Calculate total runtime for each work based on scene data.
--       Compare to the documented runtime if available.
-- 
-- HINTS:
--   - SUM(DurationSec) grouped by work
--   - Convert to minutes: / 60.0
-- 
-- TABLES: learn_scenes

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Scene Event Heatmap Data
-- ============================================================================
-- GOAL: For each scene in A New Hope, show:
--       - Scene number and name
--       - Duration
--       - Event count
--       - Events per minute (if duration known)
-- 
-- HINTS:
--   - Join events with scenes
--   - Calculate events per minute carefully
--   - Handle divide by zero
-- 
-- TABLES: learn_scenes, learn_events

-- Write your query below:



