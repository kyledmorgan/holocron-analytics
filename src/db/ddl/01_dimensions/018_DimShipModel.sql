-- DimShipModel: ship-specific extension of DimTechAsset.
-- ShipModelGuid ensures stability; governance metadata tracks versions.
CREATE TABLE dbo.DimShipModel (
    ShipModelKey INT IDENTITY(1,1) NOT NULL,
    ShipModelGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimShipModel_ShipModelGuid DEFAULT (NEWID()),

    TechAssetKey INT NOT NULL,
    ShipClass NVARCHAR(50) NOT NULL,
    PropulsionType NVARCHAR(20) NOT NULL,
    HyperdriveClassRef NVARCHAR(100) NULL,
    CrewCapacityRef NVARCHAR(100) NULL,
    PassengerCapacityRef NVARCHAR(100) NULL,
    ArmamentRef NVARCHAR(200) NULL,
    ShieldingRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimShipModel_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimShipModel_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimShipModel_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimShipModel_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimShipModel_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimShipModel PRIMARY KEY CLUSTERED (ShipModelKey),
    CONSTRAINT UQ_DimShipModel_ShipModelGuid UNIQUE (ShipModelGuid),
    CONSTRAINT FK_DimShipModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimShipModel_TechAssetKey ON dbo.DimShipModel(TechAssetKey);
CREATE INDEX IX_DimShipModel_RowHash ON dbo.DimShipModel(RowHash);
CREATE UNIQUE INDEX UX_DimShipModel_TechAssetKey_IsLatest
    ON dbo.DimShipModel(TechAssetKey)
    WHERE IsLatest = 1;
