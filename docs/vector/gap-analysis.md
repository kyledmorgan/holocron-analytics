# Gap Analysis — Vector/Embedding Subsystem

**Status:** Phase III Evaluation (Documentation Only)  
**Date:** 2026-02-13  
**Purpose:** Identify gaps preventing a first end-to-end embedding run against raw ingest datasets.

---

## Overview

This document analyzes the gaps between the current state (documented in [current-state-inventory.md](current-state-inventory.md)) and the minimum viable capability to **run embeddings against raw ingest content and store them** with model flexibility and dedupe.

**Goal:** Achieve a first successful embedding run with minimal lift by reusing existing components.

---

## Executive Summary

**Current State:** We have a complete `vector` schema, functional `VectorStore`, working `OllamaClient.embed()`, and raw content sources. We can already run embeddings using the existing `Indexer` class.

**Main Gap:** No **job-based orchestration** for vector operations. The `Indexer` is a script, not a job-driven system. We need vector jobs to be first-class citizens in the orchestration framework.

**Secondary Gaps:** Configuration (model metadata), data extraction (HTML-to-text), and observability (logging/metrics).

---

## Gap Category 1: Configuration

### Gap 1.1: Model Metadata Registry Not Populated

**Current State:**
- `vector.embedding_space` table exists with columns for `provider`, `model_name`, `model_tag`, `model_digest`, `dimensions`
- No embedding spaces pre-created
- No automatic dimension detection from Ollama models

**Impact:**
- Manual creation of embedding spaces required before first run
- Risk of incorrect dimension values
- No model registry to query for available models

**Required for First Run:**
- Pre-create at least one embedding space for `nomic-embed-text` (768 dimensions)
- OR: Auto-create embedding space on first embed call with dimension detection

**Recommendation:**
- Create a "model discovery" script that:
  1. Queries Ollama for available models (`ollama list`)
  2. Embeds a test string to measure dimensions
  3. Calls `get_model_digest()` to get SHA256
  4. Creates/updates `vector.embedding_space` entries
- Run this script as part of vector job initialization or as a manual setup step

**Files Touched (Implementation Phase):**
- New: `src/vector/tools/discover_models.py`
- Update: `src/vector/store.py` (add `get_or_create_embedding_space()` with auto-dimension detection)

---

### Gap 1.2: Context Window and Parameter Tracking

**Current State:**
- `vector.embedding_space` has columns for `model_name`, `dimensions`
- No explicit tracking of:
  - Context window (max tokens for embedding input)
  - Model parameter size (137M, 335M, etc.)
  - Model family (nomic-bert, etc.)

**Impact:**
- Cannot enforce context window limits during chunking
- Cannot optimize chunk size based on model capabilities
- No metadata for model comparison

**Required for First Run:**
- Not strictly required for MVP (can use default chunk size)
- But recommended for production quality

**Recommendation:**
- Add columns to `vector.embedding_space`:
  - `context_window_tokens INT` - Max input tokens
  - `parameter_size NVARCHAR(50)` - e.g., "137M", "335M"
  - `model_family NVARCHAR(100)` - e.g., "nomic-bert", "all-minilm"
- Update model discovery script to populate these fields
- Use context window to validate chunk size in chunking policy

**Files Touched (Implementation Phase):**
- Migration: New migration to add columns
- Update: `src/vector/contracts/models.py` (add fields to `EmbeddingSpace`)
- Update: `src/vector/tools/discover_models.py`

---

### Gap 1.3: Chunking Policy Versioning

**Current State:**
- Chunking policy stored in `vector.chunk.policy_json` as JSON blob
- No formal versioning scheme
- `Chunker` class has default policy but no version tracking

**Impact:**
- Cannot track changes in chunking strategy over time
- Difficult to invalidate/re-chunk content when policy changes
- No lineage for chunk ID generation

**Required for First Run:**
- Use a simple version string (e.g., "v1.0") in policy JSON
- Include in chunk ID generation (already part of `generate_chunk_id()`)

