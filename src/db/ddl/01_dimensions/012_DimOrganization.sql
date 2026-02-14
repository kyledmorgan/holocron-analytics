-- DimOrganization: organization/faction specialization of DimEntity.
-- OrganizationGuid ensures stable identity paired with governance metadata.
CREATE TABLE dbo.DimOrganization (
    OrganizationKey INT IDENTITY(1,1) NOT NULL,
    OrganizationGuid UNIQUEIDENTIFIER NOT NULL CONSTRAINT DF_DimOrganization_OrganizationGuid DEFAULT (NEWID()),

    EntityKey INT NOT NULL,
    OrgType NVARCHAR(50) NOT NULL,
    Scope NVARCHAR(50) NOT NULL,
    AlignmentRef NVARCHAR(200) NULL,
    FoundedRef NVARCHAR(200) NULL,
    DissolvedRef NVARCHAR(200) NULL,
    HeadquartersRef NVARCHAR(200) NULL,
    Notes NVARCHAR(1000) NULL,

    RowHash VARBINARY(32) NOT NULL,
    IsActive BIT NOT NULL CONSTRAINT DF_DimOrganization_IsActive DEFAULT (1),
    IsLatest BIT NOT NULL CONSTRAINT DF_DimOrganization_IsLatest DEFAULT (1),
    VersionNum INT NOT NULL CONSTRAINT DF_DimOrganization_VersionNum DEFAULT (1),
    ValidFromUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimOrganization_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc DATETIME2(3) NULL,
    CreatedUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimOrganization_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc DATETIME2(3) NULL,

    SourceSystem NVARCHAR(100) NULL,
    SourceRef NVARCHAR(400) NULL,
    IngestBatchKey NVARCHAR(100) NULL,
    AttributesJson NVARCHAR(max) NULL,

    CONSTRAINT PK_DimOrganization PRIMARY KEY CLUSTERED (OrganizationKey),
    CONSTRAINT UQ_DimOrganization_OrganizationGuid UNIQUE (OrganizationGuid),
    CONSTRAINT FK_DimOrganization_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_DimOrganization_EntityKey ON dbo.DimOrganization(EntityKey);
CREATE INDEX IX_DimOrganization_RowHash ON dbo.DimOrganization(RowHash);
CREATE UNIQUE INDEX UX_DimOrganization_EntityKey_IsLatest
    ON dbo.DimOrganization(EntityKey)
    WHERE IsLatest = 1;
