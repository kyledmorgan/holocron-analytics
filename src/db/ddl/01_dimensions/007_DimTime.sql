-- DimTime: analytical time dimension (hour/minute/second).
CREATE TABLE dbo.DimTime (
    TimeKey int NOT NULL, -- HHMMSS or HHMM
    ClockTime time NOT NULL,

    [Hour] int NOT NULL,
    [Minute] int NOT NULL,
    [Second] int NOT NULL,
    TimeBucket nvarchar(20) NOT NULL, -- Hour|Minute|Second
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTime_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimTime_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimTime_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimTime PRIMARY KEY CLUSTERED (TimeKey)
);