**Recommendation:**
- Define a formal `ChunkingPolicy` dataclass with:
  - `version` (e.g., "v1.0", "v1.1")
  - `chunk_size`, `overlap`, `max_chunks`
  - `strategy` (e.g., "character-sliding-window", "token-aware")
  - `word_boundary_respect` (bool)
- Store as JSON in `policy_json` column
- Update `Chunker` to accept policy object
- Use policy version in chunk ID generation

**Files Touched (Implementation Phase):**
- Update: `src/llm/retrieval/chunker.py` (add ChunkingPolicy dataclass)
- Update: `src/vector/contracts/models.py` (import ChunkingPolicy)
- Update: `src/llm/retrieval/indexer.py` (use versioned policy)

---

## Gap Category 2: Data Extraction

### Gap 2.1: HTML-to-Text Extraction Missing

**Current State:**
- Raw HTML stored in `ingest.IngestRecords.payload` for Wookieepedia pages
- No built-in HTML-to-text extraction
- `Indexer` expects plain text or handles inline content

**Impact:**
- Cannot directly embed raw HTML (contains tags, scripts, styles)
- Need preprocessing step to extract readable text
- Ingest pipeline doesn't store extracted text

**Required for First Run:**
- Add HTML parsing to extract readable text before chunking
- Options:
  - Use `beautifulsoup4` or `lxml` to strip tags
  - Extract main content areas (article body, skip navigation/footer)
  - Normalize whitespace

**Recommendation:**
- Create `src/vector/extraction/` module with extractors:
  - `html_to_text(html: str) -> str` - Basic HTML stripping
  - `extract_article_text(html: str) -> str` - MediaWiki-specific extraction
- Update `Indexer` to detect content type and apply appropriate extractor
- Store extracted text in `vector.chunk.content` (not original HTML)

**Files Touched (Implementation Phase):**
- New: `src/vector/extraction/html_extractor.py`
- Update: `src/llm/retrieval/indexer.py` (add extraction step before chunking)
- Optional: Add dependency to `requirements.txt` (beautifulsoup4, lxml)

---

### Gap 2.2: Source Selection Query for First Run

**Current State:**
- No predefined SQL query or view to select "first batch" of pages for embedding
- No manifest generation tool

**Impact:**
- Manual query writing required to identify input sources
- No standard starting point for first run

**Required for First Run:**
- Define SQL query to select top N pages for first embedding run
- Criteria suggestions:
  - Pages with classification in `sem.source_page`
  - Pages with content length > threshold (e.g., 1000 chars)
  - Pages of specific primary types (e.g., PersonCharacter, Droid)
  - Limit to manageable size (e.g., 100-500 pages)

**Recommendation:**
- Create SQL view: `vector.vw_candidate_sources_for_embedding`
- Create Python script: `src/vector/tools/generate_manifest.py`
  - Queries `vw_candidate_sources_for_embedding`
  - Generates JSON manifest for `Indexer`
  - Supports filters (primary_type, source_system, limit)

**Example SQL:**
```sql
CREATE VIEW vector.vw_candidate_sources_for_embedding AS
SELECT 
    ir.ingest_id,
    ir.resource_id as page_id,
    sp.title,
    sp.primary_type,
    ir.payload,
    LEN(ir.payload) as payload_length,
    ir.hash_sha256,
    ir.fetched_at_utc
FROM ingest.IngestRecords ir
INNER JOIN sem.source_page sp ON ir.resource_id = sp.page_id
WHERE ir.source_system = 'wookieepedia'
    AND sp.primary_type IS NOT NULL
    AND LEN(ir.payload) > 1000
    AND ir.status_code = 200;
```

**Files Touched (Implementation Phase):**
- New: Migration to create view
- New: `src/vector/tools/generate_manifest.py`

---

### Gap 2.3: Linking Chunks to Core Entities

**Current State:**
- `vector.chunk` has `source_ref_json` for arbitrary source linkage
- No explicit FK to `dbo.dim_entity` or `sem.source_page`
- Linking requires JSON parsing of `source_ref`

