-- Migration 0023: Create Phase 1 vector schema and runtime tables
-- Idempotent: Only creates schema/tables if they don't exist
--
-- This migration introduces the new `vector` schema for embedding and retrieval,
-- separating it from the `llm` chat runtime schema. This is Phase 1 of the
-- schema refactor (additive, no legacy tables dropped).
--
-- See docs/llm/schema-refactor-migration-notes.md for migration rationale.

-- ============================================================================
-- Create vector schema
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'vector')
BEGIN
    EXEC('CREATE SCHEMA [vector]');
    PRINT 'Schema [vector] created successfully.'
END
ELSE
BEGIN
    PRINT 'Schema [vector] already exists.'
END
GO


-- ============================================================================
-- vector.embedding_space table: First-class embedding space identity
-- ============================================================================
-- This is the critical new concept in the vector schema. An embedding space
-- defines where cosine/dot-product distance is meaningful. Vectors from 
-- different spaces MUST NOT be compared.
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'embedding_space' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[embedding_space] (
        embedding_space_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        provider NVARCHAR(100) NOT NULL,              -- 'ollama', 'openai', etc.
        model_name NVARCHAR(200) NOT NULL,            -- 'nomic-embed-text'
        model_tag NVARCHAR(100) NULL,                 -- 'latest'
        model_digest NVARCHAR(200) NULL,              -- SHA256 of model weights
        dimensions INT NOT NULL,                       -- 768, 1024, etc.
        normalize_flag BIT NOT NULL DEFAULT 1,        -- Whether vectors are L2 normalized
        distance_metric NVARCHAR(50) NOT NULL DEFAULT 'cosine',
        preprocess_policy_json NVARCHAR(MAX) NULL,    -- Text preprocessing config
        transform_ref NVARCHAR(200) NULL,             -- Optional PCA/projection reference
        description NVARCHAR(500) NULL,               -- Human-readable description
        is_active BIT NOT NULL DEFAULT 1,
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_vector_embedding_space PRIMARY KEY CLUSTERED (embedding_space_id),
        CONSTRAINT UQ_vector_embedding_space_identity 
            UNIQUE (provider, model_name, model_tag, model_digest, dimensions)
    );
    PRINT 'Table [vector].[embedding_space] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[embedding_space] already exists.'
END
GO


-- ============================================================================
-- vector.job table: Queue of pending/active vector jobs
-- ============================================================================
-- Mirrors llm.job pattern but for vector operations:
--   CHUNK_SOURCE: Chunk a new source
--   EMBED_CHUNKS: Generate embeddings for chunks  
--   REEMBED_SPACE: Re-embed all chunks in a space
--   RETRIEVE_TEST: Run retrieval benchmark
--   DRIFT_TEST: Compare spaces over time
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'job' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[job] (
        job_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        status VARCHAR(20) NOT NULL DEFAULT 'NEW',
        priority INT NOT NULL DEFAULT 100,
        job_type NVARCHAR(50) NOT NULL,               -- CHUNK_SOURCE, EMBED_CHUNKS, etc.
        input_json NVARCHAR(MAX) NOT NULL,
        embedding_space_id UNIQUEIDENTIFIER NULL,     -- Optional FK to embedding_space
        max_attempts INT NOT NULL DEFAULT 3,
        attempt_count INT NOT NULL DEFAULT 0,
        available_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        locked_by NVARCHAR(200) NULL,
        locked_utc DATETIME2 NULL,
        last_error NVARCHAR(MAX) NULL,
        
        CONSTRAINT PK_vector_job PRIMARY KEY CLUSTERED (job_id),
        CONSTRAINT FK_vector_job_embedding_space FOREIGN KEY (embedding_space_id) 
            REFERENCES [vector].[embedding_space](embedding_space_id),
        CONSTRAINT CK_vector_job_status CHECK (status IN ('NEW', 'RUNNING', 'SUCCEEDED', 'FAILED', 'DEADLETTER')),
        CONSTRAINT CK_vector_job_type CHECK (job_type IN ('CHUNK_SOURCE', 'EMBED_CHUNKS', 'REEMBED_SPACE', 'RETRIEVE_TEST', 'DRIFT_TEST')),
        CONSTRAINT CK_vector_job_attempt CHECK (attempt_count >= 0),
        CONSTRAINT CK_vector_job_max_attempts CHECK (max_attempts >= 1),
        CONSTRAINT CK_vector_job_priority CHECK (priority >= 0)
    );
    PRINT 'Table [vector].[job] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[job] already exists.'
END
GO


