-- DimTechInstance: specific named instance of a built thing.
-- TechInstanceGuid provides stable identity; governance columns support versioned lifecycle.
CREATE TABLE dbo.DimTechInstance (
    TechInstanceKey int IDENTITY(1,1) NOT NULL,
    TechInstanceGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimTechInstance_TechInstanceGuid DEFAULT (NEWSEQUENTIALID()),

    EntityKey int NOT NULL,
    TechAssetKey int NOT NULL,
    InstanceName nvarchar(200) NOT NULL,
    SerialRef nvarchar(100) NULL,
    BuildRef nvarchar(200) NULL,
    CurrentStatus nvarchar(50) NULL,
    LastKnownLocationRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimTechInstance_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimTechInstance_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimTechInstance_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechInstance_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechInstance_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimTechInstance PRIMARY KEY CLUSTERED (TechInstanceKey),
    CONSTRAINT UQ_DimTechInstance_TechInstanceGuid UNIQUE (TechInstanceGuid),
    CONSTRAINT FK_DimTechInstance_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_DimTechInstance_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimTechInstance_EntityKey ON dbo.DimTechInstance(EntityKey);
CREATE INDEX IX_DimTechInstance_TechAssetKey ON dbo.DimTechInstance(TechAssetKey);
CREATE INDEX IX_DimTechInstance_RowHash ON dbo.DimTechInstance(RowHash);
CREATE UNIQUE INDEX UX_DimTechInstance_EntityKey_IsLatest
    ON dbo.DimTechInstance(EntityKey)
    WHERE IsLatest = 1;
