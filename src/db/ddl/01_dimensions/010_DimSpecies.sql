-- DimSpecies: species/creature taxonomy.
-- SpeciesGuid tracks stable identity; governance metadata captures versioning.
CREATE TABLE dbo.DimSpecies (
    SpeciesKey int IDENTITY(1,1) NOT NULL,
    SpeciesGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimSpecies_SpeciesGuid DEFAULT (NEWSEQUENTIALID()),

    EntityKey int NOT NULL,
    Category nvarchar(50) NOT NULL,
    HomeworldRef nvarchar(200) NULL,
    TypicalLifespanRef nvarchar(100) NULL,
    AverageHeightRef nvarchar(100) NULL,
    SkinTypesRef nvarchar(200) NULL,
    LanguageRef nvarchar(200) NULL,
    DietRef nvarchar(200) NULL,
    TraitsJson nvarchar(max) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimSpecies_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimSpecies_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimSpecies_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimSpecies_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimSpecies_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimSpecies PRIMARY KEY CLUSTERED (SpeciesKey),
    CONSTRAINT UQ_DimSpecies_SpeciesGuid UNIQUE (SpeciesGuid),
    CONSTRAINT FK_DimSpecies_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_DimSpecies_EntityKey ON dbo.DimSpecies(EntityKey);
CREATE INDEX IX_DimSpecies_RowHash ON dbo.DimSpecies(RowHash);
CREATE UNIQUE INDEX UX_DimSpecies_EntityKey_IsLatest
    ON dbo.DimSpecies(EntityKey)
    WHERE IsLatest = 1;
