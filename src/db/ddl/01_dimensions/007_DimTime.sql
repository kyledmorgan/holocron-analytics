-- DimTime: analytical time dimension (hour/minute/second).
-- TimeGuid provides stable identity; governance columns track active/latest versions.
CREATE TABLE dbo.DimTime (
    TimeKey int NOT NULL,
    TimeGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimTime_TimeGuid DEFAULT (NEWSEQUENTIALID()),

    ClockTime time NOT NULL,
    [Hour] int NOT NULL,
    [Minute] int NOT NULL,
    [Second] int NOT NULL,
    TimeBucket nvarchar(20) NOT NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimTime_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimTime_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimTime_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTime_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTime_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimTime PRIMARY KEY CLUSTERED (TimeKey),
    CONSTRAINT UQ_DimTime_TimeGuid UNIQUE (TimeGuid)
);

CREATE INDEX IX_DimTime_ClockTime_RowHash ON dbo.DimTime(ClockTime, RowHash);
CREATE UNIQUE INDEX UX_DimTime_ClockTime_IsLatest
    ON dbo.DimTime(ClockTime)
    WHERE IsLatest = 1;
