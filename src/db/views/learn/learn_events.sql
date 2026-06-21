/*******************************************************************************
 * LEARN: learn_events
 * 
 * PURPOSE: Simplified, flat event table for SQL learners.
 *          Full event context without requiring joins.
 *
 * AUDIENCE: SQL learners in modules 3-4 (timeline queries, grouping).
 *
 * KEY COLUMNS:
 *   - EventId: Unique identifier (GUID for user-friendly lookup)
 *   - EventSummary: Brief description of what happened
 *   - EventType: Category (Combat, Movement, Dialogue, etc.)
 *   - WorkTitle, SceneName: Context for where it happened
 *   - SceneNumber, EventNumber: Ordering within the work
 *   - ConfidenceScore: Data quality indicator (0.0 to 1.0)
 *   - Location: Where the event occurred
 *
 * NOTES: This is the primary event table for learners.
 *        Confidence filtering teaches data quality concepts.
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.learn_events
AS
SELECT
    e.EventGuid                 AS EventId,
    e.SummaryShort              AS EventSummary,
    e.EventTypeName             AS EventType,
    e.EventTypeCode,
    e.VerbClass,
    e.WorkTitle,
    e.WorkCode,
    e.SceneName,
    e.SceneOrdinal              AS SceneNumber,
    e.EventOrdinal              AS EventNumber,
    e.LocationName              AS Location,
    e.StartSec,
    e.EndSec,
    e.EraName,
    e.EraCode,
    e.UniverseYearMin,
    e.UniverseYearMax,
    e.ConfidenceScore,
    e.ExtractionMethod,
    e.ContinuityFrameName       AS ContinuityFrame,
    e.FranchiseName             AS Franchise,
    e.EventKey,                 -- Include for advanced join exercises
    e.SceneKey,                 -- Include for advanced join exercises
    e.WorkKey                   -- Include for advanced join exercises
FROM sem.vw_event e;
GO
