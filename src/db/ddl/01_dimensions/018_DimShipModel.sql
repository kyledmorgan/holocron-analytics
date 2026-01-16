-- DimShipModel: ship-specific extension of DimTechAsset.
-- ShipModelGuid ensures stability; governance metadata tracks versions.
CREATE TABLE dbo.DimShipModel (
    ShipModelKey int IDENTITY(1,1) NOT NULL,
    ShipModelGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimShipModel_ShipModelGuid DEFAULT (NEWSEQUENTIALID()),

    TechAssetKey int NOT NULL,
    ShipClass nvarchar(50) NOT NULL,
    PropulsionType nvarchar(20) NOT NULL,
    HyperdriveClassRef nvarchar(100) NULL,
    CrewCapacityRef nvarchar(100) NULL,
    PassengerCapacityRef nvarchar(100) NULL,
    ArmamentRef nvarchar(200) NULL,
    ShieldingRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimShipModel_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimShipModel_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimShipModel_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimShipModel_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimShipModel_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimShipModel PRIMARY KEY CLUSTERED (ShipModelKey),
    CONSTRAINT UQ_DimShipModel_ShipModelGuid UNIQUE (ShipModelGuid),
    CONSTRAINT FK_DimShipModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimShipModel_TechAssetKey ON dbo.DimShipModel(TechAssetKey);
CREATE INDEX IX_DimShipModel_RowHash ON dbo.DimShipModel(RowHash);
CREATE UNIQUE INDEX UX_DimShipModel_TechAssetKey_IsLatest
    ON dbo.DimShipModel(TechAssetKey)
    WHERE IsLatest = 1;
