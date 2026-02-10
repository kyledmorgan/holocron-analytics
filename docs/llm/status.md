# LLM-Derived Data: Implementation Status

This document tracks the implementation status of the LLM-Derived Data subsystem. It is updated as features are completed.

**Last Updated:** February 2026

---

## Current Phase: Phase 3 — Retrieval Augmentation ✅

**Status: COMPLETE**

Phase 3 has been completed. The retrieval augmentation system is now fully implemented with chunking, embeddings, vector storage, and evidence selection capabilities.

---

## Phase 0 Checklist

### Documentation (`docs/llm/`)

| Item | Status | Notes |
|------|--------|-------|
| Vision and Roadmap | ✅ Complete | [vision-and-roadmap.md](vision-and-roadmap.md) |
| Glossary | ✅ Complete | [glossary.md](glossary.md) |
| Ollama Integration Guide | ✅ Complete | [ollama.md](ollama.md) |
| Contracts | ✅ Complete | [contracts.md](contracts.md) |
| Governance (placeholder) | ✅ Complete | [governance.md](governance.md) |
| Lineage (placeholder) | ✅ Complete | [lineage.md](lineage.md) |
| Status Tracker | ✅ Complete | This file |
| Derived Data Overview | ✅ Complete | [derived-data.md](derived-data.md) |

### Source Scaffolding (`src/llm/`)

| Component | Status | Notes |
|-----------|--------|-------|
| Module README | ✅ Complete | [README.md](../../src/llm/README.md) |
| `__init__.py` | ✅ Complete | Module initialization |
| **Contracts** | | |
| ├─ manifest_schema.json | ✅ Complete | v1 placeholder schema |
| ├─ derived_output_schema.json | ✅ Complete | v1 placeholder schema |
| └─ README.md | ✅ Complete | Schema documentation |
| **Core** | | |
| ├─ types.py | ✅ Complete | Dataclass models |
| ├─ exceptions.py | ✅ Complete | Custom exceptions |
| └─ logging.py | ✅ Complete | Logging utilities |
| **Providers** | | |
| ├─ ollama_client.py | ✅ Complete | Thin HTTP client |
| └─ README.md | ✅ Complete | Provider strategy |
| **Runners** | | |
| └─ derive_runner.py | ✅ Complete | Orchestration skeleton |
| **Storage** | | |
| ├─ artifact_store.py | ✅ Complete | Filesystem writer |
| ├─ sql_queue_store.py | ✅ Complete | SQL stub (in-memory) |
| └─ README.md | ✅ Complete | Storage documentation |
| **Prompts** | | |
| ├─ README.md | ✅ Complete | Prompt philosophy |
| └─ templates/ | ✅ Complete | Template directory |
| **Config** | | |
| ├─ config.md | ✅ Complete | Configuration reference |
| └─ llm.example.yaml | ✅ Complete | Example config |
| **Interrogations** | | |
| ├─ README.md | ✅ Complete | Catalog concept |
| ├─ definitions/ | ✅ Complete | Example definitions |
| ├─ rubrics/ | ✅ Complete | Rubric templates |
| └─ vocab/ | ✅ Complete | Controlled vocabularies |
| **Tools** | | |
| └─ capture_ollama_models.py | ✅ Complete | Model inventory tool |

### Docker Compose

| Item | Status | Notes |
|------|--------|-------|
| Ollama service | ✅ Complete | In `docker-compose.yml` |
| Localhost-only binding | ✅ Complete | `127.0.0.1:11434` |
| Named volume for models | ✅ Complete | `ollama_data` |
| Optional GPU reservation | ✅ Complete | Commented, ready to enable |

### Agent Guidance

| Item | Status | Notes |
|------|--------|-------|
| `agents/llm-derived-data.md` | ✅ Complete | Subsystem guidance |
| Root `AGENTS.md` update | ✅ Complete | References subsystem doc |

### Smoke Test

| Item | Status | Notes |
|------|--------|-------|
| `scripts/llm_smoke_test.py` | ✅ Complete | Validates Ollama connectivity |

### Docs Index

| Item | Status | Notes |
|------|--------|-------|
| `docs/DOCS_INDEX.md` update | ✅ Complete | Links to new docs |

---

## Phase 1 Checklist ✅

**Status: COMPLETE**

### MVP Runner

