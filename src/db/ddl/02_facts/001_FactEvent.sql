-- FactEvent: analytical event spine (actions/outcomes).
-- FactEventGuid provides stable identity (random GUID for security).
-- Governance metadata supports versioned records (SCD Type 2 pattern).
--
-- Key Naming Conventions (see docs/agent/db_policies.md):
--   EventKey = internal surrogate key (BIGINT for fact table - high cardinality)
--   FactEventGuid = public-facing stable identifier (random UNIQUEIDENTIFIER)
--
CREATE TABLE dbo.FactEvent (
    EventKey BIGINT IDENTITY(1,1) NOT NULL,
    FactEventGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_FactEvent_FactEventGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    ContinuityFrameKey INT NOT NULL,
    WorkKey INT NOT NULL,
    SceneKey INT NOT NULL,
    ParentEventKey BIGINT NULL,

    EventOrdinal INT NOT NULL,
    EventTypeKey INT NOT NULL,
    LocationKey INT NULL,

    StartSec INT NULL,
    EndSec INT NULL,
    EraKey INT NULL,
    UniverseYearMin INT NULL,
    UniverseYearMax INT NULL,
    DateKey INT NULL,
    TimeKey INT NULL,
    EventTimestampUtc DATETIME2(3) NULL,

    SummaryShort NVARCHAR(1000) NOT NULL,
    SummaryNormalized NVARCHAR(1000) NULL,
    ConfidenceScore DECIMAL(5,4) NOT NULL,
    ExtractionMethod NVARCHAR(20) NOT NULL, -- AI|Manual|Rules|Hybrid
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_FactEvent_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_FactEvent_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_FactEvent_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_FactEvent_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_FactEvent_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(MAX) NULL,

    CONSTRAINT PK_FactEvent PRIMARY KEY CLUSTERED (EventKey),
    CONSTRAINT UQ_FactEvent_FactEventGuid UNIQUE (FactEventGuid),
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
CREATE INDEX IX_FactEvent_RowHash ON dbo.FactEvent(RowHash);
CREATE UNIQUE INDEX UX_FactEvent_Franchise_Work_Scene_Ordinal_IsLatest
    ON dbo.FactEvent(FranchiseKey, WorkKey, SceneKey, EventOrdinal)
    WHERE IsLatest = 1;
CREATE INDEX IX_FactEvent_IsLatest ON dbo.FactEvent(IsLatest);
