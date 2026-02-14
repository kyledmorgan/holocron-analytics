-- DimDroidModel: droid-specific extension of DimTechAsset.
-- DroidModelGuid ensures stable identity; governance columns track version growth.
CREATE TABLE dbo.DimDroidModel (
    DroidModelKey INT IDENTITY(1,1) NOT NULL,
    DroidModelGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimDroidModel_DroidModelGuid DEFAULT (NEWID()),

    TechAssetKey INT NOT NULL,
    DroidClass NVARCHAR(50) NOT NULL,
    PrimaryFunction NVARCHAR(200) NULL,
    AutonomyLevel NVARCHAR(20) NOT NULL,
    MobilityRef NVARCHAR(200) NULL,
    ChassisRef NVARCHAR(200) NULL,
    SensorSuiteRef NVARCHAR(200) NULL,
    LanguageCapabilitiesRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimDroidModel_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimDroidModel_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimDroidModel_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDroidModel_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDroidModel_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimDroidModel PRIMARY KEY CLUSTERED (DroidModelKey),
    CONSTRAINT UQ_DimDroidModel_DroidModelGuid UNIQUE (DroidModelGuid),
    CONSTRAINT FK_DimDroidModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimDroidModel_TechAssetKey ON dbo.DimDroidModel(TechAssetKey);
CREATE INDEX IX_DimDroidModel_RowHash ON dbo.DimDroidModel(RowHash);
CREATE UNIQUE INDEX UX_DimDroidModel_TechAssetKey_IsLatest
    ON dbo.DimDroidModel(TechAssetKey)
    WHERE IsLatest = 1;
