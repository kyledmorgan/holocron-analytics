-- ============================================================================
-- LEGACY SCHEMA SNAPSHOT: LLM Vector Subsystem Tables
-- ============================================================================
-- 
-- THIS FILE IS A HISTORICAL REFERENCE ONLY - DO NOT EXECUTE
-- 
-- Purpose:
--   This file documents the legacy vector-related tables that were originally
--   created in the `llm` schema as part of Phase 3 (Retrieval Augmented 
--   Generation) development. These tables are being deprecated and replaced
--   by a new `vector` schema as part of the schema refactor to split the
--   Holocron database into two independent runtimes:
--
--     - `llm` schema: Chat/interrogation runtime (text-in → text-out)
--     - `vector` schema: Embedding & retrieval runtime (text-in → vectors-out)
--
-- Background:
--   The original design placed embedding and retrieval functionality alongside
--   the chat/interrogation runtime in a single `llm` schema. As the project
--   evolved, it became clear that these are fundamentally different workloads:
--
--   - Chat runtime: Processes text prompts, generates text responses, tracks
--     evidence bundles, produces artifacts stored in the data lake.
--   
--   - Vector runtime: Chunks content, generates embeddings, supports multi-model
--     experiments, logs retrievals for evaluation and analytics.
--
--   The new `vector` schema provides:
--   - First-class `embedding_space` identity for multi-model experimentation
--   - Stronger version coupling (input_content_sha256 + run lineage)
--   - Idempotency constraints to prevent stale vector reuse
--   - Separate queue/run lifecycle for vector operations
--
-- Migration Status:
--   As of this snapshot, these tables have minimal production usage and can
--   be safely deprecated. The vector subsystem will be rebuilt cleanly in
--   the new `vector` schema (Phase 1 of the refactor).
--
-- Created: 2026-02-10
-- Migration: 0008_create_retrieval_tables.sql
-- ============================================================================

-- ############################################################################
-- SECTION 1: llm.chunk
-- ############################################################################
-- 
-- Purpose:
--   Stores chunked content units for retrieval. Each chunk represents a
--   bounded segment of source text that can be embedded and searched.
--
-- Why it's being replaced:
--   - No explicit embedding space identity (model mixing risk)
--   - No input version coupling for idempotent re-embedding
--   - Lacks source registry integration for incremental indexing
--
-- New replacement: vector.chunk
--   The new table adds:
--   - Stronger source registry linkage
--   - content_sha256 used for embedding version coupling
--   - Better support for diverse source types (SQL results, contracts, etc.)
--
-- ============================================================================
/*
CREATE TABLE [llm].[chunk] (
    chunk_id NVARCHAR(128) NOT NULL,           -- Deterministic SHA256 hash
    source_type NVARCHAR(100) NOT NULL,         -- lake_text, lake_http, doc, etc.
    source_ref_json NVARCHAR(MAX) NOT NULL,     -- Source identity metadata
    offsets_json NVARCHAR(MAX) NOT NULL,        -- Byte/line range, chunk index
    content NVARCHAR(MAX) NOT NULL,             -- Bounded text content
    content_sha256 NVARCHAR(64) NOT NULL,       -- Content hash for deduplication
    byte_count BIGINT NOT NULL,                 -- Size in bytes
    policy_json NVARCHAR(MAX) NOT NULL,         -- Chunking policy used
    created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT PK_llm_chunk PRIMARY KEY CLUSTERED (chunk_id)
);

-- Indexes for llm.chunk
CREATE NONCLUSTERED INDEX IX_llm_chunk_source_type 
    ON [llm].[chunk] (source_type);
CREATE NONCLUSTERED INDEX IX_llm_chunk_content_sha256 
    ON [llm].[chunk] (content_sha256);
CREATE NONCLUSTERED INDEX IX_llm_chunk_created 
    ON [llm].[chunk] (created_utc DESC);
*/


