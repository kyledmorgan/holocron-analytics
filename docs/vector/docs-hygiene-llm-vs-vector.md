# Documentation Hygiene Report — LLM vs. Vector Markdown Split

**Status:** Phase III Evaluation (Documentation Only)  
**Date:** 2026-02-13  
**Purpose:** Identify and recommend how to split/move blended LLM and vector documentation content.

---

## Overview

This report identifies markdown files in `docs/llm/` that contain vector/embedding content and recommends how to organize them for clear separation between:
- **LLM subsystem** (`docs/llm/`) — Chat/completions, interrogations, text-in → text-out
- **Vector subsystem** (`docs/vector/`) — Embeddings/retrieval, text-in → vectors-out

**Critical Constraint:** Do NOT use blended LLM docs as input to vector design recommendations. Vector design guidance should live in `docs/vector/`.

---

## Classification Summary

| File | Classification | Primary Subsystem | Recommendation |
|------|----------------|-------------------|----------------|
| `retrieval.md` | **Vector-Only** | Vector | **MOVE** to `docs/vector/retrieval-legacy.md` |
| `indexing.md` | **Vector-Only** | Vector | **MOVE** to `docs/vector/indexing-legacy.md` |
| `operational.md` | **Vector-Only** | Vector | **MOVE** to `docs/vector/operational-legacy.md` |
| `dependency-inventory-vector-subsystem.md` | **Vector-Only** | Vector | **MOVE** to `docs/vector/dependency-inventory-vector-subsystem.md` |
| `evidence.md` | **Mixed** (60% LLM / 40% Vector) | LLM | **KEEP** with cross-reference to vector docs |
| `status.md` | **Mixed** (50% LLM / 50% Vector) | Both | **KEEP** with clear subsystem separation |
| `phase1-runner.md` | **LLM-Only** (95% LLM / 5% Vector mentions) | LLM | **KEEP** as-is |
| `derived-data.md` | **LLM-Only** (85% LLM / 15% Vector mentions) | LLM | **KEEP** with updated vector pointers |
| `ollama.md` | **LLM-Only** (80% LLM / 20% Vector) | LLM | **KEEP** with embedding endpoint documentation |

---

## Detailed File Analysis

### 1. `docs/llm/retrieval.md` ⇒ **MOVE**

**Current Location:** `docs/llm/retrieval.md`  
**Recommended Location:** `docs/vector/retrieval-legacy.md`  
**Classification:** Vector-Only (95% vector content)

**Content Summary:**
- Phase 3 RAG system architecture
- Vector store design (SQL Server + Python similarity)
- Embedding model (nomic-embed-text)
- Chunking policy
- Data models: ChunkRecord, EmbeddingRecord, RetrievalQuery, RetrievalHit
- SQL schema for `llm.chunk`, `llm.embedding`, `llm.retrieval`, `llm.retrieval_hit`
- Determinism and reproducibility
- Usage examples (indexing, retrieval, evidence conversion)

**Why Move:**
- Entire document describes vector/embedding operations
- Legacy documentation for deprecated `llm.*` vector tables
- Already has warning banner: "⚠️ LEGACY DOCUMENTATION" pointing to `vector` schema

**Action:**
1. **Move** `docs/llm/retrieval.md` → `docs/vector/retrieval-legacy.md`
2. Leave **redirect stub** at `docs/llm/retrieval.md`:
   ```markdown
   # Retrieval System (Moved)
   
   **This document has been moved to the vector subsystem.**
   
   See: [docs/vector/retrieval-legacy.md](../vector/retrieval-legacy.md)
   
   For current documentation, see: [docs/vector/README.md](../vector/README.md)
   ```

---

### 2. `docs/llm/indexing.md` ⇒ **MOVE**

**Current Location:** `docs/llm/indexing.md`  
**Recommended Location:** `docs/vector/indexing-legacy.md`  
**Classification:** Vector-Only (95% vector content)

**Content Summary:**
- Indexing guide for Phase 3 RAG system
- Source manifest format
- Running the indexer (CLI options)
- Chunking configuration
- Embedding generation (Ollama `embed()` API)
- Verifying indexed data (chunks, embeddings)
- Incremental mode
- Troubleshooting

