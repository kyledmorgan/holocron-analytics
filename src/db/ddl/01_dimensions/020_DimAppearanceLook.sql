-- DimAppearanceLook: observed character appearance per work/scene.
-- LookGuid is stable identity; governance columns support versioned look records.
CREATE TABLE dbo.DimAppearanceLook (
    LookKey INT IDENTITY(1,1) NOT NULL,
    LookGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimAppearanceLook_LookGuid DEFAULT (NEWID()),

    CharacterKey INT NOT NULL,
    WorkKey INT NOT NULL,
    SceneKey INT NOT NULL,
    LookLabel NVARCHAR(200) NOT NULL,
    LookType NVARCHAR(50) NOT NULL,
    PrimaryColorRef NVARCHAR(100) NULL,
    SecondaryColorRef NVARCHAR(100) NULL,
    MaterialRef NVARCHAR(200) NULL,
    InsigniaRef NVARCHAR(200) NULL,
    HairStyle NVARCHAR(100) NULL,
    HairColor NVARCHAR(50) NULL,
    FacialHair NVARCHAR(100) NULL,
    MakeupOrMarkingsRef NVARCHAR(200) NULL,
    ConditionRef NVARCHAR(50) NOT NULL,
    AccessoriesRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    ConfidenceScore DECIMAL(5,4) NULL,
    IsPrimaryLookInScene BIT NULL,
    EvidenceRef NVARCHAR(200) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimAppearanceLook_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimAppearanceLook_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimAppearanceLook_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimAppearanceLook_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimAppearanceLook_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimAppearanceLook PRIMARY KEY CLUSTERED (LookKey),
    CONSTRAINT UQ_DimAppearanceLook_LookGuid UNIQUE (LookGuid),
    CONSTRAINT FK_DimAppearanceLook_DimCharacter FOREIGN KEY (CharacterKey) REFERENCES dbo.DimCharacter(CharacterKey),
    CONSTRAINT FK_DimAppearanceLook_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey),
    CONSTRAINT FK_DimAppearanceLook_DimScene FOREIGN KEY (SceneKey) REFERENCES dbo.DimScene(SceneKey)
);

CREATE INDEX IX_DimAppearanceLook_CharacterKey ON dbo.DimAppearanceLook(CharacterKey);
CREATE INDEX IX_DimAppearanceLook_WorkKey ON dbo.DimAppearanceLook(WorkKey);
CREATE INDEX IX_DimAppearanceLook_SceneKey ON dbo.DimAppearanceLook(SceneKey);
CREATE INDEX IX_DimAppearanceLook_RowHash ON dbo.DimAppearanceLook(RowHash);
