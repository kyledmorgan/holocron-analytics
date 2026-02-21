/*******************************************************************************
 * VIEW: sem_event_participant
 *
 * PURPOSE: Canonical semantic view over event participants.
 *          Links events to entities (characters, organizations) with roles.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - BridgeEventParticipantKey: Surrogate key
 *   - EventKey: Link to event
 *   - EntityKey: Link to participating entity
 *   - ParticipantName: Human-readable entity name
 *   - RoleInEvent: Role played (Actor, Target, Observer, etc.)
 *   - WeightClass: Participation importance (Primary, Secondary, Background)
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_event_participant
AS
SELECT
    bp.BridgeEventParticipantKey,
    bp.BridgeEventParticipantGuid AS ParticipantGuid,
    bp.EventKey,
    ev.FactEventGuid            AS EventGuid,
    ev.SummaryShort             AS EventSummary,
    ev.EventOrdinal,
    bp.EntityKey,
    e.EntityGuid,
    e.DisplayName               AS ParticipantName,
    e.EntityType                AS ParticipantType,
    bp.RoleInEvent,
    bp.RoleSubtype,
    bp.WeightClass,
    bp.ParticipantOrdinal,
    bp.ParticipationScore,
    bp.Notes,
    ev.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    ev.SceneKey,
    sc.SceneName,
    ev.FranchiseKey,
    f.Name                      AS FranchiseName,
    bp.ValidFromUtc
FROM dbo.BridgeEventParticipant bp
INNER JOIN dbo.FactEvent ev
    ON bp.EventKey = ev.EventKey
   AND ev.IsActive = 1
   AND ev.IsLatest = 1
INNER JOIN dbo.DimEntity e
    ON bp.EntityKey = e.EntityKey
   AND e.IsActive = 1
   AND e.IsLatest = 1
INNER JOIN dbo.DimWork w
    ON ev.WorkKey = w.WorkKey
   AND w.IsActive = 1
   AND w.IsLatest = 1
INNER JOIN dbo.DimScene sc
    ON ev.SceneKey = sc.SceneKey
   AND sc.IsActive = 1
   AND sc.IsLatest = 1
INNER JOIN dbo.DimFranchise f
    ON ev.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE bp.IsActive = 1
  AND bp.IsLatest = 1;