**Why Move:**
- Entire document describes vector indexing operations
- Already has note: "As of Phase 2, indexing now uses `vector` schema exclusively"
- Core vector subsystem documentation

**Action:**
1. **Move** `docs/llm/indexing.md` → `docs/vector/indexing-legacy.md`
2. Leave **redirect stub** at `docs/llm/indexing.md`

---

### 3. `docs/llm/operational.md` ⇒ **MOVE**

**Current Location:** `docs/llm/operational.md`  
**Recommended Location:** `docs/vector/operational-legacy.md`  
**Classification:** Vector-Only (95% vector content)

**Content Summary:**
- Vector storage retention
- Embedding concurrency
- Vector-specific troubleshooting
- Operational guides for vector subsystem

**Why Move:**
- Entire document describes vector operational concerns
- No LLM chat/completions content

**Action:**
1. **Move** `docs/llm/operational.md` → `docs/vector/operational-legacy.md`
2. Leave **redirect stub** at `docs/llm/operational.md`

---

### 4. `docs/llm/dependency-inventory-vector-subsystem.md` ⇒ **MOVE**

**Current Location:** `docs/llm/dependency-inventory-vector-subsystem.md`  
**Recommended Location:** `docs/vector/dependency-inventory-vector-subsystem.md`  
**Classification:** Vector-Only (95% vector content)

**Content Summary:**
- Dependency inventory for legacy `llm.*` vector tables
- SQL object dependencies
- Python code dependencies
- Migration impact analysis

**Why Move:**
- Document is specifically about vector subsystem migration
- Name already indicates "vector-subsystem"
- Should live with other vector schema docs

**Action:**
1. **Move** `docs/llm/dependency-inventory-vector-subsystem.md` → `docs/vector/dependency-inventory-vector-subsystem.md`
2. Leave **redirect stub** at `docs/llm/dependency-inventory-vector-subsystem.md`

---

### 5. `docs/llm/evidence.md` ⇒ **KEEP** (with cross-reference)

**Current Location:** `docs/llm/evidence.md`  
**Recommended Action:** Keep in place, add cross-reference  
**Classification:** Mixed (60% LLM / 40% Vector)

**Content Summary:**
- Evidence bundle object model
- Evidence builder (Phase 2)
- Evidence sources: inline, lake_text, lake_http, sql_result, sql_query
- Bounding and redaction
- SQL evidence packaging
- Evidence used by Phase 1 (LLM chat) and Phase 3 (RAG retrieval)

**Why Keep:**
- Evidence bundles are **core to Phase 1 LLM chat pipeline** (primary use)
- Evidence builder is in `src/llm/evidence/` module
- Phase 3 retrieval uses evidence, but as a consumer (converts retrieval hits to evidence items)
- Splitting would duplicate content or create confusing structure

**Recommended Updates:**
1. **Add section** at top:
   ```markdown
   ## Evidence in Vector Retrieval
   
   Evidence bundles are also used in Phase 3 retrieval operations.
   Retrieval results can be converted to evidence items for LLM interrogations.
   
   See:
   - [Vector Retrieval](../vector/retrieval-legacy.md) — RAG pipeline using evidence
   - [Evidence Converter](../llm/retrieval/evidence_converter.py) — Convert retrieval hits to evidence
   ```

2. **Keep file in `docs/llm/`** (primary home for evidence documentation)

---

### 6. `docs/llm/status.md` ⇒ **KEEP** (with subsystem separation)

**Current Location:** `docs/llm/status.md`  
**Recommended Action:** Keep in place, clarify subsystem separation  
**Classification:** Mixed (50% LLM / 50% Vector)

**Content Summary:**
- Implementation status tracker
- Phase 0: Foundation ✅
- Phase 1: MVP Runner ✅ (LLM chat)
- Phase 2: Evidence Bundles ✅ (LLM chat)
- Phase 3: Retrieval Augmentation ✅ (Vector)
- Lists features/checklists for each phase

