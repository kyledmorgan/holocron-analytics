# Current State Inventory — Vector/Embedding Subsystem

**Status:** Phase III Evaluation (Documentation Only)  
**Date:** 2026-02-13  
**Purpose:** Comprehensive inventory of existing vector/embedding infrastructure to support first embedding run planning.

---

## Overview

This document inventories all existing components related to vector/embedding operations in the Holocron Analytics repository. It covers SQL objects, Python modules, Ollama integration points, job orchestration patterns, and available raw data sources.

**Scope:** This is a snapshot of what exists today. No new functionality is implemented as part of this evaluation phase.

---

## SQL Schema Objects

### 1. Vector Schema (`vector`)

**Migration:** `db/migrations/0023_create_vector_schema.sql` (Phase 1 - Complete)

The `vector` schema provides complete infrastructure for embedding generation, storage, and retrieval, operating independently from the `llm` chat runtime.

#### Tables

| Table | Purpose | Key Columns | Key Constraints |
|-------|---------|-------------|-----------------|
| **embedding_space** | First-class embedding space identity | `embedding_space_id` (PK), `provider`, `model_name`, `model_tag`, `model_digest`, `dimensions`, `normalize_flag`, `distance_metric`, `preprocess_policy_json`, `created_utc` | UQ on `(provider, model_name, model_tag, model_digest, dimensions)` |
| **job** | Vector task queue | `job_id` (PK), `job_type` (CHUNK_SOURCE\|EMBED_CHUNKS\|REEMBED_SPACE\|RETRIEVE_TEST\|DRIFT_TEST), `status` (NEW\|RUNNING\|SUCCEEDED\|FAILED\|DEADLETTER), `priority`, `input_json`, `embedding_space_id` (FK), `max_attempts`, `attempt_count`, `locked_by`, `locked_utc`, `available_utc` | FK to `embedding_space` |
| **run** | Vector execution lineage | `run_id` (PK), `job_id` (FK), `worker_id`, `status`, `embedding_space_id`, `endpoint_url`, `model_name`, `model_tag`, `model_digest`, `options_json`, `metrics_json`, `error`, `started_utc`, `completed_utc` | FK to `job` |
| **source_registry** | Source index state tracking | `source_id` (PK), `source_type`, `source_ref_json`, `content_sha256`, `last_indexed_utc`, `chunk_count`, `tags_json`, `status` (indexed\|pending\|error) | - |
| **chunk** | Canonical chunk table | `chunk_id` (PK, SHA256), `source_id` (FK), `source_type`, `source_ref_json`, `offsets_json`, `content` (NVARCHAR(MAX)), `content_sha256`, `byte_count`, `policy_json`, `created_utc` | FK to `source_registry` |
| **embedding** | Embeddings with lineage | `embedding_id` (PK), `chunk_id` (FK), `embedding_space_id` (FK), `input_content_sha256`, `run_id` (FK), `vector_json` (NVARCHAR(MAX)), `vector_sha256`, `created_utc` | UQ on `(chunk_id, embedding_space_id, input_content_sha256)` for idempotency |
| **retrieval** | Retrieval query log | `retrieval_id` (PK), `embedding_space_id` (FK), `query_text`, `query_embedding_json`, `top_k`, `filters_json`, `policy_json`, `run_id` (FK), `created_utc` | FK to `embedding_space`, `run` |
| **retrieval_hit** | Retrieval results | `retrieval_id` (FK, PK), `rank` (PK), `chunk_id` (FK), `score`, `metadata_json` | Composite PK on `(retrieval_id, rank)` |

**Key Stored Procedures:**
- None currently implemented (job queue operations in Python)

**Key Features:**
- ✅ First-class embedding space identity prevents vector mixing
- ✅ Idempotency constraint on embeddings: `(chunk_id, embedding_space_id, input_content_sha256)`
- ✅ Version coupling: `input_content_sha256` must match chunk's `content_sha256`
- ✅ Run lineage tracking via `run_id`
- ✅ Job queue with priority, status, and retry logic
- ✅ Source registry for incremental indexing with content hash change detection

