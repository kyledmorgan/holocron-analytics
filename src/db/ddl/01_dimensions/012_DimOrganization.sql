-- DimOrganization: organization/faction specialization of DimEntity.
CREATE TABLE dbo.DimOrganization (
    OrganizationKey int IDENTITY(1,1) NOT NULL,
    EntityKey int NOT NULL,

    OrgType nvarchar(50) NOT NULL, -- Government|Guild|Gang|Order|Military|Corp|Other
    Scope nvarchar(50) NOT NULL, -- Local|Planetary|Sector|Regional|Galaxy|Intergalactic
    AlignmentRef nvarchar(200) NULL,
    FoundedRef nvarchar(200) NULL,
    DissolvedRef nvarchar(200) NULL,
    HeadquartersRef nvarchar(200) NULL,
    Notes nvarchar(1000) NULL,

    SourceSystem nvarchar(100) NULL,
    SourceRef nvarchar(400) NULL,
    IngestBatchId nvarchar(100) NULL,
    RowCreatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimOrganization_RowCreatedUtc DEFAULT (SYSUTCDATETIME()),
    RowUpdatedUtc datetime2(3) NOT NULL CONSTRAINT DF_DimOrganization_RowUpdatedUtc DEFAULT (SYSUTCDATETIME()),
    IsActive bit NOT NULL CONSTRAINT DF_DimOrganization_IsActive DEFAULT (1),
    AttributesJson nvarchar(max) NULL,

    CONSTRAINT PK_DimOrganization PRIMARY KEY CLUSTERED (OrganizationKey),
    CONSTRAINT FK_DimOrganization_DimEntity FOREIGN KEY (EntityKey) REFERENCES dbo.DimEntity(EntityKey)
);

CREATE INDEX IX_DimOrganization_EntityKey ON dbo.DimOrganization(EntityKey);
