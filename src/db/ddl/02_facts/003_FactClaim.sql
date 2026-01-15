-- FactClaim: atomic assertions with provenance and confidence.
CREATE TABLE dbo.FactClaim (
    ClaimKey bigint IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,
    ContinuityFrameKey int NOT NULL,

    ClaimType nvarchar(50) NOT NULL, -- Attribute|Relationship|Ordering|Identity|Other
    SubjectEntityKey int NOT NULL,
    Predicate nvarchar(200) NOT NULL,
    ObjectValue nvarchar(1000) NOT NULL, -- literal or EntityKey-as-text
    ObjectValueType nvarchar(20) NOT NULL, -- EntityRef|String|Number|Date|Range|Other

    WorkKey int NULL,
    SceneKey int NULL,

    ConfidenceScore decimal(5,4) NOT NULL,
    EvidenceRef nvarchar(200) NULL,
    ExtractionMethod nvarchar(20) NOT NULL, -- AI|Manual|Rules|Hybrid
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_FactClaim_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_FactClaim_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_FactClaim PRIMARY KEY CLUSTERED (ClaimKey),
    CONSTRAINT FK_FactClaim_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_FactClaim_DimContinuityFrame FOREIGN KEY (ContinuityFrameKey) REFERENCES dbo.DimContinuityFrame(ContinuityFrameKey),
    CONSTRAINT FK_FactClaim_DimEntity FOREIGN KEY (SubjectEntityKey) REFERENCES dbo.DimEntity(EntityKey),
    CONSTRAINT FK_FactClaim_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey),
    CONSTRAINT FK_FactClaim_DimScene FOREIGN KEY (SceneKey) REFERENCES dbo.DimScene(SceneKey)
);

CREATE INDEX IX_FactClaim_FranchiseKey ON dbo.FactClaim(FranchiseKey);
CREATE INDEX IX_FactClaim_ContinuityFrameKey ON dbo.FactClaim(ContinuityFrameKey);
CREATE INDEX IX_FactClaim_SubjectEntityKey ON dbo.FactClaim(SubjectEntityKey);
CREATE INDEX IX_FactClaim_WorkKey ON dbo.FactClaim(WorkKey);
CREATE INDEX IX_FactClaim_SceneKey ON dbo.FactClaim(SceneKey);
