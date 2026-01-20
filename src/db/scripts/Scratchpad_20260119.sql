

SELECT 'SELECT COUNT(*) FROM ' + TABLE_NAME + ' WITH(NOLOCK)' FROM INFORMATION_SCHEMA.TABLES

SELECT COUNT(*) FROM DimEntity WITH(NOLOCK)
SELECT COUNT(*) FROM DimIssueType WITH(NOLOCK)
SELECT COUNT(*) FROM DimSpecies WITH(NOLOCK)
SELECT COUNT(*) FROM FactEvent WITH(NOLOCK)
SELECT COUNT(*) FROM DimCharacter WITH(NOLOCK)
SELECT COUNT(*) FROM ContinuityIssue WITH(NOLOCK)
SELECT COUNT(*) FROM DimOrganization WITH(NOLOCK)
SELECT COUNT(*) FROM DimLocation WITH(NOLOCK)
SELECT COUNT(*) FROM FactClaim WITH(NOLOCK)
SELECT COUNT(*) FROM DimTechAsset WITH(NOLOCK)
SELECT COUNT(*) FROM DimFranchise WITH(NOLOCK)
SELECT COUNT(*) FROM BridgeEventParticipant WITH(NOLOCK)
SELECT COUNT(*) FROM DimTechInstance WITH(NOLOCK)
SELECT COUNT(*) FROM DimWork WITH(NOLOCK)
SELECT COUNT(*) FROM BridgeEventAsset WITH(NOLOCK)
SELECT COUNT(*) FROM DimDroidModel WITH(NOLOCK)
SELECT COUNT(*) FROM DimScene WITH(NOLOCK)
SELECT COUNT(*) FROM BridgeContinuityIssueClaim WITH(NOLOCK)
SELECT COUNT(*) FROM DimDroidInstance WITH(NOLOCK)
SELECT COUNT(*) FROM DimContinuityFrame WITH(NOLOCK)
SELECT COUNT(*) FROM DimShipModel WITH(NOLOCK)
SELECT COUNT(*) FROM DimEra WITH(NOLOCK)
SELECT COUNT(*) FROM DimWeaponModel WITH(NOLOCK)
SELECT COUNT(*) FROM DimDate WITH(NOLOCK)
SELECT COUNT(*) FROM DimTime WITH(NOLOCK)
SELECT COUNT(*) FROM DimAppearanceLook WITH(NOLOCK)
SELECT COUNT(*) FROM DimEraAnchor WITH(NOLOCK)
SELECT COUNT(*) FROM DimEventType WITH(NOLOCK)

SELECT * FROM DimTechAsset

SELECT DimEntity. * FROM DimLocation
LEFT OUTER JOIN DimEntity
    ON DimLocation.EntityKey = DimEntity.EntityKey


SELECT * FROM DimEntity
WHERE 1=1
AND SummaryShort like '%planet%'

SELECT * FROM DimEventType


SELECT * FROM FactEvent
LEFT OUTER JOIN DimEventType
    ON FactEvent.EventTypeKey = DimEventType.EventTypeKey
-- LEFT OUTER JOIN DimLocation
--     ON FactEvent.LocationKey = DimLocation.LocationKey
-- LEFT OUTER JOIN DimScene
--     ON FactEvent.SceneKey = DimScene.SceneKey
WHERE 1=1






SELECT 'UPDATE ' + TABLE_NAME + ' SET IsActive = 1, IsLatest =1 FROM ' + TABLE_NAME + ''  FROM INFORMATION_SCHEMA.TABLES
WHERE 1=1
AND TABLE_NAME  like '%dim%'


UPDATE DimEntity SET IsActive = 1, IsLatest =1 FROM DimEntity
UPDATE DimIssueType SET IsActive = 1, IsLatest =1 FROM DimIssueType
UPDATE DimSpecies SET IsActive = 1, IsLatest =1 FROM DimSpecies
UPDATE DimCharacter SET IsActive = 1, IsLatest =1 FROM DimCharacter
UPDATE DimOrganization SET IsActive = 1, IsLatest =1 FROM DimOrganization
UPDATE DimLocation SET IsActive = 1, IsLatest =1 FROM DimLocation
UPDATE DimTechAsset SET IsActive = 1, IsLatest =1 FROM DimTechAsset
UPDATE DimFranchise SET IsActive = 1, IsLatest =1 FROM DimFranchise
UPDATE DimTechInstance SET IsActive = 1, IsLatest =1 FROM DimTechInstance
UPDATE DimWork SET IsActive = 1, IsLatest =1 FROM DimWork
UPDATE DimDroidModel SET IsActive = 1, IsLatest =1 FROM DimDroidModel
UPDATE DimScene SET IsActive = 1, IsLatest =1 FROM DimScene
UPDATE DimDroidInstance SET IsActive = 1, IsLatest =1 FROM DimDroidInstance
UPDATE DimContinuityFrame SET IsActive = 1, IsLatest =1 FROM DimContinuityFrame
UPDATE DimShipModel SET IsActive = 1, IsLatest =1 FROM DimShipModel
UPDATE DimEra SET IsActive = 1, IsLatest =1 FROM DimEra
UPDATE DimWeaponModel SET IsActive = 1, IsLatest =1 FROM DimWeaponModel
UPDATE DimDate SET IsActive = 1, IsLatest =1 FROM DimDate
UPDATE DimTime SET IsActive = 1, IsLatest =1 FROM DimTime
UPDATE DimAppearanceLook SET IsActive = 1, IsLatest =1 FROM DimAppearanceLook
UPDATE DimEraAnchor SET IsActive = 1, IsLatest =1 FROM DimEraAnchor
UPDATE DimEventType SET IsActive = 1, IsLatest =1 FROM DimEventType


SELECT * 
FROM dbo.DimAppearanceLook al
LEFT OUTER JOIN dbo.DimCharacter c
    ON al.CharacterKey = c.CharacterKey
   AND c.IsActive = 1
   AND c.IsLatest = 1



SELECT * FROM DimAppearanceLook




SELECT * FROM DimEntity
