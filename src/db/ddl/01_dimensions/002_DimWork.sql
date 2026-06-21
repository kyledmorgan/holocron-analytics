-- DimWork: catalog of published works (films, episodes, books, comics, etc.).
-- WorkGuid ensures stable identity; governance columns track versioning metadata.
CREATE TABLE dbo.DimWork (
    WorkKey INT IDENTITY(1,1) NOT NULL,
    WorkGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimWork_WorkGuid DEFAULT (NEWID()),

    FranchiseKey INT NOT NULL,
    WorkType NVARCHAR(50) NOT NULL,
    Title NVARCHAR(300) NOT NULL,
    TitleSort NVARCHAR(300) NULL,
    EditionOrCut NVARCHAR(200) NULL,
    SeasonEpisode NVARCHAR(20) NULL,
    SeasonNumber INT NULL,
    EpisodeNumber INT NULL,
    VolumeOrIssue NVARCHAR(50) NULL,
    WorkCode NVARCHAR(50) NULL,

    ReleaseDate date NULL,
    ReleaseDatePrecision NVARCHAR(20) NOT NULL,
    ReleaseDateEnd date NULL,
    ReleaseRegion NVARCHAR(100) NULL,

    RuntimeRef NVARCHAR(50) NULL,
    SynopsisShort NVARCHAR(1000) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimWork_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimWork_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimWork_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimWork_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimWork_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimWork PRIMARY KEY CLUSTERED (WorkKey),
    CONSTRAINT UQ_DimWork_WorkGuid UNIQUE (WorkGuid),
    CONSTRAINT FK_DimWork_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimWork_FranchiseKey ON dbo.DimWork(FranchiseKey);
CREATE INDEX IX_DimWork_RowHash ON dbo.DimWork(RowHash);
CREATE UNIQUE INDEX UX_DimWork_WorkCode_IsLatest
    ON dbo.DimWork(WorkCode)
    WHERE WorkCode IS NOT NULL AND IsLatest = 1;
