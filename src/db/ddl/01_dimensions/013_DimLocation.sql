-- DimLocation: hierarchical location specialization of DimEntity.
CREATE TABLE dbo.DimLocation (
    LocationKey int IDENTITY(1,1) NOT NULL,
    EntityKey int NOT NULL,
    ParentLocationKey int NULL,

    LocationType nvarchar(50) NOT NULL, -- Galaxy|Region|System|Planet|Moon|City|Site|Structure
    RegionCode nvarchar(100) NULL,
    LatitudeRef decimal(9,6) NULL,
    LongitudeRef decimal(9,6) NULL,
    ClimateRef nvarchar(200) NULL,
    TerrainRef nvarchar(200) NULL,
    PopulationRef nvarchar(200) NULL,
    GovernmentRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimLocation_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimLocation_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimLocation_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimLocation PRIMARY KEY CLUSTERED (LocationKey),
    CONSTRAINT FK_DimLocation_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_DimLocation_Parent FOREIGN KEY (ParentLocationKey) REFERENCES dbo.DimLocation(LocationKey)
);

CREATE INDEX IX_DimLocation_EntityKey ON dbo.DimLocation(EntityKey);
CREATE INDEX IX_DimLocation_ParentLocationKey ON dbo.DimLocation(ParentLocationKey);
