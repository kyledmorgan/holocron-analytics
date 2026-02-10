# Documentation Index

This document provides a navigational hub for all documentation in the holocron-analytics repository. Use it to quickly find authoritative docs, understand the repository structure, and locate specific topics.

---

## Start Here

New to this repository? Start with these essential documents:

| Document | Description |
|----------|-------------|
| [Root README](../README.md) | Project overview, goals, quick start guide |
| [Quick Start Guide](../QUICKSTART.md) | **5-minute setup** — Get running with Docker immediately |
| [Contributing Guide](../CONTRIBUTING.md) | How to contribute to the project |
| [Docker Local Dev Runbook](runbooks/docker_local_dev.md) | Detailed step-by-step guide to run the stack locally with Docker |
| [Repository Structure](REPO_STRUCTURE.md) | Top-level folder layout and guiding principles |
| [Project Vision](vision/ProjectVision.md) | Long-term goals and design philosophy |
| [Agent Overview](../agents/README.md) | Policies, playbooks, and templates for contributors |
| [ERD Explained](diagrams/mermaid/ERD_Explained.md) | Schema overview and dimensional modeling concepts |

---

## By Topic / Area

### Local Development & Docker

| Document | Description |
|----------|-------------|
| [Docker Local Dev Runbook](runbooks/docker_local_dev.md) | Full setup guide for Windows + Docker Desktop |
| [Repository Structure](REPO_STRUCTURE.md) | Folder layout and where to find things |

### Database (DDL, Schema, Naming Conventions)

| Document | Description |
|----------|-------------|
| [ERD Explained](diagrams/mermaid/ERD_Explained.md) | Comprehensive schema documentation with column dictionaries |
| [DDL Ordering and Manifest](../agents/playbooks/db/ddl_ordering_and_manifest.md) | DDL file organization and execution order |

### Seed Data & Ingestion

| Document | Description |
|----------|-------------|
| [Seed Data Framework](../src/db/seeds/README.md) | JSON seed format specification and loader usage |
| [Sources Overview](../sources/README.md) | Source metadata and mapping templates |
| [Ingest Transform Load](../agents/playbooks/pipeline/ingest_transform_load.md) | Conceptual ETL flow |
| [Ingest Framework README](../src/ingest/README.md) | Ingestion framework overview and architecture |
| [Ingest Quick Start](../src/ingest/QUICKSTART.md) | Getting started with the ingestion framework |

### Integrations

| Document | Description |
|----------|-------------|
| [OpenAlex Integration Guide](openalex-integration.md) | User guide for OpenAlex API integration |
| [OpenAlex Implementation Summary](integrations/openalex-implementation-summary.md) | Technical implementation details and architecture decisions |

### LLM-Derived Data

| Document | Description |
|----------|-------------|
| [Vision and Roadmap](llm/vision-and-roadmap.md) | Project vision, goals, and phased roadmap |
| [LLM-Derived Data Overview](llm/derived-data.md) | Concepts, architecture, and roadmap for the LLM-derived data subsystem |
| [Phase 1 Runner](llm/phase1-runner.md) | End-to-end LLM derive pipeline usage guide |
| [retrieval.md](llm/retrieval.md) | Phase 3 RAG architecture, chunking, embeddings, and retrieval |
| [Indexing Guide](llm/indexing.md) | How to index sources for retrieval |
| [Operational Guide](llm/operational.md) | Operations, retention, and troubleshooting |
| [Schema Refactor Migration Notes](llm/schema-refactor-migration-notes.md) | Chat/vector runtime split migration plan |
| [Dependency Inventory](llm/dependency-inventory-vector-subsystem.md) | Vector subsystem dependency analysis |
| [Ollama Integration Guide](llm/ollama.md) | Ollama API documentation, configuration, and operational guidance |
| [Ollama in Docker](llm/ollama-docker.md) | Running Ollama as a Docker Compose service (Windows + WSL2) |
| [Ollama Resilience](ollama-resilience.md) | Retry logic, error handling, and troubleshooting for Ollama JSON parsing |
| [Glossary](llm/glossary.md) | Core terminology and definitions |
| [Contracts](llm/contracts.md) | Schema versioning, validation behavior, and contract-first approach |
| [Implementation Status](llm/status.md) | Living checklist of implementation progress |
| [Governance](llm/governance.md) | Retention, redaction, and policy placeholders (TBD) |
| [Lineage](llm/lineage.md) | Data lineage tracking approach (TBD) |
| [LLM Module README](../src/llm/README.md) | Source code overview and quick start for the LLM module |
| [LLM Configuration Reference](../src/llm/config/config.md) | Configuration options and environment variables |
| [LLM Contracts README](../src/llm/contracts/README.md) | JSON schema documentation for manifests and outputs |
| [Interrogations README](../src/llm/interrogations/README.md) | Interrogation catalog concept and structure |

### Vector Runtime

| Document | Description |
|----------|-------------|
| [Vector Runtime Overview](vector/README.md) | Embedding, storage, and retrieval runtime documentation |

