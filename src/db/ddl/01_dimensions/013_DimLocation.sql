-- DimLocation: hierarchical location specialization of DimEntity.
-- LocationGuid remains stable; governance metadata tracks version history.
CREATE TABLE dbo.DimLocation (
    LocationKey INT IDENTITY(1,1) NOT NULL,
    LocationGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimLocation_LocationGuid DEFAULT (NEWID()),

    EntityKey INT NOT NULL,
    ParentLocationKey INT NULL,
    LocationType NVARCHAR(50) NOT NULL,
    RegionCode NVARCHAR(100) NULL,
    LatitudeRef DECIMAL(9,6) NULL,
    LongitudeRef DECIMAL(9,6) NULL,
    ClimateRef NVARCHAR(200) NULL,
    TerrainRef NVARCHAR(200) NULL,
    PopulationRef NVARCHAR(200) NULL,
    GovernmentRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimLocation_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimLocation_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimLocation_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimLocation_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimLocation_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

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
