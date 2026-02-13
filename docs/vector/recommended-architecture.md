# Recommended Architecture — Vector/Embedding Subsystem

**Status:** Phase III Evaluation (Documentation Only)  
**Date:** 2026-02-13  
**Purpose:** Define the recommended target architecture to achieve "run embeddings against raw ingest content and store them" with model flexibility and dedupe.

---

## Overview

This document describes the recommended architecture for embedding generation, storage, and retrieval that addresses the gaps identified in [gap-analysis.md](gap-analysis.md) while reusing existing orchestration patterns.

**Design Principles:**
1. **Reuse existing patterns** - Job queue, runners, artifact storage
2. **Schema separation** - Keep vector and LLM schemas independent
3. **Model flexibility** - Support multiple embedding models and spaces
4. **Idempotency and dedupe** - SHA256-based change detection
5. **Minimal viable first** - Start with script-based, evolve to job-based

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EMBEDDING PIPELINE                            │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   Ingest     │  Raw HTTP responses (HTML/JSON)
│  IngestRecords│
│   (payload)  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│   Data Extraction        │  HTML → Text extraction
│                          │  (BeautifulSoup/lxml)
│  - Strip HTML tags       │
│  - Extract article text  │
│  - Normalize whitespace  │
└──────────┬───────────────┘
           │
           ▼
┌────────────────────────────────┐
│   Source Selection & Manifest  │  Query candidate sources
│                                │  Generate JSON manifest
│  - SQL view filtering          │
│  - Limit/pagination            │
│  - Prioritization              │
└────────────┬───────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                   VECTOR JOB ORCHESTRATION                    │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ vector.job   │      │VectorJobQueue│                     │
│  │   Queue      │◄─────│   (Python)   │                     │
│  └──────┬───────┘      └──────────────┘                     │
│         │ claim                                               │
│         ▼                                                     │
│  ┌─────────────────────────────────────────┐                │
│  │    VectorDispatcher (Runner)            │                │
│  │                                          │                │
│  │  - Polls queue                           │                │
│  │  - Routes to handlers                    │                │
│  │  - Manages run lifecycle                 │                │
│  └─────────┬───────────────────────────────┘                │
│            │ route                                            │
│            ▼                                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │ ChunkSourceHandler  │    │ EmbedChunksHandler  │        │
│  │                     │    │                     │        │
│  │ - Read source       │    │ - Read chunks       │        │
│  │ - Extract text      │    │ - Batch embed()     │        │
│  │ - Chunk content     │    │ - Store embeddings  │        │
│  │ - Store chunks      │    │ - Handle failures   │        │
│  └─────────────────────┘    └─────────────────────┘        │
└──────────────────────────────────────────────────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────┐         ┌────────────────────────┐
│   Chunking         │         │   Embedding Generation │
│                    │         │                        │
│  - Sliding window  │         │  Ollama /api/embed     │
│  - Character-based │         │  ┌──────────────────┐  │
│  - 2000 / 200      │         │  │ nomic-embed-text │  │
│  - Word boundaries │         │  │   (768 dims)     │  │
│                    │         │  └──────────────────┘  │
└────────┬───────────┘         └─────────┬──────────────┘
         │                               │
         ▼                               ▼
┌───────────────────────────────────────────────────────────┐
│                  VECTOR SCHEMA (SQL)                       │
│                                                            │
│  ┌───────────────────┐    ┌──────────────────┐           │
│  │ embedding_space   │    │  source_registry │           │
│  │                   │    │                  │           │
│  │ - provider        │    │ - source_id      │           │
│  │ - model_name      │    │ - content_sha256 │◄─── Change│
│  │ - dimensions      │    │ - status         │     Detection│
│  │ - model_digest    │    └──────────────────┘           │
│  └───────────────────┘                                    │
│                                                            │
│  ┌────────────────┐       ┌──────────────────┐           │
│  │     chunk      │       │    embedding     │           │
│  │                │       │                  │           │
│  │ - chunk_id ◄───┼───────┤ - chunk_id (FK) │           │
│  │ - content      │       │ - embedding_space_id (FK)   │
│  │ - content_sha256│       │ - input_content_sha256     │
│  │ - offsets_json │       │ - vector_json    │           │
│  │ - policy_json  │       │ - run_id (FK)    │           │
│  └────────────────┘       └──────────────────┘           │
│                                                            │
│  UQ: (chunk_id, embedding_space_id, input_content_sha256) │
└────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Retrieval (Future)  │
                     │                       │
                     │ - Cosine similarity   │
                     │ - Top-K results       │
                     │ - Evidence conversion │
                     └───────────────────────┘