---

### 2. LLM Schema (`llm`) - Chat Runtime Only

**Migrations:** 
- `db/migrations/0005_create_llm_tables.sql` (initial)
- `db/migrations/0024_deprecate_llm_vector_tables.sql` (Phase 2 - deprecated vector tables)
- `db/migrations/0025_llm_job_idempotency.sql` (added `dedupe_key`)

The `llm` schema is the **chat/interrogation runtime** (text-in → text-out). Vector tables have been **deprecated** and renamed to `*_legacy`.

#### Active LLM Tables (Chat Runtime)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **job** | LLM chat job queue | `job_id` (PK), `interrogation_key`, `input_json`, `evidence_ref_json`, `status`, `priority`, `attempt_count`, `max_attempts`, `locked_by`, `dedupe_key` (v0025), `created_utc` |
| **run** | Individual job attempts | `run_id` (PK), `job_id` (FK), `worker_id`, `model_name`, `model_tag`, `model_digest`, `metrics_json`, `status`, `error`, `started_utc`, `completed_utc` |
| **artifact** | Output artifacts | `artifact_id` (PK), `run_id` (FK), `artifact_type` (request_json\|response_json\|evidence_bundle\|prompt_text\|parsed_output\|raw_response), `content_json`, `content_ref`, `created_utc` |
| **evidence_bundle** | Evidence bundles for interrogations | `bundle_id` (PK), `created_utc`, `bundle_type`, `policy_json` |
| **evidence_item** | Individual evidence items | `item_id` (PK), `bundle_id` (FK), `sequence`, `content_type`, `content_text`, `content_ref_json`, `metadata_json`, `created_utc` |
| **run_evidence** | Links runs to evidence bundles | `run_id` (FK, PK), `bundle_id` (FK, PK) |

#### Deprecated LLM Tables (Renamed to *_legacy in v0024)

| Table | Status | Replacement |
|-------|--------|-------------|
| **chunk_legacy** | Deprecated | `vector.chunk` |
| **embedding_legacy** | Deprecated | `vector.embedding` |
| **retrieval_legacy** | Deprecated | `vector.retrieval` |
| **retrieval_hit_legacy** | Deprecated | `vector.retrieval_hit` |
| **source_registry_legacy** | Deprecated | `vector.source_registry` |

**Key Stored Procedures:**
- `dbo.usp_claim_next_job` - Atomic job claim with locking
- `dbo.usp_complete_job` - Mark job succeeded/failed with retry backoff
- `dbo.usp_enqueue_job` - Enqueue new LLM job
- `dbo.usp_create_artifact` - Create run artifact
- `dbo.usp_create_evidence_bundle` - Create evidence bundle with items

---

### 3. Ingest Schema (`ingest`) - Raw Content Sources

**Migration:** `db/migrations/0002_create_tables.sql`, `0011_concurrent_runner_support.sql`

The `ingest` schema stores **raw HTTP response payloads** and manages the **concurrent work queue** for ingestion.

#### Raw Content Tables

| Table | Purpose | Key Columns | Content Storage |
|-------|---------|-------------|-----------------|
| **IngestRecords** | Raw HTTP responses | `ingest_id` (PK), `source_system`, `resource_id`, `request_uri`, `request_method`, `status_code`, `payload` (NVARCHAR(MAX)), `response_headers`, `content_type`, `content_length`, `hash_sha256`, `work_item_id`, `run_id`, `fetched_at_utc` | **Full JSON/HTML payloads in `payload` column** |
| **work_items** | Concurrent work queue | `work_item_id` (PK), `source_system`, `source_name`, `resource_type`, `resource_id`, `variant`, `request_uri`, `status` (pending\|claimed\|completed\|failed), `priority`, `attempt`, `max_attempts`, `claimed_by`, `claimed_at`, `lease_expires_at`, `last_error`, `dedupe_key` | Atomic lease-based ownership |

