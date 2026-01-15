-- DimSpecies: species/creature taxonomy.
CREATE TABLE dbo.DimSpecies (
    SpeciesKey int IDENTITY(1,1) NOT NULL,
    EntityKey int NOT NULL,

    Category nvarchar(50) NOT NULL, -- Humanoid|Creature|Aquatic|Avian|Reptilian|Other
    HomeworldRef nvarchar(200) NULL,
    TypicalLifespanRef nvarchar(100) NULL,
    AverageHeightRef nvarchar(100) NULL,
    SkinTypesRef nvarchar(200) NULL,
    LanguageRef nvarchar(200) NULL,
    DietRef nvarchar(200) NULL,
    TraitsJson nvarchar(max) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimSpecies_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimSpecies_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimSpecies_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimSpecies PRIMARY KEY CLUSTERED (SpeciesKey),
    CONSTRAINT FK_DimSpecies_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_DimSpecies_EntityKey ON dbo.DimSpecies(EntityKey);
