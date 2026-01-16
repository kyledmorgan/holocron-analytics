-- DimDroidModel: droid-specific extension of DimTechAsset.
-- DroidModelGuid ensures stable identity; governance columns track version growth.
CREATE TABLE dbo.DimDroidModel (
    DroidModelKey int IDENTITY(1,1) NOT NULL,
    DroidModelGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimDroidModel_DroidModelGuid DEFAULT (NEWSEQUENTIALID()),

    TechAssetKey int NOT NULL,
    DroidClass nvarchar(50) NOT NULL,
    PrimaryFunction nvarchar(200) NULL,
    AutonomyLevel nvarchar(20) NOT NULL,
    MobilityRef nvarchar(200) NULL,
    ChassisRef nvarchar(200) NULL,
    SensorSuiteRef nvarchar(200) NULL,
    LanguageCapabilitiesRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimDroidModel_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimDroidModel_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimDroidModel_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidModel_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidModel_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimDroidModel PRIMARY KEY CLUSTERED (DroidModelKey),
    CONSTRAINT UQ_DimDroidModel_DroidModelGuid UNIQUE (DroidModelGuid),
    CONSTRAINT FK_DimDroidModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimDroidModel_TechAssetKey ON dbo.DimDroidModel(TechAssetKey);
CREATE INDEX IX_DimDroidModel_RowHash ON dbo.DimDroidModel(RowHash);
CREATE UNIQUE INDEX UX_DimDroidModel_TechAssetKey_IsLatest
    ON dbo.DimDroidModel(TechAssetKey)
    WHERE IsLatest = 1;
