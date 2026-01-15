-- DimAppearanceLook: observed character appearance in a work/scene context.
CREATE TABLE dbo.DimAppearanceLook (
    LookKey int IDENTITY(1,1) NOT NULL,
    CharacterKey int NOT NULL,
    WorkKey int NOT NULL,
    SceneKey int NOT NULL,

    LookLabel nvarchar(200) NOT NULL,
    LookType nvarchar(50) NOT NULL, -- Robes|Armor|Uniform|Civilian|Disguise|Other
    PrimaryColorRef nvarchar(100) NULL,
    SecondaryColorRef nvarchar(100) NULL,
    MaterialRef nvarchar(200) NULL,
    InsigniaRef nvarchar(200) NULL,
    HairStyle nvarchar(100) NULL,
    HairColor nvarchar(50) NULL,
    FacialHair nvarchar(100) NULL,
    MakeupOrMarkingsRef nvarchar(200) NULL,
    ConditionRef nvarchar(50) NOT NULL, -- Clean|Damaged|Weathered|Bloodied|Other
    AccessoriesRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    ConfidenceScore decimal(5,4) NULL,
    IsPrimaryLookInScene bit NULL,
    EvidenceRef nvarchar(200) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimAppearanceLook_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimAppearanceLook_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimAppearanceLook_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimAppearanceLook PRIMARY KEY CLUSTERED (LookKey),
    CONSTRAINT FK_DimAppearanceLook_DimCharacter FOREIGN KEY (CharacterKey) REFERENCES dbo.DimCharacter(CharacterKey),
    CONSTRAINT FK_DimAppearanceLook_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey),
    CONSTRAINT FK_DimAppearanceLook_DimScene FOREIGN KEY (SceneKey) REFERENCES dbo.DimScene(SceneKey)
);

CREATE INDEX IX_DimAppearanceLook_CharacterKey ON dbo.DimAppearanceLook(CharacterKey);
CREATE INDEX IX_DimAppearanceLook_WorkKey ON dbo.DimAppearanceLook(WorkKey);
CREATE INDEX IX_DimAppearanceLook_SceneKey ON dbo.DimAppearanceLook(SceneKey);