-- ============================================================================
-- vector.run table: Tracks individual vector execution attempts
-- ============================================================================
-- Mirrors llm.run pattern for vector operation tracking
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'run' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[run] (
        run_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        job_id UNIQUEIDENTIFIER NOT NULL,
        started_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        completed_utc DATETIME2 NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
        worker_id NVARCHAR(200) NOT NULL,
        embedding_space_id UNIQUEIDENTIFIER NULL,     -- Space used for this run
        endpoint_url NVARCHAR(500) NULL,              -- Provider endpoint
        model_name NVARCHAR(100) NULL,
        model_tag NVARCHAR(100) NULL,
        model_digest NVARCHAR(200) NULL,
        options_json NVARCHAR(MAX) NULL,
        metrics_json NVARCHAR(MAX) NULL,              -- Performance metrics
        error NVARCHAR(MAX) NULL,
        
        CONSTRAINT PK_vector_run PRIMARY KEY CLUSTERED (run_id),
        CONSTRAINT FK_vector_run_job FOREIGN KEY (job_id) REFERENCES [vector].[job](job_id),
        CONSTRAINT FK_vector_run_embedding_space FOREIGN KEY (embedding_space_id) 
            REFERENCES [vector].[embedding_space](embedding_space_id),
        CONSTRAINT CK_vector_run_status CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED'))
    );
    PRINT 'Table [vector].[run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[run] already exists.'
END
GO


-- ============================================================================
-- vector.source_registry table: Index state for incremental indexing
-- ============================================================================
-- Tracks sources that have been indexed with lifecycle and content hash
-- for change detection.
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'source_registry' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[source_registry] (
        source_id NVARCHAR(256) NOT NULL,
        source_type NVARCHAR(100) NOT NULL,           -- lake_text, lake_http, doc, etc.
        source_ref_json NVARCHAR(MAX) NOT NULL,       -- Source identity metadata
        content_sha256 NVARCHAR(64) NULL,             -- Content hash for change detection
        last_indexed_utc DATETIME2 NULL,
        chunk_count INT NULL,
        tags_json NVARCHAR(MAX) NULL,
        status NVARCHAR(50) NOT NULL DEFAULT 'indexed',  -- indexed, pending, error
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_vector_source_registry PRIMARY KEY CLUSTERED (source_id),
        CONSTRAINT CK_vector_source_registry_status CHECK (status IN ('indexed', 'pending', 'error'))
    );
    PRINT 'Table [vector].[source_registry] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[source_registry] already exists.'
END
GO


-- ============================================================================
-- vector.chunk table: Canonical unit of embedding and retrieval
-- ============================================================================
-- Improved version with better source registry linkage and version coupling.
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'chunk' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[chunk] (
        chunk_id NVARCHAR(128) NOT NULL,              -- Deterministic SHA256 hash
        source_id NVARCHAR(256) NULL,                 -- FK to source_registry (nullable for flexibility)
        source_type NVARCHAR(100) NOT NULL,           -- lake_text, lake_http, doc, etc.
        source_ref_json NVARCHAR(MAX) NOT NULL,       -- Source identity metadata
        offsets_json NVARCHAR(MAX) NOT NULL,          -- Byte/line range, chunk index
        content NVARCHAR(MAX) NOT NULL,               -- Bounded text content
        content_sha256 NVARCHAR(64) NOT NULL,         -- Content hash for version coupling
        byte_count BIGINT NOT NULL,
        policy_json NVARCHAR(MAX) NOT NULL,           -- Chunking policy used
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_vector_chunk PRIMARY KEY CLUSTERED (chunk_id),
        CONSTRAINT FK_vector_chunk_source FOREIGN KEY (source_id) 
            REFERENCES [vector].[source_registry](source_id)
    );
    PRINT 'Table [vector].[chunk] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[chunk] already exists.'
END
GO


