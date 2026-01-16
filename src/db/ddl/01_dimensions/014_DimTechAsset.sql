-- DimTechAsset: model/class definition for built things.
-- TechAssetGuid provides stable identity; governance metadata tracks versions.
CREATE TABLE dbo.DimTechAsset (
    TechAssetKey int IDENTITY(1,1) NOT NULL,
    TechAssetGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimTechAsset_TechAssetGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    AssetType nvarchar(50) NOT NULL,
    ModelName nvarchar(200) NOT NULL,
    ModelNameNormalized nvarchar(200) NULL,
    ManufacturerRef nvarchar(200) NULL,
    ManufacturerCode nvarchar(50) NULL,
    EraRef nvarchar(100) NULL,
    FirstAppearanceRef nvarchar(200) NULL,
    TechLevelRef nvarchar(100) NULL,
    PowerSourceRef nvarchar(100) NULL,
    MaterialRef nvarchar(200) NULL,
    SafetyNotes nvarchar(500) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimTechAsset_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimTechAsset_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimTechAsset_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechAsset_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechAsset_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimTechAsset PRIMARY KEY CLUSTERED (TechAssetKey),
    CONSTRAINT UQ_DimTechAsset_TechAssetGuid UNIQUE (TechAssetGuid),
    CONSTRAINT FK_DimTechAsset_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimTechAsset_FranchiseKey ON dbo.DimTechAsset(FranchiseKey);
CREATE INDEX IX_DimTechAsset_RowHash ON dbo.DimTechAsset(RowHash);
CREATE UNIQUE INDEX UX_DimTechAsset_Franchise_Model_IsLatest
    ON dbo.DimTechAsset(FranchiseKey, ModelName)
    WHERE IsLatest = 1;
