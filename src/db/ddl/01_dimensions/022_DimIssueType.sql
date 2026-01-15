-- DimIssueType: taxonomy for continuity issue categories.
CREATE TABLE dbo.DimIssueType (
    IssueTypeKey int IDENTITY(1,1) NOT NULL,
    IssueTypeName nvarchar(200) NOT NULL,
    IssueTypeCode nvarchar(50) NOT NULL,
    Description nvarchar(1000) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimIssueType_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimIssueType_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimIssueType_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimIssueType PRIMARY KEY CLUSTERED (IssueTypeKey)
);
