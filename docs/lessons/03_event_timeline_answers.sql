/******************************************************************************
 * MODULE 03: Event Timeline Explorer - ANSWER KEY
 * 
 * This file contains solutions for the event timeline exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Events
-- ============================================================================

SELECT TOP 20 *
FROM learn_events
ORDER BY WorkCode, SceneNumber, EventNumber;
-- Comment: Events are ordered by scene and event number within each work.
--          This gives chronological ordering within the narrative.

/* VARIATIONS:
   - ORDER BY ConfidenceScore DESC         -- Highest confidence first
   - WHERE WorkCode = 'ANH'                -- Focus on one work
*/


-- ============================================================================
-- EXERCISE 2: Event Types
-- ============================================================================

SELECT DISTINCT EventType
FROM learn_events
WHERE EventType IS NOT NULL
ORDER BY EventType;
-- Comment: Event types categorize what kind of action occurred.
--          Common types: Combat, Movement, Dialogue, Force Use, etc.

/* VARIATIONS:
   - SELECT DISTINCT EventTypeCode         -- Short codes instead
   - SELECT DISTINCT VerbClass             -- Verb classification
   - SELECT EventType, COUNT(*) FROM learn_events GROUP BY EventType  -- With counts
*/


-- ============================================================================
-- EXERCISE 3: High-Confidence Events
-- ============================================================================

SELECT TOP 20
    EventSummary,
    EventType,
    ConfidenceScore,
    WorkTitle,
    SceneName
FROM learn_events
WHERE ConfidenceScore >= 0.90              -- High confidence threshold
ORDER BY ConfidenceScore DESC, EventSummary;
-- Comment: High confidence events are well-sourced and verified.

/* VARIATIONS:
   - WHERE ConfidenceScore >= 0.95         -- Very high confidence only
   - WHERE ConfidenceScore BETWEEN 0.85 AND 0.95  -- Mid-high range
   - AND ExtractionMethod = 'Manual'       -- Manually verified events
*/


-- ============================================================================
-- EXERCISE 4: Events in A New Hope
-- ============================================================================

SELECT
    SceneNumber,
    SceneName,
    EventNumber,
    EventSummary,
    EventType,
    Location
FROM learn_events
WHERE WorkCode = 'ANH'                     -- A New Hope work code
ORDER BY SceneNumber, EventNumber;         -- Chronological order
-- Comment: This ordering matches the film's narrative sequence.

/* VARIATIONS:
   - WHERE WorkTitle LIKE '%New Hope%'     -- Title match
   - AND SceneNumber <= 10                 -- First 10 scenes only
   - AND EventType = 'Combat'              -- Combat events only
*/


-- ============================================================================
-- EXERCISE 5: Events by Scene Range
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
  AND SceneNumber BETWEEN 44 AND 54        -- Trench Run sequence
ORDER BY SceneNumber, EventNumber;
-- Comment: BETWEEN is inclusive of both endpoints.
--          Scenes 44-54 cover the Battle of Yavin trench run.

/* VARIATIONS:
   - BETWEEN 1 AND 10                      -- Opening sequence
   - BETWEEN 27 AND 35                     -- Death Star infiltration
   - AND ConfidenceScore >= 0.80           -- Add confidence filter
*/


-- ============================================================================
-- EXERCISE 6: Combat Events
-- ============================================================================

SELECT
    WorkTitle,
    SceneName,
    EventSummary,
    EventType,
    Location
FROM learn_events
WHERE EventType LIKE '%Combat%'
   OR EventType LIKE '%Attack%'            -- Multiple patterns
ORDER BY WorkTitle, SceneNumber, EventNumber;
-- Comment: LIKE with OR catches multiple event type patterns.

/* VARIATIONS:
   - WHERE EventType IN ('Combat', 'Attack', 'Battle')  -- Exact matches
   - WHERE VerbClass = 'Attack'            -- Use verb classification
   - AND ConfidenceScore >= 0.75           -- Reliable combat events
*/


-- ============================================================================
-- EXERCISE 7: Events with Location
-- ============================================================================

SELECT TOP 20
    WorkTitle,
    SceneName,
    Location,
    EventSummary,
    EventType
FROM learn_events
WHERE Location IS NOT NULL                 -- Has location data
ORDER BY Location, WorkTitle, SceneNumber;
-- Comment: Location data helps understand the geographic context.

/* VARIATIONS:
   - WHERE Location LIKE '%Tatooine%'      -- Specific location
   - WHERE Location LIKE '%Death Star%'    -- Death Star events
   - GROUP BY Location ... COUNT(*)        -- Events per location
*/


-- ============================================================================
-- EXERCISE 8: Low Confidence Review
-- ============================================================================

SELECT
    EventSummary,
    ConfidenceScore,
    ExtractionMethod,
    WorkTitle,
    SceneName
FROM learn_events
WHERE ConfidenceScore < 0.70               -- Below confidence threshold
ORDER BY ConfidenceScore ASC, WorkTitle;
-- Comment: Low confidence may indicate ambiguous source material
--          or AI extraction that needs verification.

/* VARIATIONS:
   - WHERE ConfidenceScore < 0.50          -- Very low confidence
   - AND ExtractionMethod = 'AI'           -- AI-extracted events
   - AND ExtractionMethod = 'Manual'       -- Manual but uncertain
*/


-- ============================================================================
-- EXERCISE 9: Event Counts by Work
-- ============================================================================

SELECT
    WorkTitle,
    WorkCode,
    COUNT(*) AS EventCount
FROM learn_events
GROUP BY WorkTitle, WorkCode
ORDER BY EventCount DESC;
-- Comment: Shows which works have the most detailed event coverage.

/* VARIATIONS:
   - HAVING COUNT(*) > 50                  -- Only works with many events
   - Add: AVG(ConfidenceScore) AS AvgConfidence  -- Average confidence
   - GROUP BY WorkCode only                -- Simpler grouping
*/


-- ============================================================================
-- EXERCISE 10: Event Type Distribution
-- ============================================================================

SELECT
    EventType,
    COUNT(*) AS EventCount,
    AVG(ConfidenceScore) AS AvgConfidence  -- Bonus: average confidence
FROM learn_events
WHERE WorkCode = 'ANH'
GROUP BY EventType
ORDER BY EventCount DESC;
-- Comment: Shows the distribution of event types in A New Hope.
--          Helps understand the narrative focus (action vs. dialogue, etc.)

/* VARIATIONS:
   - WHERE WorkCode = 'TPM'                -- Try: The Phantom Menace
   - HAVING COUNT(*) >= 5                  -- Only common types
   - Add: MIN(ConfidenceScore), MAX(ConfidenceScore)  -- Range
*/
