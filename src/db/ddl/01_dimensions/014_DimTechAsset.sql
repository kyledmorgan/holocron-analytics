-- DimTechAsset: model/class definition for built things.
CREATE TABLE dbo.DimTechAsset (
    TechAssetKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,

    AssetType nvarchar(50) NOT NULL, -- DroidModel|ShipModel|WeaponModel|StructureModel|ToolModel|Other
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

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechAsset_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTechAsset_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimTechAsset_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimTechAsset PRIMARY KEY CLUSTERED (TechAssetKey),
    CONSTRAINT FK_DimTechAsset_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimTechAsset_FranchiseKey ON dbo.DimTechAsset(FranchiseKey);