**Impact:**
- Difficult to query "all chunks for entity X"
- No direct join path from chunks to entities
- Retrieval results require JSON parsing to identify entities

**Required for First Run:**
- Not strictly required (can use source_ref JSON)
- But recommended for queryability

**Recommendation:**
- Option 1: Add `entity_id` FK column to `vector.chunk`
  - Requires entity resolution at chunk time
  - May not always have 1:1 mapping (chunk spans multiple entities)
- Option 2: Create bridge table `vector.chunk_entity_bridge`
  - Many-to-many relationship
  - Allows chunks to link to multiple entities
- Option 3: Keep source_ref JSON, add indexed computed column for page_id
  - `page_id AS JSON_VALUE(source_ref_json, '$.page_id') PERSISTED`
  - Allows efficient joins without schema change

**Preferred:** Option 3 for MVP (minimal schema change, queryable)

**Files Touched (Implementation Phase):**
- Migration: Add computed column to `vector.chunk`
- Update: Queries in `VectorStore` to leverage indexed column

---

## Gap Category 3: Job Queue Integration

### Gap 3.1: No Python Wrapper for vector.job Queue

**Current State:**
- `vector.job` and `vector.run` tables exist
- No stored procedures for atomic job operations
- No Python class like `SqlJobQueue` for vector schema

**Impact:**
- Cannot enqueue vector jobs programmatically
- No job claim/complete/fail operations
- Cannot integrate with dispatcher pattern

**Required for First Run:**
- Create `VectorJobQueue` class mirroring `SqlJobQueue`
- Implement core methods:
  - `enqueue_job(job_type, input_json, embedding_space_id, priority)`
  - `claim_next_job(worker_id)`
  - `mark_succeeded(job_id)` / `mark_failed(job_id, error, backoff)`
  - `create_run(job_id, worker_id)` / `complete_run(run_id, status, metrics)`

**Recommendation:**
- Create `src/vector/queue.py` with `VectorJobQueue` class
- Copy patterns from `src/llm/storage/sql_job_queue.py`
- Optionally create stored procedures for atomic operations (like LLM schema):
  - `vector.usp_claim_next_job`
  - `vector.usp_complete_job`
  - `vector.usp_enqueue_job`

**Files Touched (Implementation Phase):**
- New: `src/vector/queue.py`
- New: Migration with stored procedures (optional but recommended)

---

### Gap 3.2: Vector Job Types Not Registered

**Current State:**
- `vector.job.job_type` column supports: CHUNK_SOURCE, EMBED_CHUNKS, REEMBED_SPACE, RETRIEVE_TEST, DRIFT_TEST
- No Python registry for vector job types
- No handler classes for vector job types
- LLM dispatcher doesn't know about vector jobs

**Impact:**
- Cannot route vector jobs to handlers
- No unified job system across LLM and vector workloads

**Required for First Run:**
- Define handler classes for each vector job type (at least CHUNK_SOURCE and EMBED_CHUNKS)
- Register job types in a vector-specific registry OR extend existing LLM registry

**Recommendation:**
- Option 1: Create separate `VectorJobRegistry` in `src/vector/jobs/registry.py`
  - Mirrors LLM job registry pattern
  - Keeps vector and LLM job systems decoupled
- Option 2: Extend `llm.jobs.registry` to support vector job types
  - Single unified registry
  - Requires namespace differentiation (e.g., "vector:embed_chunks")

**Preferred:** Option 1 for MVP (decoupled, simpler)

**Job Type Definitions Needed:**
```python
JobTypeDefinition(
    job_type_key="chunk_source",
    handler_module_path="src.vector.handlers.chunk_source_handler",
    handler_class_name="ChunkSourceHandler",
    description="Chunk a source into searchable units",
    schema="vector",
    enabled=True,
)

JobTypeDefinition(
    job_type_key="embed_chunks",
    handler_module_path="src.vector.handlers.embed_chunks_handler",
    handler_class_name="EmbedChunksHandler",
    description="Generate embeddings for chunks",
    schema="vector",
    enabled=True,
)
```

