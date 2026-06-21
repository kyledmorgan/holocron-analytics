-- DimWeaponModel: weapon-specific extension of DimTechAsset.
-- WeaponModelGuid provides stable identity; governance metadata tracks versions.
CREATE TABLE dbo.DimWeaponModel (
    WeaponModelKey INT IDENTITY(1,1) NOT NULL,
    WeaponModelGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimWeaponModel_WeaponModelGuid DEFAULT (NEWID()),

    TechAssetKey INT NOT NULL,
    WeaponClass NVARCHAR(50) NOT NULL,
    EnergyType NVARCHAR(50) NOT NULL,
    EffectiveRangeRef NVARCHAR(100) NULL,
    AmmunitionRef NVARCHAR(100) NULL,
    RateOfFireRef NVARCHAR(100) NULL,
    LethalityRef NVARCHAR(100) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimWeaponModel_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimWeaponModel_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimWeaponModel_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimWeaponModel_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimWeaponModel_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimWeaponModel PRIMARY KEY CLUSTERED (WeaponModelKey),
    CONSTRAINT UQ_DimWeaponModel_WeaponModelGuid UNIQUE (WeaponModelGuid),
    CONSTRAINT FK_DimWeaponModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimWeaponModel_TechAssetKey ON dbo.DimWeaponModel(TechAssetKey);
CREATE INDEX IX_DimWeaponModel_RowHash ON dbo.DimWeaponModel(RowHash);
CREATE UNIQUE INDEX UX_DimWeaponModel_TechAssetKey_IsLatest
    ON dbo.DimWeaponModel(TechAssetKey)
    WHERE IsLatest = 1;