**Why Keep:**
- Document tracks **overall subsystem progress** (both LLM and vector)
- Phase 1-2 are LLM chat
- Phase 3 is vector/retrieval
- Already has clear phase separation
- Useful historical reference

**Recommended Updates:**
1. **Add note** at top:
   ```markdown
   ## Subsystem Separation Note
   
   This document tracks the implementation status of **both** the LLM chat runtime
   (Phase 1-2) and the vector/retrieval runtime (Phase 3).
   
   - **LLM Chat Runtime** (Phase 1-2): `llm` schema, chat/completions, interrogations
   - **Vector Runtime** (Phase 3): `vector` schema, embeddings, retrieval
   
   For vector-specific status, see: [docs/vector/README.md](../vector/README.md)
   ```

2. **Keep file in `docs/llm/`** (historical tracking document)

---

### 7. `docs/llm/phase1-runner.md` ⇒ **KEEP**

**Current Location:** `docs/llm/phase1-runner.md`  
**Recommended Action:** Keep as-is  
**Classification:** LLM-Only (95% LLM / 5% Vector mentions)

**Content Summary:**
- Phase 1 runner for LLM chat derivations
- Job queue, evidence bundling, Ollama calls
- Artifact storage
- CLI interface
- Error handling and retry logic

**Why Keep:**
- Document is about **LLM chat pipeline** (Phase 1)
- Vector mentions are minimal (optional retrieval flag)
- Core LLM runner documentation

**No action needed.**

---

### 8. `docs/llm/derived-data.md` ⇒ **KEEP** (with updated pointers)

**Current Location:** `docs/llm/derived-data.md`  
**Recommended Action:** Keep in place, update vector pointers  
**Classification:** LLM-Only (85% LLM / 15% Vector mentions)

**Content Summary:**
- LLM-Derived Data subsystem overview
- Evidence-led structured extraction
- Reproducibility through manifests
- Roadmap with Phase 0-3 placeholders

**Why Keep:**
- Document is about **LLM subsystem vision** (not vector-specific)
- Phase 3 (retrieval) mentioned as future work
- Core LLM subsystem documentation

**Recommended Updates:**
1. **Update Phase 3 section** to reference vector docs:
   ```markdown
   ### Phase 3: Retrieval Augmentation
   
   Phase 3 has been completed as the **vector subsystem** with its own schema and runtime.
   
   See:
   - [Vector Runtime README](../vector/README.md) — Vector schema overview
   - [Vector Documentation](../vector/) — Vector subsystem docs
   ```

---

### 9. `docs/llm/ollama.md` ⇒ **KEEP** (with embedding endpoint documentation)

**Current Location:** `docs/llm/ollama.md`  
**Recommended Action:** Keep in place, clarify chat vs embedding usage  
**Classification:** LLM-Only (80% LLM / 20% Vector)

**Content Summary:**
- Ollama integration guide
- Installation, model pulling
- API endpoints: `/api/generate`, `/api/chat`, `/api/embed`, `/v1/chat/completions`
- Configuration options
- Operational behavior (GPU, memory, health checks)
- Docker Compose setup

**Why Keep:**
- Ollama is the **primary LLM provider for both chat and embeddings**
- Document is about Ollama service setup (infrastructure)
- `/api/embed` endpoint documented but not primary focus
- Used by both LLM chat and vector subsystems

**Recommended Updates:**
1. **Add section** distinguishing chat vs embedding usage:
   ```markdown
   ## Ollama for Chat vs. Embeddings
   
   Ollama provides two primary capabilities:
   
   ### Chat/Completions (LLM Subsystem)
   - `/api/generate` — Single-turn generation
   - `/api/chat` — Multi-turn chat
   - `/v1/chat/completions` — OpenAI-compatible chat
   - Used by Phase 1 runner, LLM interrogations
   
   ### Embeddings (Vector Subsystem)
   - `/api/embed` — Generate embedding vectors
   - Default model: `nomic-embed-text` (768 dimensions)
   - Used by vector indexer, retrieval pipeline
   - See: [Vector Runtime](../vector/README.md)
   ```

