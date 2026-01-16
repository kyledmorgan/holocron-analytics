-- DimLocation: hierarchical location specialization of DimEntity.
-- LocationGuid remains stable; governance metadata tracks version history.
CREATE TABLE dbo.DimLocation (
    LocationKey int IDENTITY(1,1) NOT NULL,
    LocationGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimLocation_LocationGuid DEFAULT (NEWSEQUENTIALID()),

    EntityKey int NOT NULL,
    ParentLocationKey int NULL,
    LocationType nvarchar(50) NOT NULL,
    RegionCode nvarchar(100) NULL,
    LatitudeRef decimal(9,6) NULL,
    LongitudeRef decimal(9,6) NULL,
    ClimateRef nvarchar(200) NULL,
    TerrainRef nvarchar(200) NULL,
    PopulationRef nvarchar(200) NULL,
    GovernmentRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimLocation_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimLocation_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimLocation_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimLocation_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimLocation_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimLocation PRIMARY KEY CLUSTERED (LocationKey),
    CONSTRAINT UQ_DimLocation_LocationGuid UNIQUE (LocationGuid),
    CONSTRAINT FK_DimLocation_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_DimLocation_Parent FOREIGN KEY (ParentLocationKey) REFERENCES dbo.DimLocation(LocationKey)
);

CREATE INDEX IX_DimLocation_EntityKey ON dbo.DimLocation(EntityKey);
CREATE INDEX IX_DimLocation_ParentLocationKey ON dbo.DimLocation(ParentLocationKey);
CREATE INDEX IX_DimLocation_RowHash ON dbo.DimLocation(RowHash);
CREATE UNIQUE INDEX UX_DimLocation_EntityKey_IsLatest
    ON dbo.DimLocation(EntityKey)
    WHERE IsLatest = 1;
