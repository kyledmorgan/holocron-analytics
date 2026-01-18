/******************************************************************************
 * MODULE 03: Event Timeline Explorer
 * 
 * OBJECTIVE: Learn to explore and filter chronological event data.
 * 
 * SKILLS PRACTICED:
 *   - Complex WHERE clauses
 *   - BETWEEN for ranges
 *   - ORDER BY multiple columns
 *   - Working with confidence scores
 *   - Filtering by event types
 * 
 * TABLES USED: learn_events
 * 
 * DIFFICULTY: Beginner-Intermediate
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Events
-- ============================================================================
-- GOAL: Preview the events table to understand available data.
-- 
-- HINTS:
--   - Look at EventType, ConfidenceScore, and ordering columns
--   - Notice how events are ordered within scenes
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Event Types
-- ============================================================================
-- GOAL: Find all distinct event types in the database.
-- 
-- HINTS:
--   - Use DISTINCT on EventType
--   - Look for categories like Combat, Movement, Dialogue, etc.
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: High-Confidence Events
-- ============================================================================
-- GOAL: List events with confidence score 0.90 or higher.
--       Show the top 20, ordered by confidence descending.
-- 
-- HINTS:
--   - ConfidenceScore ranges from 0.0 to 1.0
--   - Higher scores indicate more reliable data
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Events in A New Hope
-- ============================================================================
-- GOAL: List all events from 'A New Hope' in chronological order.
-- 
-- HINTS:
--   - Filter by WorkCode = 'ANH' or WorkTitle
--   - Order by SceneNumber, then EventNumber
--   - This gives the proper sequence within the film
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Events by Scene Range
-- ============================================================================
-- GOAL: Find all events in A New Hope scenes 44-54 (the Trench Run sequence).
-- 
-- HINTS:
--   - Use BETWEEN for the scene range
--   - Combine with work filter
--   - Order chronologically
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Combat Events
-- ============================================================================
-- GOAL: Find all events with 'Combat' or 'Attack' in the event type.
--       Show work, scene, and event summary.
-- 
-- HINTS:
--   - Use LIKE with wildcards
--   - OR can combine multiple conditions
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Events with Location
-- ============================================================================
-- GOAL: List events that have a known location (Location IS NOT NULL).
--       Show top 20 with work, scene, location, and summary.
-- 
-- HINTS:
--   - IS NOT NULL filters out missing data
--   - Location tells us where the event happened
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Low Confidence Review
-- ============================================================================
-- GOAL: Find events with confidence score below 0.70.
--       These might need review or additional verification.
-- 
-- HINTS:
--   - Low confidence doesn't mean wrong, just less certain
--   - Include ExtractionMethod to see data source
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Event Counts by Work
-- ============================================================================
-- GOAL: Count total events per work.
--       Order by event count descending.
-- 
-- HINTS:
--   - Use GROUP BY on WorkTitle
--   - COUNT(*) for total events
-- 
-- TABLES: learn_events

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Event Type Distribution
-- ============================================================================
-- GOAL: Count events by EventType for A New Hope only.
--       Which event types are most common?
-- 
-- HINTS:
--   - Filter to WorkCode = 'ANH'
--   - GROUP BY EventType
--   - Order by count descending
-- 
-- TABLES: learn_events

-- Write your query below:



