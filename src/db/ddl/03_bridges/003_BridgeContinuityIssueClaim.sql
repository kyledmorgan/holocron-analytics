-- BridgeContinuityIssueClaim: links claims to continuity issues with roles.
-- BridgeContinuityIssueClaimGuid maintains stable identity; governance metadata records versions.
CREATE TABLE dbo.BridgeContinuityIssueClaim (
    BridgeContinuityIssueClaimKey int IDENTITY(1,1) NOT NULL,
    BridgeContinuityIssueClaimGuid uniqueidentifier NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_BridgeContinuityIssueClaimGuid DEFAULT (NEWSEQUENTIALID()),

    ContinuityIssueKey bigint NOT NULL,
    ClaimKey bigint NOT NULL,

    Role nvarchar(30) NOT NULL, -- Conflicting|Context|Supporting|ResolutionBasis
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