| Item | Status | Notes |
|------|--------|-------|
| SQL Server queue schema | ✅ Complete | Tables: job, run, artifact |
| Atomic claim-next semantics | ✅ Complete | READPAST/UPDLOCK |
| End-to-end interrogation | ✅ Complete | Full derive pipeline |
| Artifact persistence | ✅ Complete | Lake writer with date partitioning |
| CLI interface | ✅ Complete | --once and --loop modes |

---

## Phase 2 Checklist ✅

**Status: COMPLETE**

### Evidence Object Model

| Item | Status | Notes |
|------|--------|-------|
| Evidence contracts (Pydantic) | ✅ Complete | EvidenceItem, EvidenceBundle, EvidencePolicy |
| Deterministic evidence IDs | ✅ Complete | Stable naming conventions |
| Content hashing | ✅ Complete | SHA256 for integrity |

### Evidence Bundle Builder

| Item | Status | Notes |
|------|--------|-------|
| Builder core module | ✅ Complete | `evidence/builder.py` |
| Inline source adapter | ✅ Complete | Job-provided evidence |
| Lake text source adapter | ✅ Complete | Text artifacts from lake |
| Lake HTTP source adapter | ✅ Complete | HTTP response artifacts |
| SQL result source adapter | ✅ Complete | Tabular result packaging |
| SQL query source adapter | ✅ Complete | Query definitions |

### Bounding and Redaction

| Item | Status | Notes |
|------|--------|-------|
| Deterministic bounding rules | ✅ Complete | Global and per-item caps |
| SQL sampling strategies | ✅ Complete | first_only, first_last, stride |
| Redaction hooks | ✅ Complete | Pattern-based, toggle-able |
| Text extractors | ✅ Complete | Plain text, JSON, HTTP, SQL |

### SQL Evidence Packaging

| Item | Status | Notes |
|------|--------|-------|
| Mode D1: Load existing results | ✅ Complete | From lake artifacts |
| Mode D2: Execute queries | ✅ Complete | With SELECT-only guards |
| Bounded SQL text format | ✅ Complete | Row/column sampling |
| Full vs bounded separation | ✅ Complete | full_ref pointers |

### SQL Server Schema

| Item | Status | Notes |
|------|--------|-------|
| evidence_bundle table | ✅ Complete | Migration 0007 |
| run_evidence table | ✅ Complete | Links runs to bundles |
| evidence_item table | ✅ Complete | Optional item tracking |

### Documentation

| Item | Status | Notes |
|------|--------|-------|
| evidence.md | ✅ Complete | Bundle format and usage |
| sql-evidence.md | ✅ Complete | SQL packaging guide |
| redaction.md | ✅ Complete | Redaction hooks documentation |
| Status update | ✅ Complete | This document |

### Tests

| Item | Status | Notes |
|------|--------|-------|
| Evidence contracts tests | ✅ Complete | 22 tests passing |
| Bounding rules tests | ✅ Complete | 14 tests passing |
| Redaction tests | ✅ Complete | 17 tests passing |
| SQL text extraction tests | ✅ Complete | 11 tests passing |

---

## Phase 3 Checklist ✅

**Status: COMPLETE**

### Retrieval Contracts

| Item | Status | Notes |
|------|--------|-------|
| ChunkRecord model | ✅ Complete | Deterministic chunk IDs |
| EmbeddingRecord model | ✅ Complete | Vector storage with hashing |
| RetrievalQuery model | ✅ Complete | Query metadata for reproducibility |
| RetrievalHit model | ✅ Complete | Results with scores |
| ChunkingPolicy model | ✅ Complete | Configurable chunking |
| RetrievalPolicy model | ✅ Complete | Scoring configuration |

### SQL Server Schema

| Item | Status | Notes |
|------|--------|-------|
| llm.chunk table | ✅ Complete | Migration 0008 |
| llm.embedding table | ✅ Complete | Vector storage as JSON |
| llm.retrieval table | ✅ Complete | Query logging |
| llm.retrieval_hit table | ✅ Complete | Result logging |
| llm.source_registry table | ✅ Complete | Incremental indexing support |
| Indexes | ✅ Complete | Performance indexes |

### Embeddings Client

