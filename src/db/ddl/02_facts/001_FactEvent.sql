-- FactEvent: analytical event spine (actions/outcomes).
CREATE TABLE dbo.FactEvent (
    EventKey bigint IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,
    ContinuityFrameKey int NOT NULL,
    WorkKey int NOT NULL,
    SceneKey int NOT NULL,
    ParentEventKey bigint NULL,

    EventOrdinal int NOT NULL,
    EventTypeKey int NOT NULL,
    LocationKey int NULL,

    StartSec int NULL,
    EndSec int NULL,
    EraKey int NULL,
    UniverseYearMin int NULL,
    UniverseYearMax int NULL,
    DateKey int NULL,
    TimeKey int NULL,
    EventTimestampUtc datetime2(3) NULL,

    SummaryShort nvarchar(1000) NOT NULL,
    SummaryNormalized nvarchar(1000) NULL,
    ConfidenceScore decimal(5,4) NOT NULL,
    ExtractionMethod nvarchar(20) NOT NULL, -- AI|Manual|Rules|Hybrid
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_FactEvent_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_FactEvent_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_FactEvent PRIMARY KEY CLUSTERED (EventKey),
    CONSTRAINT FK_FactEvent_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey),
    CONSTRAINT FK_FactEvent_DimContinuityFrame FOREIGN KEY (ContinuityFrameKey) REFERENCES dbo.DimContinuityFrame(ContinuityFrameKey),
    CONSTRAINT FK_FactEvent_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey),
    CONSTRAINT FK_FactEvent_DimScene FOREIGN KEY (SceneKey) REFERENCES dbo.DimScene(SceneKey),
    CONSTRAINT FK_FactEvent_Parent FOREIGN KEY (ParentEventKey) REFERENCES dbo.FactEvent(EventKey),
    CONSTRAINT FK_FactEvent_DimEventType FOREIGN KEY (EventTypeKey) REFERENCES dbo.DimEventType(EventTypeKey),
    CONSTRAINT FK_FactEvent_DimLocation FOREIGN KEY (LocationKey) REFERENCES dbo.DimLocation(LocationKey),
    CONSTRAINT FK_FactEvent_DimEra FOREIGN KEY (EraKey) REFERENCES dbo.DimEra(EraKey),
    CONSTRAINT FK_FactEvent_DimDate FOREIGN KEY (DateKey) REFERENCES dbo.DimDate(DateKey),
    CONSTRAINT FK_FactEvent_DimTime FOREIGN KEY (TimeKey) REFERENCES dbo.DimTime(TimeKey)
);

CREATE INDEX IX_FactEvent_FranchiseKey ON dbo.FactEvent(FranchiseKey);
CREATE INDEX IX_FactEvent_ContinuityFrameKey ON dbo.FactEvent(ContinuityFrameKey);
CREATE INDEX IX_FactEvent_WorkKey ON dbo.FactEvent(WorkKey);
CREATE INDEX IX_FactEvent_SceneKey ON dbo.FactEvent(SceneKey);
CREATE INDEX IX_FactEvent_EventTypeKey ON dbo.FactEvent(EventTypeKey);
CREATE INDEX IX_FactEvent_LocationKey ON dbo.FactEvent(LocationKey);
CREATE INDEX IX_FactEvent_EraKey ON dbo.FactEvent(EraKey);
CREATE INDEX IX_FactEvent_DateKey ON dbo.FactEvent(DateKey);
CREATE INDEX IX_FactEvent_TimeKey ON dbo.FactEvent(TimeKey);
