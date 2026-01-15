-- BridgeContinuityIssueClaim: links claims to continuity issues with roles.
CREATE TABLE dbo.BridgeContinuityIssueClaim (
    ContinuityIssueKey bigint NOT NULL,
    ClaimKey bigint NOT NULL,

    Role nvarchar(30) NOT NULL, -- Conflicting|Context|Supporting|ResolutionBasis
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeContinuityIssueClaim_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_BridgeContinuityIssueClaim PRIMARY KEY CLUSTERED (ContinuityIssueKey, ClaimKey),
    CONSTRAINT FK_BridgeContinuityIssueClaim_ContinuityIssue FOREIGN KEY (ContinuityIssueKey) REFERENCES dbo.ContinuityIssue(ContinuityIssueKey),
    CONSTRAINT FK_BridgeContinuityIssueClaim_FactClaim FOREIGN KEY (ClaimKey) REFERENCES dbo.FactClaim(ClaimKey)
);

CREATE INDEX IX_BridgeContinuityIssueClaim_ClaimKey ON dbo.BridgeContinuityIssueClaim(ClaimKey);
