# Retrieval Augmented Generation (Phase 3)

> **⚠️ LEGACY DOCUMENTATION**
> 
> This document describes the original Phase 3 retrieval system using the `llm.*` tables.
> **As of Phase 2 of the schema refactor, this documentation is historical.**
> 
> The `llm.*` vector tables have been renamed to `*_legacy` and are deprecated.
> 
> **For current documentation, see:**
> - [Vector Runtime README](../vector/README.md) — New vector schema
> - [Schema Refactor Migration Notes](schema-refactor-migration-notes.md) — Migration history
> - [VectorStore usage](../vector/README.md#usage-example) — Current API

This document describes the original Phase 3 Retrieval Augmented Generation (RAG) system for the LLM-Derived Data subsystem.

**Last Updated:** February 2026 (marked as legacy)

---

## Overview

Phase 3 added retrieval augmentation to the LLM pipeline, enabling:

- **Chunking**: Split internal artifacts into searchable units
- **Embeddings**: Generate vector representations using Ollama locally
- **Vector Store**: Store embeddings in SQL Server for retrieval
- **Evidence Selection**: Retrieve relevant chunks for LLM interrogations

This creates a local RAG pipeline that:
1. Indexes internal documents into chunks with embeddings
2. Retrieves relevant chunks for each query
3. Assembles evidence bundles from retrieved content
4. Maintains full audit trails for reproducibility

---

## Architecture

### Vector Store Design

Phase 3 uses **Option 2: SQL Server + Python similarity**:

- Embeddings are stored as JSON in SQL Server (`llm.embedding.vector_json`)
- Candidate vectors are retrieved by metadata filters (source_type, tags)
- Cosine similarity is computed in Python
- Retrieval results are persisted back to SQL for auditing

This approach was chosen for:
- Simplicity and reliability
- No additional infrastructure required
- Full control over scoring and ranking
- SQL Server 2019+ compatibility

### Embedding Model

Default embedding model: **nomic-embed-text** (via Ollama)

- Generates 768-dimensional embeddings
- Runs locally, no external API keys required
- Configurable via `OLLAMA_EMBED_MODEL` environment variable

### Chunking Policy

Configurable chunking parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 2000 | Target chunk size in characters |
| `overlap` | 200 | Overlap between chunks |
| `max_chunks_per_source` | 100 | Maximum chunks per source |
| `version` | 1.0 | Policy version for reproducibility |

---

## Data Models

### ChunkRecord

Represents a bounded unit of text extracted from a source:

```python
@dataclass
class ChunkRecord:
    chunk_id: str           # Deterministic SHA256 hash
    source_type: str        # lake_text, lake_http, doc, etc.
    source_ref: dict        # Source identity (lake_uri, url, etc.)
    offsets: dict           # Byte/line range, chunk index
    content: str            # Bounded text content
    content_sha256: str     # Content hash for deduplication
    byte_count: int         # Size in bytes
    policy: dict            # Chunking policy used
    created_utc: datetime   # Creation timestamp
```

### EmbeddingRecord

Stores the vector representation of a chunk:

```python
@dataclass
class EmbeddingRecord:
    embedding_id: str       # UUID
    chunk_id: str           # FK to chunk
    embedding_model: str    # Model name
    vector_dim: int         # Vector dimensionality
    vector: list[float]     # Embedding vector
    vector_sha256: str      # Vector hash for integrity
    created_utc: datetime   # Creation timestamp
```

### RetrievalQuery

Captures retrieval query metadata for reproducibility:

```python
@dataclass
class RetrievalQuery:
    retrieval_id: str           # UUID
    run_id: Optional[str]       # Links to LLM run
    query_text: str             # Query text
    query_embedding_model: str  # Model used for query
    top_k: int                  # Results requested
    filters: dict               # Filter criteria
    policy: dict                # Scoring policy
    created_utc: datetime       # Query timestamp
```

### RetrievalHit

Represents a single retrieval result:

```python
@dataclass
class RetrievalHit:
    retrieval_id: str   # FK to query
    chunk_id: str       # FK to chunk
    score: float        # Similarity score
    rank: int           # Position in results
    metadata: dict      # Additional metadata
```

---

## Determinism and Reproducibility

Phase 3 ensures retrieval is fully deterministic and reproducible:

### Chunk ID Generation

Chunk IDs are SHA256 hashes of:
- Source ID (lake_uri or unique identifier)
- Chunk index within source
- Start and end offsets
- Policy version

This ensures the same content produces the same chunk ID.

### Tie-Breaking

When chunks have identical scores:
1. Primary sort: Score (descending)
2. Secondary sort: Chunk ID (ascending)

This ensures consistent ordering regardless of database query order.

### Audit Trail

Every retrieval operation stores:
- Full query parameters in `llm.retrieval`
- All hits with scores in `llm.retrieval_hit`
- Artifacts in the lake at `lake/llm_retrieval/{retrieval_id}/`

---

## SQL Schema

Phase 3 adds these tables to the `llm` schema:

### llm.chunk

Stores chunk records:

| Column | Type | Description |
|--------|------|-------------|
| chunk_id | NVARCHAR(128) | Deterministic hash (PK) |
| source_type | NVARCHAR(100) | Source type |
| source_ref_json | NVARCHAR(MAX) | Source reference |
| offsets_json | NVARCHAR(MAX) | Chunk offsets |
| content | NVARCHAR(MAX) | Chunk text |
| content_sha256 | NVARCHAR(64) | Content hash |
| byte_count | BIGINT | Size in bytes |
| policy_json | NVARCHAR(MAX) | Chunking policy |
| created_utc | DATETIME2 | Creation time |

### llm.embedding

Stores embedding vectors:

| Column | Type | Description |
|--------|------|-------------|
| embedding_id | UNIQUEIDENTIFIER | UUID (PK) |
| chunk_id | NVARCHAR(128) | FK to chunk |
| embedding_model | NVARCHAR(200) | Model name |
| vector_dim | INT | Dimensionality |
| vector_json | NVARCHAR(MAX) | Vector as JSON |
| vector_sha256 | NVARCHAR(64) | Vector hash |
| created_utc | DATETIME2 | Creation time |

### llm.retrieval

Logs retrieval queries:

| Column | Type | Description |
|--------|------|-------------|
| retrieval_id | UNIQUEIDENTIFIER | UUID (PK) |
| run_id | UNIQUEIDENTIFIER | FK to run |
| query_text | NVARCHAR(MAX) | Query text |
| query_embedding_model | NVARCHAR(200) | Model |
| top_k | INT | Results requested |
| filters_json | NVARCHAR(MAX) | Filters |
| policy_json | NVARCHAR(MAX) | Policy |
| created_utc | DATETIME2 | Query time |

### llm.retrieval_hit

Stores retrieval results:

| Column | Type | Description |
|--------|------|-------------|
| retrieval_id | UNIQUEIDENTIFIER | FK (PK) |
| rank | INT | Result rank (PK) |
| chunk_id | NVARCHAR(128) | FK to chunk |
| score | FLOAT | Similarity score |
| metadata_json | NVARCHAR(MAX) | Metadata |

### llm.source_registry

Tracks sources for incremental indexing:

| Column | Type | Description |
|--------|------|-------------|
| source_id | NVARCHAR(256) | Source ID (PK) |
| source_type | NVARCHAR(100) | Type |
| source_ref_json | NVARCHAR(MAX) | Reference |
| content_sha256 | NVARCHAR(64) | Content hash |
| last_indexed_utc | DATETIME2 | Last indexed |
| chunk_count | INT | Chunks created |
| tags_json | NVARCHAR(MAX) | Source tags |

---

## Usage

### Indexing Sources

See [indexing.md](indexing.md) for detailed indexing instructions.

Quick start:
```bash
python -m src.llm.retrieval.indexer \
    --source-manifest manifest.json \
    --mode full
```

### Performing Retrieval

```python
from llm.retrieval.search import retrieve_chunks
from llm.contracts.retrieval_contracts import RetrievalPolicy

# Get candidate embeddings (from store or cache)
candidates = store.get_embeddings_by_filter("nomic-embed-text", ["lake_text"])

# Perform retrieval
result = retrieve_chunks(
    query_embedding=query_vector,
    candidate_embeddings=candidates,
    query_text="What is the Force?",
    embedding_model="nomic-embed-text",
    top_k=10,
    policy=RetrievalPolicy(min_score_threshold=0.5),
)

# Access results
for hit in result.hits:
    print(f"Rank {hit.rank}: {hit.chunk_id} (score: {hit.score:.3f})")
```

### Converting to Evidence

```python
from llm.retrieval.evidence_converter import convert_retrieval_to_evidence

# Get chunk contents
chunk_contents = {hit.chunk_id: store.get_chunk_content(hit.chunk_id) 
                  for hit in result.hits}

# Convert to evidence items
evidence_items = convert_retrieval_to_evidence(result, chunk_contents)
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `INDEX_CHUNK_SIZE` | `2000` | Chunk size (chars) |
| `INDEX_CHUNK_OVERLAP` | `200` | Chunk overlap (chars) |
| `INDEX_MAX_CHUNKS_PER_SOURCE` | `100` | Max chunks per source |
| `INDEX_EMBED_CONCURRENCY` | `1` | Concurrent embed calls |
| `LLM_RETRIEVAL_ENABLED` | `false` | Enable retrieval in runner |
| `LLM_RETRIEVAL_TOP_K` | `10` | Default top-K |

---

## Related Documentation

- [Indexing Guide](indexing.md) — How to index sources
- [Operational Guide](operational.md) — Operations and troubleshooting
- [Evidence Bundles](evidence.md) — Phase 2 evidence system
- [Implementation Status](status.md) — Overall progress
