-- DimIssueType: taxonomy for continuity issue categories.
-- IssueTypeGuid tracks identity; governance metadata captures versioning.
CREATE TABLE dbo.DimIssueType (
    IssueTypeKey INT IDENTITY(1,1) NOT NULL,
    IssueTypeGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimIssueType_IssueTypeGuid DEFAULT (NEWID()),

    IssueTypeName NVARCHAR(200) NOT NULL,
    IssueTypeCode NVARCHAR(50) NOT NULL,
    Description NVARCHAR(1000) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimIssueType_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimIssueType_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimIssueType_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimIssueType_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimIssueType_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimIssueType PRIMARY KEY CLUSTERED (IssueTypeKey),
    CONSTRAINT UQ_DimIssueType_IssueTypeGuid UNIQUE (IssueTypeGuid)
);

CREATE INDEX IX_DimIssueType_RowHash ON dbo.DimIssueType(RowHash);
CREATE UNIQUE INDEX UX_DimIssueType_IssueTypeCode_IsLatest
    ON dbo.DimIssueType(IssueTypeCode)
    WHERE IsLatest = 1;