**Key Indexes:**
- `IngestRecords`: Dedupe on `(source_system, resource_id)`, `(run_id)`, `(fetched_at_utc)`
- `work_items`: Dedupe on `(source_system, source_name, resource_type, resource_id, variant)`

**Content Types Available:**
- `application/json` - MediaWiki API responses, OpenAlex API responses
- `text/html` - Wookieepedia page HTML
- Mixed content types from various sources

---

### 4. Lake Schema (`lake`) - Snapshot/Interchange

**Migration:** `db/migrations/0003_RawExchangeRecord.sql` (approximate, may be in DDL)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **RawExchangeRecord** | Snapshot/interchange table | `exchange_id` (PK), `exchange_type` (http\|mediawiki\|openalex\|llm\|file), `natural_key`, `payload_json` (NVARCHAR(MAX)), `content_sha256`, `source_entity`, `observed_at_utc`, `created_at_utc` |

**Purpose:** Used for data lake snapshots and bidirectional sync with external systems.

---

## Python Modules

### 1. Vector Module (`src/vector/`)

**Purpose:** Persistence layer for the `vector` schema.

#### Core Classes

| File | Class/Function | Purpose |
|------|----------------|---------|
| `store.py` | `VectorStore` | Database operations for vector schema (save/get embedding spaces, chunks, embeddings, retrieval logs) |
| `contracts/models.py` | `EmbeddingSpace` | First-class embedding space identity model |
| | `VectorJob` | Vector job queue entry |
| | `VectorRun` | Vector execution record |
| | `VectorSourceRegistry` | Source registry entry |
| | `VectorChunk` | Chunk model with source linkage |
| | `VectorEmbedding` | Embedding with lineage and idempotency |
| | `VectorRetrieval` | Retrieval query log |
| | `VectorRetrievalHit` | Retrieval result |
| | `JobType` | Enum: CHUNK_SOURCE, EMBED_CHUNKS, REEMBED_SPACE, RETRIEVE_TEST, DRIFT_TEST |
| | `JobStatus` | Enum: NEW, RUNNING, SUCCEEDED, FAILED, DEADLETTER |
| | `compute_content_hash()` | SHA256 hash of content string |
| | `compute_vector_hash()` | SHA256 hash of embedding vector |
| | `generate_chunk_id()` | Deterministic chunk ID from source + offsets + policy version |

**Key Methods in VectorStore:**
- `save_embedding_space()`, `get_embedding_space()`, `get_or_create_embedding_space()`
- `save_chunk()`, `get_chunk()`, `chunk_exists()`
- `save_embedding()`, `get_embedding()`, `embedding_exists()` (checks idempotency)
- `save_retrieval()`, `save_retrieval_hits()`
- `get_embeddings_by_space()`, `get_embeddings_by_filter()`

**Current Status:** ✅ Complete and production-ready (Phase 2)

---

### 2. LLM Retrieval Module (`src/llm/retrieval/`)

**Purpose:** Chunking and embedding generation (now uses `VectorStore`).

#### Key Files

| File | Class/Function | Purpose | Status |
|------|----------------|---------|--------|
| `indexer.py` | `Indexer` | Index sources into chunks with embeddings | ✅ Updated to use `VectorStore` (Phase 2) |
| | `IndexerConfig` | Configuration for indexer (chunk_size, overlap, embed_model) | Active |
| | `SourceManifest` | Manifest of sources to index | Active |
| `chunker.py` | `Chunker` | Text chunking with sliding window | Active |
| | `chunk_text()` | Character-based chunking with overlap and word boundaries | Active |
| `search.py` | `RetrievalStore` | Legacy retrieval store (deprecated) | ⚠️ Deprecated - use `VectorStore` |
| | `retrieve_chunks()` | Cosine similarity retrieval in Python | Active (uses VectorStore data) |
| `evidence_converter.py` | `convert_retrieval_to_evidence()` | Convert retrieval hits to evidence items | Active |

