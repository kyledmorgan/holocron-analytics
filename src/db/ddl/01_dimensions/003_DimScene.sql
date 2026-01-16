-- DimScene: ordered subdivisions within a work; SceneGuid identifies the logical scene record.
CREATE TABLE dbo.DimScene (
    SceneKey int IDENTITY(1,1) NOT NULL,
    SceneGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimScene_SceneGuid DEFAULT (NEWSEQUENTIALID()),

    WorkKey int NOT NULL,
    SceneOrdinal int NOT NULL,
    SceneName nvarchar(200) NULL,
    SceneType nvarchar(50) NOT NULL,
    StartSec int NULL,
    EndSec int NULL,
    DurationSec int NULL,
    LocationHint nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimScene_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimScene_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimScene_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimScene_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimScene_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimScene PRIMARY KEY CLUSTERED (SceneKey),
    CONSTRAINT UQ_DimScene_SceneGuid UNIQUE (SceneGuid),
    CONSTRAINT FK_DimScene_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey)
);

CREATE INDEX IX_DimScene_WorkKey ON dbo.DimScene(WorkKey);
CREATE INDEX IX_DimScene_RowHash ON dbo.DimScene(RowHash);
CREATE UNIQUE INDEX UX_DimScene_WorkKey_SceneOrdinal_IsLatest
    ON dbo.DimScene(WorkKey, SceneOrdinal)
    WHERE IsLatest = 1;
