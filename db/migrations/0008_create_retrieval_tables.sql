-- Migration 0008: Create Phase 3 retrieval tables (chunks, embeddings, retrieval logs)
-- Idempotent: Only creates tables if they don't exist

-- ============================================================================
-- llm.chunk table: Stores chunked content for retrieval
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'chunk' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[chunk] (
        chunk_id NVARCHAR(128) NOT NULL,
        source_type NVARCHAR(100) NOT NULL,
        source_ref_json NVARCHAR(MAX) NOT NULL,
        offsets_json NVARCHAR(MAX) NOT NULL,
        content NVARCHAR(MAX) NOT NULL,
        content_sha256 NVARCHAR(64) NOT NULL,
        byte_count BIGINT NOT NULL,
        policy_json NVARCHAR(MAX) NOT NULL,
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_llm_chunk PRIMARY KEY CLUSTERED (chunk_id)
    );
    PRINT 'Table [llm].[chunk] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[chunk] already exists.'
END
GO

-- ============================================================================
-- llm.embedding table: Stores embedding vectors for chunks
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'embedding' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[embedding] (
        embedding_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        chunk_id NVARCHAR(128) NOT NULL,
        embedding_model NVARCHAR(200) NOT NULL,
        vector_dim INT NOT NULL,
        vector_json NVARCHAR(MAX) NOT NULL,
        vector_sha256 NVARCHAR(64) NOT NULL,
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_llm_embedding PRIMARY KEY CLUSTERED (embedding_id),
        CONSTRAINT FK_llm_embedding_chunk FOREIGN KEY (chunk_id) REFERENCES [llm].[chunk](chunk_id),
        CONSTRAINT UQ_llm_embedding_chunk_model_vector UNIQUE (chunk_id, embedding_model, vector_sha256)
    );
    PRINT 'Table [llm].[embedding] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[embedding] already exists.'
END
GO

-- ============================================================================
-- llm.retrieval table: Logs retrieval queries for reproducibility
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[retrieval] (
        retrieval_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        run_id UNIQUEIDENTIFIER NULL,
        query_text NVARCHAR(MAX) NOT NULL,
        query_embedding_model NVARCHAR(200) NOT NULL,
        top_k INT NOT NULL,
        filters_json NVARCHAR(MAX) NULL,
        policy_json NVARCHAR(MAX) NULL,
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_llm_retrieval PRIMARY KEY CLUSTERED (retrieval_id),
        CONSTRAINT FK_llm_retrieval_run FOREIGN KEY (run_id) REFERENCES [llm].[run](run_id)
    );
    PRINT 'Table [llm].[retrieval] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[retrieval] already exists.'
END
GO

-- ============================================================================
-- llm.retrieval_hit table: Stores retrieval results for each query
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval_hit' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[retrieval_hit] (
        retrieval_id UNIQUEIDENTIFIER NOT NULL,
        rank INT NOT NULL,
        chunk_id NVARCHAR(128) NOT NULL,
        score FLOAT NOT NULL,
        metadata_json NVARCHAR(MAX) NULL,
        
        CONSTRAINT PK_llm_retrieval_hit PRIMARY KEY CLUSTERED (retrieval_id, rank),
        CONSTRAINT FK_llm_retrieval_hit_retrieval FOREIGN KEY (retrieval_id) REFERENCES [llm].[retrieval](retrieval_id),
        CONSTRAINT FK_llm_retrieval_hit_chunk FOREIGN KEY (chunk_id) REFERENCES [llm].[chunk](chunk_id)
    );
    PRINT 'Table [llm].[retrieval_hit] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[retrieval_hit] already exists.'
END
GO

-- ============================================================================
-- llm.source_registry table: Tracks known sources and their indexing status
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'source_registry' AND s.name = 'llm'
)
BEGIN
    CREATE TABLE [llm].[source_registry] (
        source_id NVARCHAR(256) NOT NULL,
        source_type NVARCHAR(100) NOT NULL,
        source_ref_json NVARCHAR(MAX) NOT NULL,
        content_sha256 NVARCHAR(64) NULL,
        last_indexed_utc DATETIME2 NULL,
        chunk_count INT NULL,
        tags_json NVARCHAR(MAX) NULL,
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_llm_source_registry PRIMARY KEY CLUSTERED (source_id)
    );
    PRINT 'Table [llm].[source_registry] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [llm].[source_registry] already exists.'