```

---

## Component Architecture

### 1. Data Extraction Layer

**Purpose:** Convert raw ingest payloads to clean text for chunking.

**Components:**

#### HTML Extractor (`src/vector/extraction/html_extractor.py`)

```python
def html_to_text(html: str) -> str:
    """
    Strip HTML tags and extract readable text.
    
    Uses BeautifulSoup to:
    - Remove <script>, <style>, <nav>, <footer> tags
    - Extract text from article body
    - Normalize whitespace
    - Preserve paragraph breaks
    
    Returns:
        Clean text suitable for chunking
    """
```

**Integration Point:**
- Called by `Indexer` or `ChunkSourceHandler`
- Detects content type from source_ref
- Routes to appropriate extractor (html, json, text)

**Dependencies:**
- `beautifulsoup4` or `lxml` (add to `requirements.txt`)

---

### 2. Source Selection Layer

**Purpose:** Identify and prioritize sources for embedding.

**Components:**

#### SQL View: `vector.vw_candidate_sources_for_embedding`

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
    -- Check if already in source_registry
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

**Filters:**
- Only classified pages (`sem.source_page` join)
- Minimum content length (1000 chars)
- Successful HTTP status (200)
- Exclude already-embedded unless changed

#### Manifest Generator (`src/vector/tools/generate_manifest.py`)

```python
def generate_manifest(
    conn,
    output_path: str,
    primary_type: Optional[str] = None,
    limit: Optional[int] = None,
    status_filter: str = "pending",
) -> SourceManifest:
    """
    Generate a source manifest for the Indexer.
    
    Args:
        conn: Database connection
        output_path: Path to write manifest JSON
        primary_type: Filter by primary_type (e.g., "PersonCharacter")
        limit: Max sources to include
        status_filter: "pending", "changed", or "all"
    
    Returns:
        SourceManifest object
    """