**Files Touched (Implementation Phase):**
- New: `src/vector/jobs/registry.py`
- New: `src/vector/handlers/chunk_source_handler.py`
- New: `src/vector/handlers/embed_chunks_handler.py`

---

### Gap 3.3: No Vector Job Runner/Dispatcher

**Current State:**
- `Indexer` is a standalone script, not job-driven
- No CLI runner for vector jobs (like `dispatcher.py` for LLM)
- No worker loop for vector queue

**Impact:**
- Cannot run vector operations as background jobs
- No concurrency/parallelism for vector workloads
- Cannot monitor/retry/backoff vector jobs

**Required for First Run:**
- Create a vector job dispatcher that:
  1. Polls `vector.job` queue
  2. Claims next job
  3. Routes to handler based on job type
  4. Creates run, executes handler, marks complete/failed
  5. Supports --once, --loop, --dry-run modes

**Recommendation:**
- Create `src/vector/runners/vector_dispatcher.py`
- Copy structure from `src/llm/runners/dispatcher.py`
- Use `VectorJobQueue` for queue operations
- Use `VectorJobRegistry` for job type → handler resolution

**CLI Pattern:**
```bash
python -m src.vector.runners.vector_dispatcher \
    --once              # Process 1 job
    --loop              # Continuous polling
    --dry-run           # Report mode
    --worker-id <id>
    --poll-seconds <n>
```

**Files Touched (Implementation Phase):**
- New: `src/vector/runners/vector_dispatcher.py`
- New: `src/vector/runners/__init__.py`

---

### Gap 3.4: No Job Enqueuing from Ingest Completion

**Current State:**
- Ingest completes HTTP fetch → stores in `IngestRecords`
- No trigger to enqueue vector job for newly ingested content
- Manual enqueuing required

**Impact:**
- No automated pipeline from ingest → embed
- First run must manually select and enqueue sources

**Required for First Run:**
- Not required for MVP (can manually enqueue)
- But needed for production automation

**Recommendation:**
- Option 1: Add post-ingest hook to enqueue vector job
  - In `ConcurrentRunner._complete_work_item()`
  - Enqueue CHUNK_SOURCE job after successful ingest
- Option 2: Separate batch job that scans for un-embedded content
  - Query `ingest.IngestRecords` for records not in `vector.source_registry`
  - Enqueue CHUNK_SOURCE jobs for missing sources
- Option 3: SQL trigger on `ingest.IngestRecords` insert
  - Insert into `vector.job` automatically
  - Less flexible, harder to debug

**Preferred:** Option 2 for MVP (explicit, auditable, retriable)

**Files Touched (Implementation Phase):**
- New: `src/vector/tools/enqueue_missing_sources.py`
- OR Update: `src/ingest/runner/concurrent_runner.py` (add post-ingest hook)

---

## Gap Category 4: Storage and Idempotency

### Gap 4.1: Chunk Deduplication Strategy

**Current State:**
- `vector.chunk.chunk_id` is deterministic SHA256 from `(source_id, chunk_index, offsets, policy_version)`
- PK constraint prevents duplicate chunk_ids
- `generate_chunk_id()` function exists

**Impact:**
- Re-running chunking on same source with same policy creates duplicates (fails on PK)
- No "upsert" or "skip if exists" logic

**Required for First Run:**
- Add "skip if exists" logic in `Indexer`
- Check if chunk_id already exists before insert

**Recommendation:**
- Update `VectorStore.save_chunk()` to use MERGE or check existence first
- Update `Indexer` to call `store.chunk_exists(chunk_id)` before creating
- Or: Use MERGE in SQL to handle upsert silently

**Files Touched (Implementation Phase):**
- Update: `src/vector/store.py` (add `chunk_exists()` method, use MERGE in `save_chunk()`)

---

### Gap 4.2: Embedding Idempotency Enforcement

**Current State:**
- `vector.embedding` has unique constraint: `(chunk_id, embedding_space_id, input_content_sha256)`
- Prevents duplicate embeddings for same chunk + space + content version
- But no "skip if exists" in `Indexer`

