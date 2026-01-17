/******************************************************************************
 * MODULE 04: Who Met Whom (Interactions)
 * 
 * OBJECTIVE: Analyze character co-occurrence and interactions.
 * 
 * SKILLS PRACTICED:
 *   - GROUP BY with multiple columns
 *   - HAVING for group-level filtering
 *   - Self-joins concept
 *   - COUNT DISTINCT
 *   - Aggregation patterns
 * 
 * TABLES USED: learn_event_participants
 * 
 * DIFFICULTY: Intermediate
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Participant Summary
-- ============================================================================
-- GOAL: Count how many events each participant appears in.
--       Show top 20 most active participants.
-- 
-- HINTS:
--   - GROUP BY ParticipantName
--   - COUNT(*) for event count
--   - ORDER BY count DESC
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Role Distribution
-- ============================================================================
-- GOAL: For each participant, count their appearances by role.
--       Show participants who have multiple roles.
-- 
-- HINTS:
--   - GROUP BY ParticipantName, Role
--   - Include the role in output
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: Event Participation Density
-- ============================================================================
-- GOAL: Find events with the most participants.
--       List the top 10 events by participant count.
-- 
-- HINTS:
--   - GROUP BY EventSummary (or EventId)
--   - COUNT DISTINCT ParticipantName
--   - Show event summary and work context
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Primary Actors
-- ============================================================================
-- GOAL: Find participants who are 'Primary' importance 'Actor' role.
--       Count their appearances in this capacity.
-- 
-- HINTS:
--   - Filter on Importance = 'Primary' AND Role = 'Actor'
--   - GROUP BY ParticipantName
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Scene Co-occurrence
-- ============================================================================
-- GOAL: For each scene, list the distinct participants present.
--       Focus on scenes with 3+ participants.
-- 
-- HINTS:
--   - GROUP BY SceneName, WorkTitle
--   - COUNT DISTINCT ParticipantName
--   - HAVING to filter groups
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Villain Activity
-- ============================================================================
-- GOAL: Count events where characters with 'Vader' or 'Palpatine' 
--       in their name participate.
-- 
-- HINTS:
--   - Use LIKE with OR for multiple name patterns
--   - Group by participant name
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Target Analysis
-- ============================================================================
-- GOAL: Find participants who are most often the 'Target' of events.
--       Who gets attacked or affected the most?
-- 
-- HINTS:
--   - Filter on Role = 'Target'
--   - GROUP BY ParticipantName
--   - ORDER BY count DESC
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Cross-Work Appearances
-- ============================================================================
-- GOAL: Find participants who appear in multiple works.
--       Show how many works each participant appears in.
-- 
-- HINTS:
--   - COUNT DISTINCT WorkTitle
--   - HAVING to filter for 2+ works
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Scene Dominance
-- ============================================================================
-- GOAL: For each participant, count their distinct scene appearances.
--       Who appears in the most scenes?
-- 
-- HINTS:
--   - COUNT DISTINCT SceneName (or use a unique scene identifier)
--   - GROUP BY ParticipantName
-- 
-- TABLES: learn_event_participants

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Interaction Partners
-- ============================================================================
-- GOAL: For a specific character (e.g., Luke Skywalker), find all other
--       participants who appeared in the same events.
-- 
-- HINTS:
--   - First find the events where Luke appears
--   - Then find all participants in those events
--   - Exclude Luke from the final list
--   - This requires a subquery
-- 
-- TABLES: learn_event_participants

-- Write your query below:



