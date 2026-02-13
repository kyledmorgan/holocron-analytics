# Functional Gap Analysis (FGA)

**Status:** Phase 0 — Documentation Only  
**Date:** 2026-02-12  
**Purpose:** Comprehensive analysis of current state and gaps for LLM-driven knowledge expansion pipeline.

---

## Overview

This directory contains a complete Functional Gap Analysis (FGA) for the Holocron Analytics LLM expansion pipeline. The analysis was conducted to inform the next phase of development: building a repeatable, queued, prioritized pipeline that leverages LLM "contracts" (Ollama) to extract entities, relationships, and enriched dimension records from raw content.

**Important:** These documents are **documentation only**. No code changes, migrations, or refactors are included. This is a planning and analysis artifact.

---

## Documents (Read in Order)

### 1. [Current State Inventory](01-current-state-inventory.md)
**Purpose:** Complete inventory of existing infrastructure  
**Contents:**
- Repository structure and key directories
- SQL artifact inventory (schemas, tables, stored procedures, views)
- Python code inventory (runners, stores, contracts)
- Storage conventions (filesystem lake, database)
- Configuration and orchestration (Docker Compose, environment variables)

**Read this first** to understand what exists today.

---

### 2. [Data Model Map](02-data-model-map.md)
**Purpose:** Data warehouse-style overview of database schema  
**Contents:**
- High-level schema relationships (ingestion → semantic → LLM → vector → core dimensions)
- Detailed ERD diagrams (Mermaid) for each schema
- Dimension, fact, bridge, and staging table classifications
- Subtype modeling patterns (entities by type, pages by type)
- Missing relationships (entity-entity, entity-event, entity-work)
- Data flow diagrams (current state vs desired future state)

**Includes 5 detailed Mermaid ER diagrams** covering all schemas.

---

### 3. [Workflow and Runner Map](03-workflow-and-runner-map.md)
**Purpose:** Work item lifecycle and runner orchestration patterns  
**Contents:**
- Work item lifecycle for all queue systems (ingestion, LLM, vector)
- State transition diagrams (Mermaid) for each queue
- Runner orchestration patterns (ingestion, LLM Phase 1)
- Concurrency and lease management patterns
- End-to-end processing flows (HTTP ingestion → semantic staging → LLM classification → entity promotion)
- Recovery and error handling scenarios
- Observability and monitoring (current state and gaps)

**Includes 3 detailed Mermaid flowcharts** for orchestration and state transitions.

---

### 4. [Functional Gap Analysis](04-functional-gap-analysis.md)
**Purpose:** Compare current capabilities vs LLM expansion pipeline requirements  
**Contents:**
- Gap analysis for 9 capability areas:
  1. Work queue reuse for LLM jobs
  2. LLM contract definition (input/output)
  3. Chunking strategy + traceability
  4. Multi-entity extraction + dedupe/identity resolution
  5. Relationship/bridge creation patterns
  6. Stored procedure routing from JSON payload
  7. Observability (logging, metrics, run history)
  8. Idempotency + re-runs + backfills
  9. Governance (confidence scoring, human review hooks)
- Impact assessment (High/Medium/Low)
- Recommended solutions with effort estimates (S/M/L)
- Risk assessment (technical and operational)
- Decision points requiring stakeholder input

**Key Output:** Summary table with current state, gap, impact, solution, effort, and dependencies.

---

### 5. [Recommendations and Next Steps](05-recommendations-and-next-steps.md)
**Purpose:** Phased implementation roadmap with milestones and success criteria  
**Contents:**
- **Phase 0:** Minimal scaffolding (job type registry, structured logging, dry-run mode) — 3-5 days
- **Phase 1:** One contract end-to-end (droid entity extraction) — 1-2 weeks
- **Phase 2:** Relationships + multi-output routing — 2-3 weeks
- **Phase 3:** Broader coverage + automated backfill — 3-4 weeks
- **Long-term roadmap:** Phases 4-7 (governance UI, vector retrieval, event/work extraction, CI/CD)
- Explicit decision points with recommendations (JSON schema design, chunking strategy, identity resolution, stored procedure design, priority escalation)
- Success metrics per phase
- Risk mitigation plan
- Rollback plan per phase
- Example queries for validation

**Key Output:** Actionable, incremental implementation plan with clear milestones.

---

