# Schema Refactor: Splitting Chat Runtime from Vector Runtime

**Date:** 2026-02-10  
**Status:** Phase 2 Complete (Feature Complete)  
**Author:** Copilot Agent

---

## Overview

This document describes the completed refactor that split the Holocron `llm` schema into two independent runtimes:

| Schema | Purpose | Semantic |
|--------|---------|----------|
| **`llm`** | Chat/interrogation runtime | Text-in → Text-out |
| **`vector`** | Embedding & retrieval runtime | Text-in → Vectors-out |

---

## Motivation

### Why Split?

The original `llm` schema was designed for **LLM interrogation** (sending prompts, receiving structured JSON responses). Embeddings and vector retrieval were later added as a "bolt-on" for RAG (Retrieval Augmented Generation) experiments.

As both systems evolved, several design tensions emerged:

1. **Different lifecycles**: Chat jobs complete in seconds; embedding jobs may batch thousands of chunks.

2. **Different model semantics**: Chat models produce text; embedding models produce fixed-dimension vectors that must not be mixed across incompatible "spaces."

3. **Different experimentation needs**: Vector retrieval requires testing multiple embedding models, dimensions, normalization strategies, and transforms. Chat runtime doesn't need this complexity.

4. **Different lineage requirements**: Embeddings must track the exact input version (`content_sha256`) and model identity to prevent stale vector reuse. Chat doesn't have this concern.

### What We Gained

- **Cleaner separation of concerns**: Each runtime has its own job queue, run lineage, and artifact patterns.

- **Better experimentation support**: The new `vector.embedding_space` table provides first-class identity for embedding spaces, enabling multi-family experiments and drift testing.

- **Stronger correctness guarantees**: Idempotency constraints (`chunk_id` + `embedding_space_id` + `input_content_sha256`) prevent accidentally mixing embeddings from different input versions.

- **Future-proof design**: The vector schema is designed for extensibility (transforms, anchor sets, drift reports) without affecting chat runtime.

---

## Phased Approach

### Phase 0: Baseline & Safety Net ✅

**Goal:** Establish a safe baseline before making changes.

**Deliverables:**
- [x] Legacy schema snapshot artifact (`db/legacy_snapshots/llm_vector_subsystem_snapshot.sql`)
- [x] Dependency inventory (`docs/llm/dependency-inventory-vector-subsystem.md`)
- [x] Migration notes documentation (this file)

**Constraints:**
- No tables dropped
- No runtime code changed
- Chat runtime fully preserved

### Phase 1: Introduce `vector` Schema ✅

**Goal:** Create the new vector schema and Python code in parallel with legacy.

**Deliverables:**
- [x] Create `vector` schema with migration script (`db/migrations/0023_create_vector_schema.sql`)
- [x] Create all `vector.*` tables:
  - `vector.job` — Vector task queue
  - `vector.run` — Vector execution lineage
  - `vector.source_registry` — Source index state
  - `vector.chunk` — Canonical chunk table
  - `vector.embedding_space` — Embedding space identity
  - `vector.embedding` — Embeddings with lineage
  - `vector.retrieval` — Retrieval query log
  - `vector.retrieval_hit` — Retrieval results
- [x] Add `VectorStore` Python class for new schema (`src/vector/store.py`)
- [x] Add vector contract models (`src/vector/contracts/models.py`)
- [x] Add unit tests for vector contracts (`tests/unit/vector/test_vector_contracts.py`)
- [x] Keep `RetrievalStore` for backward compatibility

**Constraints:**
- Legacy `llm.*` vector tables remain
- Chat runtime unchanged
- Both old and new code paths work

### Phase 2: Cutover & Cleanup ✅

**Goal:** Make `vector` the single source of truth and remove legacy.

**Deliverables:**
- [x] Switch all embedding/retrieval code to `vector.*` (`src/llm/retrieval/indexer.py` now uses `VectorStore`)
- [x] Mark `RetrievalStore` class as deprecated with deprecation warnings
- [x] Rename legacy vector tables from `llm` to `*_legacy` (migration 0024):
  - `llm.chunk` → `llm.chunk_legacy`
  - `llm.embedding` → `llm.embedding_legacy`
  - `llm.retrieval` → `llm.retrieval_legacy`
  - `llm.retrieval_hit` → `llm.retrieval_hit_legacy`
  - `llm.source_registry` → `llm.source_registry_legacy`
- [x] Update documentation

**Constraints:**
- Chat runtime remains unchanged
- Legacy snapshot preserved as historical artifact

---

## Schema Comparison

### What's Changing

| Aspect | Legacy (`llm.*`) | New (`vector.*`) |
|--------|------------------|------------------|
| **Space identity** | `embedding_model` string | `embedding_space_id` FK with full metadata |
| **Version coupling** | None | `input_content_sha256` required |
| **Run lineage** | Optional `run_id` | Required `run_id` for embeddings |
| **Idempotency** | Weak (model + vector hash) | Strong (chunk + space + input hash) |
| **Job queue** | Shares `llm.job` | Separate `vector.job` |
| **Experimentation** | Limited | Multi-space, drift testing support |

### What's Preserved

| Component | Schema | Status |
|-----------|--------|--------|
| `llm.job` | `llm` | **Unchanged** |
| `llm.run` | `llm` | **Unchanged** |
| `llm.artifact` | `llm` | **Unchanged** |
| `llm.evidence_bundle` | `llm` | **Unchanged** |
| `llm.evidence_item` | `llm` | **Unchanged** |
| `llm.run_evidence` | `llm` | **Unchanged** |
| All stored procedures | `llm` | **Unchanged** |

---