-- ============================================================================
-- vector.embedding table: Embeddings with lineage and idempotency
-- ============================================================================
-- Key improvements over legacy:
-- - embedding_space_id FK for explicit space identity
-- - input_content_sha256 for version coupling
-- - run_id for execution lineage
-- - Idempotency constraint: (chunk_id, embedding_space_id, input_content_sha256)
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'embedding' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[embedding] (
        embedding_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        chunk_id NVARCHAR(128) NOT NULL,
        embedding_space_id UNIQUEIDENTIFIER NOT NULL,
        input_content_sha256 NVARCHAR(64) NOT NULL,   -- Must match chunk version
        run_id UNIQUEIDENTIFIER NULL,                 -- FK to vector.run
        vector_json NVARCHAR(MAX) NOT NULL,           -- Vector as JSON array
        vector_sha256 NVARCHAR(64) NOT NULL,          -- Vector hash for integrity
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_vector_embedding PRIMARY KEY CLUSTERED (embedding_id),
        CONSTRAINT FK_vector_embedding_chunk FOREIGN KEY (chunk_id) 
            REFERENCES [vector].[chunk](chunk_id),
        CONSTRAINT FK_vector_embedding_space FOREIGN KEY (embedding_space_id) 
            REFERENCES [vector].[embedding_space](embedding_space_id),
        CONSTRAINT FK_vector_embedding_run FOREIGN KEY (run_id) 
            REFERENCES [vector].[run](run_id),
        -- Idempotency constraint: same chunk + space + content version = same embedding
        CONSTRAINT UQ_vector_embedding_idempotent 
            UNIQUE (chunk_id, embedding_space_id, input_content_sha256)
    );
    PRINT 'Table [vector].[embedding] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[embedding] already exists.'
END
GO


-- ============================================================================
-- vector.retrieval table: Retrieval query log for audit/evaluation
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[retrieval] (
        retrieval_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        run_id UNIQUEIDENTIFIER NULL,                 -- Optional FK to vector.run
        embedding_space_id UNIQUEIDENTIFIER NOT NULL, -- Space for query embedding
        query_text NVARCHAR(MAX) NOT NULL,
        query_embedding_json NVARCHAR(MAX) NULL,      -- Optional: store query vector
        top_k INT NOT NULL,
        filters_json NVARCHAR(MAX) NULL,
        policy_json NVARCHAR(MAX) NULL,               -- Rerank/MMR settings
        created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        
        CONSTRAINT PK_vector_retrieval PRIMARY KEY CLUSTERED (retrieval_id),
        CONSTRAINT FK_vector_retrieval_run FOREIGN KEY (run_id) 
            REFERENCES [vector].[run](run_id),
        CONSTRAINT FK_vector_retrieval_space FOREIGN KEY (embedding_space_id) 
            REFERENCES [vector].[embedding_space](embedding_space_id)
    );
    PRINT 'Table [vector].[retrieval] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[retrieval] already exists.'
END
GO


-- ============================================================================
-- vector.retrieval_hit table: Retrieval results for analytics
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.tables t 
    JOIN sys.schemas s ON t.schema_id = s.schema_id 
    WHERE t.name = 'retrieval_hit' AND s.name = 'vector'
)
BEGIN
    CREATE TABLE [vector].[retrieval_hit] (
        retrieval_id UNIQUEIDENTIFIER NOT NULL,
        rank INT NOT NULL,                            -- Position in results (1-indexed)
        chunk_id NVARCHAR(128) NOT NULL,
        score FLOAT NOT NULL,                         -- Similarity score
        metadata_json NVARCHAR(MAX) NULL,             -- Additional metadata
        
        CONSTRAINT PK_vector_retrieval_hit PRIMARY KEY CLUSTERED (retrieval_id, rank),
        CONSTRAINT FK_vector_retrieval_hit_retrieval FOREIGN KEY (retrieval_id) 
            REFERENCES [vector].[retrieval](retrieval_id),
        CONSTRAINT FK_vector_retrieval_hit_chunk FOREIGN KEY (chunk_id) 
            REFERENCES [vector].[chunk](chunk_id)
    );
    PRINT 'Table [vector].[retrieval_hit] created successfully.'
END
ELSE
BEGIN
    PRINT 'Table [vector].[retrieval_hit] already exists.'
END
GO


