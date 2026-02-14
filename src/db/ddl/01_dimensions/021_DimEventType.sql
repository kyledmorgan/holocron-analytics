-- DimEventType: hierarchical taxonomy for event classification.
-- EventTypeGuid tracks intent while governance metadata supports versioning.
CREATE TABLE dbo.DimEventType (
    EventTypeKey INT IDENTITY(1,1) NOT NULL,
    EventTypeGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimEventType_EventTypeGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    ParentEventTypeKey INT NULL,
    EventTypeName NVARCHAR(200) NOT NULL,
    EventTypeCode NVARCHAR(50) NOT NULL,
    VerbClass NVARCHAR(50) NOT NULL,
    VerbLemma NVARCHAR(100) NOT NULL,
    PolarityDefault NVARCHAR(20) NOT NULL,
    GranularityGuidance NVARCHAR(20) NOT NULL,
    IsLeafType BIT NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimEventType_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimEventType_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimEventType_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEventType_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimEventType_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimEventType PRIMARY KEY CLUSTERED (EventTypeKey),
    CONSTRAINT UQ_DimEventType_EventTypeGuid UNIQUE (EventTypeGuid),
    CONSTRAINT FK_DimEventType_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_DimEventType_Parent FOREIGN KEY (ParentEventTypeKey) REFERENCES dbo.DimEventType(EventTypeKey)
);

CREATE INDEX IX_DimEventType_FranchiseKey ON dbo.DimEventType(FranchiseKey);
CREATE INDEX IX_DimEventType_ParentEventTypeKey ON dbo.DimEventType(ParentEventTypeKey);
CREATE INDEX IX_DimEventType_RowHash ON dbo.DimEventType(RowHash);
CREATE UNIQUE INDEX UX_DimEventType_Franchise_EventTypeCode_IsLatest
    ON dbo.DimEventType(FranchiseKey, EventTypeCode)
    WHERE IsLatest = 1;
