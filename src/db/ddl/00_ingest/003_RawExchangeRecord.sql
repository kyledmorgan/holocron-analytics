-- Create lake schema for raw exchange records
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'lake')
BEGIN
    EXEC('CREATE SCHEMA lake')
END
GO

-- Create RawExchangeRecord table for snapshot/interchange data
-- This table stores the ExchangeRecord envelope for bidirectional sync with JSON

IF OBJECT_ID('lake.RawExchangeRecord', 'U') IS NOT NULL
    DROP TABLE lake.RawExchangeRecord;
GO

CREATE TABLE lake.RawExchangeRecord (
    -- Primary key
    exchange_id UNIQUEIDENTIFIER NOT NULL,
    
    -- Exchange metadata
    exchange_type NVARCHAR(50) NOT NULL,      -- http, mediawiki, openalex, llm, file
    source_system NVARCHAR(100) NOT NULL,     -- e.g., wookieepedia, openalex, local_llm
    entity_type NVARCHAR(100) NOT NULL,       -- e.g., page, work, completion
    natural_key NVARCHAR(500) NULL,           -- Stable identifier if available (page_id, DOI)
    
    -- Timestamps
    observed_at_utc DATETIME2 NOT NULL,
    
    -- Content hash for deduplication and delta sync
    content_sha256 CHAR(64) NOT NULL,
    
    -- Full envelope payload as JSON
    payload_json NVARCHAR(MAX) NOT NULL,
    
    -- Schema version for forward compatibility
    schema_version INT NOT NULL DEFAULT 1,
    
    -- Audit/tracking
    created_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    
    -- Constraints
    CONSTRAINT PK_RawExchangeRecord PRIMARY KEY CLUSTERED (exchange_id),
    CONSTRAINT CK_RawExchangeRecord_HashLength CHECK (LEN(content_sha256) = 64)
);
GO

-- Index for fast hash lookups (delta sync)
CREATE UNIQUE NONCLUSTERED INDEX IX_RawExchangeRecord_ContentHash
    ON lake.RawExchangeRecord (content_sha256);
GO

-- Index for natural key lookups (conflict detection)
CREATE NONCLUSTERED INDEX IX_RawExchangeRecord_NaturalKey
    ON lake.RawExchangeRecord (source_system, entity_type, natural_key)
    WHERE natural_key IS NOT NULL;
GO

-- Index for source/entity filtering
CREATE NONCLUSTERED INDEX IX_RawExchangeRecord_SourceEntity
    ON lake.RawExchangeRecord (source_system, entity_type, observed_at_utc DESC);
GO

-- Index for temporal queries
CREATE NONCLUSTERED INDEX IX_RawExchangeRecord_ObservedAt
    ON lake.RawExchangeRecord (observed_at_utc DESC);
GO
