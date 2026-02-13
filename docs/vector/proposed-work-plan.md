# Proposed Work Plan — Vector/Embedding Subsystem Implementation

**Status:** Phase III Evaluation (Documentation Only)  
**Date:** 2026-02-13  
**Purpose:** Enumerate proposed backlog items to implement the recommended architecture from [recommended-architecture.md](recommended-architecture.md).

---

## Overview

This document breaks down the implementation into discrete tasks that address the gaps identified in [gap-analysis.md](gap-analysis.md) and achieve the architecture described in [recommended-architecture.md](recommended-architecture.md).

**Sequencing Strategy:** Smallest-first, additive, iterative. Each task is independently testable and adds incremental value.

---

## Implementation Paths

### Path A: Script-Based MVP (Fast Proof-of-Concept)

**Goal:** Run first embeddings against raw ingest content using existing `Indexer` script.  
**Timeline:** 1-2 days  
**Outcome:** Prove end-to-end pipeline works, uncover issues early.

### Path B: Job-Based Production (Full Orchestration)

**Goal:** Integrate vector operations into job queue system with retry/monitoring.  
**Timeline:** 3-5 days after Path A  
**Outcome:** Production-quality, scalable, observable vector runtime.

---

## Path A: Script-Based MVP Tasks

### Task A1: Model Discovery Script

**Objective:** Create a script to discover available Ollama embedding models and populate `vector.embedding_space`.

**Components Touched:**
- **New:** `src/vector/tools/discover_models.py`
- **Update:** `src/vector/store.py` (add `get_or_create_embedding_space()` with dimension auto-detection)

**Dependencies:** None

**Steps:**
1. Query Ollama for available models (via API or CLI wrapper)
2. Filter to embedding models (heuristic: name contains "embed" or known list)
3. For each model:
   - Embed test string: `["test"]`
   - Measure dimension: `len(response.embeddings[0])`
   - Get model digest: `client.get_model_digest(model)`
4. Create `EmbeddingSpace` entries via `VectorStore`
5. CLI interface: `python -m src.vector.tools.discover_models --auto-create-spaces`

