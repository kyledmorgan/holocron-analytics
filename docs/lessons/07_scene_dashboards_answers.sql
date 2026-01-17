/******************************************************************************
 * MODULE 07: Scene Breakdown Dashboards - ANSWER KEY
 * 
 * This file contains solutions for the scene dashboard exercises.
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Scene Overview
-- ============================================================================

SELECT
    WorkTitle,
    WorkCode,
    COUNT(*) AS SceneCount,
    SUM(DurationSec) AS TotalDurationSec,
    AVG(DurationSec) AS AvgDurationSec,
    MIN(DurationSec) AS MinDurationSec,
    MAX(DurationSec) AS MaxDurationSec
FROM learn_scenes
WHERE DurationSec IS NOT NULL
GROUP BY WorkTitle, WorkCode
ORDER BY TotalDurationSec DESC;
-- Comment: This gives a high-level view of scene coverage per work.

/* VARIATIONS:
   - Remove WHERE to include scenes without duration
   - Add: SUM(DurationSec) / 60.0 AS TotalMinutes  -- In minutes
   - HAVING COUNT(*) >= 10                 -- Only detailed works
*/


-- ============================================================================
-- EXERCISE 2: Scene Type Distribution
-- ============================================================================

SELECT
    SceneType,
    COUNT(*) AS SceneCount,
    AVG(DurationSec) AS AvgDurationSec
FROM learn_scenes
GROUP BY SceneType
ORDER BY SceneCount DESC;
-- Comment: Scene types categorize the narrative function of scenes.
--          Action scenes may be longer on average.

/* VARIATIONS:
   - WHERE WorkCode = 'ANH'                -- One work only
   - Add: SUM(DurationSec) AS TotalDuration
   - HAVING AVG(DurationSec) > 120         -- Longer scene types
*/


-- ============================================================================
-- EXERCISE 3: Longest Scenes per Work
-- ============================================================================

-- Simple version: just max duration
SELECT
    WorkTitle,
    MAX(DurationSec) AS MaxDurationSec
FROM learn_scenes
WHERE DurationSec IS NOT NULL
GROUP BY WorkTitle
ORDER BY MaxDurationSec DESC;

-- Advanced version: include scene name (requires subquery or window function)
SELECT
    s.WorkTitle,
    s.SceneName,
    s.DurationSec
FROM learn_scenes s
INNER JOIN (
    SELECT WorkTitle, MAX(DurationSec) AS MaxDuration
    FROM learn_scenes
    GROUP BY WorkTitle
) m ON s.WorkTitle = m.WorkTitle AND s.DurationSec = m.MaxDuration
ORDER BY s.DurationSec DESC;
-- Comment: Finding the "which row has the max" requires a self-join or subquery.

/* VARIATIONS:
   - Use ROW_NUMBER() window function instead of self-join
   - Find shortest scene: MIN instead of MAX
*/


-- ============================================================================
-- EXERCISE 4: Scene Timing Analysis
-- ============================================================================

SELECT
    SceneName,
    SceneNumber,
    StartSec,
    EndSec,
    DurationSec,
    CAST(StartSec AS FLOAT) / (SELECT MAX(EndSec) FROM learn_scenes WHERE WorkCode = 'ANH') * 100 
        AS PercentThroughFilm
FROM learn_scenes
WHERE WorkCode = 'ANH'
ORDER BY SceneNumber;
-- Comment: This shows where each scene falls in the overall film timeline.
--          Useful for identifying pacing and structure.

/* VARIATIONS:
   - Add: StartSec / 60.0 AS StartMinutes  -- Time in minutes
   - Add: CASE WHEN PercentThroughFilm < 25 THEN 'Act 1' ... END AS Act
*/


-- ============================================================================
-- EXERCISE 5: Event Density by Scene
-- ============================================================================

SELECT TOP 20
    SceneName,
    SceneNumber,
    COUNT(*) AS EventCount
FROM learn_events
WHERE WorkCode = 'ANH'
GROUP BY SceneName, SceneNumber
ORDER BY EventCount DESC;
-- Comment: High event count scenes are action-packed or complex.
--          Low count scenes may be transitional or atmospheric.

/* VARIATIONS:
   - ORDER BY SceneNumber                  -- Chronological order
   - HAVING COUNT(*) >= 5                  -- Only event-dense scenes
   - Add: AVG(ConfidenceScore)             -- Average confidence
*/


-- ============================================================================
-- EXERCISE 6: Action Scene Analysis
-- ============================================================================

SELECT
    s.WorkTitle,
    s.SceneName,
    s.DurationSec,
    COUNT(e.EventId) AS EventCount
FROM learn_scenes s
LEFT JOIN learn_events e 
    ON s.SceneKey = e.SceneKey
