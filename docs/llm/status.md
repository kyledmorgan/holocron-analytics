# LLM-Derived Data: Implementation Status

This document tracks the implementation status of the LLM-Derived Data subsystem. It is updated as features are completed.

**Last Updated:** January 2026

---

## Current Phase: Phase 2 — Evidence Assembly + Packaging ✅

**Status: COMPLETE**

Phase 2 has been completed. The evidence assembly system is now fully implemented with bounded artifacts, SQL result packaging, redaction hooks, and comprehensive testing.

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

## TBD Decisions

The following decisions are tracked but not yet finalized:

| Decision | Status | Current State |
|----------|--------|---------------|
| Native vs OpenAI-compatible API | ✅ Decided | Both supported, config-driven |
| JSON validation library | ✅ Decided | Dataclasses with manual validation |
| SQL Server schema | ✅ Decided | Implemented in migrations 0004-0007 |
| Vector store strategy | TBD | Phase 3 |
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
- [SQL Evidence](sql-evidence.md) — SQL result packaging
- [Redaction](redaction.md) — PII redaction hooks