END
GO

-- ============================================================================
-- Indexes for chunk table
-- ============================================================================

-- Index for lookups by source_type
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_chunk_source_type' 
    AND object_id = OBJECT_ID('[llm].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_chunk_source_type 
    ON [llm].[chunk] (source_type);
    PRINT 'Index [IX_llm_chunk_source_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_chunk_source_type] already exists.'
END
GO

-- Index for deduplication by content hash
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_chunk_content_sha256' 
    AND object_id = OBJECT_ID('[llm].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_chunk_content_sha256 
    ON [llm].[chunk] (content_sha256);
    PRINT 'Index [IX_llm_chunk_content_sha256] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_chunk_content_sha256] already exists.'
END
GO

-- Index for chunk creation date
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_chunk_created' 
    AND object_id = OBJECT_ID('[llm].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_chunk_created 
    ON [llm].[chunk] (created_utc DESC);
    PRINT 'Index [IX_llm_chunk_created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_chunk_created] already exists.'
END
GO

-- ============================================================================
-- Indexes for embedding table
-- ============================================================================

-- Index for lookups by chunk_id
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_embedding_chunk' 
    AND object_id = OBJECT_ID('[llm].[embedding]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_embedding_chunk 
    ON [llm].[embedding] (chunk_id, embedding_model);
    PRINT 'Index [IX_llm_embedding_chunk] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_embedding_chunk] already exists.'
END
GO

-- Index for lookups by embedding model
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_embedding_model' 
    AND object_id = OBJECT_ID('[llm].[embedding]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_embedding_model 
    ON [llm].[embedding] (embedding_model, created_utc DESC);
    PRINT 'Index [IX_llm_embedding_model] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_embedding_model] already exists.'
END
GO

-- ============================================================================
-- Indexes for retrieval table
-- ============================================================================

-- Index for lookups by run_id
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_retrieval_run' 
    AND object_id = OBJECT_ID('[llm].[retrieval]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_retrieval_run 
    ON [llm].[retrieval] (run_id, created_utc DESC);
    PRINT 'Index [IX_llm_retrieval_run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_retrieval_run] already exists.'
END
GO

-- Index for retrieval by date
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_retrieval_created' 
    AND object_id = OBJECT_ID('[llm].[retrieval]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_retrieval_created 
    ON [llm].[retrieval] (created_utc DESC);
    PRINT 'Index [IX_llm_retrieval_created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_retrieval_created] already exists.'
END
GO

-- ============================================================================
-- Indexes for retrieval_hit table
-- ============================================================================

-- Index for lookups by chunk_id
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_retrieval_hit_chunk' 
    AND object_id = OBJECT_ID('[llm].[retrieval_hit]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_retrieval_hit_chunk 
    ON [llm].[retrieval_hit] (chunk_id);
    PRINT 'Index [IX_llm_retrieval_hit_chunk] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_retrieval_hit_chunk] already exists.'
END
GO

-- ============================================================================
-- Indexes for source_registry table
-- ============================================================================

-- Index for lookups by source_type
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_source_registry_type' 
    AND object_id = OBJECT_ID('[llm].[source_registry]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_source_registry_type 
    ON [llm].[source_registry] (source_type, last_indexed_utc DESC);
    PRINT 'Index [IX_llm_source_registry_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_source_registry_type] already exists.'
END
GO

-- Index for lookups by content hash
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_llm_source_registry_content_hash' 
    AND object_id = OBJECT_ID('[llm].[source_registry]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_source_registry_content_hash 
    ON [llm].[source_registry] (content_sha256);
    PRINT 'Index [IX_llm_source_registry_content_hash] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_llm_source_registry_content_hash] already exists.'
END
GO
