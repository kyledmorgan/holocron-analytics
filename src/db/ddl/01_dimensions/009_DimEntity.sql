-- DimEntity: identity registry for characters, orgs, locations, tech instances, etc.
CREATE TABLE dbo.DimEntity (
    EntityKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,

    EntityType nvarchar(50) NOT NULL, -- Character|Org|Species|Location|TechInstance|Other
    DisplayName nvarchar(200) NOT NULL,
    DisplayNameNormalized nvarchar(200) NULL,
    SortName nvarchar(200) NULL,
    AliasCsv nvarchar(1000) NULL,
    ExternalId nvarchar(200) NULL,
    ExternalIdType nvarchar(50) NULL, -- MediaWikiPageId|Slug|Other
    ExternalUrl nvarchar(400) NULL,
    SummaryShort nvarchar(1000) NULL,
    SummaryLong nvarchar(2000) NULL,
    DescriptionSource nvarchar(200) NULL,
    ConfidenceScore decimal(5,4) NULL,
    IsCanonical bit NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEntity_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEntity_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimEntity_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimEntity PRIMARY KEY CLUSTERED (EntityKey),
    CONSTRAINT FK_DimEntity_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimEntity_FranchiseKey ON dbo.DimEntity(FranchiseKey);
CREATE INDEX IX_DimEntity_DisplayName ON dbo.DimEntity(DisplayName);