| Item | Status | Notes |
|------|--------|-------|
| Ollama embed() method | ✅ Complete | /api/embed endpoint |
| EmbeddingResponse model | ✅ Complete | Response handling |
| Model configuration | ✅ Complete | OLLAMA_EMBED_MODEL env var |

### Chunking Pipeline

| Item | Status | Notes |
|------|--------|-------|
| Chunker class | ✅ Complete | Configurable chunking |
| chunk_text function | ✅ Complete | Text splitting with overlap |
| Deterministic chunk IDs | ✅ Complete | SHA256-based IDs |
| Indexer CLI | ✅ Complete | Full and incremental modes |
| Source manifest format | ✅ Complete | JSON manifest spec |

### Retrieval Pipeline

| Item | Status | Notes |
|------|--------|-------|
| cosine_similarity function | ✅ Complete | Vector similarity |
| retrieve_chunks function | ✅ Complete | Top-K retrieval |
| RetrievalStore class | ✅ Complete | DB persistence |
| Deterministic tie-breaking | ✅ Complete | Secondary sort by chunk_id |

### Evidence Integration

| Item | Status | Notes |
|------|--------|-------|
| Evidence converter | ✅ Complete | Hits to EvidenceItems |
| Retrieval evidence refs | ✅ Complete | Evidence bundle integration |

### Documentation

| Item | Status | Notes |
|------|--------|-------|
| retrieval.md | ✅ Complete | Architecture overview |
| indexing.md | ✅ Complete | How to index sources |
| operational.md | ✅ Complete | Operations guide |
| Status update | ✅ Complete | This document |

### Tests

| Item | Status | Notes |
|------|--------|-------|
| Retrieval contracts tests | ✅ Complete | 30 tests passing |
| Chunking tests | ✅ Complete | 19 tests passing |
| Retrieval search tests | ✅ Complete | 22 tests passing |

---

## Upcoming: Schema Refactor (Chat/Vector Runtime Split)

**Status: Phase 0 Complete**

A schema refactor is underway to split the `llm` schema into two independent runtimes:

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | ✅ Complete | Baseline inventory, snapshot, and migration notes |
| Phase 1 | 🔜 Planned | Create `vector` schema with new tables |
| Phase 2 | 🔜 Planned | Cutover and deprecate legacy vector tables |

### What's Changing

The vector-related tables (`llm.chunk`, `llm.embedding`, `llm.retrieval`, `llm.retrieval_hit`, `llm.source_registry`) are moving to a new `vector` schema with enhanced lineage and experimentation support.

### What's Preserved

The chat runtime tables (`llm.job`, `llm.run`, `llm.artifact`, `llm.evidence_bundle`, `llm.evidence_item`, `llm.run_evidence`) remain unchanged.

### Related Documents

- [Schema Refactor Migration Notes](schema-refactor-migration-notes.md) — Full migration plan
- [Dependency Inventory](dependency-inventory-vector-subsystem.md) — Impact analysis
- [Legacy Schema Snapshot](../../db/legacy_snapshots/llm_vector_subsystem_snapshot.sql) — Historical reference

---

## TBD Decisions

The following decisions are tracked but not yet finalized:

| Decision | Status | Current State |
|----------|--------|---------------|
| Native vs OpenAI-compatible API | ✅ Decided | Both supported, config-driven |
| JSON validation library | ✅ Decided | Dataclasses with manual validation |
| SQL Server schema | ✅ Decided | Implemented in migrations 0004-0008 |
| Vector store strategy | ✅ Decided | SQL Server + Python similarity (Option 2) |
| Prompt templating engine | ✅ Decided | Jinja2 in interrogations |

---

## How to Update This Document

When completing work on the LLM-Derived Data subsystem:

1. Update the relevant checklist item to ✅ Complete
2. Add notes if needed
3. Update the "Last Updated" date at the top
4. Commit with a message referencing this status update

---

## Related Documentation

- [Vision and Roadmap](vision-and-roadmap.md) — Full roadmap
- [LLM Module README](../../src/llm/README.md) — Source overview
- [Evidence Bundles](evidence.md) — Phase 2 evidence system
- [Retrieval (Phase 3)](retrieval.md) — RAG architecture
- [Indexing Guide](indexing.md) — How to index sources
- [Operational Guide](operational.md) — Operations and troubleshooting
- [SQL Evidence](sql-evidence.md) — SQL result packaging
- [Redaction](redaction.md) — PII redaction hooks
