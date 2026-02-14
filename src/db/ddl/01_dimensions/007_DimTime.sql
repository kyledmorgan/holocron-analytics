-- DimTime: analytical time dimension (hour/minute/second).
-- TimeGuid provides stable identity; governance columns track active/latest versions.
CREATE TABLE dbo.DimTime (
    TimeKey INT NOT NULL,
    TimeGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimTime_TimeGuid DEFAULT (NEWID()),

    ClockTime time NOT NULL,
    [Hour] INT NOT NULL,
    [Minute] INT NOT NULL,
    [Second] INT NOT NULL,
    TimeBucket NVARCHAR(20) NOT NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimTime_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimTime_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimTime_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimTime_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimTime_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimTime PRIMARY KEY CLUSTERED (TimeKey),
    CONSTRAINT UQ_DimTime_TimeGuid UNIQUE (TimeGuid)
);

CREATE INDEX IX_DimTime_ClockTime_RowHash ON dbo.DimTime(ClockTime, RowHash);
CREATE UNIQUE INDEX UX_DimTime_ClockTime_IsLatest
    ON dbo.DimTime(ClockTime)
    WHERE IsLatest = 1;