---

## Summary of Actions

### Files to Move (Vector-Only)

| Source | Destination | Action |
|--------|-------------|--------|
| `docs/llm/retrieval.md` | `docs/vector/retrieval-legacy.md` | Move + redirect stub |
| `docs/llm/indexing.md` | `docs/vector/indexing-legacy.md` | Move + redirect stub |
| `docs/llm/operational.md` | `docs/vector/operational-legacy.md` | Move + redirect stub |
| `docs/llm/dependency-inventory-vector-subsystem.md` | `docs/vector/dependency-inventory-vector-subsystem.md` | Move + redirect stub |

### Files to Keep with Updates (Mixed/LLM-Only)

| File | Action | Updates Needed |
|------|--------|----------------|
| `docs/llm/evidence.md` | Keep | Add cross-reference to vector retrieval usage |
| `docs/llm/status.md` | Keep | Add subsystem separation note at top |
| `docs/llm/phase1-runner.md` | Keep | No changes needed |
| `docs/llm/derived-data.md` | Keep | Update Phase 3 section with vector doc pointers |
| `docs/llm/ollama.md` | Keep | Add "Chat vs. Embeddings" section |

---

## Redirect Stub Template

For files being moved, leave a redirect stub in the original location:

```markdown
# [Original Title] (Moved)

**This document has been moved to the vector subsystem.**

See: [docs/vector/[new-name].md](../vector/[new-name].md)

For current vector documentation, see:
- [Vector Runtime README](../vector/README.md)
- [Current State Inventory](../vector/current-state-inventory.md)
- [Recommended Architecture](../vector/recommended-architecture.md)
```

---

## Cross-Reference Strategy

**Minimal and Directional:**
- LLM docs → Vector docs: "For vector/retrieval operations, see docs/vector/..."
- Vector docs → LLM docs: "For LLM chat/interrogations, see docs/llm/..."
- Maximum 1-2 cross-reference links per doc

**Avoid:**
- Duplicating content across LLM and vector docs
- Deep conceptual overlap (each subsystem has clear boundary)
- Circular references

---

## Naming Conventions

### Legacy vs. Current

Files moved from `docs/llm/` to `docs/vector/` that describe **deprecated `llm.*` vector tables** should be renamed with `-legacy` suffix:
- `retrieval.md` → `retrieval-legacy.md`
- `indexing.md` → `indexing-legacy.md`
- `operational.md` → `operational-legacy.md`

**Current vector docs** (new Phase III evaluation docs) use canonical names:
- `current-state-inventory.md`
- `gap-analysis.md`
- `recommended-architecture.md`
- `proposed-work-plan.md`

---

## Implementation Checklist

### Phase 1: Move Vector-Only Docs
- [ ] Move `docs/llm/retrieval.md` → `docs/vector/retrieval-legacy.md`
- [ ] Move `docs/llm/indexing.md` → `docs/vector/indexing-legacy.md`
- [ ] Move `docs/llm/operational.md` → `docs/vector/operational-legacy.md`
- [ ] Move `docs/llm/dependency-inventory-vector-subsystem.md` → `docs/vector/dependency-inventory-vector-subsystem.md`
- [ ] Create redirect stubs at original locations

### Phase 2: Update Mixed/LLM Docs
- [ ] Update `docs/llm/evidence.md` with vector retrieval cross-reference
- [ ] Update `docs/llm/status.md` with subsystem separation note
- [ ] Update `docs/llm/derived-data.md` Phase 3 section with vector pointers
- [ ] Update `docs/llm/ollama.md` with "Chat vs. Embeddings" section

### Phase 3: Update Vector README
- [ ] Add links to moved docs in `docs/vector/README.md`
- [ ] Add link to this hygiene report in `docs/vector/README.md`

---

## Related Documents

- [Current State Inventory](current-state-inventory.md) — Existing vector components
- [Gap Analysis](gap-analysis.md) — What's missing for first run
- [Recommended Architecture](recommended-architecture.md) — Target architecture
- [Vector Runtime README](README.md) — Vector schema overview