**Impact:**
- Re-running embedding on same chunks fails on constraint violation
- No graceful handling of already-embedded chunks

**Required for First Run:**
- Check if embedding exists before calling `ollama.embed()`
- Skip already-embedded chunks

**Recommendation:**
- Update `Indexer` to call `store.embedding_exists(chunk_id, embedding_space_id, content_sha256)` before embedding
- Add batch existence check method: `store.get_missing_embeddings(chunk_ids, embedding_space_id)`
- Use batch check to filter chunks before embedding (more efficient)

**Files Touched (Implementation Phase):**
- Update: `src/vector/store.py` (add `get_missing_embeddings()` batch method)
- Update: `src/llm/retrieval/indexer.py` (use batch check, skip existing)

---

### Gap 4.3: Source Registry Incremental Detection

**Current State:**
- `vector.source_registry` tracks `content_sha256` for change detection
- `Indexer` has "incremental mode" that compares hashes
- But no explicit "force re-embed" option

**Impact:**
- If content changes, old embeddings remain (with old content_sha256)
- No cleanup of stale embeddings

**Required for First Run:**
- Not critical for MVP (first run is always "full")
- But needed for incremental updates

**Recommendation:**
- Add "force" flag to `Indexer` CLI: `--force` (ignore hash, always re-chunk/embed)
- Add cleanup logic: when content hash changes, mark old embeddings as "stale"
- Option 1: Delete old embeddings for same chunk_id but different content_sha256
- Option 2: Keep old embeddings, add `is_current` flag
  - Allows time-travel queries

**Preferred:** Option 1 for MVP (simpler), Option 2 for production

**Files Touched (Implementation Phase):**
- Update: `src/llm/retrieval/indexer.py` (add --force flag, cleanup logic)
- Optional: Add `is_current` column to `vector.embedding`

---

## Gap Category 5: Observability

### Gap 5.1: Logging and Correlation IDs

**Current State:**
- LLM runner has structured logging with correlation IDs
- `RunContext.get_log_context()` provides structured fields
- Vector operations don't use consistent logging

**Impact:**
- Difficult to trace vector operations across logs
- No correlation between job → run → chunks → embeddings

**Required for First Run:**
- Add structured logging to vector handlers
- Use correlation IDs (job_id, run_id) in all log messages

**Recommendation:**
- Copy `RunContext` pattern from `src/llm/jobs/handlers.py`
- Create `VectorRunContext` with:
  - `job_id`, `run_id`, `worker_id`, `correlation_id`
  - `get_log_context()` method for structured logging
- Use in all vector handlers and `Indexer`

**Files Touched (Implementation Phase):**
- New: `src/vector/handlers/context.py` (VectorRunContext)
- Update: All vector handlers to use VectorRunContext
- Update: `src/llm/retrieval/indexer.py` (add structured logging)

---

### Gap 5.2: Metrics Collection

**Current State:**
- `vector.run` has `metrics_json` column
- No standard metrics schema
- No automatic metrics collection

**Impact:**
- Cannot measure performance (chunks/sec, embeddings/sec)
- No duration tracking
- No error rate monitoring

**Required for First Run:**
- Define metrics schema for vector runs
- Capture at least:
  - `duration_ms` - Total run duration
  - `chunks_processed` - Number of chunks created
  - `embeddings_created` - Number of embeddings generated
  - `api_calls` - Number of Ollama API calls
  - `api_duration_ms` - Time spent in API calls

**Recommendation:**
- Create `VectorRunMetrics` dataclass:
  ```python
  @dataclass
  class VectorRunMetrics:
      duration_ms: int
      chunks_processed: int
      embeddings_created: int
      api_calls: int
      api_duration_ms: int
      bytes_processed: int
  ```
- Update `Indexer` to collect metrics
- Store in `vector.run.metrics_json`

**Files Touched (Implementation Phase):**
- New: `src/vector/contracts/metrics.py`
- Update: `src/llm/retrieval/indexer.py` (collect metrics)
- Update: `src/vector/runners/vector_dispatcher.py` (store metrics)

