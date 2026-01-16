-- BridgeEventAsset: event-to-tech-instance usage mapping.
-- BridgeEventAssetGuid keeps identity consistent; governance columns track versions.
CREATE TABLE dbo.BridgeEventAsset (
    BridgeEventAssetKey int IDENTITY(1,1) NOT NULL,
    BridgeEventAssetGuid uniqueidentifier NOT NULL CONSTRAINT DF_BridgeEventAsset_BridgeEventAssetGuid DEFAULT (NEWSEQUENTIALID()),

    EventKey bigint NOT NULL,
    TechInstanceKey int NOT NULL,

    AssetRole nvarchar(50) NOT NULL, -- Used|Damaged|Destroyed|Operated|Referenced
    AssetRoleDetail nvarchar(200) NULL,
    AssetOrdinal int NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_BridgeEventAsset_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_BridgeEventAsset_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_BridgeEventAsset_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventAsset_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventAsset_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
