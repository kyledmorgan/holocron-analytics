-- BridgeEventAsset: event-to-tech-instance usage mapping.
-- BridgeEventAssetGuid keeps identity consistent; governance columns track versions.
CREATE TABLE dbo.BridgeEventAsset (
    BridgeEventAssetKey INT IDENTITY(1,1) NOT NULL,
    BridgeEventAssetGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_BridgeEventAsset_BridgeEventAssetGuid DEFAULT (NEWID()),

    EventKey BIGINT NOT NULL,
    TechInstanceKey INT NOT NULL,

    AssetRole NVARCHAR(50) NOT NULL, -- Used|Damaged|Destroyed|Operated|Referenced
    AssetRoleDetail NVARCHAR(200) NULL,
    AssetOrdinal INT NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_BridgeEventAsset_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_BridgeEventAsset_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_BridgeEventAsset_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_BridgeEventAsset_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_BridgeEventAsset_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_BridgeEventAsset PRIMARY KEY CLUSTERED (BridgeEventAssetKey),
    CONSTRAINT UQ_BridgeEventAsset_BridgeEventAssetGuid UNIQUE (BridgeEventAssetGuid),
    CONSTRAINT FK_BridgeEventAsset_FactEvent FOREIGN KEY (EventKey) REFERENCES dbo.FactEvent(EventKey),
    CONSTRAINT FK_BridgeEventAsset_DimTechInstance FOREIGN KEY (TechInstanceKey) REFERENCES dbo.DimTechInstance(TechInstanceKey)
);

CREATE INDEX IX_BridgeEventAsset_EventKey ON dbo.BridgeEventAsset(EventKey);
CREATE INDEX IX_BridgeEventAsset_TechInstanceKey ON dbo.BridgeEventAsset(TechInstanceKey);
CREATE INDEX IX_BridgeEventAsset_RowHash ON dbo.BridgeEventAsset(RowHash);
CREATE UNIQUE INDEX UX_BridgeEventAsset_Event_Asset_IsLatest
    ON dbo.BridgeEventAsset(EventKey, TechInstanceKey)
    WHERE IsLatest = 1;
CREATE INDEX IX_BridgeEventAsset_IsLatest ON dbo.BridgeEventAsset(IsLatest);
