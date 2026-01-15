-- BridgeEventParticipant: event-to-entity participation with roles.
CREATE TABLE dbo.BridgeEventParticipant (
    EventKey bigint NOT NULL,
    EntityKey int NOT NULL,

    RoleInEvent nvarchar(50) NOT NULL,
    RoleSubtype nvarchar(100) NULL,
    WeightClass nvarchar(20) NOT NULL, -- Primary|Secondary|Background
    ParticipantOrdinal int NULL,
    ParticipationScore decimal(5,4) NULL,

    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventParticipant_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_BridgeEventParticipant_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_BridgeEventParticipant PRIMARY KEY CLUSTERED (EventKey, EntityKey),
    CONSTRAINT FK_BridgeEventParticipant_FactEvent FOREIGN KEY (EventKey) REFERENCES dbo.FactEvent(EventKey),
    CONSTRAINT FK_BridgeEventParticipant_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_BridgeEventParticipant_EntityKey ON dbo.BridgeEventParticipant(EntityKey);
