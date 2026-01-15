-- DimTechInstance: specific named instance of a built thing.
CREATE TABLE dbo.DimTechInstance (
    TechInstanceKey int IDENTITY(1,1) NOT NULL,
    EntityKey int NOT NULL,
    TechAssetKey int NOT NULL,

    InstanceName nvarchar(200) NOT NULL,
    SerialRef nvarchar(100) NULL,
    BuildRef nvarchar(200) NULL,
    CurrentStatus nvarchar(50) NULL, -- Active|Destroyed|Unknown
    LastKnownLocationRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechInstance_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechInstance_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimTechInstance_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimTechInstance PRIMARY KEY CLUSTERED (TechInstanceKey),
    CONSTRAINT FK_DimTechInstance_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_DimTechInstance_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimTechInstance_EntityKey ON dbo.DimTechInstance(EntityKey);
CREATE INDEX IX_DimTechInstance_TechAssetKey ON dbo.DimTechInstance(TechAssetKey);
