-- FactClaim: atomic assertions with provenance and confidence.
-- FactClaimGuid provides stable identity; governance metadata tracks versioned claims.
CREATE TABLE dbo.FactClaim (
    ClaimKey bigint IDENTITY(1,1) NOT NULL,
    FactClaimGuid uniqueidentifier NOT NULL CONSTRAINT DF_FactClaim_FactClaimGuid DEFAULT (NEWSEQUENTIALID()),

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

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_FactClaim_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_FactClaim_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_FactClaim_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_FactClaim_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_FactClaim_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_FactClaim PRIMARY KEY CLUSTERED (ClaimKey),
    CONSTRAINT UQ_FactClaim_FactClaimGuid UNIQUE (FactClaimGuid),
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
CREATE INDEX IX_FactClaim_RowHash ON dbo.FactClaim(RowHash);
CREATE UNIQUE INDEX UX_FactClaim_Subject_Predicate_IsLatest
    ON dbo.FactClaim(SubjectEntityKey, Predicate)
    WHERE IsLatest = 1;
CREATE INDEX IX_FactClaim_IsLatest ON dbo.FactClaim(IsLatest);
