-- DimWork: catalog of published works (film, episode, book, comic, etc.).
CREATE TABLE dbo.DimWork (
    WorkKey int IDENTITY(1,1) NOT NULL,
    FranchiseKey int NOT NULL,

    WorkType nvarchar(50) NOT NULL, -- Film|Episode|Book|Comic|Game|Short|Web
    Title nvarchar(300) NOT NULL,
    TitleSort nvarchar(300) NULL,
    EditionOrCut nvarchar(200) NULL,
    SeasonEpisode nvarchar(20) NULL,
    SeasonNumber int NULL,
    EpisodeNumber int NULL,
    VolumeOrIssue nvarchar(50) NULL,
    WorkCode nvarchar(50) NULL,

    ReleaseDate date NULL,
    ReleaseDatePrecision nvarchar(20) NOT NULL, -- Exact|Estimated|Range|Unknown
    ReleaseDateEnd date NULL,
    ReleaseRegion nvarchar(100) NULL,

    RuntimeRef nvarchar(50) NULL,
    SynopsisShort nvarchar(1000) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWork_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimWork_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimWork_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimWork PRIMARY KEY CLUSTERED (WorkKey),
    CONSTRAINT FK_DimWork_DimFranchise FOREIGN KEY (FranchiseKey) REFERENCES dbo.DimFranchise(FranchiseKey)
);

CREATE INDEX IX_DimWork_FranchiseKey ON dbo.DimWork(FranchiseKey);
