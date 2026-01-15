-- DimScene: ordered subdivisions within a work.
CREATE TABLE dbo.DimScene (
    SceneKey int IDENTITY(1,1) NOT NULL,
    WorkKey int NOT NULL,

    SceneOrdinal int NOT NULL,
    SceneName nvarchar(200) NULL,
    SceneType nvarchar(50) NOT NULL, -- Act|Chapter|Sequence|Scene
    StartSec int NULL,
    EndSec int NULL,
    DurationSec int NULL,

    LocationHint nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimScene_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimScene_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimScene_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimScene PRIMARY KEY CLUSTERED (SceneKey),
    CONSTRAINT FK_DimScene_DimWork FOREIGN KEY (WorkKey) REFERENCES dbo.DimWork(WorkKey)
);

CREATE INDEX IX_DimScene_WorkKey ON dbo.DimScene(WorkKey);
CREATE INDEX IX_DimScene_WorkKey_SceneOrdinal ON dbo.DimScene(WorkKey, SceneOrdinal);
