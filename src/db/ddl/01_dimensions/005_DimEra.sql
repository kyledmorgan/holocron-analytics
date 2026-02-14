-- DimEra: universe-relative era definition (e.g., BBY/ABY-like).
-- EraGuid identifies the era record; versioning columns manage updates.
CREATE TABLE dbo.DimEra (
    EraKey INT IDENTITY(1,1) NOT NULL,
    EraGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimEra_EraGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    EraName NVARCHAR(200) NOT NULL,
    EraCode NVARCHAR(50) NOT NULL,
    AnchorYear INT NOT NULL,
    CalendarModel NVARCHAR(50) NOT NULL,
    AnchorEventLabel NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimEra_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimEra_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimEra_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEra_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEra_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimEra PRIMARY KEY CLUSTERED (EraKey),
    CONSTRAINT UQ_DimEra_EraGuid UNIQUE (EraGuid),
    CONSTRAINT FK_DimEra_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimEra_FranchiseKey ON dbo.DimEra(FranchiseKey);
CREATE INDEX IX_DimEra_RowHash ON dbo.DimEra(RowHash);
CREATE UNIQUE INDEX UX_DimEra_FranchiseKey_EraCode_IsLatest
    ON dbo.DimEra(FranchiseKey, EraCode)
    WHERE IsLatest = 1;
