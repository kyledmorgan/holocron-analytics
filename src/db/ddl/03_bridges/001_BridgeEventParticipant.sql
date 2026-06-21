-- BridgeEventParticipant: event-to-entity participation with roles.
-- BridgeEventParticipantGuid stabilizes identity while governance metadata tracks versions.
CREATE TABLE dbo.BridgeEventParticipant (
    BridgeEventParticipantKey INT IDENTITY(1,1) NOT NULL,
    BridgeEventParticipantGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_BridgeEventParticipant_BridgeEventParticipantGuid DEFAULT (NEWID()),

    EventKey BIGINT NOT NULL,
    EntityKey INT NOT NULL,

    RoleInEvent NVARCHAR(50) NOT NULL,
    RoleSubtype NVARCHAR(100) NULL,
    WeightClass NVARCHAR(20) NOT NULL, -- Primary|Secondary|Background
    ParticipantOrdinal INT NULL,
    ParticipationScore DECIMAL(5,4) NULL,

    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_BridgeEventParticipant_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_BridgeEventParticipant_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_BridgeEventParticipant_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_BridgeEventParticipant_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_BridgeEventParticipant_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    EvidenceBundleGuid UNIQUEIDENTIFIER NULL,
    AttributesJson NVARCHAR(MAX) NULL,

    CONSTRAINT PK_BridgeEventParticipant PRIMARY KEY CLUSTERED (BridgeEventParticipantKey),
    CONSTRAINT UQ_BridgeEventParticipant_BridgeEventParticipantGuid UNIQUE (BridgeEventParticipantGuid),
    CONSTRAINT FK_BridgeEventParticipant_FactEvent FOREIGN KEY (EventKey) REFERENCES dbo.FactEvent(EventKey),
    CONSTRAINT FK_BridgeEventParticipant_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_BridgeEventParticipant_EventKey ON dbo.BridgeEventParticipant(EventKey);
CREATE INDEX IX_BridgeEventParticipant_EntityKey ON dbo.BridgeEventParticipant(EntityKey);
CREATE INDEX IX_BridgeEventParticipant_RowHash ON dbo.BridgeEventParticipant(RowHash);
CREATE UNIQUE INDEX UX_BridgeEventParticipant_Event_Entity_Role_IsLatest
    ON dbo.BridgeEventParticipant(EventKey, EntityKey, RoleInEvent)
    WHERE IsLatest = 1;
CREATE INDEX IX_BridgeEventParticipant_IsLatest ON dbo.BridgeEventParticipant(IsLatest);
CREATE INDEX IX_BridgeEventParticipant_EvidenceBundleGuid ON dbo.BridgeEventParticipant(EvidenceBundleGuid)
    WHERE EvidenceBundleGuid IS NOT NULL;