---

### Gap 5.3: Error Reporting and Artifacts

**Current State:**
- LLM runner writes error artifacts (invalid_json_response.txt, error_manifest.json)
- No equivalent for vector operations

**Impact:**
- Difficult to debug embedding failures
- No record of what content failed

**Required for First Run:**
- Write error artifacts for vector failures
- Store failed chunks, API errors, etc.

**Recommendation:**
- Extend `LakeWriter` to support vector runs
- Create `lake/vector_runs/{run_id}/` directory structure
- Write artifacts:
  - `run_manifest.json` - Run metadata
  - `chunk_manifest.json` - List of chunks processed
  - `embedding_manifest.json` - List of embeddings created
  - `error_manifest.json` - Error details if failed
  - `failed_chunks.json` - Chunks that failed embedding

**Files Touched (Implementation Phase):**
- Update: `src/llm/storage/lake_writer.py` (support vector runs)
- OR New: `src/vector/storage/lake_writer.py` (vector-specific)

---

## Gap Category 6: Chunking Strategy

### Gap 6.1: Token-Based Chunking Not Implemented

**Current State:**
- `Chunker` uses **character-based** sliding window
- No token-aware chunking
- Context window limits not enforced

**Impact:**
- Cannot guarantee chunks fit within model context window
- Token count may vary significantly per chunk
- Risk of exceeding model limits (though rare with 2000 chars)

**Required for First Run:**
- Not required for MVP (character-based is functional)
- 2000 chars ≈ 500-700 tokens for English text (safe for most models)

**Recommendation:**
- For production: Add token-based chunking option
- Use `tiktoken` library (OpenAI) or model-specific tokenizer
- Update `ChunkingPolicy` to support:
  - `strategy: "character-sliding-window" | "token-aware"`
  - `max_tokens` (instead of/in addition to `chunk_size`)

**Files Touched (Implementation Phase):**
- Update: `src/llm/retrieval/chunker.py` (add token-aware mode)
- Add: Dependency `tiktoken` or equivalent

---

### Gap 6.2: Chunk Overlap Handling

**Current State:**
- `Chunker` supports overlap (default 200 chars)
- Overlap stored in `offsets_json`
- No validation that overlap < chunk_size

**Impact:**
- Misconfiguration could create infinite loop
- No clear documentation of overlap semantics

**Required for First Run:**
- Current implementation is functional
- Add validation in `ChunkingPolicy`

**Recommendation:**
- Add validation: `overlap < chunk_size`
- Document overlap semantics:
  - Overlap measured in characters (or tokens if token-aware)
  - Overlapping text included in both chunks
  - Ensures context continuity across chunk boundaries

**Files Touched (Implementation Phase):**
- Update: `src/llm/retrieval/chunker.py` (add validation)
- Add: Documentation in `ChunkingPolicy` docstring

---

### Gap 6.3: Max Chunks Per Source Enforcement

**Current State:**
- `IndexerConfig.max_chunks_per_source` defaults to 100
- No enforcement in `Chunker` (soft limit)
- Could generate more chunks for very long sources

**Impact:**
- Could exceed expected chunk count
- No truncation or warning for long sources

**Required for First Run:**
- Current implementation is functional (soft limit)
- Add hard limit enforcement

**Recommendation:**
- Update `Chunker` to enforce `max_chunks`
- Options:
  - Truncate at max_chunks (discard rest)
  - Error/warn if exceeded
  - Intelligently select representative chunks (start + end + samples)

**Preferred:** Truncate with warning for MVP

**Files Touched (Implementation Phase):**
- Update: `src/llm/retrieval/chunker.py` (enforce max_chunks)

---

## Priority Matrix