**Acceptance Criteria:**
- Script successfully discovers `nomic-embed-text` model
- Creates `embedding_space` entry with correct dimensions (768)
- Script is idempotent (re-running doesn't create duplicates)
- Prints summary of discovered models

**Estimated Effort:** 0.5 day

---

### Task A2: HTML Extraction Module

**Objective:** Add HTML-to-text extraction for raw Wookieepedia pages.

**Components Touched:**
- **New:** `src/vector/extraction/html_extractor.py`
- **Update:** `src/llm/retrieval/indexer.py` (integrate extraction before chunking)
- **Update:** `requirements.txt` (add `beautifulsoup4` or `lxml`)

**Dependencies:** None

**Steps:**
1. Create `html_to_text(html: str) -> str` function:
   - Use BeautifulSoup to parse HTML
   - Remove `<script>`, `<style>`, `<nav>`, `<footer>` tags
   - Extract text from article body
   - Normalize whitespace
   - Preserve paragraph breaks
2. Create `extract_article_text(html: str) -> str` for MediaWiki-specific extraction
3. Update `Indexer._load_content()` to detect content type and apply extractor
4. Test with sample Wookieepedia HTML

**Acceptance Criteria:**
- Extracts readable text from Wookieepedia HTML
- Strips navigation, scripts, styles
- Preserves paragraph structure
- Handles malformed HTML gracefully

**Estimated Effort:** 0.5 day

---

### Task A3: Source Selection View

**Objective:** Create SQL view to identify candidate pages for embedding.

**Components Touched:**
- **New:** Migration to create `vector.vw_candidate_sources_for_embedding`

**Dependencies:** None

**SQL:**
```sql
CREATE VIEW vector.vw_candidate_sources_for_embedding AS
SELECT 
    ir.ingest_id,
    ir.resource_id as page_id,
    sp.title,
    sp.primary_type,
    ir.source_system,
    ir.payload,
    LEN(ir.payload) as payload_length,
    ir.hash_sha256 as content_hash,
    ir.content_type,
    ir.fetched_at_utc,
    CASE 
        WHEN sr.source_id IS NULL THEN 'pending'
        WHEN sr.content_sha256 <> ir.hash_sha256 THEN 'changed'
        ELSE 'current'
    END as embedding_status
FROM ingest.IngestRecords ir
INNER JOIN sem.source_page sp 
    ON ir.resource_id = sp.page_id
LEFT JOIN vector.source_registry sr 
    ON ir.resource_id = sr.source_id
WHERE ir.source_system = 'wookieepedia'
    AND sp.primary_type IS NOT NULL
    AND LEN(ir.payload) > 1000
    AND ir.status_code = 200;
```

**Acceptance Criteria:**
- View returns only classified pages
- Filters by content length > 1000 chars
- Shows embedding status (pending/changed/current)
- Joins correctly to `ingest.IngestRecords` and `sem.source_page`

**Estimated Effort:** 0.25 day

---

### Task A4: Manifest Generator Script

**Objective:** Generate JSON manifest for `Indexer` from candidate sources.

**Components Touched:**
- **New:** `src/vector/tools/generate_manifest.py`

**Dependencies:** Task A3 (SQL view)

**Steps:**
1. Query `vw_candidate_sources_for_embedding`
2. Apply filters (primary_type, limit, status)
3. Generate JSON manifest in `Indexer` format
4. Write to output file
5. CLI interface:
   ```bash
   python -m src.vector.tools.generate_manifest \
       --primary-type PersonCharacter \
       --limit 100 \
       --status pending \
       --output /tmp/first_run_manifest.json
   ```

**Manifest Format:**
```json
{
    "version": "1.0",
    "sources": [
        {
            "source_id": "page_123",
            "source_type": "wookieepedia_page",
            "ingest_id": "abc-def",
            "page_title": "Luke Skywalker",
            "primary_type": "PersonCharacter",
            "content_type": "text/html",
            "content_hash": "sha256:..."
        }
    ]
}
```

**Acceptance Criteria:**
- Generates valid manifest JSON
- Filters work correctly (type, limit, status)
- Prints summary (sources selected, total available)
- Handles empty results gracefully

**Estimated Effort:** 0.5 day

---

### Task A5: Update Indexer for HTML Extraction

**Objective:** Integrate HTML extraction into existing `Indexer` class.

**Components Touched:**
- **Update:** `src/llm/retrieval/indexer.py`

**Dependencies:** Task A2 (HTML extractor)

**Steps:**
1. Import `html_extractor` module
2. Update `_load_content()` method to detect content type
3. If `text/html`, apply `html_to_text()`
4. If `application/json`, extract relevant text fields
5. Otherwise, use content as-is

**Acceptance Criteria:**
- Indexer correctly extracts text from HTML sources
- Chunks extracted text (not raw HTML)
- Stores extracted text in `vector.chunk.content`
- Backward compatible with existing plain text sources

**Estimated Effort:** 0.25 day

---

### Task A6: Run First Embedding Batch (100 Pages)

**Objective:** Execute first end-to-end embedding run.

**Components Touched:** None (uses existing code)

**Dependencies:** Tasks A1-A5

**Steps:**
1. Pull embedding model:
   ```bash
   docker exec -it holocron-ollama ollama pull nomic-embed-text
   ```
2. Run model discovery:
   ```bash
   python -m src.vector.tools.discover_models --auto-create-spaces
   ```
3. Generate manifest:
   ```bash
   python -m src.vector.tools.generate_manifest \
       --primary-type PersonCharacter \
       --limit 100 \
       --output /tmp/first_run_manifest.json
   ```
4. Run indexer:
   ```bash
   python -m src.llm.retrieval.indexer \
       --source-manifest /tmp/first_run_manifest.json \
       --mode full \
       --chunk-size 2000 \
       --chunk-overlap 200 \
       --embed-model nomic-embed-text \
       --verbose
   ```
5. Verify:
   ```sql
   SELECT COUNT(*) as chunks FROM vector.chunk;
   SELECT COUNT(*) as embeddings FROM vector.embedding;
   SELECT * FROM vector.source_registry WHERE status = 'indexed';
   ```

**Acceptance Criteria:**
- 100 pages processed successfully
- ~2000-5000 chunks created
- ~2000-5000 embeddings stored
- Source registry updated with content hashes
- No critical errors
- Run completes in < 2 hours

**Estimated Effort:** 0.5 day (includes troubleshooting)

---

### Path A Summary

**Total Estimated Effort:** 2-3 days

**Deliverables:**
- Model discovery script ✅
- HTML extraction ✅
- Source selection view ✅
- Manifest generator ✅
- Updated Indexer ✅
- First 100 pages embedded ✅

**Outcome:** Proof-of-concept complete, pipeline validated.

---

## Path B: Job-Based Production Tasks

### Task B1: VectorJobQueue Class

**Objective:** Create Python wrapper for `vector.job` and `vector.run` operations.

**Components Touched:**
- **New:** `src/vector/queue.py`

**Dependencies:** None

**Steps:**
1. Create `VectorJobQueue` class mirroring `SqlJobQueue`
2. Implement methods:
   - `enqueue_job(job_type, input_json, embedding_space_id, priority)`
   - `claim_next_job(worker_id)` — Atomic claim with locking
   - `mark_succeeded(job_id)`
   - `mark_failed(job_id, error, backoff_seconds)`
   - `create_run(job_id, worker_id, embedding_space_id)`
   - `complete_run(run_id, status, metrics, error)`
3. Use direct SQL or create stored procedures (recommended for atomic operations)

**Acceptance Criteria:**
- Can enqueue vector jobs to `vector.job`
- Can claim jobs atomically (no race conditions)
- Can mark jobs succeeded/failed
- Can create and complete runs with metrics
- Thread-safe (supports multiple workers)

**Estimated Effort:** 1 day

---

### Task B2: Vector Job Stored Procedures (Optional but Recommended)

**Objective:** Create stored procedures for atomic vector job operations.

**Components Touched:**
- **New:** Migration with stored procedures

**Dependencies:** None (parallel to Task B1)

**Procedures to Create:**
- `vector.usp_claim_next_job` — Atomic claim with READPAST/UPDLOCK
- `vector.usp_complete_job` — Mark succeeded/failed with status transition validation
- `vector.usp_enqueue_job` — Insert new job with defaults
- `vector.usp_create_run` — Create run linked to job
- `vector.usp_complete_run` — Update run with metrics

**Acceptance Criteria:**
- Procedures mirror LLM schema patterns
- Atomic operations (no race conditions)
- Status transitions validated (e.g., can't mark NEW job as SUCCEEDED)
- Error handling and logging

**Estimated Effort:** 1 day

---

### Task B3: Vector Job Handlers

**Objective:** Create handler classes for vector job types.

**Components Touched:**
- **New:** `src/vector/handlers/__init__.py`
- **New:** `src/vector/handlers/base.py` (VectorJobHandler ABC)
- **New:** `src/vector/handlers/chunk_source_handler.py`
- **New:** `src/vector/handlers/embed_chunks_handler.py`

**Dependencies:** Task B1 (VectorJobQueue), Path A tasks (HTML extraction)

**ChunkSourceHandler Steps:**
1. Load source from `ingest.IngestRecords` (by ingest_id or source_id)
2. Extract text (HTML → text if needed)
3. Chunk content using `Chunker`
4. Compute chunk hashes and IDs
5. Store chunks via `VectorStore`
6. Update source_registry

**EmbedChunksHandler Steps:**
1. Load chunks from `vector.chunk` (by source_id or chunk_ids)
2. Filter out already-embedded chunks (idempotency)
3. Batch embed via `OllamaClient.embed()`
4. Store embeddings via `VectorStore`
5. Link embeddings to run_id

**Acceptance Criteria:**
- Handlers implement `VectorJobHandler` interface
- ChunkSourceHandler creates chunks from sources
- EmbedChunksHandler creates embeddings from chunks
- Handlers are idempotent (re-running skips existing)
- Handlers log progress with structured logging
- Handlers handle errors gracefully

**Estimated Effort:** 1.5 days

---

### Task B4: Vector Job Registry

**Objective:** Create registry for vector job types.

**Components Touched:**
- **New:** `src/vector/jobs/__init__.py`
- **New:** `src/vector/jobs/registry.py`

**Dependencies:** Task B3 (handlers)

**Steps:**
1. Define `JobTypeDefinition` dataclass (if not already in common)
2. Create registry dictionary:
   ```python
   VECTOR_JOB_TYPES = {
       "chunk_source": JobTypeDefinition(...),
       "embed_chunks": JobTypeDefinition(...),
   }
   ```
3. Create `get_vector_job_type(job_type_key)` function

**Acceptance Criteria:**
- Registry returns job type definitions
- Job types map to handler classes
- Registry is extensible (easy to add new job types)

**Estimated Effort:** 0.25 day

---

### Task B5: Vector Dispatcher

**Objective:** Create dispatcher/runner for vector jobs.

**Components Touched:**
- **New:** `src/vector/runners/__init__.py`
- **New:** `src/vector/runners/vector_dispatcher.py`

**Dependencies:** Tasks B1-B4

**Steps:**
1. Create `VectorDispatcher` class mirroring LLM dispatcher
2. Implement `run_once()` method:
   - Claim next job
   - Create run
   - Resolve handler from registry
   - Execute handler
   - Mark succeeded/failed
   - Complete run with metrics
3. Implement `run_loop()` method:
   - Poll queue continuously
   - Support shutdown signals
4. CLI interface:
   ```bash
   python -m src.vector.runners.vector_dispatcher \
       --once | --loop \
       --dry-run \
       --worker-id <id> \
       --poll-seconds <n>
   ```

**Acceptance Criteria:**
- Dispatcher claims and processes vector jobs
- Supports --once and --loop modes
- Supports --dry-run mode
- Handles shutdown signals gracefully
- Logs structured messages with correlation IDs
- Stores metrics in `vector.run`

**Estimated Effort:** 1 day

---

### Task B6: VectorRunContext and Structured Logging

**Objective:** Add structured logging support for vector operations.

**Components Touched:**
- **New:** `src/vector/handlers/context.py`
- **Update:** All vector handlers to use VectorRunContext

**Dependencies:** Task B3 (handlers)

**Steps:**
1. Create `VectorRunContext` dataclass:
   ```python
   @dataclass
   class VectorRunContext:
       job_id: str
       run_id: str
       worker_id: str
       correlation_id: str
       
       def get_log_context(self) -> Dict[str, str]:
           return {
               "job_id": self.job_id,
               "run_id": self.run_id,
               "worker_id": self.worker_id,
               "correlation_id": self.correlation_id,
               "subsystem": "vector",
           }
   ```
2. Update handlers to accept `context` parameter
3. Use `logger.info(..., extra=context.get_log_context())` in all handlers

**Acceptance Criteria:**
- All vector logs include job_id, run_id, correlation_id
- Logs are JSON-structured (if formatter configured)
- Logs can be filtered by subsystem="vector"

**Estimated Effort:** 0.5 day

---

### Task B7: Batch Enqueue Script

**Objective:** Create script to batch enqueue vector jobs for missing sources.

**Components Touched:**
- **New:** `src/vector/tools/enqueue_missing_sources.py`

**Dependencies:** Task B1 (VectorJobQueue), Task A3 (SQL view)

**Steps:**
1. Query `vw_candidate_sources_for_embedding` with status='pending'
2. For each source:
   - Enqueue CHUNK_SOURCE job
   - Input JSON: `{"ingest_id": ingest_id, "source_id": source_id}`
3. Optionally enqueue EMBED_CHUNKS jobs after chunking (or auto-enqueue in handler)
4. CLI interface:
   ```bash
   python -m src.vector.tools.enqueue_missing_sources \
       --primary-type PersonCharacter \
       --limit 100 \
       --dry-run
   ```

**Acceptance Criteria:**
- Script enqueues jobs for pending sources
- Supports filters (type, limit)
- Supports --dry-run mode
- Prints summary (sources enqueued)
- Idempotent (doesn't re-enqueue completed sources)

**Estimated Effort:** 0.5 day

---

### Task B8: Idempotency and Deduplication Enhancements

**Objective:** Add batch existence checks and MERGE support to VectorStore.

**Components Touched:**
- **Update:** `src/vector/store.py`

**Dependencies:** None

**Steps:**
1. Add `get_missing_embeddings(chunk_ids, embedding_space_id)` method:
   - Returns chunk_ids that don't have embeddings in the space
   - Efficient batch query
2. Update `save_chunk()` to use MERGE (handle duplicates gracefully)
3. Update `save_embedding()` to use MERGE (or check existence first)

**Acceptance Criteria:**
- Batch existence check is efficient (single query)
- Re-running chunking doesn't fail on PK constraint
- Re-running embedding skips existing (no duplicates)

**Estimated Effort:** 0.5 day

---

### Task B9: Metrics Collection

**Objective:** Define and collect metrics for vector runs.

**Components Touched:**
- **New:** `src/vector/contracts/metrics.py`
- **Update:** All vector handlers to collect metrics

**Dependencies:** Task B3 (handlers)

**Steps:**
1. Create `VectorRunMetrics` dataclass:
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
2. Update handlers to collect metrics during execution
3. Store metrics in `vector.run.metrics_json`

**Acceptance Criteria:**
- All runs have metrics in `metrics_json`
- Metrics are queryable via SQL
- Metrics include duration, counts, API stats

**Estimated Effort:** 0.5 day

---

### Task B10: End-to-End Job-Based Test Run

**Objective:** Run first batch of embeddings via job queue.

**Components Touched:** None (uses existing code)

**Dependencies:** Tasks B1-B9

**Steps:**
1. Start vector dispatcher:
   ```bash
   python -m src.vector.runners.vector_dispatcher --loop
   ```
2. Enqueue jobs:
   ```bash
   python -m src.vector.tools.enqueue_missing_sources \
       --primary-type PersonCharacter \
       --limit 100
   ```
3. Monitor:
   ```sql
   SELECT status, COUNT(*) FROM vector.job GROUP BY status;
   SELECT TOP 10 * FROM vector.run ORDER BY started_utc DESC;
   ```
4. Verify:
   ```sql
   SELECT COUNT(*) as chunks FROM vector.chunk;
   SELECT COUNT(*) as embeddings FROM vector.embedding;
   ```

**Acceptance Criteria:**
- Jobs processed successfully
- Chunks and embeddings created
- Runs logged with metrics
- No critical errors
- Handles retries on transient failures

**Estimated Effort:** 0.5 day (includes troubleshooting)

---

### Path B Summary

**Total Estimated Effort:** 5-7 days

**Deliverables:**
- VectorJobQueue class ✅
- Stored procedures (optional) ✅
- Vector job handlers ✅
- Vector job registry ✅
- Vector dispatcher ✅
- Structured logging ✅
- Batch enqueue script ✅
- Idempotency enhancements ✅
- Metrics collection ✅
- Job-based test run ✅

**Outcome:** Production-quality vector job orchestration.

---

## Optional Enhancements (Post-MVP)

### Task C1: Context Window and Parameter Tracking

**Objective:** Extend `vector.embedding_space` to track context window and parameter size.

**Components Touched:**
- **New:** Migration to add columns
- **Update:** `src/vector/contracts/models.py` (EmbeddingSpace model)
- **Update:** `src/vector/tools/discover_models.py` (populate new fields)

**Estimated Effort:** 0.5 day

---

### Task C2: Chunking Policy Versioning

**Objective:** Formalize chunking policy with version tracking.

**Components Touched:**
- **Update:** `src/llm/retrieval/chunker.py` (ChunkingPolicy dataclass)
- **Update:** `src/vector/contracts/models.py` (import ChunkingPolicy)

**Estimated Effort:** 0.5 day

---

### Task C3: Token-Aware Chunking

**Objective:** Add token-based chunking option (instead of character-based).

**Components Touched:**
- **Update:** `src/llm/retrieval/chunker.py`
- **Update:** `requirements.txt` (add `tiktoken`)

**Estimated Effort:** 1 day

---

### Task C4: Error Artifacts and Lake Writer Integration

**Objective:** Write error artifacts for vector runs to lake.

**Components Touched:**
- **Update:** `src/llm/storage/lake_writer.py` (support vector runs)
- **OR New:** `src/vector/storage/lake_writer.py`

**Estimated Effort:** 1 day

---

### Task C5: Computed Column for Page ID in vector.chunk

**Objective:** Add indexed computed column to simplify chunk → entity joins.

**Components Touched:**
- **New:** Migration to add computed column

**SQL:**
```sql
ALTER TABLE vector.chunk 
ADD page_id AS JSON_VALUE(source_ref_json, '$.page_id') PERSISTED;

CREATE INDEX IX_vector_chunk_page_id ON vector.chunk (page_id);
```

**Estimated Effort:** 0.25 day

---

### Task C6: Post-Ingest Hook for Auto-Embedding

**Objective:** Automatically enqueue vector jobs after successful ingest.

**Components Touched:**
- **Update:** `src/ingest/runner/concurrent_runner.py` (add post-completion hook)

**Estimated Effort:** 0.5 day

---

## Task Dependencies Graph

```
Path A (Script-Based MVP):
├─ A1: Model Discovery [0.5d]
├─ A2: HTML Extraction [0.5d]
├─ A3: Source Selection View [0.25d]
├─ A4: Manifest Generator [0.5d] ──depends on──> A3
├─ A5: Update Indexer [0.25d] ──depends on──> A2
└─ A6: First Run [0.5d] ──depends on──> A1, A4, A5

Path B (Job-Based Production):
├─ B1: VectorJobQueue [1d]
├─ B2: Stored Procedures [1d] (parallel to B1)
├─ B3: Vector Handlers [1.5d] ──depends on──> B1, A2
├─ B4: Vector Registry [0.25d] ──depends on──> B3
├─ B5: Vector Dispatcher [1d] ──depends on──> B1, B3, B4
├─ B6: Structured Logging [0.5d] ──depends on──> B3
├─ B7: Batch Enqueue Script [0.5d] ──depends on──> B1, A3
├─ B8: Idempotency Enhancements [0.5d]
├─ B9: Metrics Collection [0.5d] ──depends on──> B3
└─ B10: Job-Based Test Run [0.5d] ──depends on──> B1-B9

Path B depends on Path A components: A2 (HTML extraction), A3 (SQL view)
```

---

## Recommended Sequencing

### Sprint 1: Script-Based MVP (Days 1-3)
- **Day 1:** Tasks A1, A2 (Model discovery + HTML extraction)
- **Day 2:** Tasks A3, A4, A5 (Source selection + Manifest + Indexer update)
- **Day 3:** Task A6 (First run + validation)

**Milestone:** First 100 pages embedded via script

---

### Sprint 2: Job Infrastructure (Days 4-8)
- **Day 4:** Tasks B1, B2 (VectorJobQueue + Stored procedures)
- **Day 5:** Task B3 (Vector handlers)
- **Day 6:** Tasks B4, B5 (Registry + Dispatcher)
- **Day 7:** Tasks B6, B7, B8, B9 (Logging + Enqueue + Idempotency + Metrics)
- **Day 8:** Task B10 (Job-based test run + validation)

**Milestone:** Job-based orchestration functional

---

### Sprint 3: Polish and Enhancements (Days 9-10, optional)
- **Day 9:** Tasks C1, C2 (Context window + Policy versioning)
- **Day 10:** Task C3 or C4 (Token chunking or Error artifacts)

**Milestone:** Production-ready features

---

## Success Metrics

### Path A Success Criteria
- ✅ 100 pages embedded successfully
- ✅ ~2000-5000 chunks created
- ✅ ~2000-5000 embeddings stored
- ✅ Source registry populated
- ✅ No critical errors
- ✅ Run completes in < 2 hours

### Path B Success Criteria
- ✅ Jobs enqueued and processed via queue
- ✅ Multiple workers can process jobs concurrently
- ✅ Retry on transient failures
- ✅ Structured logging with correlation IDs
- ✅ Metrics captured in all runs
- ✅ Idempotency enforced (re-running skips existing)

---

## Risk Mitigation

### Risk 1: Ollama Embedding API Failures
- **Mitigation:** Implement retry logic with exponential backoff
- **Detection:** Monitor API duration and error rates in metrics

### Risk 2: Large Content Causes Timeouts
- **Mitigation:** Enforce max chunk size, timeout configuration
- **Detection:** Track API duration per request, alert on outliers

### Risk 3: Database Deadlocks on Concurrent Writes
- **Mitigation:** Use stored procedures for atomic operations, batch inserts
- **Detection:** Monitor SQL error logs for deadlock errors

### Risk 4: Incorrect Dimension Detection
- **Mitigation:** Validate against known models, manual override option
- **Detection:** Compare detected dimensions with expected values

### Risk 5: HTML Extraction Quality Issues
- **Mitigation:** Test with diverse HTML samples, fallback to raw text
- **Detection:** Sample chunk content, validate readability

---

## Related Documents

- [Current State Inventory](current-state-inventory.md) — What exists today
- [Gap Analysis](gap-analysis.md) — What's missing
- [Recommended Architecture](recommended-architecture.md) — Target architecture
