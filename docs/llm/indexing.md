# Indexing Guide (Phase 3)

> **Note: As of Phase 2 of the schema refactor, indexing now uses the `vector` schema exclusively.**
> 
> The indexer has been updated to use `VectorStore` and persist data to `vector.*` tables.
> See [Vector Runtime README](../vector/README.md) for current schema documentation.

This document describes how to index sources for retrieval in the Phase 3 RAG system.

**Last Updated:** February 2026

---

## Overview

The indexer reads sources from a manifest file, chunks them into searchable units, generates embeddings using Ollama, and stores everything in SQL Server for retrieval.

**Schema used:** `vector.*` (via `VectorStore`)

---

## Source Manifest Format

Create a JSON manifest file listing sources to index:

```json
{
    "version": "1.0",
    "sources": [
        {
            "source_id": "wookieepedia-force",
            "source_type": "lake_text",
            "lake_uri": "docs/wookieepedia/force.txt",
            "tags": {
                "franchise": "starwars",
                "corpus": "wookieepedia"
            }
        },
        {
            "source_id": "script-empire-strikes-back",
            "source_type": "lake_text",
            "lake_uri": "docs/scripts/empire_strikes_back.txt",
            "tags": {
                "franchise": "starwars",
                "type": "script"
            }
        }
    ]
}
```

### Source Fields

| Field | Required | Description |
|-------|----------|-------------|
| `source_id` | Yes | Unique identifier for this source |
| `source_type` | Yes | Type: `lake_text`, `lake_http`, `inline`, etc. |
| `lake_uri` | Conditional | Path relative to lake root (required for lake types) |
| `content` | Conditional | Direct content (required for inline type) |
| `tags` | No | Key-value pairs for filtering |

### Source Types

| Type | Description |
|------|-------------|
| `lake_text` | Plain text file in the lake |
| `lake_http` | HTTP response artifact |
| `inline` | Content provided directly in manifest |
| `doc` | Document file |
| `transcript` | Transcript or script |

---

## Running the Indexer

### Basic Usage

```bash
# Full indexing (process all sources)
python -m src.llm.retrieval.indexer \
    --source-manifest sources.json \
    --mode full

# Incremental indexing (skip unchanged)
python -m src.llm.retrieval.indexer \
    --source-manifest sources.json \
    --mode incremental
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--source-manifest` | Path to manifest JSON file (required) |
| `--mode` | `full` or `incremental` (default: full) |
| `--embed-model` | Embedding model (default: from env) |
| `--ollama-url` | Ollama base URL (default: from env) |
| `--lake-root` | Lake root directory (default: from env) |
| `--chunk-size` | Chunk size in characters (default: 2000) |
| `--chunk-overlap` | Overlap in characters (default: 200) |
| `--verbose`, `-v` | Enable verbose logging |

### Docker Usage

```bash
# From the host machine
docker compose run --rm app \
    python -m src.llm.retrieval.indexer \
    --source-manifest /app/lake/manifests/sources.json \
    --mode full

# With custom options
docker compose run --rm app \
    python -m src.llm.retrieval.indexer \
    --source-manifest /app/sources.json \
    --chunk-size 1000 \
    --chunk-overlap 100 \
    --verbose
```

---

## Chunking Configuration

### Default Policy

| Parameter | Value | Description |
|-----------|-------|-------------|
| Chunk Size | 2000 chars | Target size per chunk |
| Overlap | 200 chars | Overlap between chunks |
| Max Chunks | 100 | Per source limit |

### Custom Chunking

Override via CLI or environment:

```bash
# CLI options
python -m src.llm.retrieval.indexer \
    --source-manifest sources.json \
    --chunk-size 1500 \
    --chunk-overlap 150

# Environment variables
INDEX_CHUNK_SIZE=1500 \
INDEX_CHUNK_OVERLAP=150 \
python -m src.llm.retrieval.indexer --source-manifest sources.json
```

### Chunking Behavior

