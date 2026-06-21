-- DimTechAsset: model/class definition for built things.
-- TechAssetGuid provides stable identity; governance metadata tracks versions.
CREATE TABLE dbo.DimTechAsset (
    TechAssetKey INT IDENTITY(1,1) NOT NULL,
    TechAssetGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimTechAsset_TechAssetGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    AssetType NVARCHAR(50) NOT NULL,
    ModelName NVARCHAR(200) NOT NULL,
    ModelNameNormalized NVARCHAR(200) NULL,
    ManufacturerRef NVARCHAR(200) NULL,
    ManufacturerCode NVARCHAR(50) NULL,
    EraRef NVARCHAR(100) NULL,
    FirstAppearanceRef NVARCHAR(200) NULL,
    TechLevelRef NVARCHAR(100) NULL,
    PowerSourceRef NVARCHAR(100) NULL,
    MaterialRef NVARCHAR(200) NULL,
    SafetyNotes NVARCHAR(500) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimTechAsset_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimTechAsset_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimTechAsset_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimTechAsset_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimTechAsset_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimTechAsset PRIMARY KEY CLUSTERED (TechAssetKey),
    CONSTRAINT UQ_DimTechAsset_TechAssetGuid UNIQUE (TechAssetGuid),
    CONSTRAINT FK_DimTechAsset_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimTechAsset_FranchiseKey ON dbo.DimTechAsset(FranchiseKey);
CREATE INDEX IX_DimTechAsset_RowHash ON dbo.DimTechAsset(RowHash);
CREATE UNIQUE INDEX UX_DimTechAsset_Franchise_Model_IsLatest
    ON dbo.DimTechAsset(FranchiseKey, ModelName)
    WHERE IsLatest = 1;