-- ============================================================================
-- Indexes for embedding_space table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_embedding_space_provider_model' 
    AND object_id = OBJECT_ID('[vector].[embedding_space]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_embedding_space_provider_model 
    ON [vector].[embedding_space] (provider, model_name, is_active);
    PRINT 'Index [IX_vector_embedding_space_provider_model] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_embedding_space_provider_model] already exists.'
END
GO


-- ============================================================================
-- Indexes for job table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_job_status_available' 
    AND object_id = OBJECT_ID('[vector].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_job_status_available 
    ON [vector].[job] (status, available_utc, priority DESC)
    WHERE status IN ('NEW', 'RUNNING');
    PRINT 'Index [IX_vector_job_status_available] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_job_status_available] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_job_type' 
    AND object_id = OBJECT_ID('[vector].[job]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_job_type 
    ON [vector].[job] (job_type, status);
    PRINT 'Index [IX_vector_job_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_job_type] already exists.'
END
GO


-- ============================================================================
-- Indexes for run table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_run_job' 
    AND object_id = OBJECT_ID('[vector].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_run_job 
    ON [vector].[run] (job_id, started_utc DESC);
    PRINT 'Index [IX_vector_run_job] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_run_job] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_run_space' 
    AND object_id = OBJECT_ID('[vector].[run]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_run_space 
    ON [vector].[run] (embedding_space_id, started_utc DESC);
    PRINT 'Index [IX_vector_run_space] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_run_space] already exists.'
END
GO


-- ============================================================================
-- Indexes for source_registry table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_source_registry_type' 
    AND object_id = OBJECT_ID('[vector].[source_registry]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_source_registry_type 
    ON [vector].[source_registry] (source_type, last_indexed_utc DESC);
    PRINT 'Index [IX_vector_source_registry_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_source_registry_type] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_source_registry_content_hash' 
    AND object_id = OBJECT_ID('[vector].[source_registry]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_source_registry_content_hash 
    ON [vector].[source_registry] (content_sha256);
    PRINT 'Index [IX_vector_source_registry_content_hash] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_source_registry_content_hash] already exists.'
END
GO


-- ============================================================================
-- Indexes for chunk table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_chunk_source_type' 
    AND object_id = OBJECT_ID('[vector].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_chunk_source_type 
    ON [vector].[chunk] (source_type);
    PRINT 'Index [IX_vector_chunk_source_type] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_chunk_source_type] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_chunk_source_id' 
    AND object_id = OBJECT_ID('[vector].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_chunk_source_id 
    ON [vector].[chunk] (source_id);
    PRINT 'Index [IX_vector_chunk_source_id] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_chunk_source_id] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_chunk_content_sha256' 
    AND object_id = OBJECT_ID('[vector].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_chunk_content_sha256 
    ON [vector].[chunk] (content_sha256);
    PRINT 'Index [IX_vector_chunk_content_sha256] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_chunk_content_sha256] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_chunk_created' 
    AND object_id = OBJECT_ID('[vector].[chunk]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_chunk_created 
    ON [vector].[chunk] (created_utc DESC);
    PRINT 'Index [IX_vector_chunk_created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_chunk_created] already exists.'
END
GO


-- ============================================================================
-- Indexes for embedding table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_embedding_chunk_space' 
    AND object_id = OBJECT_ID('[vector].[embedding]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_embedding_chunk_space 
    ON [vector].[embedding] (chunk_id, embedding_space_id);
    PRINT 'Index [IX_vector_embedding_chunk_space] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_embedding_chunk_space] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_embedding_space' 
    AND object_id = OBJECT_ID('[vector].[embedding]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_embedding_space 
    ON [vector].[embedding] (embedding_space_id, created_utc DESC);
    PRINT 'Index [IX_vector_embedding_space] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_embedding_space] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_embedding_run' 
    AND object_id = OBJECT_ID('[vector].[embedding]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_embedding_run 
    ON [vector].[embedding] (run_id);
    PRINT 'Index [IX_vector_embedding_run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_embedding_run] already exists.'
END
GO


-- ============================================================================
-- Indexes for retrieval table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_retrieval_run' 
    AND object_id = OBJECT_ID('[vector].[retrieval]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_retrieval_run 
    ON [vector].[retrieval] (run_id, created_utc DESC);
    PRINT 'Index [IX_vector_retrieval_run] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_retrieval_run] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_retrieval_space' 
    AND object_id = OBJECT_ID('[vector].[retrieval]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_retrieval_space 
    ON [vector].[retrieval] (embedding_space_id, created_utc DESC);
    PRINT 'Index [IX_vector_retrieval_space] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_retrieval_space] already exists.'
END
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_retrieval_created' 
    AND object_id = OBJECT_ID('[vector].[retrieval]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_retrieval_created 
    ON [vector].[retrieval] (created_utc DESC);
    PRINT 'Index [IX_vector_retrieval_created] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_retrieval_created] already exists.'
END
GO


-- ============================================================================
-- Indexes for retrieval_hit table
-- ============================================================================
IF NOT EXISTS (
    SELECT * FROM sys.indexes 
    WHERE name = 'IX_vector_retrieval_hit_chunk' 
    AND object_id = OBJECT_ID('[vector].[retrieval_hit]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_vector_retrieval_hit_chunk 
    ON [vector].[retrieval_hit] (chunk_id);
    PRINT 'Index [IX_vector_retrieval_hit_chunk] created successfully.'
END
ELSE
BEGIN
    PRINT 'Index [IX_vector_retrieval_hit_chunk] already exists.'
END
GO


-- ============================================================================
-- End of Migration 0023
-- ============================================================================
PRINT 'Migration 0023_create_vector_schema.sql completed successfully.'
GO
