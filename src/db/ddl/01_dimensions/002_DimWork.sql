-- DimWork: catalog of published works (films, episodes, books, comics, etc.).
-- WorkGuid ensures stable identity; governance columns track versioning metadata.
CREATE TABLE dbo.DimWork (
    WorkKey int IDENTITY(1,1) NOT NULL,
    WorkGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimWork_WorkGuid DEFAULT (NEWSEQUENTIALID()),

    FranchiseKey int NOT NULL,
    WorkType nvarchar(50) NOT NULL,
    Title nvarchar(300) NOT NULL,
    TitleSort nvarchar(300) NULL,
    EditionOrCut nvarchar(200) NULL,
    SeasonEpisode nvarchar(20) NULL,
    SeasonNumber int NULL,
    EpisodeNumber int NULL,
    VolumeOrIssue nvarchar(50) NULL,
    WorkCode nvarchar(50) NULL,

    ReleaseDate date NULL,
    ReleaseDatePrecision nvarchar(20) NOT NULL,
    ReleaseDateEnd date NULL,
    ReleaseRegion nvarchar(100) NULL,

    RuntimeRef nvarchar(50) NULL,
    SynopsisShort nvarchar(1000) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimWork_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimWork_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimWork_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWork_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWork_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimWork PRIMARY KEY CLUSTERED (WorkKey),
    CONSTRAINT UQ_DimWork_WorkGuid UNIQUE (WorkGuid),
    CONSTRAINT FK_DimWork_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimWork_FranchiseKey ON dbo.DimWork(FranchiseKey);
CREATE INDEX IX_DimWork_RowHash ON dbo.DimWork(RowHash);
CREATE UNIQUE INDEX UX_DimWork_WorkCode_IsLatest
    ON dbo.DimWork(WorkCode)
    WHERE WorkCode IS NOT NULL AND IsLatest = 1;
