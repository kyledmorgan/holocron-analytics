-- DimCharacter: character specialization of DimEntity.
-- CharacterGuid provides stable cross-system identity (random GUID).
-- Governance metadata tracks record versions (SCD Type 2 pattern).
--
-- Key Naming Conventions (see docs/agent/db_policies.md):
--   CharacterKey = internal surrogate key (INT for dimension)
--   CharacterGuid = public-facing stable identifier (random UNIQUEIDENTIFIER)
--
CREATE TABLE dbo.DimCharacter (
    CharacterKey INT IDENTITY(1,1) NOT NULL,
    CharacterGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimCharacter_CharacterGuid DEFAULT (NEWID()),

    EntityKey INT NOT NULL,
    SpeciesKey INT NULL,
    Gender NVARCHAR(50) NULL,
    Pronouns NVARCHAR(50) NULL,
    BirthRef NVARCHAR(200) NULL,
    DeathRef NVARCHAR(200) NULL,
    BirthPlaceRef NVARCHAR(200) NULL,
    HomeworldRef NVARCHAR(200) NULL,
    SpeciesNameRef NVARCHAR(200) NULL,
    HeightRef NVARCHAR(50) NULL,
    MassRef NVARCHAR(50) NULL,
    EyeColor NVARCHAR(50) NULL,
    HairColor NVARCHAR(50) NULL,
    SkinColor NVARCHAR(50) NULL,
    DistinguishingMarks NVARCHAR(200) NULL,
    RoleArchetype NVARCHAR(50) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimCharacter_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimCharacter_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimCharacter_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimCharacter_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimCharacter_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(MAX) NULL,

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
