-- DimContinuityFrame: continuity/canon frame definitions.
CREATE TABLE dbo.DimContinuityFrame (
    ContinuityFrameKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,

    FrameName nvarchar(100) NOT NULL, -- Canon|Legends|AltCut|Fan|Other
    FrameCode nvarchar(50) NOT NULL,
    AuthorityType nvarchar(50) NOT NULL, -- Publisher|Creator|Community
    AuthorityRef nvarchar(200) NULL,
    PolicySummary nvarchar(1000) NULL,
    EffectiveStartDate date NULL,
    EffectiveEndDate date NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimContinuityFrame_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimContinuityFrame_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimContinuityFrame_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimContinuityFrame PRIMARY KEY CLUSTERED (ContinuityFrameKey),
    CONSTRAINT FK_DimContinuityFrame_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimContinuityFrame_FranchiseKey ON dbo.DimContinuityFrame(FranchiseKey);
