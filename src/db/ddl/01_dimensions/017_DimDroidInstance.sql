-- DimDroidInstance: droid-specific extension of DimTechInstance.
CREATE TABLE dbo.DimDroidInstance (
    DroidInstanceKey int IDENTITY(1,1) NOT NULL,
    TechInstanceKey int NOT NULL,

    PersonalityName nvarchar(200) NULL,
    MemoryWipeRef nvarchar(200) NULL,
    RestrainingBoltFlag bit NULL,
    PrimaryLanguageRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidInstance_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidInstance_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimDroidInstance_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimDroidInstance PRIMARY KEY CLUSTERED (DroidInstanceKey),
    CONSTRAINT FK_DimDroidInstance_DimTechInstance FOREIGN KEY (TechInstanceKey) REFERENCES dbo.DimTechInstance(TechInstanceKey)
);

CREATE INDEX IX_DimDroidInstance_TechInstanceKey ON dbo.DimDroidInstance(TechInstanceKey);
