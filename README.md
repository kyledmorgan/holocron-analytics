# Media Semantics Workbench  
*(working title — name subject to change)*

## Overview

This repository is a **learning-focused data engineering and analytics project** centered on transforming **semi-structured narrative content** into **structured, queryable data models**.

The initial dataset and examples use **Star Wars–related material** (e.g., public wiki-style sources), but the **architecture, schemas, and workflows are designed to generalize to any fictional or narrative media** (film, television, books, games, etc.).

The primary goals are:
- Practice **data warehousing and dimensional modeling**
- Explore **event modeling, continuity analysis, and claims-based facts**
- Experiment with **ELT pipelines** and **local LLM-assisted structuring**
- Provide a **safe, reproducible sandbox** for SQL, Python, and analytics exercises

This is **not a fan site, content mirror, or narrative retelling platform**.

---

## Project Intent

This repository exists to support:
- Learning SQL (DDL, DML, querying, backups/restores)
- Learning ELT and schema evolution
- Practicing analytics over static and semi-static datasets
- Exploring how ambiguous or conflicting information can be modeled without declaring “truth”

The database is intentionally **non-transactional** and **analytics-oriented**.

---

## What *is* included

- SQL DDL for building the database schema from scratch
- Example SQL scripts (inserts, updates, queries)
- Python code for:
  - Calling public APIs (e.g., MediaWiki)
  - Parsing and staging semi-structured data
  - Producing structured outputs (JSON, CSV)
- Local LLM workflows (Ollama-first, tool-agnostic by design)
- Markdown guides and “agent instructions” for:
  - Structuring narrative data
  - Extracting facts, events, and claims
  - Identifying continuity issues

---

## What is *not* included

To avoid copyright and licensing issues:

- ❌ No raw copyrighted scripts, dialogue, or scene descriptions
- ❌ No scraped wiki text committed to the repository
- ❌ No media files (images, video, audio)
- ❌ No fan fiction or narrative rewrites

All **source content remains external** and is processed **locally** by the user.

---

## Data ethics & IP posture

This project is designed to be **transformative and analytical**, not expressive.

- Source material is treated as **input only**
- Outputs are **facts, claims, events, and metadata**
- Interpretations and fan theories are treated as **user-generated claims**, not canon
- No attempt is made to reproduce or substitute original works

Users are responsible for complying with the terms of service of any external data sources they choose to access.

---

## Technology stack (current / planned)

- **Database**
  - SQL Server (primary)
  - SQLite / DuckDB (optional local experiments)

- **Languages**
  - SQL
  - Python

- **AI / LLM**
  - Ollama (local models, primary)
  - API-based tools (optional smoke testing only)

- **Analytics**
  - SQL queries
  - JSON → HTML rendering
  - Static site experiments (future)

---

## Quick Start with Docker

The fastest way to get started is with Docker Desktop. With just one command, you can spin up SQL Server with a fully seeded database:

```bash
# 1. Copy environment file and set your password
cp .env.example .env
# Edit .env and set MSSQL_SA_PASSWORD

# 2. Start everything
docker compose up --build
```

This will:
- Start SQL Server 2022 Developer Edition
- Create the database and all tables
- Load seed data automatically

**Requirements:** Docker Desktop only (no SQL Server or Python installation needed)

📖 **[Full Docker Setup Guide →](docs/runbooks/docker_local_dev.md)**

---

## Documentation Index

For a complete navigational guide to all documentation in this repository, see the **[Documentation Index](docs/DOCS_INDEX.md)**. It provides quick links to essential docs, topic-based navigation, and a full inventory of all Markdown files.

---

## Getting Started (Docker)

The Docker runbook is the single source of truth for standing up the stack on Windows:

- `docs/runbooks/docker_local_dev.md`

It includes a happy-path quickstart, detailed steps, troubleshooting, and cleanup notes.

---

## Learning & exercise focus

This repo is intentionally structured so that:
- The database can be **rebuilt from scratch**
- Data can be **reloaded, broken, and restored**
- Backups can be created and restored for practice
- Schema evolution is expected and documented

It is suitable for:
- Individual learning
- Pair learning
- Teaching foundational data engineering concepts

---

## Current state

- Early schema design (entities, events, continuity)
- Initial ingestion scripts
- Manual and AI-assisted data shaping experiments

Expect breaking changes as patterns evolve.

---

## Future directions (vision)

Potential future explorations include:
- Cross-franchise modeling
- Continuity drift analytics
- Community-submitted claims and theories (metadata only)
- Visualization of events and relationships
- Schema refactoring toward more generic media analytics

---

## Contributions

Contributions are welcome.

- Open issues for ideas, bugs, or modeling discussions
- Submit pull requests for:
  - Schema improvements
  - New exercises
  - Documentation
- This is a **learning project**, not a production system—experimentation is encouraged

---

## Disclaimer

This project is **unofficial**, **non-commercial**, and **not affiliated with or endorsed by any rights holder**.

All trademarks and copyrighted works referenced remain the property of their respective owners.