**Indexer CLI:**
```bash
python -m src.llm.retrieval.indexer \
    --source-manifest <path> \
    --mode full|incremental \
    --embed-model <model> \
    --ollama-url <url> \
    --chunk-size <chars> \
    --chunk-overlap <chars>
```

**Chunking Configuration:**
- Default chunk size: 2000 characters
- Default overlap: 200 characters
- Max chunks per source: 100
- Deterministic chunk IDs from source ID + offsets + policy version

**Current Status:** 
- ✅ Indexer fully functional with `VectorStore`
- ✅ Chunking strategy implemented (character-based sliding window)
- ✅ Embedding generation via Ollama `embed()` API
- ⚠️ No CLI runner for vector jobs yet (uses indexer script directly)

---

### 3. LLM Providers Module (`src/llm/providers/`)

#### OllamaClient (`ollama_client.py`)

**Purpose:** HTTP client for Ollama API with comprehensive endpoint support.

**Supported Endpoints:**
- `/api/generate` - Native generate (non-chat)
- `/api/chat` - Native chat with message history
- `/api/embed` - **Embedding generation** ⭐
- `/v1/chat/completions` - OpenAI-compatible chat
- Model metadata: `get_model_info()`, `get_model_digest()`

**Key Methods:**
```python
def embed(self, texts: list, model: Optional[str] = None) -> EmbeddingResponse:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of texts to embed
        model: Embedding model (defaults to OLLAMA_EMBED_MODEL env var)
        
    Returns:
        EmbeddingResponse with embeddings list and metadata
    """
```

**EmbeddingResponse Dataclass:**
```python
@dataclass
class EmbeddingResponse:
    success: bool
    embeddings: list              # List of embedding vectors (list[float])
    model: Optional[str]
    raw_response: Optional[Dict]
    total_duration: Optional[int] # Nanoseconds
    load_duration: Optional[int]  # Nanoseconds
    error_message: Optional[str]
```

**Default Embedding Model:** `nomic-embed-text` (768 dimensions)  
**Environment Variable:** `OLLAMA_EMBED_MODEL`  
**Ollama Endpoint:** `http://ollama:11434/api/embed` (configurable via `OLLAMA_BASE_URL`)

**Request/Response Capture:**
- `get_full_request_payload()` - Returns complete request metadata
- `extract_metrics()` - Parses performance metrics (duration, token counts)
- Integrated with artifact storage patterns

**Current Status:** ✅ Fully functional and production-ready

---

### 4. LLM Job Orchestration (`src/llm/jobs/`, `src/llm/runners/`)

#### Job Type Registry (`src/llm/jobs/registry.py`)

**Purpose:** Registry of LLM job types with handler routing.

**Current LLM Job Types:**
- `page_classification` - Classify pages by primary type
- `sw_entity_facts` - Extract Star Wars entity facts
- `entity_extraction_droid` - Extract entities from page content (Phase 1)

**Registry Pattern:**
```python
@dataclass
class JobTypeDefinition:
    job_type_key: str
    interrogation_key: str
    handler_module_path: str
    handler_class_name: str
    description: str
    enabled: bool
```

**Usage:**
```python
from llm.jobs.registry import get_job_type, get_job_type_registry

job_def = get_job_type("page_classification")
registry = get_job_type_registry()  # Returns all registered types
```

**Current Status:** ✅ Extensible registry pattern in place for LLM jobs (vector jobs not yet registered)

---

#### Job Dispatcher (`src/llm/runners/dispatcher.py`)

**Purpose:** Routes and executes LLM jobs based on job type with handler dispatch.

**Key Features:**
- Job claim from SQL queue (`SqlJobQueue.claim_next_job()`)
- Job type → handler resolution via registry
- Execution context construction (job_id, run_id, correlation_id)
- Status transitions (NEW → RUNNING → SUCCEEDED/FAILED)
- Retry logic with exponential backoff
- Dry-run mode for safe iteration