## How to Use This Analysis

### For Tech Leads and Architects
1. **Read all 5 documents in order** to understand the complete picture.
2. **Review decision points** in [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md) and make decisions (approve/reject/modify).
3. **Prioritize phases** based on business value and team capacity.
4. **Create implementation tickets** from Phase 0-3 tasks (each task can be a ticket).

### For Developers
1. **Start with [01-current-state-inventory.md](01-current-state-inventory.md)** to familiarize yourself with the codebase.
2. **Read [02-data-model-map.md](02-data-model-map.md)** to understand database schema and relationships.
3. **Refer to [03-workflow-and-runner-map.md](03-workflow-and-runner-map.md)** when working on runner or queue code.
4. **Use [04-functional-gap-analysis.md](04-functional-gap-analysis.md)** to understand why specific features are missing and what's needed.
5. **Implement phases incrementally** as outlined in [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md).

### For Product Owners
1. **Read [04-functional-gap-analysis.md](04-functional-gap-analysis.md)** for capability gaps and impact assessment.
2. **Review [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md)** for effort estimates and success metrics.
3. **Prioritize phases** based on business value (e.g., Phase 1 delivers first concrete entity extraction, Phase 2 adds relationships).

### For DBAs
1. **Read [02-data-model-map.md](02-data-model-map.md)** to understand schema design and missing relationships.
2. **Review stored procedure recommendations** in [04-functional-gap-analysis.md](04-functional-gap-analysis.md) (Section 6: Stored Procedure Routing).
3. **Review decision point 4** in [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md) (stored procedure design).

---

## Key Findings Summary

### ✅ What Exists Today (Strengths)
- **Mature ingestion framework** with work queue, deduplication, and retry logic
- **Operational LLM job queue** with atomic claiming, backoff, and stored procedure routing
- **Semantic staging** for page classification (rules + LLM hybrid)
- **Vector schema** for embedding space management and retrieval tracking
- **File-based artifact lake** with content hashing and integrity verification
- **Docker Compose orchestration** for local development

### ❌ What's Missing (Gaps)
- **Multi-entity extraction:** No support for extracting N entities from single source
- **Relationship/bridge creation:** No entity-entity, entity-event, or entity-work bridges populated
- **Stored procedure routing:** No stored procedures that accept JSON payloads and route to multiple tables
- **Chunking pipeline:** No production chunking (only stubs in vector schema)
- **Identity resolution:** No entity deduplication or merge logic
- **Human review UI:** No web UI or CLI tool for reviewing flagged pages
- **Backfill tooling:** No bulk re-processing or priority escalation utilities

### 🎯 North Star Goal (Reminder)
Take an **Entity/Page** + **Source Page ID** + **raw content** (possibly chunked), "interrogate" the source with an LLM, and produce **multi-pronged outputs**: new or enriched dimension records, relationships via bridge tables, and potentially new tables/bridges when content requires it. Route outputs to correct tables via **stored procedures** using a **JSON input contract**, not direct ad hoc inserts.

---

## Document Statistics

| Document | Lines | Size | Mermaid Diagrams | Tables |
|----------|-------|------|-----------------|--------|
| 01-current-state-inventory.md | 516 | 31 KB | 0 | 20+ |
| 02-data-model-map.md | 779 | 27 KB | 5 ERDs | 15+ |
| 03-workflow-and-runner-map.md | 768 | 26 KB | 3 flowcharts | 10+ |
| 04-functional-gap-analysis.md | 716 | 31 KB | 0 | 5 |
| 05-recommendations-and-next-steps.md | 721 | 26 KB | 0 | 10+ |
| **Total** | **3,500** | **141 KB** | **8 diagrams** | **60+ tables** |

---

## Related Documentation

- [../llm/](../llm/) — LLM-Derived Data subsystem documentation
- [../vector/](../vector/) — Vector runtime documentation
- [../REPO_STRUCTURE.md](../REPO_STRUCTURE.md) — High-level repository guide
- [../DOCS_INDEX.md](../DOCS_INDEX.md) — Full documentation index
- [../../db/migrations/](../../db/migrations/) — SQL migration files referenced in this analysis

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-02-12 | Initial FGA documentation created (5 documents, 3,500 lines) | GitHub Copilot Agent |

---

## Contact

For questions about this analysis or implementation support, contact the Holocron Analytics team.
