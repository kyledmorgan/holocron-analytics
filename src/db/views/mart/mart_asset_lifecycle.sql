/*******************************************************************************
 * MART: mart_asset_lifecycle
 * 
 * PURPOSE: Asset usage and lifecycle events over time.
 *          Tracks when ships, weapons, droids were used, damaged, or destroyed.
 *
 * AUDIENCE: Analysts, learning exercises, asset tracking dashboards.
 *
 * KEY COLUMNS:
 *   - TechInstanceKey, AssetName: Asset identity
 *   - ModelName, AssetType: Asset classification
 *   - AssetRole: Usage type (Used, Damaged, Destroyed, etc.)
 *   - EventSummary, EventTypeName: What happened
 *   - WorkTitle, SceneName, SceneOrdinal: Where it happened
 *
 * DEPENDENCIES: sem_event_asset, sem_event
 ******************************************************************************/
CREATE OR ALTER VIEW dbo.mart_asset_lifecycle
AS
SELECT
    ea.BridgeEventAssetKey,
    ea.EventAssetGuid,
    ea.TechInstanceKey,
    ea.TechInstanceGuid,
    ea.AssetName,
    ea.TechAssetKey,
    ea.ModelName,
    ea.AssetType,
    ea.AssetRole,
    ea.AssetRoleDetail,
    ea.AssetOrdinal,
    ea.EventKey,
    ea.EventGuid,
    ea.EventSummary,
    ea.EventOrdinal,
    e.EventTypeName,
    e.EventTypeCode,
    ea.WorkKey,
    ea.WorkTitle,
    ea.WorkCode,
    ea.SceneKey,
    ea.SceneName,
    e.SceneOrdinal,
    e.StartSec,
    e.EndSec,
    e.LocationName,
    e.ConfidenceScore,
    ea.FranchiseKey,
    ea.FranchiseName,
    /* Computed timeline ordering */
    (e.SceneOrdinal * 1000 + ea.EventOrdinal) AS TimelineOrdinal
FROM sem.vw_event_asset ea
INNER JOIN sem.vw_event e
    ON ea.EventKey = e.EventKey;
GO
