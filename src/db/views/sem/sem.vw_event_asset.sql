/*******************************************************************************
 * VIEW: sem_event_asset
 *
 * PURPOSE: Canonical semantic view over event-to-asset relationships.
 *          Links events to technology instances with usage roles.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - BridgeEventAssetKey: Surrogate key
 *   - EventKey: Link to event
 *   - TechInstanceKey: Link to asset instance
 *   - AssetName: Human-readable asset name
 *   - AssetRole: Usage role (Used, Damaged, Destroyed, Operated, Referenced)
 *   - ModelName: Base model/class name
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_event_asset
AS
SELECT
    ba.BridgeEventAssetKey,
    ba.BridgeEventAssetGuid     AS EventAssetGuid,
    ba.EventKey,
    ev.FactEventGuid            AS EventGuid,
    ev.SummaryShort             AS EventSummary,
    ev.EventOrdinal,
    ba.TechInstanceKey,
    ti.TechInstanceGuid,
    ti.InstanceName             AS AssetName,
    ta.TechAssetKey,
    ta.ModelName,
    ta.AssetType,
    ba.AssetRole,
    ba.AssetRoleDetail,
    ba.AssetOrdinal,
    ba.Notes,
    ev.WorkKey,
    w.Title                     AS WorkTitle,
    w.WorkCode,
    ev.SceneKey,
    sc.SceneName,
    ev.FranchiseKey,
    f.Name                      AS FranchiseName,
    ba.ValidFromUtc
FROM dbo.BridgeEventAsset ba
INNER JOIN dbo.FactEvent ev
    ON ba.EventKey = ev.EventKey
   AND ev.IsActive = 1
   AND ev.IsLatest = 1
INNER JOIN dbo.DimTechInstance ti
    ON ba.TechInstanceKey = ti.TechInstanceKey
   AND ti.IsActive = 1
   AND ti.IsLatest = 1
INNER JOIN dbo.DimTechAsset ta
    ON ti.TechAssetKey = ta.TechAssetKey
   AND ta.IsActive = 1
   AND ta.IsLatest = 1
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
WHERE ba.IsActive = 1
  AND ba.IsLatest = 1;
