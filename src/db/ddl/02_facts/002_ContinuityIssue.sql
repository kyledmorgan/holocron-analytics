-- ContinuityIssue: records continuity discrepancies or ambiguities.
CREATE TABLE dbo.ContinuityIssue (
    ContinuityIssueKey bigint IDENTITY(1,1) NOT NULL,
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

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_ContinuityIssue_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_ContinuityIssue_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_ContinuityIssue_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_ContinuityIssue PRIMARY KEY CLUSTERED (ContinuityIssueKey),
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
