-- DimDroidInstance: droid-specific extension of DimTechInstance.
-- DroidInstanceGuid keeps stability; versioning columns capture history.
CREATE TABLE dbo.DimDroidInstance (
    DroidInstanceKey INT IDENTITY(1,1) NOT NULL,
    DroidInstanceGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimDroidInstance_DroidInstanceGuid DEFAULT (NEWID()),

    TechInstanceKey INT NOT NULL,
    PersonalityName NVARCHAR(200) NULL,
    MemoryWipeRef NVARCHAR(200) NULL,
    RestrainingBoltFlag BIT NULL,
    PrimaryLanguageRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimDroidInstance_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimDroidInstance_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimDroidInstance_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDroidInstance_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDroidInstance_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimDroidInstance PRIMARY KEY CLUSTERED (DroidInstanceKey),
    CONSTRAINT UQ_DimDroidInstance_DroidInstanceGuid UNIQUE (DroidInstanceGuid),
    CONSTRAINT FK_DimDroidInstance_DimTechInstance FOREIGN KEY (TechInstanceKey) REFERENCES dbo.DimTechInstance(TechInstanceKey)
);

CREATE INDEX IX_DimDroidInstance_TechInstanceKey ON dbo.DimDroidInstance(TechInstanceKey);
CREATE INDEX IX_DimDroidInstance_RowHash ON dbo.DimDroidInstance(RowHash);
CREATE UNIQUE INDEX UX_DimDroidInstance_TechInstanceKey_IsLatest
    ON dbo.DimDroidInstance(TechInstanceKey)
    WHERE IsLatest = 1;
