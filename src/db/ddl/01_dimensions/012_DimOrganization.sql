-- DimOrganization: organization/faction specialization of DimEntity.
-- OrganizationGuid ensures stable identity paired with governance metadata.
CREATE TABLE dbo.DimOrganization (
    OrganizationKey int IDENTITY(1,1) NOT NULL,
    OrganizationGuid uniqueidentifier NOT NULL CONSTRAINT DF_DimOrganization_OrganizationGuid DEFAULT (NEWSEQUENTIALID()),

    EntityKey int NOT NULL,
    OrgType nvarchar(50) NOT NULL,
    Scope nvarchar(50) NOT NULL,
    AlignmentRef nvarchar(200) NULL,
    FoundedRef nvarchar(200) NULL,
    DissolvedRef nvarchar(200) NULL,
    HeadquartersRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    RowHash varbinary(32) NOT NULL,
    IsActive bit NOT NULL CONSTRAINT DF_DimOrganization_IsActive DEFAULT (1),
    IsLatest bit NOT NULL CONSTRAINT DF_DimOrganization_IsLatest DEFAULT (1),
    VersionNum int NOT NULL CONSTRAINT DF_DimOrganization_VersionNum DEFAULT (1),
    ValidFromUtc datetime2(3) NOT NULL CONSTRAINT DF_DimOrganization_ValidFromUtc DEFAULT (SYSUTCDATETIME()),
    ValidToUtc datetime2(3) NULL,
    CreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimOrganization_CreatedUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedUtc datetime2(3) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimOrganization PRIMARY KEY CLUSTERED (OrganizationKey),
    CONSTRAINT UQ_DimOrganization_OrganizationGuid UNIQUE (OrganizationGuid),
    CONSTRAINT FK_DimOrganization_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_DimOrganization_EntityKey ON dbo.DimOrganization(EntityKey);
CREATE INDEX IX_DimOrganization_RowHash ON dbo.DimOrganization(RowHash);
CREATE UNIQUE INDEX UX_DimOrganization_EntityKey_IsLatest
    ON dbo.DimOrganization(EntityKey)
    WHERE IsLatest = 1;
