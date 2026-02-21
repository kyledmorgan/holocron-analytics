/*******************************************************************************
 * LEARN: learn_event_participants
 *
 * PURPOSE: Simplified event participation table for SQL learners.
 *          Shows who participated in which events with roles.
 *
 * AUDIENCE: SQL learners in modules 4-5 (joins, grouping, aggregation).
 *
 * KEY COLUMNS:
 *   - ParticipantId: Unique identifier
 *   - ParticipantName: Who participated
 *   - ParticipantType: Character, Organization, etc.
 *   - Role: Role in the event (Actor, Target, Observer, etc.)
 *   - Importance: Weight class (Primary, Secondary, Background)
 *   - EventSummary: What happened
 *   - WorkTitle, SceneName: Where it happened
 *
 * NOTES: This is for "who met whom" and interaction queries.
 *        Can be joined with learn_events on EventKey.
 ******************************************************************************/
CREATE   VIEW dbo.learn_event_participants
AS
SELECT
    p.ParticipantGuid           AS ParticipantId,
    p.ParticipantName,
    p.ParticipantType,
    p.RoleInEvent               AS Role,
    p.RoleSubtype,
    p.WeightClass               AS Importance,
    p.ParticipantOrdinal        AS ParticipantOrder,
    p.ParticipationScore,
    p.EventGuid                 AS EventId,
    p.EventSummary,
    p.EventOrdinal              AS EventNumber,
    p.WorkTitle,
    p.WorkCode,
    p.SceneName,
    p.FranchiseName             AS Franchise,
    p.EventKey,                 -- Include for advanced join exercises
    p.EntityKey                 -- Include for advanced join exercises
FROM dbo.sem_event_participant p;
