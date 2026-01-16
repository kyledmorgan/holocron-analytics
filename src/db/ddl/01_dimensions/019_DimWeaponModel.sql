-- DimWeaponModel: weapon-specific extension of DimTechAsset.
-- WeaponModelGuid provides stable identity; governance metadata tracks versions.
CREATE TABLE dbo.DimWeaponModel (
    WeaponModelKey int IDENTITY(1,1) NOT NULL,
    WeaponModelGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimWeaponModel_WeaponModelGuid DEFAULT (NEWSEQUENTIALID()),

    TechAssetKey int NOT NULL,
    WeaponClass nvarchar(50) NOT NULL,
    EnergyType nvarchar(50) NOT NULL,
    EffectiveRangeRef nvarchar(100) NULL,
    AmmunitionRef nvarchar(100) NULL,
    RateOfFireRef nvarchar(100) NULL,
    LethalityRef nvarchar(100) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimWeaponModel_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimWeaponModel_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimWeaponModel_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWeaponModel_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWeaponModel_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimWeaponModel PRIMARY KEY CLUSTERED (WeaponModelKey),
    CONSTRAINT UQ_DimWeaponModel_WeaponModelGuid UNIQUE (WeaponModelGuid),
    CONSTRAINT FK_DimWeaponModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimWeaponModel_TechAssetKey ON dbo.DimWeaponModel(TechAssetKey);
CREATE INDEX IX_DimWeaponModel_RowHash ON dbo.DimWeaponModel(RowHash);
CREATE UNIQUE INDEX UX_DimWeaponModel_TechAssetKey_IsLatest
    ON dbo.DimWeaponModel(TechAssetKey)
    WHERE IsLatest = 1;
