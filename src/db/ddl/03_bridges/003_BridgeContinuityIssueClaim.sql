-- BridgeContinuityIssueClaim: links claims to continuity issues with roles.
-- BridgeContinuityIssueClaimGuid maintains stable identity; governance metadata records versions.
CREATE TABLE dbo.BridgeContinuityIssueClaim (
    BridgeContinuityIssueClaimKey INT IDENTITY(1,1) NOT NULL,
    BridgeContinuityIssueClaimGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_BridgeContinuityIssueClaimGuid DEFAULT (NEWID()),

    ContinuityIssueKey BIGINT NOT NULL,
    ClaimKey BIGINT NOT NULL,

    Role NVARCHAR(30) NOT NULL, -- Conflicting|Context|Supporting|ResolutionBasis
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_BridgeContinuityIssueClaim PRIMARY KEY CLUSTERED (BridgeContinuityIssueClaimKey),
    CONSTRAINT UQ_BridgeContinuityIssueClaim_BridgeContinuityIssueClaimGuid UNIQUE (BridgeContinuityIssueClaimGuid),
    CONSTRAINT FK_BridgeContinuityIssueClaim_ContinuityIssue FOREIGN KEY (ContinuityIssueKey) REFERENCES dbo.ContinuityIssue(ContinuityIssueKey),
    CONSTRAINT FK_BridgeContinuityIssueClaim_FactClaim FOREIGN KEY (ClaimKey) REFERENCES dbo.FactClaim(ClaimKey)
);

CREATE INDEX IX_BridgeContinuityIssueClaim_ClaimKey ON dbo.BridgeContinuityIssueClaim(ClaimKey);
CREATE INDEX IX_BridgeContinuityIssueClaim_RowHash ON dbo.BridgeContinuityIssueClaim(RowHash);
CREATE INDEX IX_BridgeContinuityIssueClaim_ContinuityIssueKey ON dbo.BridgeContinuityIssueClaim(ContinuityIssueKey);
CREATE UNIQUE INDEX UX_BridgeContinuityIssueClaim_IssueClaim_IsLatest
    ON dbo.BridgeContinuityIssueClaim(ContinuityIssueKey, ClaimKey)
    WHERE IsLatest = 1;
CREATE INDEX IX_BridgeContinuityIssueClaim_IsLatest ON dbo.BridgeContinuityIssueClaim(IsLatest);