```

**Output Format:**
```json
{
    "version": "1.0",
    "sources": [
        {
            "source_id": "page_123",
            "source_type": "wookieepedia_page",
            "ingest_id": "abc-def-ghi",
            "page_title": "Luke Skywalker",
            "primary_type": "PersonCharacter",
            "content_type": "text/html",
            "content_hash": "sha256:..."
        }
    ]
}
```

---

### 3. Job Orchestration Layer

**Purpose:** Manage vector workloads through job queue with retry/monitoring.

#### Vector Job Queue (`src/vector/queue.py`)

```python
class VectorJobQueue:
    """
    SQL-backed job queue for vector operations.
    
    Mirrors SqlJobQueue pattern from LLM subsystem but operates
    on vector.job and vector.run tables.
    """
    
    def enqueue_job(
        self,
        job_type: JobType,
        input_json: Dict[str, Any],
        embedding_space_id: Optional[str] = None,
        priority: int = 100,
    ) -> str:
        """Enqueue a new vector job. Returns job_id."""
    
    def claim_next_job(self, worker_id: str) -> Optional[VectorJob]:
        """Atomically claim the next available job."""
    
    def mark_succeeded(self, job_id: str) -> None:
        """Mark job as succeeded."""
    
    def mark_failed(
        self,
        job_id: str,
        error: str,
        backoff_seconds: int = 60,
    ) -> None:
        """Mark job as failed with retry backoff."""
    
    def create_run(
        self,
        job_id: str,
        worker_id: str,
        embedding_space_id: Optional[str] = None,
    ) -> str:
        """Create a new run for this job attempt. Returns run_id."""
    
    def complete_run(
        self,
        run_id: str,
        status: RunStatus,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Complete a run with metrics and status."""
```

**Database Operations:**
- Uses MERGE or stored procedures for atomic operations
- Supports priority-based job ordering
- Implements exponential backoff for retries

---

#### Vector Job Handlers

**Base Handler Interface:**

```python
class VectorJobHandler(ABC):
    """Base class for vector job handlers."""
    
    @abstractmethod
    def handle(
        self,
        job: VectorJob,
        context: VectorRunContext,
    ) -> HandlerResult:
        """Execute the job. Returns result with status and artifacts."""
```

**ChunkSourceHandler** (`src/vector/handlers/chunk_source_handler.py`):

```python
class ChunkSourceHandler(VectorJobHandler):
    """
    Handler for CHUNK_SOURCE jobs.
    
    Workflow:
    1. Read source from input_json (ingest_id or source_id)
    2. Extract content (HTML → text if needed)
    3. Chunk content using Chunker
    4. Compute chunk hashes and IDs
    5. Store chunks via VectorStore
    6. Update source_registry
    """
    
    def handle(self, job: VectorJob, context: VectorRunContext) -> HandlerResult:
        # Load source from database
        source = self._load_source(job.input_json)
        
        # Extract text
        text = self.extractor.extract(source.payload, source.content_type)
        
        # Chunk
        chunks = self.chunker.chunk_text(
            text=text,
            source_id=source.source_id,
            policy=self.policy,
        )
        
        # Store chunks
        for chunk in chunks:
            self.store.save_chunk(chunk)
        
        # Update registry
        self.store.update_source_registry(
            source_id=source.source_id,
            content_sha256=source.content_hash,
            chunk_count=len(chunks),
            status=SourceStatus.INDEXED,
        )
        
        return HandlerResult(
            status=HandlerStatus.SUCCESS,
            chunks_created=len(chunks),
        )
```

**EmbedChunksHandler** (`src/vector/handlers/embed_chunks_handler.py`):

```python
class EmbedChunksHandler(VectorJobHandler):
    """
    Handler for EMBED_CHUNKS jobs.
    
    Workflow:
    1. Read chunks from vector.chunk (by source_id or chunk_ids)
    2. Filter out already-embedded chunks (idempotency)
    3. Batch chunks for embedding (Ollama supports list input)
    4. Call ollama.embed() in batches
    5. Store embeddings via VectorStore
    6. Link embeddings to run_id
    """
    
    def handle(self, job: VectorJob, context: VectorRunContext) -> HandlerResult:
        # Load chunks
        chunk_ids = job.input_json.get("chunk_ids")
        chunks = self.store.get_chunks(chunk_ids)
        
        # Filter already-embedded
        missing = self.store.get_missing_embeddings(
            chunk_ids=[c.chunk_id for c in chunks],
            embedding_space_id=job.embedding_space_id,
        )
        
        # Batch embed
        texts = [chunks_by_id[cid].content for cid in missing]
        response = self.ollama.embed(texts=texts, model=self.model)
        
        # Store embeddings
        for i, chunk_id in enumerate(missing):
            chunk = chunks_by_id[chunk_id]
            embedding = VectorEmbedding.create_new(
                chunk_id=chunk_id,
                embedding_space_id=job.embedding_space_id,
                input_content_sha256=chunk.content_sha256,
                vector=response.embeddings[i],
                run_id=context.run_id,
            )
            self.store.save_embedding(embedding)
        
        return HandlerResult(
            status=HandlerStatus.SUCCESS,
            embeddings_created=len(missing),
        )
```

---

#### Vector Job Registry (`src/vector/jobs/registry.py`)

```python
VECTOR_JOB_TYPES = {
    "chunk_source": JobTypeDefinition(
        job_type_key="chunk_source",
        handler_module_path="src.vector.handlers.chunk_source_handler",
        handler_class_name="ChunkSourceHandler",
        description="Chunk a source into searchable units",
        schema="vector",
        enabled=True,
    ),
    "embed_chunks": JobTypeDefinition(
        job_type_key="embed_chunks",
        handler_module_path="src.vector.handlers.embed_chunks_handler",
        handler_class_name="EmbedChunksHandler",
        description="Generate embeddings for chunks",
        schema="vector",
        enabled=True,
    ),
}

def get_vector_job_type(job_type_key: str) -> JobTypeDefinition:
    """Get vector job type definition."""
    return VECTOR_JOB_TYPES.get(job_type_key)
```

---

#### Vector Dispatcher (`src/vector/runners/vector_dispatcher.py`)

```python
class VectorDispatcher:
    """
    Dispatcher for vector jobs.
    
    Polls vector.job queue, routes to handlers, manages run lifecycle.
    """
    
    def run_once(self) -> bool:
        """Process one job from the queue."""
        job = self.queue.claim_next_job(self.worker_id)
        if not job:
            return False
        
        # Create run
        run_id = self.queue.create_run(
            job_id=job.job_id,
            worker_id=self.worker_id,
            embedding_space_id=job.embedding_space_id,
        )
        
        # Create context
        context = VectorRunContext(
            job_id=job.job_id,
            run_id=run_id,
            worker_id=self.worker_id,
            correlation_id=self._generate_correlation_id(),
        )
        
        try:
            # Resolve handler
            job_type_def = get_vector_job_type(job.job_type.value)
            handler = self._instantiate_handler(job_type_def)
            
            # Execute
            result = handler.handle(job, context)
            
            # Mark succeeded
            self.queue.mark_succeeded(job.job_id)
            self.queue.complete_run(
                run_id=run_id,
                status=RunStatus.SUCCEEDED,
                metrics=result.metrics,
            )
            
        except Exception as e:
            logger.exception(f"Job {job.job_id} failed")
            self.queue.mark_failed(job.job_id, str(e))
            self.queue.complete_run(
                run_id=run_id,
                status=RunStatus.FAILED,
                error=str(e),
            )
        
        return True
    
    def run_loop(self, poll_seconds: int = 10):
        """Poll queue continuously."""
        while not self.shutdown_requested:
            if not self.run_once():
                time.sleep(poll_seconds)
```

**CLI:**
```bash
python -m src.vector.runners.vector_dispatcher \
    --once              # Process 1 job
    --loop              # Continuous polling
    --dry-run           # Report mode
    --worker-id <id>    # Worker identifier
    --poll-seconds <n>  # Loop interval
```

---

### 4. Storage Layer

**Purpose:** Persist chunks, embeddings, and metadata with idempotency.

**Component:** `VectorStore` (already implemented in `src/vector/store.py`)

**Key Enhancements Needed:**

1. **Batch Operations:**
   ```python
   def get_missing_embeddings(
       self,
       chunk_ids: List[str],
       embedding_space_id: str,
   ) -> List[str]:
       """
       Return chunk_ids that do not have embeddings in the given space.
       
       Efficient batch check for idempotency.
       """
   ```

2. **MERGE Support:**
   ```python
   def save_chunk(self, chunk: VectorChunk) -> None:
       """
       Save chunk using MERGE to handle duplicates gracefully.
       
       If chunk_id exists, skip (idempotent).
       """
   ```

3. **Source Registry Updates:**
   ```python
   def update_source_registry(
       self,
       source_id: str,
       content_sha256: str,
       chunk_count: int,
       status: SourceStatus,
   ) -> None:
       """Update source registry after chunking/embedding."""
   ```

---

### 5. Model Management Layer

**Purpose:** Discover available models, track metadata, and manage embedding spaces.

#### Model Discovery Script (`src/vector/tools/discover_models.py`)

```python
def discover_models(
    ollama_client: OllamaClient,
    store: VectorStore,
    auto_create_spaces: bool = True,
) -> List[EmbeddingSpace]:
    """
    Discover available embedding models from Ollama.
    
    Workflow:
    1. Query Ollama for models (via `ollama list` or API)
    2. For each embedding model:
       - Embed a test string to measure dimensions
       - Get model digest via `get_model_digest()`
       - Extract model metadata (family, parameter size)
    3. Create or update embedding_space entries
    
    Returns:
        List of EmbeddingSpace objects
    """
    models = ollama_client.list_models()  # Hypothetical API
    
    spaces = []
    for model in models:
        if not is_embedding_model(model):
            continue
        
        # Measure dimensions
        test_response = ollama_client.embed(
            texts=["test"],
            model=model.name,
        )
        dimensions = len(test_response.embeddings[0])
        
        # Get digest
        digest = ollama_client.get_model_digest(model=model.name)
        
        # Create or update space
        space = store.get_or_create_embedding_space(
            provider="ollama",
            model_name=model.name,
            model_tag=model.tag or "latest",
            model_digest=digest,
            dimensions=dimensions,
        )
        
        spaces.append(space)
    
    return spaces
```

**CLI:**
```bash
python -m src.vector.tools.discover_models \
    --ollama-url http://ollama:11434 \
    --auto-create-spaces
```

---

## Data Flow: End-to-End

### Scenario 1: Script-Based First Run (Path A)

**Goal:** Embed 100 Wookieepedia pages as proof-of-concept.

**Steps:**

1. **Setup:**
   ```bash
   # Pull embedding model
   docker exec -it holocron-ollama ollama pull nomic-embed-text
   
   # Run model discovery (creates embedding_space)
   python -m src.vector.tools.discover_models --auto-create-spaces
   ```

2. **Generate Manifest:**
   ```bash
   python -m src.vector.tools.generate_manifest \
       --primary-type PersonCharacter \
       --limit 100 \
       --output /tmp/first_run_manifest.json
   ```

3. **Run Indexer:**
   ```bash
   python -m src.llm.retrieval.indexer \
       --source-manifest /tmp/first_run_manifest.json \
       --mode full \
       --chunk-size 2000 \
       --chunk-overlap 200 \
       --embed-model nomic-embed-text \
       --verbose
   ```

4. **Verify:**
   ```sql
   -- Check chunks created
   SELECT COUNT(*) FROM vector.chunk;
   
   -- Check embeddings created
   SELECT COUNT(*) FROM vector.embedding;
   
   -- Check source registry
   SELECT * FROM vector.source_registry 
   WHERE status = 'indexed' 
   ORDER BY last_indexed_utc DESC;
   ```

**Outcome:**
- 100 pages → ~2000-5000 chunks (depends on content length)
- ~2000-5000 embeddings stored
- Source registry updated with content hashes

---

### Scenario 2: Job-Based Production Run (Path B)

**Goal:** Continuous embedding of newly ingested content via job queue.

**Steps:**

1. **Setup (one-time):**
   ```bash
   # Model discovery
   python -m src.vector.tools.discover_models --auto-create-spaces
   
   # Start vector dispatcher
   python -m src.vector.runners.vector_dispatcher --loop
   ```

2. **Enqueue Jobs:**
   ```bash
   # Batch enqueue script
   python -m src.vector.tools.enqueue_missing_sources \
       --primary-type PersonCharacter \
       --limit 100
   ```
   
   **OR** (automatic trigger from ingest):
   ```python
   # In ingest completion hook
   queue.enqueue_job(
       job_type=JobType.CHUNK_SOURCE,
       input_json={"ingest_id": ingest_id},
       priority=100,
   )
   ```

3. **Job Processing:**
   - Dispatcher claims CHUNK_SOURCE job
   - ChunkSourceHandler reads source, extracts text, chunks, stores
   - Dispatcher claims EMBED_CHUNKS job (can be auto-enqueued after chunking)
   - EmbedChunksHandler embeds chunks, stores embeddings

4. **Monitoring:**
   ```sql
   -- Check job queue status
   SELECT status, COUNT(*) 
   FROM vector.job 
   GROUP BY status;
   
   -- Check recent runs
   SELECT TOP 10
       r.run_id,
       r.status,
       r.started_utc,
       r.completed_utc,
       JSON_VALUE(r.metrics_json, '$.chunks_processed') as chunks,
       JSON_VALUE(r.metrics_json, '$.embeddings_created') as embeddings
   FROM vector.run r
   ORDER BY r.started_utc DESC;
   ```

**Outcome:**
- Continuous background processing
- New content automatically embedded
- Retry on failures with backoff
- Metrics and logging for observability

---

## Configuration Strategy

### Environment Variables

```bash
# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_TIMEOUT_SECONDS=120

# Chunking
INDEX_CHUNK_SIZE=2000
INDEX_CHUNK_OVERLAP=200
INDEX_MAX_CHUNKS_PER_SOURCE=100

# Vector Jobs
VECTOR_WORKER_ID=vector-worker-001
VECTOR_POLL_SECONDS=10
VECTOR_MAX_ATTEMPTS=3

# Lake
LAKE_ROOT=lake
VECTOR_RUNS_PATH=lake/vector_runs
```

### Configuration Files (Optional)

`config/vector.yaml`:
```yaml
vector:
  default_embedding_space:
    provider: ollama
    model_name: nomic-embed-text
    dimensions: 768
  
  chunking:
    default_policy:
      version: "v1.0"
      chunk_size: 2000
      overlap: 200
      max_chunks_per_source: 100
      strategy: character-sliding-window
  
  extraction:
    html:
      strip_tags: [script, style, nav, footer]
      preserve_paragraphs: true
  
  queue:
    poll_seconds: 10
    max_attempts: 3
    backoff_base: 60
```

---

## Hashing and Deduplication Strategy

### Content Hashing (SHA-256)

**What to Hash:**
```python
hash_input = f"{normalized_content}|{embedding_input_type}|{model_identity}|{chunk_index}"
content_sha256 = hashlib.sha256(hash_input.encode()).hexdigest()
```

**Components:**
1. `normalized_content` - Whitespace-normalized text content
2. `embedding_input_type` - e.g., "raw_html", "extracted_text", "sql_json"
3. `model_identity` - `{provider}:{model_name}:{model_tag}:{model_digest}`
4. `chunk_index` - Position within source (for multi-chunk sources)

**Purpose:**
- Detect content changes (re-chunk if hash differs)
- Ensure deterministic chunk IDs
- Support model upgrades (different hash if model changes)

### Change Detection Workflow

```python
# Check if source has changed
existing_registry = store.get_source_registry(source_id)

if existing_registry:
    if existing_registry.content_sha256 == new_content_sha256:
        # Unchanged - skip
        return
    else:
        # Changed - invalidate old embeddings
        store.invalidate_embeddings_for_source(source_id)

# Proceed with chunking/embedding
```

### Idempotency Enforcement

**Chunk Level:**
- Chunk ID is deterministic: `SHA256(source_id, chunk_index, offsets, policy_version)`
- Re-running chunking produces same chunk IDs
- Database PK constraint prevents duplicates

**Embedding Level:**
- Unique constraint: `(chunk_id, embedding_space_id, input_content_sha256)`
- Prevents duplicate embeddings for same chunk + model + content version
- Re-running embedding skips existing (via batch check)

**Vector Level:**
- Vector SHA256 stored for integrity verification
- Can detect if embedding vector changes for same input (debugging)

---

## Chunking Strategy

### Default Policy (MVP)

```python
ChunkingPolicy(
    version="v1.0",
    strategy="character-sliding-window",
    chunk_size=2000,        # Characters
    overlap=200,            # Characters
    max_chunks_per_source=100,
    word_boundary_respect=True,
)
```

### Chunking Algorithm

```python
def chunk_text(
    text: str,
    source_id: str,
    policy: ChunkingPolicy,
) -> List[VectorChunk]:
    """
    Character-based sliding window chunking.
    
    Algorithm:
    1. Start at position 0
    2. Extract chunk_size characters
    3. Find last word boundary within chunk (if word_boundary_respect)
    4. Create chunk with offsets
    5. Move start position by (chunk_size - overlap)
    6. Repeat until end of text or max_chunks reached
    """
```

### Future Enhancements (Post-MVP)

1. **Token-Aware Chunking:**
   - Use `tiktoken` or model-specific tokenizer
   - Enforce context window limits (e.g., 512 tokens)
   - More accurate for embedding model constraints

2. **Semantic Chunking:**
   - Split on sentence or paragraph boundaries
   - Use NLP to detect topic shifts
   - Better coherence per chunk

3. **Adaptive Chunking:**
   - Vary chunk size based on content type
   - Smaller chunks for dense content (code, lists)
   - Larger chunks for narrative text

---

## Observability and Monitoring

### Structured Logging

**VectorRunContext:**
```python
@dataclass
class VectorRunContext:
    job_id: str
    run_id: str
    worker_id: str
    correlation_id: str
    
    def get_log_context(self) -> Dict[str, str]:
        """Return structured log fields."""
        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "worker_id": self.worker_id,
            "correlation_id": self.correlation_id,
            "subsystem": "vector",
        }
```

**Usage:**
```python
logger.info(
    "Chunking source",
    extra=context.get_log_context(),
    source_id=source_id,
    chunks_created=len(chunks),
)
```

### Metrics Collection

**VectorRunMetrics:**
```python
@dataclass
class VectorRunMetrics:
    duration_ms: int
    chunks_processed: int
    embeddings_created: int
    api_calls: int
    api_duration_ms: int
    bytes_processed: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

**Storage:**
- Store in `vector.run.metrics_json`
- Queryable for analytics and dashboards

### Error Artifacts

**Lake Structure:**
```
lake/vector_runs/{run_id}/
├── run_manifest.json
├── chunk_manifest.json
├── embedding_manifest.json
├── error_manifest.json (if failed)
└── failed_chunks.json (if partial failure)
```

**error_manifest.json:**
```json
{
    "run_id": "abc-123",
    "job_id": "def-456",
    "worker_id": "vector-worker-001",
    "error_type": "OllamaAPIError",
    "error_message": "Connection timeout",
    "stack_trace": "...",
    "failed_at_utc": "2026-02-13T04:00:00Z",
    "chunks_attempted": 50,
    "chunks_succeeded": 42,
    "chunks_failed": 8
}
```

---

## Migration Path

### Phase 1: Proof-of-Concept (Script-Based)

**Timeline:** 1-2 days

**Deliverables:**
- Model discovery script
- Manifest generator
- HTML extraction in Indexer
- Run first 100 pages through Indexer script

**Goal:** Prove end-to-end pipeline works

---

### Phase 2: Job Infrastructure (Job-Based)

**Timeline:** 3-5 days

**Deliverables:**
- `VectorJobQueue` class
- Vector job handlers (ChunkSource, EmbedChunks)
- Vector job registry
- Vector dispatcher
- Stored procedures for atomic job operations

**Goal:** Production-quality orchestration

---

### Phase 3: Automation and Observability

**Timeline:** 2-3 days

**Deliverables:**
- Batch enqueue script
- Post-ingest hook (optional)
- Structured logging
- Metrics collection
- Error artifacts and monitoring

**Goal:** Continuous, observable, maintainable system

---

## Deployment Considerations

### Resource Requirements

**For 1000 pages:**
- Chunks: ~20,000-50,000 (depends on content length)
- Embeddings: ~20,000-50,000 vectors (768 floats each)
- Storage: ~5-10 GB (vector_json as NVARCHAR)
- Ollama: ~2 GB GPU memory (nomic-embed-text)
- Processing time: ~1-2 hours (single worker)

**Scaling:**
- Add more vector dispatcher workers (parallel job processing)
- Batch embedding calls (Ollama supports list input)
- Use GPU for Ollama (4x-10x faster)

### Database Indexes

**Critical Indexes:**
```sql
-- Chunk lookup by source
CREATE INDEX IX_vector_chunk_source_id 
ON vector.chunk (source_id);

-- Embedding lookup by space
CREATE INDEX IX_vector_embedding_space 
ON vector.embedding (embedding_space_id);

-- Embedding idempotency check
-- Already exists: UQ on (chunk_id, embedding_space_id, input_content_sha256)

-- Job queue polling
CREATE INDEX IX_vector_job_status_priority 
ON vector.job (status, priority DESC, available_utc);
```

---

## Related Documents

- [Current State Inventory](current-state-inventory.md) — What exists today
- [Gap Analysis](gap-analysis.md) — What's missing
- [Proposed Work Plan](proposed-work-plan.md) — Implementation tasks
