-- FactClaim: atomic assertions with provenance and confidence.
-- FactClaimGuid provides stable identity; governance metadata tracks versioned claims.
CREATE TABLE dbo.FactClaim (
    ClaimKey BIGINT IDENTITY(1,1) NOT NULL,
    FactClaimGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_FactClaim_FactClaimGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    ContinuityFrameKey INT NOT NULL,
    ClaimType NVARCHAR(50) NOT NULL, -- Attribute|Relationship|Ordering|Identity|Other
    SubjectEntityKey INT NOT NULL,
    Predicate NVARCHAR(200) NOT NULL,
    ObjectValue NVARCHAR(1000) NOT NULL, -- literal or EntityKey-as-text
    ObjectValueType NVARCHAR(20) NOT NULL, -- EntityRef|String|Number|Date|Range|Other

    WorkKey INT NULL,
    SceneKey INT NULL,

    ConfidenceScore DECIMAL(5,4) NOT NULL,
    EvidenceRef NVARCHAR(200) NULL,
    ExtractionMethod NVARCHAR(20) NOT NULL, -- AI|Manual|Rules|Hybrid
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_FactClaim_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_FactClaim_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_FactClaim_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_FactClaim_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_FactClaim_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    EvidenceBundleGuid UNIQUEIDENTIFIER NULL,
    AttributesJson NVARCHAR(MAX) NULL,

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
CREATE INDEX IX_FactClaim_EvidenceBundleGuid ON dbo.FactClaim(EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