## New `vector` Schema Design

### Core Tables

#### `vector.embedding_space` (Critical)

The most important new concept. Defines a "space" where cosine/dot-product distance is meaningful.

```sql
-- Conceptual structure (exact DDL in Phase 1)
CREATE TABLE vector.embedding_space (
    embedding_space_id UNIQUEIDENTIFIER PRIMARY KEY,
    provider NVARCHAR(100) NOT NULL,        -- 'ollama', 'openai', etc.
    model_name NVARCHAR(200) NOT NULL,      -- 'nomic-embed-text'
    model_tag NVARCHAR(100) NULL,           -- 'latest'
    model_digest NVARCHAR(200) NULL,        -- SHA256 of model weights
    dimensions INT NOT NULL,                 -- 768, 1024, etc.
    normalize_flag BIT NOT NULL DEFAULT 1,
    distance_metric NVARCHAR(50) NOT NULL DEFAULT 'cosine',
    preprocess_policy_json NVARCHAR(MAX),
    transform_ref NVARCHAR(200) NULL,       -- Optional PCA/projection
    created_utc DATETIME2 NOT NULL,
    is_active BIT NOT NULL DEFAULT 1
);
```

#### `vector.embedding` (With Lineage)

```sql
-- Conceptual structure
CREATE TABLE vector.embedding (
    embedding_id UNIQUEIDENTIFIER PRIMARY KEY,
    chunk_id NVARCHAR(128) NOT NULL,        -- FK to vector.chunk
    embedding_space_id UNIQUEIDENTIFIER NOT NULL,  -- FK to embedding_space
    input_content_sha256 NVARCHAR(64) NOT NULL,    -- Must match chunk version
    run_id UNIQUEIDENTIFIER NULL,           -- FK to vector.run
    vector_json NVARCHAR(MAX) NOT NULL,
    vector_sha256 NVARCHAR(64) NOT NULL,
    created_utc DATETIME2 NOT NULL,
    
    -- Idempotency constraint
    CONSTRAINT UQ_vector_embedding_idempotent 
        UNIQUE (chunk_id, embedding_space_id, input_content_sha256)
);
```

### Runtime Tables

#### `vector.job` (Mirrors `llm.job`)

Same queue pattern as chat, but for vector operations:
- `CHUNK_SOURCE` — Chunk a new source
- `EMBED_CHUNKS` — Generate embeddings for chunks
- `REEMBED_SPACE` — Re-embed all chunks in a space
- `RETRIEVE_TEST` — Run retrieval benchmark
- `DRIFT_TEST` — Compare spaces over time

#### `vector.run` (Mirrors `llm.run`)

Same execution lineage pattern:
- Worker identity
- Endpoint details
- Model/space metadata
- Options and metrics JSON
- Error tracking

---

## Migration Considerations

### Data Migration

**Embeddings were NOT migrated.** The legacy embedding tables had minimal production data and lacked the lineage information needed for the new schema. Fresh embeddings should be generated using the new `vector` schema.

### Code Migration (Completed)

| Component | Phase 1 | Phase 2 (Final) |
|-----------|---------|-----------------|
| `RetrievalStore` | Kept (legacy) | **Deprecated** (with warnings) |
| `VectorStore` | Added (new) | **Primary** |
| Indexer | Added new mode | **Uses VectorStore exclusively** |
| Search | Added new mode | **VectorStore is default** |
| Contracts | Reused | **Reused** |

### Configuration

Vector operations now use the `vector` schema by default. No configuration needed.

```python
# Example: Using VectorStore (recommended)
from vector.store import VectorStore
store = VectorStore(connection=conn)

# Legacy: RetrievalStore (deprecated - raises DeprecationWarning)
from llm.retrieval.search import RetrievalStore
store = RetrievalStore(connection=conn)  # Warning: deprecated
```

---

## Rollback Plan

The schema refactor is now complete (Phase 2). If issues arise:

1. **Rollback migration 0024:** Legacy tables were renamed to `*_legacy`, not dropped. They can be renamed back if absolutely necessary.

2. **Restore from snapshot:** The legacy schema snapshot (`db/legacy_snapshots/llm_vector_subsystem_snapshot.sql`) provides documentation for reconstruction if needed.

3. **Code rollback:** The `RetrievalStore` class still exists (deprecated) and can be temporarily re-enabled by updating imports.

Note: Rollback should rarely be needed as the chat runtime is completely unaffected by this refactor.

---

## Related Documents

- [Dependency Inventory](dependency-inventory-vector-subsystem.md) — Full dependency analysis
- [Legacy Schema Snapshot](../../db/legacy_snapshots/llm_vector_subsystem_snapshot.sql) — Historical reference
- [Vector Runtime README](../vector/README.md) — New vector schema documentation
- [Retrieval System (Legacy)](retrieval.md) — Legacy retrieval documentation
- [Indexing Guide](indexing.md) — Indexing documentation

---

## Questions & Answers

**Q: Will existing chat jobs still work?**  
A: Yes. Chat runtime (`llm.job`, `llm.run`, etc.) is completely unchanged.

**Q: Do we need to migrate existing embeddings?**  
A: No. The legacy embeddings lacked proper lineage and were from experimental use only. Generate fresh embeddings using the new schema.

**Q: Can we still access the legacy tables?**  
A: The legacy tables have been renamed to `*_legacy` (e.g., `llm.chunk_legacy`). They are preserved for historical reference but should not be used in production.

**Q: What happens to `sem.SourcePage.source_registry_id`?**  
A: This column should reference `vector.source_registry.source_id` for new sources. The legacy `llm.source_registry_legacy` table is preserved for historical data.
