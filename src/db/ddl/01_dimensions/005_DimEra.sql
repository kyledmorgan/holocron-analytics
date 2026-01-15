-- DimEra: universe-relative era definition (e.g., BBY/ABY-like).
CREATE TABLE dbo.DimEra (
    EraKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,

    EraName nvarchar(200) NOT NULL,
    EraCode nvarchar(50) NOT NULL,
    AnchorYear int NOT NULL,
    CalendarModel nvarchar(50) NOT NULL, -- SignedYear|Range|Relative|Hybrid
    AnchorEventLabel nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEra_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEra_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimEra_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimEra PRIMARY KEY CLUSTERED (EraKey),
    CONSTRAINT FK_DimEra_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimEra_FranchiseKey ON dbo.DimEra(FranchiseKey);
