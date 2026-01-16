-- BridgeEventParticipant: event-to-entity participation with roles.
-- BridgeEventParticipantGuid stabilizes identity while governance metadata tracks versions.
CREATE TABLE dbo.BridgeEventParticipant (
    BridgeEventParticipantKey int IDENTITY(1,1) NOT NULL,
    BridgeEventParticipantGuid uniqueidentifier NOT NULL CONSTRAINT DF_BridgeEventParticipant_BridgeEventParticipantGuid DEFAULT (NEWSEQUENTIALID()),

    EventKey bigint NOT NULL,
    EntityKey int NOT NULL,

    RoleInEvent nvarchar(50) NOT NULL,
    RoleSubtype nvarchar(100) NULL,
    WeightClass nvarchar(20) NOT NULL, -- Primary|Secondary|Background
    ParticipantOrdinal int NULL,
    ParticipationScore decimal(5,4) NULL,

    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_BridgeEventParticipant_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_BridgeEventParticipant_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_BridgeEventParticipant_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventParticipant_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventParticipant_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
