-- DimAppearanceLook: observed character appearance per work/scene.
-- LookGuid is stable identity; governance columns support versioned look records.
CREATE TABLE dbo.DimAppearanceLook (
    LookKey int IDENTITY(1,1) NOT NULL,
    LookGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimAppearanceLook_LookGuid DEFAULT (NEWSEQUENTIALID()),

    CharacterKey int NOT NULL,
    WorkKey int NOT NULL,
    SceneKey int NOT NULL,
    LookLabel nvarchar(200) NOT NULL,
    LookType nvarchar(50) NOT NULL,
    PrimaryColorRef nvarchar(100) NULL,
    SecondaryColorRef nvarchar(100) NULL,
    MaterialRef nvarchar(200) NULL,
    InsigniaRef nvarchar(200) NULL,
    HairStyle nvarchar(100) NULL,
    HairColor nvarchar(50) NULL,
    FacialHair nvarchar(100) NULL,
    MakeupOrMarkingsRef nvarchar(200) NULL,
    ConditionRef nvarchar(50) NOT NULL,
    AccessoriesRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    ConfidenceScore decimal(5,4) NULL,
    IsPrimaryLookInScene bit NULL,
    EvidenceRef nvarchar(200) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimAppearanceLook_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimAppearanceLook_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimAppearanceLook_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimAppearanceLook_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimAppearanceLook_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

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