**CLI Pattern:**
```bash
python -m src.llm.runners.dispatcher \
    --once              # Process 1 job and exit
    --loop              # Poll queue continuously
    --dry-run           # Report without changes
    --list-types        # Show available job types
    --worker-id <id>
    --poll-seconds <n>
```

**Current Status:** ✅ Fully functional for LLM jobs (vector job types not yet integrated)

---

#### Phase1Runner (`src/llm/runners/phase1_runner.py`)

**Purpose:** End-to-end derive runner for Phase 1 LLM interrogations.

**Key Features:**
- Single-worker LLM derive orchestrator
- Job queue polling with `run_once()` / `run_loop()`
- Integration with `SqlJobQueue`
- Artifact storage to lake (`lake/llm_runs/{run_id}/`)
- Retry logic with JSON parsing resilience (3 attempts with exponential backoff)
- Error artifact capture (invalid_json_response.txt, error_manifest.json)

**CLI Pattern:**
```bash
python -m src.llm.runners.phase1_runner \
    --once              # Process 1 job
    --loop              # Continuous polling
    --dry-run           # Report mode
    --worker-id <id>
    --poll-seconds <n>
```

**Current Status:** ✅ Fully functional for LLM chat workloads

---

#### SqlJobQueue (`src/llm/storage/sql_job_queue.py`)

**Purpose:** SQL Server-backed job queue for LLM operations.

**Key Methods:**
- `claim_next_job(worker_id)` - Atomic job claim with locking (calls `usp_claim_next_job`)
- `mark_succeeded(job_id)` / `mark_failed(job_id, error, backoff_seconds)`
- `enqueue_job(job)` / `enqueue_job_idempotent(job, dedupe_key)` (v0025)
- `create_run(job_id, worker_id)` / `complete_run(run_id, status, metrics, error)`
- `create_artifact(run_id, artifact_type, content)`

**Queue Operations Pattern:**
```python
queue = SqlJobQueue(connection)

# Claim next job
job = queue.claim_next_job(worker_id="worker-001")

# Create run
run_id = queue.create_run(job_id=job.job_id, worker_id="worker-001")

# Process job...

# Mark complete
queue.mark_succeeded(job_id=job.job_id)
queue.complete_run(run_id=run_id, status="SUCCEEDED", metrics={...})
```

**Current Status:** ✅ Fully functional for `llm.job` queue (vector queue needs Python wrapper)

---

### 5. Ingest Runner (`src/ingest/runner/concurrent_runner.py`)

**Purpose:** Multi-worker concurrent HTTP ingestion framework.

**Key Features:**
- ThreadPoolExecutor with configurable worker count (default: 4)
- Atomic work item claiming with lease-based ownership
- Graceful shutdown (Ctrl+C / SIGTERM handlers)
- Worker heartbeats to database
- Rate limiting (global & per-worker)
- Exponential backoff with jitter (respects Retry-After header)
- Discovery plugin integration (enqueues new items after fetch)
- Pause/Resume/Drain modes

**Worker Loop Pattern:**
```python
1. claim_work_item(worker_id, lease_seconds) → atomic DB claim
2. Process work item (HTTP fetch, parse, store)
3. Run discovery plugins (enqueue new items)
4. complete_work_item() OR fail_work_item(error)
5. Lease auto-expires if worker dies
```

**CLI Pattern:**
```bash
python -m src.ingest.ingest_cli \
    --config <config.yaml> \
    --seed                  # Enqueue seed items
    --max-items <n>         # Limit items
    --max-workers <n>       # Worker threads
    --source-filter <name>  # Filter by source
```

**Current Status:** ✅ Fully functional concurrent runner (can be pattern reference for vector jobs)

---

## Ollama Integration Points

### 1. Ollama Service (Docker Compose)

**Configuration:** `docker-compose.yml`

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: holocron-ollama
    ports:
      - "127.0.0.1:11434:11434"  # Localhost only for security
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
```

**Access:**
- From host: `http://localhost:11434`
- From containers: `http://ollama:11434`