-- ############################################################################
-- SECTION 2: llm.embedding
-- ############################################################################
-- 
-- Purpose:
--   Stores embedding vectors for chunks. Each embedding represents a chunk
--   transformed into a high-dimensional vector by an embedding model.
--
-- Why it's being replaced:
--   - `embedding_model` is a simple string, no first-class space identity
--   - No `input_content_sha256` coupling to detect stale vectors
--   - No `run_id` lineage for reproducibility
--   - Uniqueness constraint doesn't prevent mixing incompatible spaces
--
-- New replacement: vector.embedding
--   The new table adds:
--   - `embedding_space_id` FK for explicit space identity
--   - `input_content_sha256` for version coupling
--   - `run_id` for execution lineage
--   - Uniqueness constraint: (chunk_id, embedding_space_id, input_content_sha256)
--
-- ============================================================================
/*
CREATE TABLE [llm].[embedding] (
    embedding_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    chunk_id NVARCHAR(128) NOT NULL,            -- FK to chunk
    embedding_model NVARCHAR(200) NOT NULL,     -- Model name (no space identity)
    vector_dim INT NOT NULL,                     -- Dimensionality
    vector_json NVARCHAR(MAX) NOT NULL,         -- Vector as JSON array
    vector_sha256 NVARCHAR(64) NOT NULL,        -- Vector hash for integrity
    created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT PK_llm_embedding PRIMARY KEY CLUSTERED (embedding_id),
    CONSTRAINT FK_llm_embedding_chunk FOREIGN KEY (chunk_id) 
        REFERENCES [llm].[chunk](chunk_id),
    CONSTRAINT UQ_llm_embedding_chunk_model_vector 
        UNIQUE (chunk_id, embedding_model, vector_sha256)
);

-- Indexes for llm.embedding
CREATE NONCLUSTERED INDEX IX_llm_embedding_chunk 
    ON [llm].[embedding] (chunk_id, embedding_model);
CREATE NONCLUSTERED INDEX IX_llm_embedding_model 
    ON [llm].[embedding] (embedding_model, created_utc DESC);
*/


-- ############################################################################
-- SECTION 3: llm.retrieval
-- ############################################################################
-- 
-- Purpose:
--   Logs retrieval queries for reproducibility and auditing. Each retrieval
--   captures the query text, model used, and filtering parameters.
--
-- Why it's being replaced:
--   - `query_embedding_model` should reference an embedding space, not just model
--   - Missing `policy_json` standardization for rerank/MMR settings
--   - Limited metadata for analytics and drift testing
--
-- New replacement: vector.retrieval
--   The new table adds:
--   - `embedding_space_id` FK for explicit space reference
--   - Better policy structure for reranking and diversification
--   - Optional `run_id` for job/run lifecycle integration
--
-- ============================================================================
/*
CREATE TABLE [llm].[retrieval] (
    retrieval_id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    run_id UNIQUEIDENTIFIER NULL,               -- Optional FK to llm.run
    query_text NVARCHAR(MAX) NOT NULL,          -- Query text
    query_embedding_model NVARCHAR(200) NOT NULL, -- Model name (not space ID)
    top_k INT NOT NULL,                          -- Results requested
    filters_json NVARCHAR(MAX) NULL,            -- Filter criteria
    policy_json NVARCHAR(MAX) NULL,             -- Retrieval policy
    created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT PK_llm_retrieval PRIMARY KEY CLUSTERED (retrieval_id),
    CONSTRAINT FK_llm_retrieval_run FOREIGN KEY (run_id) 
        REFERENCES [llm].[run](run_id)
);

-- Indexes for llm.retrieval
CREATE NONCLUSTERED INDEX IX_llm_retrieval_run 
    ON [llm].[retrieval] (run_id, created_utc DESC);
CREATE NONCLUSTERED INDEX IX_llm_retrieval_created 
    ON [llm].[retrieval] (created_utc DESC);
*/


-- ############################################################################
-- SECTION 4: llm.retrieval_hit
-- ############################################################################
-- 
-- Purpose:
--   Stores individual retrieval results. Each hit represents a chunk that
--   matched a query with its similarity score and rank.
--
-- Why it's being replaced:
--   - Tied to legacy llm.retrieval structure
--   - No explicit space validation (hits could mix spaces)
--
-- New replacement: vector.retrieval_hit
--   The new table:
--   - References vector.retrieval which has explicit space identity
--   - Maintains score/rank for analytics
--   - Better metadata structure for "why included" reasoning
--
-- ============================================================================
/*
CREATE TABLE [llm].[retrieval_hit] (
    retrieval_id UNIQUEIDENTIFIER NOT NULL,     -- FK to retrieval
    rank INT NOT NULL,                           -- Position in results (1-indexed)
    chunk_id NVARCHAR(128) NOT NULL,            -- FK to chunk
    score FLOAT NOT NULL,                        -- Similarity score
    metadata_json NVARCHAR(MAX) NULL,           -- Additional metadata
    
    CONSTRAINT PK_llm_retrieval_hit PRIMARY KEY CLUSTERED (retrieval_id, rank),
    CONSTRAINT FK_llm_retrieval_hit_retrieval FOREIGN KEY (retrieval_id) 
        REFERENCES [llm].[retrieval](retrieval_id),
    CONSTRAINT FK_llm_retrieval_hit_chunk FOREIGN KEY (chunk_id) 
        REFERENCES [llm].[chunk](chunk_id)
);

-- Indexes for llm.retrieval_hit
CREATE NONCLUSTERED INDEX IX_llm_retrieval_hit_chunk 
    ON [llm].[retrieval_hit] (chunk_id);
*/


