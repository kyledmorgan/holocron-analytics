-- DimEraAnchor: maps universe-relative era anchors to analytical calendar.
-- EraAnchorGuid is the stable identifier; governance columns capture versioning metadata.
CREATE TABLE dbo.DimEraAnchor (
    EraAnchorKey INT IDENTITY(1,1) NOT NULL,
    EraAnchorGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimEraAnchor_EraAnchorGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    EraKey INT NOT NULL,
    AnchorDateKey INT NOT NULL,
    AnchorTimeKey INT NULL,

    AnchorRule NVARCHAR(50) NOT NULL, -- SignedYearOffset|RangeOffset|Relative
    AnchorTimezoneOffsetMin INT NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimEraAnchor_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimEraAnchor_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimEraAnchor_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEraAnchor_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEraAnchor_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimEraAnchor PRIMARY KEY CLUSTERED (EraAnchorKey),
    CONSTRAINT UQ_DimEraAnchor_EraAnchorGuid UNIQUE (EraAnchorGuid),
    CONSTRAINT FK_DimEraAnchor_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_DimEraAnchor_DimEra FOREIGN KEY (EraKey) REFERENCES dbo.DimEra(EraKey),
    CONSTRAINT FK_DimEraAnchor_DimDate FOREIGN KEY (AnchorDateKey) REFERENCES dbo.DimDate(DateKey),
    CONSTRAINT FK_DimEraAnchor_DimTime FOREIGN KEY (AnchorTimeKey) REFERENCES dbo.DimTime(TimeKey)
);

CREATE INDEX IX_DimEraAnchor_FranchiseKey ON dbo.DimEraAnchor(FranchiseKey);
CREATE INDEX IX_DimEraAnchor_EraKey ON dbo.DimEraAnchor(EraKey);
CREATE INDEX IX_DimEraAnchor_AnchorDateKey ON dbo.DimEraAnchor(AnchorDateKey);
CREATE INDEX IX_DimEraAnchor_RowHash ON dbo.DimEraAnchor(RowHash);
CREATE UNIQUE INDEX UX_DimEraAnchor_EraKey_AnchorDateKey_IsLatest
    ON dbo.DimEraAnchor(EraKey, AnchorDateKey, AnchorTimeKey)
    WHERE IsLatest = 1;
