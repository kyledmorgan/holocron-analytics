/*******************************************************************************
 * MART: mart_event_interactions
 *
 * PURPOSE: Event participant interactions for co-occurrence analysis.
 *          Shows who participated in the same events for "who met whom" queries.
 *
 * AUDIENCE: Analysts, learning exercises, interaction network analysis.
 *
 * KEY COLUMNS:
 *   - EventKey: The event where interaction occurred
 *   - ParticipantName, ParticipantType, RoleInEvent: Who participated
 *   - WorkTitle, SceneName: Where it happened
 *   - EventSummary: What happened
 *   - WeightClass: Importance of participation
 *
 * DEPENDENCIES: sem_event_participant, sem_event
 ******************************************************************************/
CREATE   VIEW dbo.mart_event_interactions
AS
SELECT
    p.BridgeEventParticipantKey,
    p.ParticipantGuid,
    p.EventKey,
    p.EventGuid,
    p.EventSummary,
    p.EventOrdinal,
    p.EntityKey,
    p.EntityGuid,
    p.ParticipantName,
    p.ParticipantType,
    p.RoleInEvent,
    p.RoleSubtype,
    p.WeightClass,
    p.ParticipantOrdinal,
    p.ParticipationScore,
    p.WorkKey,
    p.WorkTitle,
    p.WorkCode,
    p.SceneKey,
    p.SceneName,
    e.SceneOrdinal,
    e.EventTypeName,
    e.EventTypeCode,
    e.LocationName,
    e.ConfidenceScore,
    p.FranchiseKey,
    p.FranchiseName
FROM dbo.sem_event_participant p
INNER JOIN dbo.sem_event e
    ON p.EventKey = e.EventKey;
