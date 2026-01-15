-- DimWeaponModel: weapon-specific extension of DimTechAsset.
CREATE TABLE dbo.DimWeaponModel (
    WeaponModelKey int IDENTITY(1,1) NOT NULL,
    TechAssetKey int NOT NULL,

    WeaponClass nvarchar(50) NOT NULL, -- Lightsaber|Blaster|Melee|Explosive|Heavy|Other
    EnergyType nvarchar(50) NOT NULL, -- Kyber|Plasma|Projectile|Chemical|Other
    EffectiveRangeRef nvarchar(100) NULL,
    AmmunitionRef nvarchar(100) NULL,
    RateOfFireRef nvarchar(100) NULL,
    LethalityRef nvarchar(100) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWeaponModel_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWeaponModel_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimWeaponModel_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimWeaponModel PRIMARY KEY CLUSTERED (WeaponModelKey),
    CONSTRAINT FK_DimWeaponModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimWeaponModel_TechAssetKey ON dbo.DimWeaponModel(TechAssetKey);
