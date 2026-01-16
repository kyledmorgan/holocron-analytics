-- DimIssueType: taxonomy for continuity issue categories.
-- IssueTypeGuid tracks identity; governance metadata captures versioning.
CREATE TABLE dbo.DimIssueType (
    IssueTypeKey int IDENTITY(1,1) NOT NULL,
    IssueTypeGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimIssueType_IssueTypeGuid DEFAULT (NEWSEQUENTIALID()),

    IssueTypeName nvarchar(200) NOT NULL,
    IssueTypeCode nvarchar(50) NOT NULL,
    Description nvarchar(1000) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimIssueType_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimIssueType_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimIssueType_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimIssueType_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimIssueType_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimIssueType PRIMARY KEY CLUSTERED (IssueTypeKey),
    CONSTRAINT UQ_DimIssueType_IssueTypeGuid UNIQUE (IssueTypeGuid)
);

CREATE INDEX IX_DimIssueType_RowHash ON dbo.DimIssueType(RowHash);
CREATE UNIQUE INDEX UX_DimIssueType_IssueTypeCode_IsLatest
    ON dbo.DimIssueType(IssueTypeCode)
    WHERE IsLatest = 1;
