-- DimEntity: identity registry for characters, orgs, locations, and tech instances.
-- EntityGuid provides stable cross-system identity (random GUID for security).
-- Governance metadata supports versioned rows (SCD Type 2 pattern).
--
-- Key Naming Conventions (see docs/agent/db_policies.md):
--   EntityKey = internal surrogate key (INT for dimension)
--   EntityGuid = public-facing stable identifier (random UNIQUEIDENTIFIER)
--   ExternalKey = external source system identifier
--
CREATE TABLE dbo.DimEntity (
    EntityKey INT IDENTITY(1,1) NOT NULL,
    EntityGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimEntity_EntityGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    EntityType NVARCHAR(50) NOT NULL,
    DisplayName NVARCHAR(200) NOT NULL,
    DisplayNameNormalized NVARCHAR(200) NULL,
    SortName NVARCHAR(200) NULL,
    AliasCsv NVARCHAR(1000) NULL,
    ExternalKey NVARCHAR(200) NULL,
    ExternalKeyType NVARCHAR(50) NULL,
    ExternalUrl NVARCHAR(400) NULL,
    SummaryShort NVARCHAR(1000) NULL,
    SummaryLong NVARCHAR(2000) NULL,
    DescriptionSource NVARCHAR(200) NULL,
    ConfidenceScore DECIMAL(5,4) NULL,
    IsCanonical BIT NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimEntity_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimEntity_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimEntity_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEntity_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEntity_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(MAX) NULL,

    CONSTRAINT PK_DimEntity PRIMARY KEY CLUSTERED (EntityKey),
    CONSTRAINT UQ_DimEntity_EntityGuid UNIQUE (EntityGuid),
    CONSTRAINT FK_DimEntity_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimEntity_FranchiseKey ON dbo.DimEntity(FranchiseKey);
CREATE INDEX IX_DimEntity_RowHash ON dbo.DimEntity(RowHash);
CREATE UNIQUE INDEX UX_DimEntity_ExternalKey_IsLatest
    ON dbo.DimEntity(ExternalKey)
    WHERE ExternalKey IS NOT NULL AND IsLatest = 1;
CREATE UNIQUE INDEX UX_DimEntity_Franchise_DisplayNameType_IsLatest
    ON dbo.DimEntity(FranchiseKey, DisplayName, EntityType)
    WHERE IsLatest = 1;