-- ############################################################################
-- SECTION 5: llm.source_registry
-- ############################################################################
-- 
-- Purpose:
--   Tracks sources for incremental indexing. Each entry represents a source
--   that has been indexed, with its content hash for change detection.
--
-- Why it's being replaced:
--   - Limited to retrieval use cases
--   - No support for source versioning or lifecycle states
--   - Weak linkage to semantic staging (sem.SourcePage)
--
-- New replacement: vector.source_registry
--   The new table adds:
--   - Better lifecycle tracking (last_indexed_utc, chunk_count)
--   - Stronger linkage to upstream source systems
--   - Support for incremental re-indexing based on content hash
--
-- ============================================================================
/*
CREATE TABLE [llm].[source_registry] (
    source_id NVARCHAR(256) NOT NULL,           -- Source identifier
    source_type NVARCHAR(100) NOT NULL,          -- Type (lake_text, lake_http, etc.)
    source_ref_json NVARCHAR(MAX) NOT NULL,     -- Source reference metadata
    content_sha256 NVARCHAR(64) NULL,           -- Content hash for change detection
    last_indexed_utc DATETIME2 NULL,            -- When last indexed
    chunk_count INT NULL,                        -- Chunks created
    tags_json NVARCHAR(MAX) NULL,               -- Source tags for filtering
    created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT PK_llm_source_registry PRIMARY KEY CLUSTERED (source_id)
);

-- Indexes for llm.source_registry
CREATE NONCLUSTERED INDEX IX_llm_source_registry_type 
    ON [llm].[source_registry] (source_type, last_indexed_utc DESC);
CREATE NONCLUSTERED INDEX IX_llm_source_registry_content_hash 
    ON [llm].[source_registry] (content_sha256);
*/


-- ############################################################################
-- SECTION 6: CHAT RUNTIME TABLES (PRESERVED IN llm SCHEMA)
-- ############################################################################
-- 
-- The following tables remain UNCHANGED in the `llm` schema and constitute
-- the chat/interrogation runtime:
--
-- - llm.job: Queue of pending/active LLM derive jobs (text prompts)
-- - llm.run: Tracks individual LLM run attempts (model, options, metrics)
-- - llm.artifact: Tracks artifacts written to the data lake
-- - llm.evidence_bundle: Evidence bundles used for LLM runs
-- - llm.evidence_item: Individual evidence items within bundles
-- - llm.run_evidence: Links runs to evidence bundles
--
-- These tables are NOT deprecated and will continue to serve the chat runtime.
-- See migration 0005_create_llm_tables.sql and 0007_evidence_bundle_tables.sql
-- for their definitions.
--
-- Stored procedures preserved:
-- - llm.usp_claim_next_job: Atomically claim next available job
-- - llm.usp_complete_job: Mark job as completed (success/failure)
-- - llm.usp_enqueue_job: Enqueue a new job
-- - llm.usp_create_run: Create a run record for a job attempt
-- - llm.usp_complete_run: Complete a run with status and metrics
-- - llm.usp_create_artifact: Record an artifact written to the lake
--
-- ============================================================================


-- ############################################################################
-- SECTION 7: DEPRECATION TIMELINE
-- ############################################################################
-- 
-- Phase 0 (This PR):
--   - Create this snapshot artifact for historical reference
--   - Inventory dependencies (SQL objects, Python code)
--   - Document migration plan
--   - NO tables dropped, NO code changes
--
-- Phase 1 (Future PR):
--   - Create new `vector` schema with all baseline tables
--   - Add Python code to write to vector.* tables
--   - Keep legacy llm.* tables in place for compatibility
--
-- Phase 2 (Future PR):
--   - Cut over all embedding/retrieval code to vector.*
--   - Drop or archive legacy vector tables from llm schema
--   - Final documentation cleanup
--
-- ============================================================================

-- END OF LEGACY SCHEMA SNAPSHOT