### Analytics / Views / Exercises

| Document | Description |
|----------|-------------|
| [SQL Learning Lessons](lessons/README.md) | Progressive SQL exercises using learner-friendly views |

### Agents & Automation Rules

| Document | Description |
|----------|-------------|
| [AGENTS.md](../AGENTS.md) | Top-level agent guidance and rule references |
| [Agent Overview](../agents/README.md) | Policies, playbooks, and templates index |
| [Global Policy](../agents/policies/00_global.md) | Core contribution guidelines |
| [IP and Data Policy](../agents/policies/10_ip-and-data.md) | Data handling and IP protection rules |
| [Security and Secrets Policy](../agents/policies/20_security-and-secrets.md) | Secrets management and security practices |
| [Style and Structure Policy](../agents/policies/30_style-and-structure.md) | Naming conventions and folder structure |
| [Doc Updates and Cross-Links](../agents/playbooks/docs/update_docs_and_links.md) | Documentation update workflow |
| [Extraction Template](../agents/templates/prompts/extraction_template.md) | Prompt template for data extraction |

### Roadmap / Vision

| Document | Description |
|----------|-------------|
| [Project Vision](vision/ProjectVision.md) | Long-term vision and design philosophy |
| [Roadmap](vision/Roadmap.md) | Phased evolution plan from MVP to production |

---

## Full Inventory

All Markdown files in this repository, grouped by location:

### Root Directory

| File | Description |
|------|-------------|
| [README.md](../README.md) | Project overview, quick start, and contribution info |
| [QUICKSTART.md](../QUICKSTART.md) | 5-minute quick start guide for new users |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines and development workflow |
| [AGENTS.md](../AGENTS.md) | Agent instruction summary with links to detailed policies |

### `docs/`

| File | Description |
|------|-------------|
| [DOCS_INDEX.md](DOCS_INDEX.md) | This documentation index |
| [REPO_STRUCTURE.md](REPO_STRUCTURE.md) | Repository folder layout and guiding principles |
| [openalex-integration.md](openalex-integration.md) | OpenAlex API integration user guide |

### `docs/_reports/`

| File | Description |
|------|-------------|
| [folder-structure-recommendations.md](_reports/folder-structure-recommendations.md) | Folder structure improvement proposals (report only) |

### `docs/data-quality/`

| File | Description |
|------|-------------|
| [seed_cleanup_report.md](data-quality/seed_cleanup_report.md) | Seed data cleanup and validation report |

### `docs/integrations/`

| File | Description |
|------|-------------|
| [openalex-implementation-summary.md](integrations/openalex-implementation-summary.md) | OpenAlex integration technical implementation summary |

### `docs/llm/`

| File | Description |
|------|-------------|
| [contracts.md](llm/contracts.md) | Contract-first approach, schema versioning, and validation |
| [derived-data.md](llm/derived-data.md) | LLM-Derived Data subsystem overview, concepts, and roadmap |
| [glossary.md](llm/glossary.md) | Core terminology and definitions |
| [governance.md](llm/governance.md) | Governance policy placeholders (retention, redaction) |
| [indexing.md](llm/indexing.md) | Phase 3 indexing guide for retrieval |
| [lineage.md](llm/lineage.md) | Data lineage tracking approach |
| [ollama.md](llm/ollama.md) | Ollama integration guide with API documentation |
| [ollama-docker.md](llm/ollama-docker.md) | Running Ollama as a Docker Compose service |
| [operational.md](llm/operational.md) | Phase 3 operations and troubleshooting |
| [phase1-runner.md](llm/phase1-runner.md) | Phase 1 LLM Runner usage guide |
| [retrieval.md](llm/retrieval.md) | Phase 3 RAG architecture and retrieval |
| [schema-refactor-migration-notes.md](llm/schema-refactor-migration-notes.md) | Chat/vector runtime split migration plan |
| [dependency-inventory-vector-subsystem.md](llm/dependency-inventory-vector-subsystem.md) | Vector subsystem dependency analysis |
| [status.md](llm/status.md) | Implementation status tracker |
| [vision-and-roadmap.md](llm/vision-and-roadmap.md) | Vision, goals, and phased roadmap |

### `docs/vector/`

| File | Description |
|------|-------------|
| [README.md](vector/README.md) | Vector runtime overview, schema tables, and Python modules |

### `docs/diagrams/mermaid/`

| File | Description |
|------|-------------|
| [ERD_Explained.md](diagrams/mermaid/ERD_Explained.md) | Detailed schema documentation with column dictionaries for all dimension, fact, and bridge tables |

### `docs/lessons/`

| File | Description |
|------|-------------|
| [README.md](lessons/README.md) | SQL learning lessons overview, module index, and learner guidance |

### `docs/runbooks/`

| File | Description |
|------|-------------|
| [docker_local_dev.md](runbooks/docker_local_dev.md) | Comprehensive Docker setup guide with troubleshooting |

### `docs/vision/`

