-- DimCharacter: character specialization of DimEntity.
-- CharacterGuid keeps identity stable; governance metadata tracks record versions.
CREATE TABLE dbo.DimCharacter (
    CharacterKey int IDENTITY(1,1) NOT NULL,
    CharacterGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimCharacter_CharacterGuid DEFAULT (NEWSEQUENTIALID()),

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

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimCharacter_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimCharacter_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimCharacter_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimCharacter_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimCharacter_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimCharacter PRIMARY KEY CLUSTERED (CharacterKey),
    CONSTRAINT UQ_DimCharacter_CharacterGuid UNIQUE (CharacterGuid),
    CONSTRAINT FK_DimCharacter_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_DimCharacter_DimSpecies FOREIGN KEY (SpeciesKey) REFERENCES dbo.DimSpecies(SpeciesKey)
);

CREATE INDEX IX_DimCharacter_EntityKey ON dbo.DimCharacter(EntityKey);
CREATE INDEX IX_DimCharacter_SpeciesKey ON dbo.DimCharacter(SpeciesKey);
CREATE INDEX IX_DimCharacter_RowHash ON dbo.DimCharacter(RowHash);
CREATE UNIQUE INDEX UX_DimCharacter_EntityKey_IsLatest
    ON dbo.DimCharacter(EntityKey)
    WHERE IsLatest = 1;
