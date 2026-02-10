# Vector Runtime

The **vector** schema provides infrastructure for embedding generation, storage, and retrieval. It operates independently from the `llm` chat runtime schema.

## Overview

| Schema | Purpose | Semantic |
|--------|---------|----------|
| **`llm`** | Chat/interrogation runtime | Text-in → Text-out |
| **`vector`** | Embedding & retrieval runtime | Text-in → Vectors-out |

## Key Concepts

### Embedding Space

The most important new concept. An **embedding space** defines where cosine/dot-product distance is meaningful. Vectors from different spaces **must not** be compared.

```
vector.embedding_space
├── embedding_space_id (GUID)
├── provider (ollama, openai, etc.)
├── model_name (nomic-embed-text, etc.)
├── model_tag (optional)
├── model_digest (optional SHA256)
├── dimensions (768, 1024, etc.)
├── normalize_flag
├── distance_metric (cosine, dot, euclidean)
└── preprocess_policy_json
```

### Chunk

A bounded unit of text extracted from a source document, ready for embedding and retrieval.

```
vector.chunk
├── chunk_id (deterministic SHA256)
├── source_id (FK to source_registry)
├── source_type (lake_text, lake_http, etc.)
├── source_ref_json
├── offsets_json
├── content
├── content_sha256 (for version coupling)
├── byte_count
└── policy_json
```

### Embedding

Vector representation of a chunk with lineage tracking.

Key improvements over legacy:
- `embedding_space_id` for explicit space identity
- `input_content_sha256` for version coupling
- `run_id` for execution lineage
- Idempotency constraint: `(chunk_id, embedding_space_id, input_content_sha256)`

```
vector.embedding
├── embedding_id (GUID)
├── chunk_id (FK)
├── embedding_space_id (FK)
├── input_content_sha256 (must match chunk version)
├── run_id (optional FK for lineage)
├── vector_json
└── vector_sha256
```

### Job/Run Orchestration

The vector runtime has its own job queue and run tracking, mirroring the patterns from `llm` but with vector-specific semantics.

**Job Types:**
- `CHUNK_SOURCE` — Chunk a new source
- `EMBED_CHUNKS` — Generate embeddings for chunks
- `REEMBED_SPACE` — Re-embed all chunks in a space
- `RETRIEVE_TEST` — Run retrieval benchmark
- `DRIFT_TEST` — Compare spaces over time

### Retrieval Logging

For audit and evaluation of retrieval operations.

```
vector.retrieval
├── retrieval_id (GUID)
├── embedding_space_id (FK)
├── query_text
├── query_embedding_json (optional)
├── top_k
├── filters_json
└── policy_json

vector.retrieval_hit
├── retrieval_id (FK)
├── rank
├── chunk_id (FK)
├── score
└── metadata_json
```

## Schema Tables

| Table | Purpose |
|-------|---------|
| `vector.embedding_space` | First-class embedding space identity |
| `vector.job` | Vector task queue |
| `vector.run` | Vector execution lineage |
| `vector.source_registry` | Source index state |
| `vector.chunk` | Canonical chunk table |
| `vector.embedding` | Embeddings with lineage |
| `vector.retrieval` | Retrieval query log |
| `vector.retrieval_hit` | Retrieval results |

## Python Modules

### `src/vector/`

The vector Python package provides:

- **`src/vector/contracts/models.py`** — Data models for all vector tables
- **`src/vector/store.py`** — `VectorStore` class for database operations

### Usage Example

```python
from vector.store import VectorStore
from vector.contracts.models import EmbeddingSpace, VectorChunk, VectorEmbedding

# Create store with database connection
store = VectorStore(connection=conn)

# Get or create an embedding space
space = store.get_or_create_embedding_space(
    provider="ollama",
    model_name="nomic-embed-text",
    dimensions=768,
)

# Save a chunk
chunk = VectorChunk(
    chunk_id="abc123",
    source_type="lake_text",
    source_ref={"lake_uri": "/path/to/file.txt"},
    offsets={"start": 0, "end": 1000},
    content="This is the chunk content...",
    content_sha256="...",
    byte_count=1000,
    policy={"chunk_size": 2000},
)
store.save_chunk(chunk)

# Save an embedding
embedding = VectorEmbedding.create_new(
    chunk_id=chunk.chunk_id,
    embedding_space_id=space.embedding_space_id,
    input_content_sha256=chunk.content_sha256,
    vector=[0.1, 0.2, 0.3, ...],
)
store.save_embedding(embedding)

# Check idempotency
exists = store.embedding_exists(
    chunk_id=chunk.chunk_id,
    embedding_space_id=space.embedding_space_id,
    input_content_sha256=chunk.content_sha256,
)
```

## Migration Path

### Current State (Phase 1)

- ✅ `vector` schema created with all tables
- ✅ Python `VectorStore` class available
- ✅ Legacy `llm.*` vector tables remain (backward compatibility)
- ✅ Both schemas can be used in parallel

### Phase 2 (Future)

- Switch all embedding/retrieval code to `vector.*`
- Remove `RetrievalStore` class
- Drop legacy vector tables from `llm`:
  - `llm.chunk`
  - `llm.embedding`
  - `llm.retrieval`
  - `llm.retrieval_hit`
  - `llm.source_registry`

## Related Documents

- [Schema Refactor Migration Notes](../llm/schema-refactor-migration-notes.md)
- [Dependency Inventory](../llm/dependency-inventory-vector-subsystem.md)
- [Legacy Schema Snapshot](../../db/legacy_snapshots/llm_vector_subsystem_snapshot.sql)
- [Retrieval System (Legacy)](../llm/retrieval.md)
