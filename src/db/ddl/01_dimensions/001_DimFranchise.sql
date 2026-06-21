-- DimFranchise: franchise/universe registry.
-- FranchiseGuid provides stable cross-system identity; governance columns support versioned records.
CREATE TABLE dbo.DimFranchise (
    FranchiseKey INT IDENTITY(1,1) NOT NULL,
    FranchiseGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimFranchise_FranchiseGuid DEFAULT (NEWID()),

    Name NVARCHAR(200) NOT NULL,
    UniverseCode NVARCHAR(50) NOT NULL,
    FranchiseGroup NVARCHAR(200) NULL,
    OwnerOrRightsHolder NVARCHAR(200) NULL,
    DefaultContinuityFrame NVARCHAR(100) NULL,
    Notes NVARCHAR(1000) NULL,

    IsActive BIT NOT NULL CONSTRAINT DF_DimFranchise_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimFranchise_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimFranchise_VersionNum DEFAULT (1),
    RowHash VARBINARY(32) NOT NULL,
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimFranchise_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimFranchise_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimFranchise PRIMARY KEY CLUSTERED (FranchiseKey),
    CONSTRAINT UQ_DimFranchise_FranchiseGuid UNIQUE (FranchiseGuid)
);

CREATE UNIQUE INDEX UX_DimFranchise_UniverseCode_IsLatest
    ON dbo.DimFranchise(UniverseCode)
    WHERE IsLatest = 1;

CREATE INDEX IX_DimFranchise_IsLatest ON dbo.DimFranchise(IsLatest);