| File | Description |
|------|-------------|
| [ProjectVision.md](vision/ProjectVision.md) | Long-term project vision and design philosophy |
| [Roadmap.md](vision/Roadmap.md) | Phased roadmap from foundations to public readiness |

### `agents/`

| File | Description |
|------|-------------|
| [README.md](../agents/README.md) | Agent overview with links to policies and playbooks |

### `agents/policies/`

| File | Description |
|------|-------------|
| [00_global.md](../agents/policies/00_global.md) | Global contribution policy |
| [10_ip-and-data.md](../agents/policies/10_ip-and-data.md) | IP and data handling policy |
| [20_security-and-secrets.md](../agents/policies/20_security-and-secrets.md) | Security and secrets policy |
| [30_style-and-structure.md](../agents/policies/30_style-and-structure.md) | Style and structure guidelines |

### `agents/playbooks/db/`

| File | Description |
|------|-------------|
| [ddl_ordering_and_manifest.md](../agents/playbooks/db/ddl_ordering_and_manifest.md) | DDL file organization and manifest guidance |
| [seed_expansion_framework.md](../agents/playbooks/db/seed_expansion_framework.md) | Framework for expanding seed data coverage |

### `agents/playbooks/docs/`

| File | Description |
|------|-------------|
| [update_docs_and_links.md](../agents/playbooks/docs/update_docs_and_links.md) | Documentation update workflow and cross-linking rules |

### `agents/playbooks/pipeline/`

| File | Description |
|------|-------------|
| [ingest_transform_load.md](../agents/playbooks/pipeline/ingest_transform_load.md) | Conceptual ETL pipeline description |

### `agents/templates/prompts/`

| File | Description |
|------|-------------|
| [extraction_template.md](../agents/templates/prompts/extraction_template.md) | Prompt template for structured data extraction |

### `src/db/seeds/`

| File | Description |
|------|-------------|
| [README.md](../src/db/seeds/README.md) | Seed data framework documentation |

### `src/ingest/`

| File | Description |
|------|-------------|
| [README.md](../src/ingest/README.md) | Ingestion framework overview and architecture |
| [QUICKSTART.md](../src/ingest/QUICKSTART.md) | Quick start guide for the ingestion framework |
| [IMPLEMENTATION_SUMMARY.md](../src/ingest/IMPLEMENTATION_SUMMARY.md) | Ingestion framework implementation summary |

### `src/llm/`

| File | Description |
|------|-------------|
| [README.md](../src/llm/README.md) | LLM-Derived Data module overview and quick start |
| [contracts/README.md](../src/llm/contracts/README.md) | JSON schema documentation for manifests and outputs |
| [interrogations/README.md](../src/llm/interrogations/README.md) | Interrogation catalog concept and structure |
| [prompts/README.md](../src/llm/prompts/README.md) | Prompt template guidelines and best practices |
| [providers/README.md](../src/llm/providers/README.md) | LLM provider strategy and client documentation |
| [config/config.md](../src/llm/config/config.md) | Configuration reference for the LLM module |

### `sources/`

| File | Description |
|------|-------------|
| [README.md](../sources/README.md) | Source definitions and mapping templates overview |

### `scripts/`

| File | Description |
|------|-------------|
| [README.md](../scripts/README.md) | Utility scripts for database, LLM, and testing operations |

### `tools/`

| File | Description |
|------|-------------|
| [README.md](../tools/README.md) | Core tools documentation (db_init and system utilities) |

### `web/`

| File | Description |
|------|-------------|
| [README.md](../web/README.md) | Web application structure and planned features (placeholder) |

### `exercises/`

| File | Description |
|------|-------------|
| [README.md](../exercises/README.md) | Learning exercises for SQL, Python, and scenario-based challenges |

### `prompts/`

| File | Description |
|------|-------------|
| [README.md](../prompts/README.md) | LLM prompt templates for extraction, normalization, and evaluation |

---

## Index Maintenance Policy

This index is **refreshed intentionally** on a manual cadence rather than continuously auto-updated.

**Guidelines:**

1. **When adding new documentation**: Add a TODO entry in the PR description or update the index during the next documentation refresh, unless explicitly asked to update immediately.

2. **When modifying existing documentation**: Minor edits (typos, clarifications) do not require index updates. Structural changes (new sections, renamed files, relocated docs) should trigger an index update.

3. **Refresh cadence**: This index should be reviewed and updated during documentation-focused sprints or when significant structural changes occur.

4. **Ownership**: Any contributor can update this index. Keep entries concise and navigational—do not duplicate content from linked documents.

---

## Future Enhancements (Not Implemented)

The following improvements are planned but not yet implemented:

- [ ] **Website rendering**: Render this documentation into a browsable static site or local web UI
- [ ] **Live search**: Add client-side search functionality for quick document discovery
- [ ] **Automated index generation**: Create hooks or scripts to auto-generate the Full Inventory section
- [ ] **Doc linting / link checking**: Integrate a Markdown linter and link checker into CI
- [ ] **Version history**: Track documentation versions alongside schema evolution
- [ ] **Cross-links to live schema**: Link documentation to actual database objects in the web UI
