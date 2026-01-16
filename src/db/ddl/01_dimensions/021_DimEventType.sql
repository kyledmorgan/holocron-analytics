-- DimEventType: hierarchical taxonomy for event classification.
-- EventTypeGuid tracks intent while governance metadata supports versioning.
CREATE TABLE dbo.DimEventType (
    EventTypeKey int IDENTITY(1,1) NOT NULL,
    EventTypeGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimEventType_EventTypeGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    ParentEventTypeKey int NULL,
    EventTypeName nvarchar(200) NOT NULL,
    EventTypeCode nvarchar(50) NOT NULL,
    VerbClass nvarchar(50) NOT NULL,
    VerbLemma nvarchar(100) NOT NULL,
    PolarityDefault nvarchar(20) NOT NULL,
    GranularityGuidance nvarchar(20) NOT NULL,
    IsLeafType bit NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimEventType_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimEventType_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimEventType_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEventType_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEventType_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