1. Text is split into chunks of approximately `chunk_size` characters
2. Chunks overlap by `overlap` characters to preserve context
3. Word boundaries are respected where possible
4. Each chunk gets a deterministic ID based on source and offsets

---

## Embedding Generation

### Default Model

The indexer uses **nomic-embed-text** by default via Ollama.

To use a different model:
```bash
python -m src.llm.retrieval.indexer \
    --source-manifest sources.json \
    --embed-model mxbai-embed-large
```

Or via environment:
```bash
OLLAMA_EMBED_MODEL=mxbai-embed-large python -m src.llm.retrieval.indexer ...
```

### Pulling Models

Ensure the embedding model is available in Ollama:

```bash
# Check available models
docker compose exec ollama ollama list

# Pull a model
docker compose exec ollama ollama pull nomic-embed-text
```

---

## Verifying Indexed Data

### Check Chunk Counts

```sql
-- Total chunks
SELECT COUNT(*) FROM llm.chunk;

-- Chunks by source type
SELECT source_type, COUNT(*) AS chunk_count
FROM llm.chunk
GROUP BY source_type;

-- Recent chunks
SELECT chunk_id, source_type, byte_count, created_utc
FROM llm.chunk
ORDER BY created_utc DESC
OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY;
```

### Check Embeddings

```sql
-- Total embeddings
SELECT COUNT(*) FROM llm.embedding;

-- Embeddings by model
SELECT embedding_model, COUNT(*) AS count, AVG(vector_dim) AS avg_dim
FROM llm.embedding
GROUP BY embedding_model;

-- Verify all chunks have embeddings
SELECT c.chunk_id
FROM llm.chunk c
LEFT JOIN llm.embedding e ON c.chunk_id = e.chunk_id
WHERE e.embedding_id IS NULL;
```

### Check Run Manifests

Indexing runs write manifests to the lake:

```bash
# List indexing runs
ls -la lake/llm_index/

# View a run manifest
cat lake/llm_index/{run_id}/run_manifest.json
```

---

## Incremental Mode

Incremental mode skips sources that haven't changed:

1. Computes content hash of each source
2. Compares with stored hash in `llm.source_registry`
3. Skips sources with matching hashes
4. Re-indexes sources with different hashes

**Note**: Incremental detection is based on content hash, not file modification time.

---

## Example Workflow

### 1. Create Source Manifest

```bash
cat > sources.json << 'EOF'
{
    "version": "1.0",
    "sources": [
        {
            "source_id": "readme",
            "source_type": "lake_text",
            "lake_uri": "README.md"
        }
    ]
}
EOF
```

### 2. Run Indexer

```bash
python -m src.llm.retrieval.indexer \
    --source-manifest sources.json \
    --mode full \
    --verbose
```

### 3. Verify Results

```sql
SELECT chunk_id, source_type, byte_count
FROM llm.chunk
WHERE JSON_VALUE(source_ref_json, '$.source_id') = 'readme';
```

---

## Troubleshooting

### Ollama Not Available

If you see connection errors:

1. Verify Ollama is running: `docker compose ps`
2. Check Ollama logs: `docker compose logs ollama`
3. Verify the model is pulled: `docker compose exec ollama ollama list`
4. Check the OLLAMA_BASE_URL setting

### No Chunks Created

If sources produce no chunks:

1. Verify the lake path exists
2. Check file encoding (must be UTF-8 compatible)
3. Increase logging with `--verbose`
4. Check for errors in indexer output

### Database Connection Errors

If you see SQL errors:

1. Verify SQL Server is running: `docker compose ps`
2. Check connection settings (host, port, credentials)
3. Verify the `llm` schema and tables exist
4. Run migrations if needed

---

## Related Documentation

- [Retrieval Overview](retrieval.md) — System architecture
- [Operational Guide](operational.md) — Operations and maintenance
- [Docker Setup](../runbooks/docker_local_dev.md) — Local development
