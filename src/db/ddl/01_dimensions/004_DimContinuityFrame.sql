-- DimContinuityFrame: continuity/canon frame definitions.
-- ContinuityFrameGuid enables cross-system identity; governance columns track versions.
CREATE TABLE dbo.DimContinuityFrame (
    ContinuityFrameKey INT IDENTITY(1,1) NOT NULL,
    ContinuityFrameGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimContinuityFrame_ContinuityFrameGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    FrameName NVARCHAR(100) NOT NULL,
    FrameCode NVARCHAR(50) NOT NULL,
    AuthorityType NVARCHAR(50) NOT NULL,
    AuthorityRef NVARCHAR(200) NULL,
    PolicySummary NVARCHAR(1000) NULL,
    EffectiveStartDate date NULL,
    EffectiveEndDate date NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimContinuityFrame_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimContinuityFrame_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimContinuityFrame_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimContinuityFrame_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimContinuityFrame_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimContinuityFrame PRIMARY KEY CLUSTERED (ContinuityFrameKey),
    CONSTRAINT UQ_DimContinuityFrame_ContinuityFrameGuid UNIQUE (ContinuityFrameGuid),
    CONSTRAINT FK_DimContinuityFrame_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimContinuityFrame_FranchiseKey ON dbo.DimContinuityFrame(FranchiseKey);
CREATE INDEX IX_DimContinuityFrame_RowHash ON dbo.DimContinuityFrame(RowHash);
CREATE UNIQUE INDEX UX_DimContinuityFrame_FranchiseKey_FrameCode_IsLatest
    ON dbo.DimContinuityFrame(FranchiseKey, FrameCode)
    WHERE IsLatest = 1;
