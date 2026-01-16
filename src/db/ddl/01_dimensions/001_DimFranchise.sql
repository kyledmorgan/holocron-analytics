-- DimFranchise: franchise/universe registry.
-- FranchiseGuid provides stable cross-system identity; governance columns support versioned records.
CREATE TABLE dbo.DimFranchise (
    FranchiseKey int IDENTITY(1,1) NOT NULL,
    FranchiseGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimFranchise_FranchiseGuid DEFAULT (NEWSEQUENTIALID()),

    Name nvarchar(200) NOT NULL,
    UniverseCode nvarchar(50) NOT NULL,
    FranchiseGroup nvarchar(200) NULL,
    OwnerOrRightsHolder nvarchar(200) NULL,
    DefaultContinuityFrame nvarchar(100) NULL,
    Notes nvarchar(1000) NULL,

    IsActive bit NOT NULL CONSTRAINT DF_DimFranchise_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimFranchise_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimFranchise_VersionNum DEFAULT (1),
    RowHash varbinary(32) NOT NULL,
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimFranchise_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimFranchise_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimFranchise PRIMARY KEY CLUSTERED (FranchiseKey),
    CONSTRAINT UQ_DimFranchise_FranchiseGuid UNIQUE (FranchiseGuid)
);

CREATE UNIQUE INDEX UX_DimFranchise_UniverseCode_IsLatest
    ON dbo.DimFranchise(UniverseCode)
    WHERE IsLatest = 1;

CREATE INDEX IX_DimFranchise_IsLatest ON dbo.DimFranchise(IsLatest);
