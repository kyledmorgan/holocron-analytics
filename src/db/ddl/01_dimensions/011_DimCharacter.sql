-- DimCharacter: character specialization of DimEntity.
CREATE TABLE dbo.DimCharacter (
    CharacterKey int IDENTITY(1,1) NOT NULL,
    EntityKey int NOT NULL,
    SpeciesKey int NULL,

    Gender nvarchar(50) NULL,
    Pronouns nvarchar(50) NULL,
    BirthRef nvarchar(200) NULL,
    DeathRef nvarchar(200) NULL,
    BirthPlaceRef nvarchar(200) NULL,
    HomeworldRef nvarchar(200) NULL,
    SpeciesNameRef nvarchar(200) NULL,
    HeightRef nvarchar(50) NULL,
    MassRef nvarchar(50) NULL,
    EyeColor nvarchar(50) NULL,
    HairColor nvarchar(50) NULL,
    SkinColor nvarchar(50) NULL,
    DistinguishingMarks nvarchar(200) NULL,
    RoleArchetype nvarchar(50) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimCharacter_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimCharacter_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimCharacter_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimCharacter PRIMARY KEY CLUSTERED (CharacterKey),
    CONSTRAINT FK_DimCharacter_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_DimCharacter_DimSpecies FOREIGN KEY (SpeciesKey) REFERENCES dbo.DimSpecies(SpeciesKey)
);

CREATE INDEX IX_DimCharacter_EntityKey ON dbo.DimCharacter(EntityKey);
CREATE INDEX IX_DimCharacter_SpeciesKey ON dbo.DimCharacter(SpeciesKey);
