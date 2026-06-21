-- DimTechInstance: specific named instance of a built thing.
-- TechInstanceGuid provides stable identity; governance columns support versioned lifecycle.
CREATE TABLE dbo.DimTechInstance (
    TechInstanceKey INT IDENTITY(1,1) NOT NULL,
    TechInstanceGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimTechInstance_TechInstanceGuid DEFAULT (NEWID()),

    EntityKey INT NOT NULL,
    TechAssetKey INT NOT NULL,
    InstanceName NVARCHAR(200) NOT NULL,
    SerialRef NVARCHAR(100) NULL,
    BuildRef NVARCHAR(200) NULL,
    CurrentStatus NVARCHAR(50) NULL,
    LastKnownLocationRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimTechInstance_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimTechInstance_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimTechInstance_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimTechInstance_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimTechInstance_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

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
