-- DimDroidInstance: droid-specific extension of DimTechInstance.
-- DroidInstanceGuid keeps stability; versioning columns capture history.
CREATE TABLE dbo.DimDroidInstance (
    DroidInstanceKey int IDENTITY(1,1) NOT NULL,
    DroidInstanceGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimDroidInstance_DroidInstanceGuid DEFAULT (NEWSEQUENTIALID()),

    TechInstanceKey int NOT NULL,
    PersonalityName nvarchar(200) NULL,
    MemoryWipeRef nvarchar(200) NULL,
    RestrainingBoltFlag bit NULL,
    PrimaryLanguageRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimDroidInstance_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimDroidInstance_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimDroidInstance_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidInstance_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDroidInstance_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimDroidInstance PRIMARY KEY CLUSTERED (DroidInstanceKey),
    CONSTRAINT UQ_DimDroidInstance_DroidInstanceGuid UNIQUE (DroidInstanceGuid),
    CONSTRAINT FK_DimDroidInstance_DimTechInstance FOREIGN KEY (TechInstanceKey) REFERENCES dbo.DimTechInstance(TechInstanceKey)
);

CREATE INDEX IX_DimDroidInstance_TechInstanceKey ON dbo.DimDroidInstance(TechInstanceKey);
CREATE INDEX IX_DimDroidInstance_RowHash ON dbo.DimDroidInstance(RowHash);
CREATE UNIQUE INDEX UX_DimDroidInstance_TechInstanceKey_IsLatest
    ON dbo.DimDroidInstance(TechInstanceKey)
    WHERE IsLatest = 1;
