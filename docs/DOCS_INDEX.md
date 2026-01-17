# Documentation Index

This document provides a navigational hub for all documentation in the holocron-analytics repository. Use it to quickly find authoritative docs, understand the repository structure, and locate specific topics.

---

## Start Here

New to this repository? Start with these essential documents:

| Document | Description |
|----------|-------------|
| [Root README](../README.md) | Project overview, goals, quick start guide |
| [Docker Local Dev Runbook](runbooks/docker_local_dev.md) | Step-by-step guide to run the stack locally with Docker |
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
| [AGENTS.md](../AGENTS.md) | Agent instruction summary with links to detailed policies |

### `docs/`

| File | Description |
|------|-------------|
| [DOCS_INDEX.md](DOCS_INDEX.md) | This documentation index |
| [REPO_STRUCTURE.md](REPO_STRUCTURE.md) | Repository folder layout and guiding principles |

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

### `sources/`

| File | Description |
|------|-------------|
| [README.md](../sources/README.md) | Source definitions and mapping templates overview |

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
