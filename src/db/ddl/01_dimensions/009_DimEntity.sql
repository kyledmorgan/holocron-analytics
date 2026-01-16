-- DimEntity: identity registry for characters, orgs, locations, and tech instances.
-- EntityGuid provides stable cross-system identity; governance metadata supports versioned rows.
CREATE TABLE dbo.DimEntity (
    EntityKey int IDENTITY(1,1) NOT NULL,
    EntityGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimEntity_EntityGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    EntityType nvarchar(50) NOT NULL,
    DisplayName nvarchar(200) NOT NULL,
    DisplayNameNormalized nvarchar(200) NULL,
    SortName nvarchar(200) NULL,
    AliasCsv nvarchar(1000) NULL,
    ExternalId nvarchar(200) NULL,
    ExternalIdType nvarchar(50) NULL,
    ExternalUrl nvarchar(400) NULL,
    SummaryShort nvarchar(1000) NULL,
    SummaryLong nvarchar(2000) NULL,
    DescriptionSource nvarchar(200) NULL,
    ConfidenceScore decimal(5,4) NULL,
    IsCanonical bit NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimEntity_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimEntity_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimEntity_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEntity_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEntity_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimEntity PRIMARY KEY CLUSTERED (EntityKey),
    CONSTRAINT UQ_DimEntity_EntityGuid UNIQUE (EntityGuid),
    CONSTRAINT FK_DimEntity_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimEntity_FranchiseKey ON dbo.DimEntity(FranchiseKey);
CREATE INDEX IX_DimEntity_RowHash ON dbo.DimEntity(RowHash);
CREATE UNIQUE INDEX UX_DimEntity_ExternalId_IsLatest
    ON dbo.DimEntity(ExternalId)
    WHERE ExternalId IS NOT NULL AND IsLatest = 1;
CREATE UNIQUE INDEX UX_DimEntity_Franchise_DisplayNameType_IsLatest
    ON dbo.DimEntity(FranchiseKey, DisplayName, EntityType)
    WHERE IsLatest = 1;
