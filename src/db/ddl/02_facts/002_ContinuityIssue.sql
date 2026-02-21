-- ContinuityIssue: records continuity discrepancies or ambiguities.
-- ContinuityIssueGuid stabilizes identity; governance metadata tracks versioned records.
CREATE TABLE dbo.ContinuityIssue (
    ContinuityIssueKey BIGINT IDENTITY(1,1) NOT NULL,
    ContinuityIssueGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_ContinuityIssue_ContinuityIssueGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    ContinuityFrameKey INT NOT NULL,
    IssueTypeKey INT NOT NULL,

    IssueSummary NVARCHAR(300) NOT NULL,
    IssueDescription NVARCHAR(2000) NULL,
    Scope NVARCHAR(50) NOT NULL, -- Scene|Work|Franchise
    WorkKey INT NULL,
    SceneKey INT NULL,

    SeverityScore INT NOT NULL,
    SeverityLabel NVARCHAR(20) NOT NULL, -- Low|Med|High|Critical
    DisputeLevel NVARCHAR(20) NOT NULL, -- Low|Med|High
    Status NVARCHAR(30) NOT NULL, -- Open|Explained|Retconned|SplitByFrame|Closed

    ConfidenceScore DECIMAL(5,4) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_ContinuityIssue_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_ContinuityIssue_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_ContinuityIssue_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_ContinuityIssue_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_ContinuityIssue_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    EvidenceBundleGuid UNIQUEIDENTIFIER NULL,
    AttributesJson NVARCHAR(MAX) NULL,

    CONSTRAINT PK_ContinuityIssue PRIMARY KEY CLUSTERED (ContinuityIssueKey),
    CONSTRAINT UQ_ContinuityIssue_ContinuityIssueGuid UNIQUE (ContinuityIssueGuid),
    CONSTRAINT FK_ContinuityIssue_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_ContinuityIssue_DimContinuityFrame FOREIGN KEY (ContinuityFrameKey) REFERENCES dbo.DimContinuityFrame(ContinuityFrameKey),
    CONSTRAINT FK_ContinuityIssue_DimIssueType FOREIGN KEY (IssueTypeKey) REFERENCES dbo.DimIssueType(IssueTypeKey),
    CONSTRAINT FK_ContinuityIssue_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey),
    CONSTRAINT FK_ContinuityIssue_DimScene FOREIGN KEY (SceneKey) REFERENCES dbo.DimScene(SceneKey)
);

CREATE INDEX IX_ContinuityIssue_FranchiseKey ON dbo.ContinuityIssue(FranchiseKey);
CREATE INDEX IX_ContinuityIssue_ContinuityFrameKey ON dbo.ContinuityIssue(ContinuityFrameKey);
CREATE INDEX IX_ContinuityIssue_IssueTypeKey ON dbo.ContinuityIssue(IssueTypeKey);
CREATE INDEX IX_ContinuityIssue_WorkKey ON dbo.ContinuityIssue(WorkKey);
CREATE INDEX IX_ContinuityIssue_SceneKey ON dbo.ContinuityIssue(SceneKey);
CREATE INDEX IX_ContinuityIssue_RowHash ON dbo.ContinuityIssue(RowHash);
CREATE UNIQUE INDEX UX_ContinuityIssue_Franchise_Frame_Summary_IsLatest
    ON dbo.ContinuityIssue(FranchiseKey, ContinuityFrameKey, IssueSummary)
    WHERE IsLatest = 1;
CREATE INDEX IX_ContinuityIssue_IsLatest ON dbo.ContinuityIssue(IsLatest);
CREATE INDEX IX_ContinuityIssue_EvidenceBundleGuid ON dbo.ContinuityIssue(EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
