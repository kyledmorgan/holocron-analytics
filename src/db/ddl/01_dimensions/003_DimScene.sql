-- DimScene: ordered subdivisions within a work; SceneGuid identifies the logical scene record.
CREATE TABLE dbo.DimScene (
    SceneKey INT IDENTITY(1,1) NOT NULL,
    SceneGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimScene_SceneGuid DEFAULT (NEWID()),

    WorkKey INT NOT NULL,
    SceneOrdinal INT NOT NULL,
    SceneName NVARCHAR(200) NULL,
    SceneType NVARCHAR(50) NOT NULL,
    StartSec INT NULL,
    EndSec INT NULL,
    DurationSec INT NULL,
    LocationHint NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimScene_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimScene_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimScene_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimScene_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimScene_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimScene PRIMARY KEY CLUSTERED (SceneKey),
    CONSTRAINT UQ_DimScene_SceneGuid UNIQUE (SceneGuid),
    CONSTRAINT FK_DimScene_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey)
);

CREATE INDEX IX_DimScene_WorkKey ON dbo.DimScene(WorkKey);
CREATE INDEX IX_DimScene_RowHash ON dbo.DimScene(RowHash);
CREATE UNIQUE INDEX UX_DimScene_WorkKey_SceneOrdinal_IsLatest
    ON dbo.DimScene(WorkKey, SceneOrdinal)
    WHERE IsLatest = 1;
