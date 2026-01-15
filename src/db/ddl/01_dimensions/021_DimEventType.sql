-- DimEventType: hierarchical taxonomy for event classification.
CREATE TABLE dbo.DimEventType (
    EventTypeKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,
    ParentEventTypeKey int NULL,

    EventTypeName nvarchar(200) NOT NULL,
    EventTypeCode nvarchar(50) NOT NULL,
    VerbClass nvarchar(50) NOT NULL, -- Physical|Force|Social|Technical|Environmental
    VerbLemma nvarchar(100) NOT NULL,
    PolarityDefault nvarchar(20) NOT NULL, -- Positive|Negative|Neutral|Mixed
    GranularityGuidance nvarchar(20) NOT NULL, -- Coarse|Moderate|Fine
    IsLeafType bit NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEventType_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimEventType_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimEventType_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimEventType PRIMARY KEY CLUSTERED (EventTypeKey),
    CONSTRAINT FK_DimEventType_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_DimEventType_Parent FOREIGN KEY (ParentEventTypeKey) REFERENCES dbo.DimEventType(EventTypeKey)
);

CREATE INDEX IX_DimEventType_FranchiseKey ON dbo.DimEventType(FranchiseKey);
CREATE INDEX IX_DimEventType_ParentEventTypeKey ON dbo.DimEventType(ParentEventTypeKey);
