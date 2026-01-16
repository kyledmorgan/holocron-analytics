-- DimEraAnchor: maps universe-relative era anchors to analytical calendar.
-- EraAnchorGuid is the stable identifier; governance columns capture versioning metadata.
CREATE TABLE dbo.DimEraAnchor (
    EraAnchorKey int IDENTITY(1,1) NOT NULL,
    EraAnchorGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimEraAnchor_EraAnchorGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    EraKey int NOT NULL,
    AnchorDateKey int NOT NULL,
    AnchorTimeKey int NULL,

    AnchorRule nvarchar(50) NOT NULL, -- SignedYearOffset|RangeOffset|Relative
    AnchorTimezoneOffsetMin int NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimEraAnchor_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimEraAnchor_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimEraAnchor_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEraAnchor_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEraAnchor_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
