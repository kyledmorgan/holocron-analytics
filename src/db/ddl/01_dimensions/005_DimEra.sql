-- DimEra: universe-relative era definition (e.g., BBY/ABY-like).
-- EraGuid identifies the era record; versioning columns manage updates.
CREATE TABLE dbo.DimEra (
    EraKey int IDENTITY(1,1) NOT NULL,
    EraGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimEra_EraGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    EraName nvarchar(200) NOT NULL,
    EraCode nvarchar(50) NOT NULL,
    AnchorYear int NOT NULL,
    CalendarModel nvarchar(50) NOT NULL,
    AnchorEventLabel nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimEra_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimEra_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimEra_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEra_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEra_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimEra PRIMARY KEY CLUSTERED (EraKey),
    CONSTRAINT UQ_DimEra_EraGuid UNIQUE (EraGuid),
    CONSTRAINT FK_DimEra_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimEra_FranchiseKey ON dbo.DimEra(FranchiseKey);
CREATE INDEX IX_DimEra_RowHash ON dbo.DimEra(RowHash);
CREATE UNIQUE INDEX UX_DimEra_FranchiseKey_EraCode_IsLatest
    ON dbo.DimEra(FranchiseKey, EraCode)
    WHERE IsLatest = 1;
