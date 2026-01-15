-- DimDroidModel: droid-specific extension of DimTechAsset.
CREATE TABLE dbo.DimDroidModel (
    DroidModelKey int IDENTITY(1,1) NOT NULL,
    TechAssetKey int NOT NULL,

    DroidClass nvarchar(50) NOT NULL, -- Protocol|Astromech|Battle|Medical|Labor|Assassin|Other
    PrimaryFunction nvarchar(200) NULL,
    AutonomyLevel nvarchar(20) NOT NULL, -- Remote|Semi|Autonomous
    MobilityRef nvarchar(200) NULL,
    ChassisRef nvarchar(200) NULL,
    SensorSuiteRef nvarchar(200) NULL,
    LanguageCapabilitiesRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidModel_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidModel_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimDroidModel_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimDroidModel PRIMARY KEY CLUSTERED (DroidModelKey),
    CONSTRAINT FK_DimDroidModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimDroidModel_TechAssetKey ON dbo.DimDroidModel(TechAssetKey);