**Model Management:**
```bash
# Pull model
docker exec -it holocron-ollama ollama pull nomic-embed-text

# List models
docker exec -it holocron-ollama ollama list

# Check running models
docker exec -it holocron-ollama ollama ps
```

**Current Status:** ✅ Ollama service configured and ready

---

### 2. Embedding Model Discovery

**Available Tools:**
- `src/llm/tools/capture_ollama_models.py` - Script to capture model metadata
- `OllamaClient.get_model_info()` - Get model metadata (name, size, parameters)
- `OllamaClient.get_model_digest()` - Get SHA256 digest of model weights

**Model Metadata Pattern:**
```python
client = OllamaClient(config)
model_info = client.get_model_info(model="nomic-embed-text")
# Returns: {
#     "modelfile": "...",
#     "parameters": "...",
#     "template": "...",
#     "details": {
#         "format": "gguf",
#         "family": "nomic-bert",
#         "families": ["nomic-bert"],
#         "parameter_size": "137M",
#         "quantization_level": "F16"
#     }
# }

digest = client.get_model_digest(model="nomic-embed-text")
# Returns: "sha256:abc123..."
```

**Gap:** No automatic extraction of **embedding dimensions** from model metadata (Ollama API doesn't expose this directly). Current workaround: embed a test string and measure vector length.

---

### 3. Supported Embedding Models (Ollama)

**Default:** `nomic-embed-text` (768 dimensions)

**Other Options (require explicit pull):**
- `mxbai-embed-large` (1024 dimensions)
- `all-minilm` (384 dimensions)
- `snowflake-arctic-embed` (multiple sizes)

**Model Selection:**
- Environment variable: `OLLAMA_EMBED_MODEL`
- CLI argument: `--embed-model <model>`
- Python: `client.embed(texts, model="nomic-embed-text")`

---

## Data Starting Points for Embeddings

### 1. Raw Page Pulls (Recommended First Run)

**Source Table:** `ingest.IngestRecords`

**Available Content:**
```sql
-- Count of raw content by source system
SELECT 
    source_system,
    COUNT(*) as record_count,
    COUNT(DISTINCT resource_id) as unique_resources,
    SUM(CASE WHEN content_type LIKE 'application/json%' THEN 1 ELSE 0 END) as json_count,
    SUM(CASE WHEN content_type LIKE 'text/html%' THEN 1 ELSE 0 END) as html_count
FROM ingest.IngestRecords
GROUP BY source_system;
```

**Content Types:**
- **Wookieepedia (MediaWiki)**: HTML pages in `payload` column
- **OpenAlex**: JSON API responses in `payload` column
- **Other sources**: Mixed JSON/HTML content

**Linking to Entities:**
- `ingest.IngestRecords.resource_id` → `sem.source_page.page_id` (via page classification)
- `sem.source_page.page_id` → `dbo.dim_entity` (via entity promotion)

**Recommended First Run Input:**
1. **Source:** Raw HTML from `ingest.IngestRecords` where `source_system = 'wookieepedia'`
2. **Selection:** Pages that have been classified in `sem.source_page`
3. **Extraction:** Strip HTML tags, extract readable text
4. **Chunk:** Apply 2000-char sliding window with 200-char overlap
5. **Embed:** Use `nomic-embed-text` model
6. **Store:** Chunks in `vector.chunk`, embeddings in `vector.embedding`

**SQL Query for First Run Input:**
```sql
-- Get classified pages with raw HTML content
SELECT 
    ir.ingest_id,
    ir.resource_id as page_id,
    sp.title as page_title,
    sp.primary_type,
    ir.payload as raw_html,
    ir.content_length,
    ir.hash_sha256 as content_hash
FROM ingest.IngestRecords ir
INNER JOIN sem.source_page sp 
    ON ir.resource_id = sp.page_id
WHERE ir.source_system = 'wookieepedia'
    AND sp.primary_type IS NOT NULL
    AND LEN(ir.payload) > 100
ORDER BY ir.fetched_at_utc DESC;
```

---

### 2. Alternative Data Sources

| Source | Table | Content | Use Case |
|--------|-------|---------|----------|
| **Extracted text** | `ingest.IngestRecords` (future column) | Clean text extracted from HTML | Cleaner input, requires preprocessing |
| **LLM artifacts** | `llm.artifact` | Parsed output from LLM runs | Structured extractions already curated |
| **Entity descriptions** | `dbo.dim_entity` (future column) | Entity summaries/descriptions | Entity-centric embeddings |
| **Page summaries** | `sem.source_page` (future column) | Page summaries from classification | Pre-curated text |

**Current Status:** Only raw payloads in `ingest.IngestRecords` are immediately available without preprocessing.

---

## Request/Response Audit Trail Patterns

### 1. LLM Run Artifacts (`llm.artifact`)

**Pattern:** Every LLM run stores multiple artifacts to the lake and database.

**Artifact Types:**
- `request_json` - Full request payload (model, prompt, options)
- `response_json` - Full response from Ollama
- `evidence_bundle` - Evidence items used
- `prompt_text` - Final prompt sent to model
- `parsed_output` - Validated JSON output
- `raw_response` - Raw response before parsing

**Storage:**
- Database: `llm.artifact` table with `content_json` or `content_ref`
- Lake: `lake/llm_runs/{run_id}/artifacts/`

**Captured Metadata:**
- Request timestamp, response timestamp
- Model name, tag, digest
- Token counts (prompt_eval_count, eval_count)
- Duration (nanoseconds)
- Worker ID, correlation ID

---

### 2. Ingest Request/Response (`ingest.IngestRecords`)

**Pattern:** Every HTTP fetch stores full request/response metadata.

**Captured Fields:**
- `request_uri`, `request_method`, `request_headers` (JSON)
- `request_timestamp`, `response_timestamp` (UTC)
- `status_code` (HTTP status)
- `response_headers` (JSON) - Content-Type, Content-Length
- `duration_ms` - Request latency
- `content_type`, `content_length` - Extracted metadata
- `error_message` - Failure reasons

---

### 3. Vector Run Tracking (`vector.run`)

**Pattern:** Vector runs track execution metadata similar to LLM runs.

**Captured Fields:**
- `run_id`, `job_id`, `worker_id`
- `embedding_space_id` - Which space was used
- `endpoint_url` - Ollama endpoint
- `model_name`, `model_tag`, `model_digest`
- `options_json` - Run options (chunk size, overlap, etc.)
- `metrics_json` - Performance metrics (duration, chunk count, embedding count)
- `error` - Failure details
- `started_utc`, `completed_utc`

**Gap:** No stored procedure or Python wrapper for vector run operations yet (uses manual SQL or VectorStore direct inserts).

---

## Existing Runner/Orchestrator Components for Reuse

### 1. Job Queue Pattern (Reusable for Vector Jobs)

**Components:**
- `SqlJobQueue` - SQL-backed job queue with atomic claiming
- Job statuses: NEW → RUNNING → SUCCEEDED/FAILED/DEADLETTER
- Retry logic with exponential backoff
- Priority-based ordering
- Worker leasing with expiration

**Current Usage:**
- ✅ LLM chat jobs (`llm.job` queue)
- ✅ Ingest work items (`ingest.work_items` queue)
- ⚠️ Vector jobs (`vector.job` queue exists but no Python wrapper yet)

**Reuse Strategy:**
- Create `VectorJobQueue` class in `src/vector/` mirroring `SqlJobQueue`
- Register vector job types in a vector-specific registry
- Integrate with existing dispatcher pattern or create vector-specific dispatcher

---

### 2. Concurrent Runner Pattern (Reference for Vector Jobs)

**File:** `src/ingest/runner/concurrent_runner.py`

**Reusable Patterns:**
- ThreadPoolExecutor with configurable workers
- Worker loop: claim → process → complete/fail
- Graceful shutdown with signal handlers
- Heartbeat tracking
- Rate limiting and backoff
- Lease-based atomic claiming

**Adaptation for Vector Jobs:**
- Vector job types: CHUNK_SOURCE, EMBED_CHUNKS, REEMBED_SPACE
- Handler dispatch similar to LLM dispatcher
- Batch embedding requests to Ollama (already supports list input)
- Store chunks and embeddings via `VectorStore`

---

### 3. Artifact Storage Pattern (Reusable for Vector Runs)

**File:** `src/llm/storage/lake_writer.py`

**Pattern:**
```python
lake_writer = LakeWriter(config)

# Write artifact to lake
artifact_ref = lake_writer.write_artifact(
    run_id=run_id,
    artifact_type="chunk_manifest",
    content=json.dumps(chunks),
    extension="json"
)

# Artifact stored at: lake/vector_runs/{run_id}/artifacts/chunk_manifest.json
```

**Reuse Strategy:**
- Create vector-specific lake writer or extend existing
- Store vector run manifests, chunk manifests, embedding manifests
- Follow same pattern: `lake/vector_runs/{run_id}/artifacts/`

---

## Summary: What's Built vs. What's Missing

### ✅ What's Built and Ready

1. **SQL Schema:**
   - ✅ Complete `vector` schema with 8 tables
   - ✅ Embedding space identity and idempotency constraints
   - ✅ Job queue and run tracking tables
   - ✅ Chunk and embedding storage with lineage

2. **Python Core:**
   - ✅ `VectorStore` class with full CRUD operations
   - ✅ Data models for all vector objects
   - ✅ `OllamaClient.embed()` method functional
   - ✅ Chunking strategy implemented (`Chunker` class)
   - ✅ `Indexer` class that ties everything together

3. **Infrastructure:**
   - ✅ Ollama service running in Docker Compose
   - ✅ Embedding models available (nomic-embed-text)
   - ✅ Raw content sources in `ingest.IngestRecords`

4. **Patterns:**
   - ✅ Job queue patterns (`SqlJobQueue`, atomic claiming)
   - ✅ Concurrent runner patterns (`ConcurrentRunner`)
   - ✅ Artifact storage patterns (`LakeWriter`)
   - ✅ Request/response audit patterns

### ⚠️ What's Missing (Gap Areas)

1. **Vector Job Orchestration:**
   - ⚠️ No Python wrapper for `vector.job` queue operations
   - ⚠️ No vector job dispatcher/runner (CLI)
   - ⚠️ No vector job type registration
   - ⚠️ No stored procedures for vector job claim/complete

2. **Configuration:**
   - ⚠️ No automatic dimension detection from Ollama models
   - ⚠️ No model registry populated with actual models
   - ⚠️ No embedding space pre-created for default model
   - ⚠️ No chunking policy versioning strategy

3. **Data Extraction:**
   - ⚠️ No SQL query/view to select first batch of pages for embedding
   - ⚠️ No HTML-to-text extraction for raw HTML payloads
   - ⚠️ No manifest generation for indexer input

4. **Pipeline Wiring:**
   - ⚠️ No end-to-end workflow: ingest → extract → chunk → embed → store
   - ⚠️ No job enqueuing from ingest completion (trigger pattern)
   - ⚠️ No progress tracking or metrics dashboard

5. **Observability:**
   - ⚠️ No logging/tracing for vector operations
   - ⚠️ No metrics collection (chunk count, embedding count, duration)
   - ⚠️ No error reporting/alerting

---

## Related Documents

- [Vector Runtime README](../vector/README.md) — Schema overview and usage examples
- [Schema Refactor Migration Notes](../llm/schema-refactor-migration-notes.md) — Migration history
- [Gap Analysis](gap-analysis.md) — Detailed gap analysis (next doc)
- [Recommended Architecture](recommended-architecture.md) — Target architecture design
- [Proposed Work Plan](proposed-work-plan.md) — Implementation backlog
