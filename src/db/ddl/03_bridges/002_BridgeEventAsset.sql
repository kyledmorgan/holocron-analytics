-- BridgeEventAsset: event-to-tech-instance usage mapping.
CREATE TABLE dbo.BridgeEventAsset (
    EventKey bigint NOT NULL,
    TechInstanceKey int NOT NULL,

    AssetRole nvarchar(50) NOT NULL, -- Used|Damaged|Destroyed|Operated|Referenced
    AssetRoleDetail nvarchar(200) NULL,
    AssetOrdinal int NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventAsset_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventAsset_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_BridgeEventAsset PRIMARY KEY CLUSTERED (EventKey, TechInstanceKey),
    CONSTRAINT FK_BridgeEventAsset_FactEvent FOREIGN KEY (EventKey) REFERENCES dbo.FactEvent(EventKey),
    CONSTRAINT FK_BridgeEventAsset_DimTechInstance FOREIGN KEY (TechInstanceKey) REFERENCES dbo.DimTechInstance(TechInstanceKey)
);

CREATE INDEX IX_BridgeEventAsset_TechInstanceKey ON dbo.BridgeEventAsset(TechInstanceKey);