WHERE s.SceneType = 'Action'
GROUP BY s.WorkTitle, s.SceneName, s.DurationSec
ORDER BY EventCount DESC;
-- Comment: Action scenes typically have more events than dialogue scenes.
--          The LEFT JOIN ensures we see action scenes even with no events.

/* VARIATIONS:
   - WHERE s.SceneType IN ('Action', 'Opening')  -- Include openings
   - HAVING COUNT(e.EventId) > 0           -- Only scenes with events
   - Add: COUNT(e.EventId) * 1.0 / NULLIF(s.DurationSec, 0) * 60 AS EventsPerMin
*/


-- ============================================================================
-- EXERCISE 7: Scene Duration Brackets
-- ============================================================================

SELECT
    CASE 
        WHEN DurationSec < 60 THEN 'Short (< 1 min)'
        WHEN DurationSec BETWEEN 60 AND 180 THEN 'Medium (1-3 min)'
        WHEN DurationSec > 180 THEN 'Long (> 3 min)'
        ELSE 'Unknown'
    END AS DurationBracket,
    COUNT(*) AS SceneCount,
    AVG(DurationSec) AS AvgDuration
FROM learn_scenes
GROUP BY 
    CASE 
        WHEN DurationSec < 60 THEN 'Short (< 1 min)'
        WHEN DurationSec BETWEEN 60 AND 180 THEN 'Medium (1-3 min)'
        WHEN DurationSec > 180 THEN 'Long (> 3 min)'
        ELSE 'Unknown'
    END
ORDER BY AvgDuration;
-- Comment: Bucketing numeric data into categories is a common analysis pattern.

/* VARIATIONS:
   - Different thresholds: 120, 300 seconds
   - WHERE WorkCode = 'ANH'                -- One work
   - Add: MIN(DurationSec), MAX(DurationSec) for bracket ranges
*/


-- ============================================================================
-- EXERCISE 8: Opening vs Ending
-- ============================================================================

SELECT
    SceneType,
    COUNT(*) AS SceneCount,
    AVG(DurationSec) AS AvgDurationSec,
    MIN(DurationSec) AS MinDurationSec,
    MAX(DurationSec) AS MaxDurationSec
FROM learn_scenes
WHERE SceneType IN ('Opening', 'Ending', 'Credits')
GROUP BY SceneType
ORDER BY SceneType;
-- Comment: Structural scenes (opening, ending, credits) follow conventions.
--          Credits are typically longest; openings set the tone.

/* VARIATIONS:
   - WHERE SceneType LIKE '%ing'           -- Pattern match
   - Add comparison to 'Scene' type        -- vs. regular scenes
*/


-- ============================================================================
-- EXERCISE 9: Work Duration Calculation
-- ============================================================================

SELECT
    WorkTitle,
    WorkCode,
    COUNT(*) AS SceneCount,
    SUM(DurationSec) AS TotalSeconds,
    SUM(DurationSec) / 60.0 AS TotalMinutes,
    SUM(DurationSec) / 3600.0 AS TotalHours
FROM learn_scenes
WHERE DurationSec IS NOT NULL
GROUP BY WorkTitle, WorkCode
ORDER BY TotalMinutes DESC;
-- Comment: Calculated runtime may differ from official due to incomplete data.
--          This is a good sanity check on data completeness.

/* VARIATIONS:
   - HAVING SUM(DurationSec) > 3600        -- Over 1 hour only
   - Add percentage: SUM(DurationSec) / (SELECT SUM(DurationSec) FROM learn_scenes) * 100
*/


-- ============================================================================
-- EXERCISE 10: Scene Event Heatmap Data
-- ============================================================================

SELECT
    s.SceneNumber,
    s.SceneName,
    s.SceneType,
    s.DurationSec,
    COALESCE(e.EventCount, 0) AS EventCount,
    CASE 
        WHEN s.DurationSec > 0 
        THEN CAST(COALESCE(e.EventCount, 0) AS FLOAT) / (s.DurationSec / 60.0)
        ELSE NULL 
    END AS EventsPerMinute
FROM learn_scenes s
LEFT JOIN (
    SELECT SceneKey, COUNT(*) AS EventCount
    FROM learn_events
    GROUP BY SceneKey
) e ON s.SceneKey = e.SceneKey
WHERE s.WorkCode = 'ANH'
ORDER BY s.SceneNumber;
-- Comment: Events per minute indicates scene intensity.
--          High density = action-packed; low density = dialogue or atmospheric.

/* VARIATIONS:
   - WHERE s.WorkCode = 'TPM'              -- Different work
   - AND e.EventCount >= 5                 -- Only event-rich scenes
   - Add: CASE WHEN EventsPerMinute > 2 THEN 'High' ... END AS Intensity
*/