| Gap ID | Category | Impact | Effort | Priority | Required for MVP |
|--------|----------|--------|--------|----------|------------------|
| 1.1 | Config | High | Low | **P0** | ✅ Yes |
| 1.2 | Config | Medium | Low | P1 | ❌ No |
| 1.3 | Config | Low | Low | P2 | ❌ No |
| 2.1 | Data Extraction | High | Medium | **P0** | ✅ Yes |
| 2.2 | Data Extraction | Medium | Low | **P0** | ✅ Yes |
| 2.3 | Data Extraction | Low | Medium | P2 | ❌ No |
| 3.1 | Job Queue | High | Medium | **P0** | ✅ Yes (if job-based) |
| 3.2 | Job Queue | High | Medium | **P0** | ✅ Yes (if job-based) |
| 3.3 | Job Queue | High | Medium | **P0** | ✅ Yes (if job-based) |
| 3.4 | Job Queue | Medium | Low | P1 | ❌ No |
| 4.1 | Storage | Medium | Low | P1 | ❌ No (will fail gracefully) |
| 4.2 | Storage | Medium | Low | P1 | ❌ No (will fail gracefully) |
| 4.3 | Storage | Low | Medium | P2 | ❌ No |
| 5.1 | Observability | Medium | Low | P1 | ❌ No |
| 5.2 | Observability | Medium | Low | P1 | ❌ No |
| 5.3 | Observability | Low | Low | P2 | ❌ No |
| 6.1 | Chunking | Low | High | P2 | ❌ No |
| 6.2 | Chunking | Low | Low | P2 | ❌ No |
| 6.3 | Chunking | Low | Low | P2 | ❌ No |

**Legend:**
- **P0** - Blocker for MVP (must have)
- **P1** - Important for production quality (should have)
- **P2** - Nice to have (future enhancement)

---

## Two Paths to First Run

### Path A: Script-Based (Fastest to First Run)

**Approach:** Use existing `Indexer` script without job orchestration.

**Gaps to Close:**
- 1.1: Model metadata (manual embedding space creation)
- 2.1: HTML extraction (add to `Indexer`)
- 2.2: Source selection (manual SQL query + manifest)

**Pros:**
- Minimal code changes
- Can run first embeddings in < 1 day
- Good for proof-of-concept

**Cons:**
- Not integrated with job system
- No retry/monitoring/observability
- Manual execution required

**Steps:**
1. Manually create embedding space in `vector.embedding_space`
2. Query `ingest.IngestRecords` to select sources
3. Generate manifest JSON
4. Add HTML extraction to `Indexer`
5. Run `python -m src.llm.retrieval.indexer --source-manifest <path> --mode full`

---

### Path B: Job-Based (Production Quality)

**Approach:** Build full job orchestration for vector operations.

**Gaps to Close:**
- All P0 gaps (1.1, 2.1, 2.2, 3.1, 3.2, 3.3)

**Pros:**
- Integrated with existing orchestration
- Retry/monitoring/observability built-in
- Scalable (can add workers)
- Follows established patterns

**Cons:**
- More code to write (VectorJobQueue, handlers, dispatcher)
- Longer time to first run (3-5 days)

**Steps:**
1. Create `VectorJobQueue` class
2. Create vector job handlers (ChunkSourceHandler, EmbedChunksHandler)
3. Create vector job registry
4. Create vector dispatcher
5. Add model discovery script
6. Add HTML extraction
7. Enqueue vector jobs for selected sources
8. Run `python -m src.vector.runners.vector_dispatcher --loop`

---

## Recommendation

**For Phase III (Evaluation):** Document both paths in [recommended-architecture.md](recommended-architecture.md).

**For Phase IV (Implementation):** Start with **Path A** (script-based) for immediate proof-of-concept, then migrate to **Path B** (job-based) for production deployment.

**Rationale:**
- Path A proves the core embedding pipeline works
- Path A uncovers unforeseen issues early
- Path B builds on proven components
- Path B can reuse code from Path A (Indexer, Chunker, VectorStore)

---

## Related Documents

- [Current State Inventory](current-state-inventory.md) — What exists today
- [Recommended Architecture](recommended-architecture.md) — Target architecture design
- [Proposed Work Plan](proposed-work-plan.md) — Implementation backlog
