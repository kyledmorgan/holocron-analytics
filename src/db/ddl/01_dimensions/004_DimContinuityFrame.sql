-- DimContinuityFrame: continuity/canon frame definitions.
-- ContinuityFrameGuid enables cross-system identity; governance columns track versions.
CREATE TABLE dbo.DimContinuityFrame (
    ContinuityFrameKey int IDENTITY(1,1) NOT NULL,
    ContinuityFrameGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimContinuityFrame_ContinuityFrameGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    FrameName nvarchar(100) NOT NULL,
    FrameCode nvarchar(50) NOT NULL,
    AuthorityType nvarchar(50) NOT NULL,
    AuthorityRef nvarchar(200) NULL,
    PolicySummary nvarchar(1000) NULL,
    EffectiveStartDate date NULL,
    EffectiveEndDate date NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimContinuityFrame_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimContinuityFrame_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimContinuityFrame_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimContinuityFrame_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimContinuityFrame_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimContinuityFrame PRIMARY KEY CLUSTERED (ContinuityFrameKey),
    CONSTRAINT UQ_DimContinuityFrame_ContinuityFrameGuid UNIQUE (ContinuityFrameGuid),
    CONSTRAINT FK_DimContinuityFrame_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimContinuityFrame_FranchiseKey ON dbo.DimContinuityFrame(FranchiseKey);
CREATE INDEX IX_DimContinuityFrame_RowHash ON dbo.DimContinuityFrame(RowHash);
CREATE UNIQUE INDEX UX_DimContinuityFrame_FranchiseKey_FrameCode_IsLatest
    ON dbo.DimContinuityFrame(FranchiseKey, FrameCode)
    WHERE IsLatest = 1;
