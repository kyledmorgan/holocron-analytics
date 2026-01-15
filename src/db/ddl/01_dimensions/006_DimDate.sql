-- DimDate: analytical date dimension (one row per day).
CREATE TABLE dbo.DimDate (
    DateKey int NOT NULL, -- YYYYMMDD surrogate
    CalendarDate date NOT NULL,

    [Year] int NOT NULL,
    [Quarter] int NOT NULL,
    [Month] int NOT NULL,
    DayOfMonth int NOT NULL,
    DayOfYear int NOT NULL,
    DayOfWeek int NOT NULL, -- 1-7
    DayName nvarchar(20) NOT NULL,
    MonthName nvarchar(20) NOT NULL,
    ISOWeek int NOT NULL,
    IsWeekend bit NOT NULL,
    IsHoliday bit NOT NULL,
    IsHolidaySpecial bit NOT NULL,
    HolidayName nvarchar(100) NULL,

    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDate_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimDate_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimDate_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimDate PRIMARY KEY CLUSTERED (DateKey)
);
