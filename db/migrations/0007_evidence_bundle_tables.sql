-- Migration 0007: Create evidence bundle tables for Phase 2
-- Idempotent: Only creates tables if they don't exist

-- ============================================================================
-- llm.evidence_bundle table: Tracks evidence bundles used for LLM runs
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'evidence_bundle' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[evidence_bundle] (
        bundle_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        build_version NVARCHAR(20) NOT NULL DEFAULT '2.0',
        policy_json NVARCHAR(MAX) NOT NULL,
        summary_json NVARCHAR(MAX) NOT NULL,
        lake_uri NVARCHAR(1000) NOT NULL,
        
        CONSTRAINT PK_llm_evidence_bundle PRIMARY KEY CLUSTERED (bundle_id)
    );
    PRINT 'Table [llm].[evidence_bundle] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[evidence_bundle] already exists.'
END
GO

-- ============================================================================
-- llm.run_evidence table: Links runs to evidence bundles
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'run_evidence' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[run_evidence] (
        run_id UNIQUEIDENTIFIER NOT NULL,
        bundle_id UNIQUEIDENTIFIER NOT NULL,
        attached_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_llm_run_evidence PRIMARY KEY CLUSTERED (run_id, bundle_id),
        CONSTRAINT FK_llm_run_evidence_run FOREIGN KEY (run_id) REFERENCES [llm].[run](run_id),
        CONSTRAINT FK_llm_run_evidence_bundle FOREIGN KEY (bundle_id) REFERENCES [llm].[evidence_bundle](bundle_id)
    );
    PRINT 'Table [llm].[run_evidence] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[run_evidence] already exists.'
END
GO

-- ============================================================================
-- llm.evidence_item table (optional): Tracks individual evidence items
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'evidence_item' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[evidence_item] (
        item_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        bundle_id UNIQUEIDENTIFIER NOT NULL,
        evidence_id NVARCHAR(200) NOT NULL,
        evidence_type NVARCHAR(100) NOT NULL,
        lake_uri NVARCHAR(1000) NULL,
        byte_count BIGINT NOT NULL,
        content_sha256 NVARCHAR(64) NOT NULL,
        metadata_json NVARCHAR(MAX) NULL,
        
        CONSTRAINT PK_llm_evidence_item PRIMARY KEY CLUSTERED (item_id),
        CONSTRAINT FK_llm_evidence_item_bundle FOREIGN KEY (bundle_id) REFERENCES [llm].[evidence_bundle](bundle_id),
        CONSTRAINT UQ_llm_evidence_item UNIQUE (bundle_id, evidence_id)
    );
    PRINT 'Table [llm].[evidence_item] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[evidence_item] already exists.'
END
GO

-- ============================================================================
-- Indexes for evidence bundle tables
-- ============================================================================

-- Index for bundle lookups by creation date
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_evidence_bundle_created' 
    AND object_id = OBJECT_ID('[llm].[evidence_bundle]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_bundle_created 
    ON [llm].[evidence_bundle] (created_utc DESC);
    PRINT 'Index [IX_llm_evidence_bundle_created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_evidence_bundle_created] already exists.'
END
GO

-- Index for run_evidence lookups by run_id
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_run_evidence_run' 
    AND object_id = OBJECT_ID('[llm].[run_evidence]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_evidence_run 
    ON [llm].[run_evidence] (run_id, attached_utc DESC);
    PRINT 'Index [IX_llm_run_evidence_run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_run_evidence_run] already exists.'
END
GO

-- Index for run_evidence lookups by bundle_id
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_run_evidence_bundle' 
    AND object_id = OBJECT_ID('[llm].[run_evidence]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_run_evidence_bundle 
    ON [llm].[run_evidence] (bundle_id, attached_utc DESC);
    PRINT 'Index [IX_llm_run_evidence_bundle] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_run_evidence_bundle] already exists.'
END
GO

-- Index for evidence_item lookups by bundle_id
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_evidence_item_bundle' 
    AND object_id = OBJECT_ID('[llm].[evidence_item]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_item_bundle 
    ON [llm].[evidence_item] (bundle_id, evidence_type);
    PRINT 'Index [IX_llm_evidence_item_bundle] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_evidence_item_bundle] already exists.'
END
GO

-- Index for evidence_item lookups by type
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_evidence_item_type' 
    AND object_id = OBJECT_ID('[llm].[evidence_item]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_evidence_item_type 
    ON [llm].[evidence_item] (evidence_type);
    PRINT 'Index [IX_llm_evidence_item_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_evidence_item_type] already exists.'
END
GO
