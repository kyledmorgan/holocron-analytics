-- DimDate: analytical date dimension (one row per day).
-- DateGuid maintains traceable identity; governance metadata is consistent across dimensions.
CREATE TABLE dbo.DimDate (
    DateKey int NOT NULL,
    DateGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimDate_DateGuid DEFAULT (NEWSEQUENTIALID()),

    CalendarDate date NOT NULL,
    [Year] int NOT NULL,
    [Quarter] int NOT NULL,
    [Month] int NOT NULL,
    DayOfMonth int NOT NULL,
    DayOfYear int NOT NULL,
    DayOfWeek int NOT NULL,
    DayName nvarchar(20) NOT NULL,
    MonthName nvarchar(20) NOT NULL,
    ISOWeek int NOT NULL,
    IsWeekend bit NOT NULL,
    IsHoliday bit NOT NULL,
    HolidayName nvarchar(100) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimDate_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimDate_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimDate_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDate_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDate_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimDate PRIMARY KEY CLUSTERED (DateKey),
    CONSTRAINT UQ_DimDate_DateGuid UNIQUE (DateGuid)
);

CREATE INDEX IX_DimDate_CalendarDate_RowHash ON dbo.DimDate(CalendarDate, RowHash);
CREATE UNIQUE INDEX UX_DimDate_CalendarDate_IsLatest
    ON dbo.DimDate(CalendarDate)
    WHERE IsLatest = 1;
