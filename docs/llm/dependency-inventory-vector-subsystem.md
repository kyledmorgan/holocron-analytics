# Dependency Inventory: LLM Vector Subsystem

**Date:** 2026-02-10  
**Phase:** 0 (Baseline & Safety Net)  
**Purpose:** Identify SQL objects and Python code referencing legacy vector tables in `llm` schema

---

## Executive Summary

This inventory catalogs all dependencies on the legacy vector-related tables in the `llm` schema that are candidates for deprecation. The goal is to enable a controlled migration to the new `vector` schema without breaking the chat runtime.

### Key Finding

**Vector subsystem has limited production usage.** The vector-related tables (`llm.chunk`, `llm.embedding`, `llm.retrieval`, `llm.retrieval_hit`, `llm.source_registry`) are primarily used by the Phase 3 RAG pipeline, which is experimental and not in active production use.

**Chat runtime is unaffected.** The chat runtime tables (`llm.job`, `llm.run`, `llm.artifact`, `llm.evidence_bundle`, `llm.evidence_item`, `llm.run_evidence`) have no dependencies on vector tables and will remain intact.

---

## 1. SQL Object Dependencies

### 1.1 Tables Being Deprecated

| Table | Migration File | Status | Notes |
|-------|---------------|--------|-------|
| `llm.chunk` | 0008_create_retrieval_tables.sql | Candidate for deprecation | Vector subsystem |
| `llm.embedding` | 0008_create_retrieval_tables.sql | Candidate for deprecation | Vector subsystem |
| `llm.retrieval` | 0008_create_retrieval_tables.sql | Candidate for deprecation | Vector subsystem |
| `llm.retrieval_hit` | 0008_create_retrieval_tables.sql | Candidate for deprecation | Vector subsystem |
| `llm.source_registry` | 0008_create_retrieval_tables.sql | Candidate for deprecation | Vector subsystem |

### 1.2 Tables Preserved (Chat Runtime)

| Table | Migration File | Status | Notes |
|-------|---------------|--------|-------|
| `llm.job` | 0005_create_llm_tables.sql | Preserved | Chat job queue |
| `llm.run` | 0005_create_llm_tables.sql | Preserved | Chat run lineage |
| `llm.artifact` | 0005_create_llm_tables.sql | Preserved | Chat artifacts |
| `llm.evidence_bundle` | 0007_evidence_bundle_tables.sql | Preserved | Evidence packaging |
| `llm.evidence_item` | 0007_evidence_bundle_tables.sql | Preserved | Evidence items |
| `llm.run_evidence` | 0007_evidence_bundle_tables.sql | Preserved | Run-evidence links |

### 1.3 Stored Procedures

| Procedure | References Vector Tables? | Status |
|-----------|--------------------------|--------|
| `llm.usp_claim_next_job` | No | Preserved |
| `llm.usp_complete_job` | No | Preserved |
| `llm.usp_enqueue_job` | No | Preserved |
| `llm.usp_create_run` | No | Preserved |
| `llm.usp_complete_run` | No | Preserved |
| `llm.usp_create_artifact` | No | Preserved |

**Finding:** No stored procedures reference vector tables. All chat runtime procedures are safe.

### 1.4 Views

No views currently reference the legacy vector tables.

### 1.5 Indexes

All indexes on vector tables are defined in `0008_create_retrieval_tables.sql` and will be dropped along with the tables.

### 1.6 Foreign Key Dependencies

| FK Constraint | Source Table | Target Table | Impact |
|---------------|--------------|--------------|--------|
| `FK_llm_embedding_chunk` | llm.embedding | llm.chunk | Drop with embedding |
| `FK_llm_retrieval_run` | llm.retrieval | llm.run | Breaks link to chat runtime |
| `FK_llm_retrieval_hit_retrieval` | llm.retrieval_hit | llm.retrieval | Drop with retrieval |
| `FK_llm_retrieval_hit_chunk` | llm.retrieval_hit | llm.chunk | Drop with chunk |

**Note:** `FK_llm_retrieval_run` links retrieval to chat runs. This was intended for RAG-augmented chat but is not actively used. The new `vector.retrieval` will have an optional `run_id` that can link to `vector.run` (not `llm.run`).

---

## 2. Python Code Dependencies

### 2.1 Files Referencing Vector Tables

| File | References | Runtime | Status |
|------|------------|---------|--------|
| `src/llm/retrieval/indexer.py` | `source_registry`, `chunk` | Vector | Safe to refactor |
| `src/llm/retrieval/search.py` | `chunk`, `embedding`, `retrieval`, `retrieval_hit` | Vector | Safe to refactor |
| `src/llm/retrieval/chunker.py` | Uses `ChunkRecord` (in-memory) | Vector | Safe to refactor |
| `src/llm/retrieval/evidence_converter.py` | Uses retrieval results | Vector | Safe to refactor |
| `src/semantic/models.py` | Comments reference `llm.source_registry` | N/A | Comment update only |

### 2.2 Detailed File Analysis

