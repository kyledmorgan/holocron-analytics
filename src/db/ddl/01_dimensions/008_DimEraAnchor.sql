-- DimEraAnchor: maps universe-relative era anchors to analytical calendar.
CREATE TABLE dbo.DimEraAnchor (
    EraAnchorKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,
    EraKey int NOT NULL,

    AnchorDateKey int NOT NULL,
    AnchorTimeKey int NULL,

    AnchorRule nvarchar(50) NOT NULL, -- SignedYearOffset|RangeOffset|Relative
    AnchorTimezoneOffsetMin int NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEraAnchor_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEraAnchor_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimEraAnchor_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimEraAnchor PRIMARY KEY CLUSTERED (EraAnchorKey),
    CONSTRAINT FK_DimEraAnchor_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_DimEraAnchor_DimEra FOREIGN KEY (EraKey) REFERENCES dbo.DimEra(EraKey),
    CONSTRAINT FK_DimEraAnchor_DimDate FOREIGN KEY (AnchorDateKey) REFERENCES dbo.DimDate(DateKey),
    CONSTRAINT FK_DimEraAnchor_DimTime FOREIGN KEY (AnchorTimeKey) REFERENCES dbo.DimTime(TimeKey)
);

CREATE INDEX IX_DimEraAnchor_FranchiseKey ON dbo.DimEraAnchor(FranchiseKey);
CREATE INDEX IX_DimEraAnchor_EraKey ON dbo.DimEraAnchor(EraKey);
CREATE INDEX IX_DimEraAnchor_AnchorDateKey ON dbo.DimEraAnchor(AnchorDateKey);
CREATE INDEX IX_DimEraAnchor_AnchorTimeKey ON dbo.DimEraAnchor(AnchorTimeKey);
