-- DimFranchise: top-level franchise/universe registry.
CREATE TABLE dbo.DimFranchise (
    FranchiseKey int IDENTITY(1,1) NOT NULL,
    Name nvarchar(200) NOT NULL,
    UniverseCode nvarchar(50) NOT NULL,
    FranchiseGroup nvarchar(200) NULL,
    OwnerOrRightsHolder nvarchar(200) NULL,
    DefaultContinuityFrame nvarchar(100) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimFranchise_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimFranchise_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimFranchise_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimFranchise PRIMARY KEY CLUSTERED (FranchiseKey)
);
