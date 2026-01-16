-- ContinuityIssue: records continuity discrepancies or ambiguities.
-- ContinuityIssueGuid stabilizes identity; governance metadata tracks versioned records.
CREATE TABLE dbo.ContinuityIssue (
    ContinuityIssueKey bigint IDENTITY(1,1) NOT NULL,
    ContinuityIssueGuid uniqueidentifier NOT NULL CONSTRAINT DF_ContinuityIssue_ContinuityIssueGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    ContinuityFrameKey int NOT NULL,
    IssueTypeKey int NOT NULL,

    IssueSummary nvarchar(300) NOT NULL,
    IssueDescription nvarchar(2000) NULL,
    Scope nvarchar(50) NOT NULL, -- Scene|Work|Franchise
    WorkKey int NULL,
    SceneKey int NULL,

    SeverityScore int NOT NULL,
    SeverityLabel nvarchar(20) NOT NULL, -- Low|Med|High|Critical
    DisputeLevel nvarchar(20) NOT NULL, -- Low|Med|High
    Status nvarchar(30) NOT NULL, -- Open|Explained|Retconned|SplitByFrame|Closed

    ConfidenceScore decimal(5,4) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_ContinuityIssue_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_ContinuityIssue_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_ContinuityIssue_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_ContinuityIssue_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_ContinuityIssue_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
