-- DimDate: analytical date dimension (one row per day).
-- DateGuid maintains traceable identity; governance metadata is consistent across dimensions.
CREATE TABLE dbo.DimDate (
    DateKey INT NOT NULL,
    DateGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimDate_DateGuid DEFAULT (NEWID()),

    CalendarDate date NOT NULL,
    [Year] INT NOT NULL,
    [Quarter] INT NOT NULL,
    [Month] INT NOT NULL,
    DayOfMonth INT NOT NULL,
    DayOfYear INT NOT NULL,
    DayOfWeek INT NOT NULL,
    DayName NVARCHAR(20) NOT NULL,
    MonthName NVARCHAR(20) NOT NULL,
    ISOWeek INT NOT NULL,
    IsWeekend BIT NOT NULL,
    IsHoliday BIT NOT NULL,
    HolidayName NVARCHAR(100) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimDate_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimDate_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimDate_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDate_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDate_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimDate PRIMARY KEY CLUSTERED (DateKey),
    CONSTRAINT UQ_DimDate_DateGuid UNIQUE (DateGuid)
);

CREATE INDEX IX_DimDate_CalendarDate_RowHash ON dbo.DimDate(CalendarDate, RowHash);
CREATE UNIQUE INDEX UX_DimDate_CalendarDate_IsLatest
    ON dbo.DimDate(CalendarDate)
    WHERE IsLatest = 1;