#### `src/llm/retrieval/indexer.py`
- **Lines affected:** 370-395, 417-458
- **Operations:** 
  - `_source_already_indexed()`: Queries `llm.source_registry`
  - `_update_source_registry()`: MERGE into `llm.source_registry`
- **Break risk:** Low (experimental code)
- **Migration:** Update to use `vector.source_registry`

#### `src/llm/retrieval/search.py`
- **Lines affected:** 187-430 (RetrievalStore class)
- **Operations:**
  - `save_chunk()`: INSERT/MERGE to `llm.chunk`
  - `save_embedding()`: INSERT to `llm.embedding`
  - `get_embeddings_by_filter()`: JOIN `llm.embedding` + `llm.chunk`
  - `save_retrieval_result()`: INSERT to `llm.retrieval` + `llm.retrieval_hit`
  - `get_chunk_content()`: SELECT from `llm.chunk`
  - `chunk_exists()`: SELECT from `llm.chunk`
  - `embedding_exists()`: SELECT from `llm.embedding`
- **Break risk:** Low (experimental code)
- **Migration:** Create `VectorStore` class pointing to `vector.*` tables

#### `src/llm/retrieval/chunker.py`
- **References:** Uses `ChunkRecord` dataclass (in-memory only)
- **Database access:** None direct
- **Break risk:** None
- **Migration:** No changes needed

#### `src/llm/retrieval/evidence_converter.py`
- **References:** Uses retrieval result dataclasses
- **Database access:** None direct
- **Break risk:** None
- **Migration:** No changes needed

#### `src/semantic/models.py`
- **Reference:** Line 147 - docstring mentions `llm.source_registry.source_id`
- **Database access:** None (comment only)
- **Break risk:** None
- **Migration:** Update comment in Phase 2

### 2.3 Contract/Model Files

| File | Contains | Status |
|------|----------|--------|
| `src/llm/contracts/retrieval_contracts.py` | `ChunkRecord`, `EmbeddingRecord`, `RetrievalQuery`, `RetrievalHit`, `RetrievalResult` | Keep (in-memory models) |

These dataclasses define in-memory structures and are agnostic to the database schema. They can be reused with the new `vector` schema.

### 2.4 Test Files

| File | References | Status |
|------|------------|--------|
| `tests/unit/llm/test_retrieval_contracts.py` | Contract dataclasses | Keep (tests in-memory models) |
| `tests/unit/llm/test_retrieval_search.py` | Search functions | Keep (unit tests) |
| `tests/unit/llm/test_chunking.py` | Chunker functions | Keep (unit tests) |

All tests use in-memory mocks and don't depend on the actual database schema.

---

## 3. Documentation Dependencies

| File | References | Action |
|------|------------|--------|
| `docs/llm/retrieval.md` | `llm.chunk`, `llm.embedding`, `llm.retrieval`, `llm.retrieval_hit`, `llm.source_registry` | Update in Phase 2 |
| `docs/llm/indexing.md` | `llm.chunk`, `llm.embedding`, `llm.source_registry` | Update in Phase 2 |
| `docs/llm/operational.md` | General vector references | Update in Phase 2 |
| `docs/llm/status.md` | Phase 3 RAG status | Update in Phase 2 |
| `docs/DOCS_INDEX.md` | Links to retrieval docs | No change needed |

---

## 4. Risk Assessment

### 4.1 Chat Runtime (CRITICAL - Must Not Break)

| Component | Vector Dependency | Risk |
|-----------|------------------|------|
| `llm.job` queue | None | ✅ No risk |
| `llm.run` lineage | None | ✅ No risk |
| `llm.artifact` storage | None | ✅ No risk |
| Evidence bundling | None | ✅ No risk |
| Phase 1 runner | None | ✅ No risk |
| Ollama client | None | ✅ No risk |

### 4.2 Vector Runtime (Safe to Refactor)

| Component | Files Affected | Risk |
|-----------|---------------|------|
| `RetrievalStore` | `search.py` | ⚠️ Needs update in Phase 1 |
| Indexer | `indexer.py` | ⚠️ Needs update in Phase 1 |
| Chunker | `chunker.py` | ✅ No change needed |
| Evidence converter | `evidence_converter.py` | ✅ No change needed |

---

## 5. Migration Path Summary

### Phase 0 (This PR)
- ✅ Create legacy schema snapshot
- ✅ Complete this dependency inventory
- ✅ Add migration notes documentation
- ❌ No tables dropped
- ❌ No code changes

### Phase 1 (Next PR)
- Create `vector` schema with new tables
- Add `VectorStore` class for new schema
- Keep legacy `RetrievalStore` for compatibility
- Add feature flag for schema selection

### Phase 2 (Future PR)
- Remove `RetrievalStore` class
- Drop legacy vector tables from `llm`
- Update documentation
- Remove feature flag

---

## 6. Conclusion

The vector subsystem in `llm` is cleanly isolated and can be safely migrated to the new `vector` schema. The chat runtime has zero dependencies on vector tables and will be unaffected.

**Recommended next steps:**
1. Merge Phase 0 (this inventory + snapshot)
2. Implement Phase 1 (additive `vector` schema + parallel code)
3. After validation, implement Phase 2 (cutover + cleanup)
