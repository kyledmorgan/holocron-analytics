-- DimShipModel: ship-specific extension of DimTechAsset.
CREATE TABLE dbo.DimShipModel (
    ShipModelKey int IDENTITY(1,1) NOT NULL,
    TechAssetKey int NOT NULL,

    ShipClass nvarchar(50) NOT NULL, -- Fighter|Freighter|Capital|Transport|Speeder|Other
    PropulsionType nvarchar(20) NOT NULL, -- Hyperdrive|Sublight|None
    HyperdriveClassRef nvarchar(100) NULL,
    CrewCapacityRef nvarchar(100) NULL,
    PassengerCapacityRef nvarchar(100) NULL,
    ArmamentRef nvarchar(200) NULL,
    ShieldingRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimShipModel_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimShipModel_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimShipModel_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimShipModel PRIMARY KEY CLUSTERED (ShipModelKey),
    CONSTRAINT FK_DimShipModel_DimTechAsset FOREIGN KEY (TechAssetKey) REFERENCES dbo.DimTechAsset(TechAssetKey)
);

CREATE INDEX IX_DimShipModel_TechAssetKey ON dbo.DimShipModel(TechAssetKey);
