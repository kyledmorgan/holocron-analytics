-- DimSpecies: species/creature taxonomy.
-- SpeciesGuid tracks stable identity; governance metadata captures versioning.
CREATE TABLE dbo.DimSpecies (
    SpeciesKey INT IDENTITY(1,1) NOT NULL,
    SpeciesGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimSpecies_SpeciesGuid DEFAULT (NEWID()),

    EntityKey INT NOT NULL,
    Category NVARCHAR(50) NOT NULL,
    HomeworldRef NVARCHAR(200) NULL,
    TypicalLifespanRef NVARCHAR(100) NULL,
    AverageHeightRef NVARCHAR(100) NULL,
    SkinTypesRef NVARCHAR(200) NULL,
    LanguageRef NVARCHAR(200) NULL,
    DietRef NVARCHAR(200) NULL,
    TraitsJson NVARCHAR(max) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimSpecies_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimSpecies_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimSpecies_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimSpecies_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimSpecies_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimSpecies PRIMARY KEY CLUSTERED (SpeciesKey),
    CONSTRAINT UQ_DimSpecies_SpeciesGuid UNIQUE (SpeciesGuid),
    CONSTRAINT FK_DimSpecies_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_DimSpecies_EntityKey ON dbo.DimSpecies(EntityKey);
CREATE INDEX IX_DimSpecies_RowHash ON dbo.DimSpecies(RowHash);
CREATE UNIQUE INDEX UX_DimSpecies_EntityKey_IsLatest
    ON dbo.DimSpecies(EntityKey)
    WHERE IsLatest = 1;
