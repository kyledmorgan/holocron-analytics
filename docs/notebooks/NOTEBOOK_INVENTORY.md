# Jupyter Notebook Inventory & Planning

> **Status:** Planning only — no notebooks or code are added in this phase.
> **Date:** 2026-02-23
> **Scope:** Ideation, architecture survey, and recommendations for notebook usage in Holocron Analytics.

---

## Table of Contents

1. [Repository Survey Summary](#1-repository-survey-summary)
2. [Execution Surfaces](#2-execution-surfaces)
3. [Environment Constraints](#3-environment-constraints)
4. [Notebook Use-Case Inventory](#4-notebook-use-case-inventory)
5. [Technology Recommendations](#5-technology-recommendations)
6. [Notebook Fit: What Works vs What Doesn't](#6-notebook-fit-what-works-vs-what-doesnt)
7. [Proposed Repository Conventions](#7-proposed-repository-conventions)
8. [Risks & Anti-Patterns](#8-risks--anti-patterns)
9. [Next Actions Checklist](#9-next-actions-checklist)

---

## 1. Repository Survey Summary

### Python Entrypoints

| Category | Path | Description |
|----------|------|-------------|
| **CLI** | `src/semantic/cli.py` | Semantic layer CLI |
| **CLI** | `src/ingest/ingest_cli.py` | Ingestion framework CLI |
| **CLI** | `src/ingest/analysis_cli.py` | Analysis CLI |
| **CLI** | `src/ingest/snapshot_cli.py` | Snapshot management CLI |
| **CLI** | `src/llm/cli/priority.py` | Job priority management |
| **CLI** | `src/llm/cli/backfill.py` | Job backfill CLI |
| **Runner** | `src/llm/runners/phase1_runner.py` | Main LLM job runner (polls queue, claims jobs, executes) |
| **Runner** | `src/llm/runners/dispatcher.py` | Job dispatcher/orchestrator |
| **Runner** | `src/llm/runners/derive_runner.py` | Derived data runner |
| **Runner** | `src/ingest/runner/ingest_runner.py` | Ingest runner |
| **Runner** | `src/ingest/runner/concurrent_runner.py` | Concurrent execution support |
| **Script** | `scripts/sqlserver_state_admin.py` | SQL Server state management |
| **Script** | `scripts/llm_inspect_jobs.py` | LLM queue inspection |
| **Script** | `scripts/llm_enqueue_job.py` | Manual job enqueueing |
| **Script** | `scripts/llm_smoke_test.py` | LLM smoke tests |
| **Script** | `scripts/ollama_capture_models.py` | Ollama model capture |
| **Script** | `scripts/verify_schema_alignment.py` | Schema naming validation |
| **Script** | `scripts/db/extract_sql_objects.py` | SQL object extraction & reconciliation |
| **Script** | `scripts/db/db_smoketest.py` | Database smoke test |
| **Seed** | `src/ingest/seed_loader.py` | Loads seed data into DB |

### SQL Assets

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| DDL — Dimensions | `src/db/ddl/01_dimensions/` | ~22 files | Characters, Works, Locations, Eras, etc. |
| DDL — Facts | `src/db/ddl/02_facts/` | ~3 files | FactEvent, ContinuityIssue, FactClaim |
| DDL — Bridges | `src/db/ddl/03_bridges/` | ~3 files | EventParticipant, EventAsset, ContinuityIssueClaim |
| DDL — Ingest | `src/db/ddl/00_ingest/` | ~3 files | Ingest schema tables |
| Migrations | `db/migrations/` | 35 files | `0001_create_schema.sql` → `0035_artifact_content_sql_first.sql` |
| Views — dbo | `src/db/views/dbo/` | Many | Semantic & mart views |
| Views — sem | `src/db/views/sem/` | Many | SEM schema views (character, event, scene, etc.) |
| Views — learn | `src/db/views/learn/` | Several | Learning/analytical views |
| Views — mart | `src/db/views/mart/` | Several | Character profiles, event timelines, asset lifecycles |
| Views — ingest | `src/db/views/ingest/` | Several | Ingest queue views |
| Stored Procedures | `src/db/dml/stored_procedures/` | 15+ | Batch inserts, job queue ops, entity queries |
| Functions | `src/db/dml/functions/` | Placeholder | `.gitkeep` only |
| Triggers | `src/db/dml/triggers/` | Placeholder | `.gitkeep` only |
| Learning Exercises | `docs/lessons/` | 10 lesson sets | SQL exercises with answers |
| Initialization | `docker/init-db.sql` | 1 file | Database creation script |

### Docker & Compose

| File | Services | Description |
|------|----------|-------------|
| `docker-compose.yml` | `sql2025`, `initdb`, `seed`, `ollama`, `llm-runner` | Main compose stack |
| `compose.debug.yaml` | — | Debug variant |
| `Dockerfile` | — | Python 3 slim image for seed/runner |
| `docker/Dockerfile.seed` | — | Seed loader image |

**Services in the main compose:**

- **`sql2025`**: MSSQL Server 2025 Developer Edition on port `1433`, persistent volumes on `W:/Docker/SQL2025/`
- **`initdb`**: One-shot schema initialization (DDL + migrations via `sqlcmd`)
- **`seed`**: One-shot seed data loader (`python src/ingest/seed_loader.py --all`)
- **`ollama`**: Local LLM runtime on `127.0.0.1:11434`, persistent model volume
- **`llm-runner`**: Phase 1 derive runner (profile: `llm`, continuous polling)

### Documentation Highlights

| Area | Key Docs |
|------|----------|
| Quick Start | `QUICKSTART.md`, `docs/runbooks/docker_local_dev.md` |
| Pipeline Flows | `agents/playbooks/pipeline/ingest_transform_load.md`, `src/ingest/README.md` |
| LLM Pipeline | `docs/llm/phase1-runner.md`, `docs/llm/derived-data.md`, `docs/llm/llm-pipeline-observability-current-state.md` |
| Schema & ERD | `docs/diagrams/mermaid/ERD_Explained.md`, `docs/db/schema_refactor_report.md` |
| Naming & Policies | `docs/agent/db_policies.md`, `docs/agent/DB_NAMING_CONVENTIONS.md`, `docs/agent/SQL_STYLE_GUIDE.md` |
| Evidence System | `docs/llm/evidence.md`, `src/llm/contracts/README.md` |
| Observability | `docs/llm/llm-pipeline-observability-current-state.md` |
| Doc Index | `docs/DOCS_INDEX.md` |

### Config & Secrets

| File | Purpose |
|------|---------|
| `.env.example` | Master env template (SQL Server, Ollama, Ingest, LLM runner settings) |
| `config/ingest.example.yaml` | Ingest connector configuration |
| `config/profiles.example.yaml` | Connection profiles |
| `config/logging.example.yaml` | Logging configuration |
| `config/schema-mapping.example.yaml` | Schema mappings |
| `agents/policies/20_security-and-secrets.md` | Security policy: no secrets in VCS |

**Secrets approach:** `.env` files (gitignored), discrete env vars or ODBC connection strings. No vault/keychain integration yet.

---

## 2. Execution Surfaces

These are the ways things are run today:

| Surface | Example Command | Notes |
|---------|----------------|-------|
| **Docker Compose** | `docker compose up --build` | Full stack: SQL Server + initdb + seed + Ollama |
| **Docker Compose (LLM)** | `docker compose --profile llm up` | Adds LLM runner |
| **Python module** | `python -m src.llm.runners.phase1_runner --loop` | LLM derive runner |
| **Python CLI** | `python src/ingest/ingest_cli.py ...` | Ingest framework |
| **Python CLI** | `python src/semantic/cli.py ...` | Semantic layer |
| **Python CLI** | `python src/ingest/snapshot_cli.py ...` | Snapshot management |
| **Python script** | `python scripts/llm_enqueue_job.py` | Manual job enqueueing |
| **Python script** | `python scripts/llm_inspect_jobs.py` | Queue inspection |
| **Python script** | `python scripts/llm_smoke_test.py` | LLM smoke test |
| **Python script** | `python scripts/db/db_smoketest.py` | DB smoke test |
| **Python script** | `python scripts/db/extract_sql_objects.py --extract --reconcile` | SQL sync |
| **Python script** | `python scripts/verify_schema_alignment.py` | Schema validation |
| **Python tool** | `python -m tools.db_init --migrations-dir db/migrations` | DB initialization |
| **Seed loader** | `python src/ingest/seed_loader.py --all --verbose` | Load seed data |
| **Make targets** | `make test`, `make verify-sqlserver`, `make db-up` | Build automation |
| **Direct SQL** | SSMS / Azure Data Studio / `sqlcmd` → `localhost:1433` | Interactive SQL |
| **Pytest** | `python -m pytest tests/unit/ -v` | Unit tests |
| **Pytest** | `python -m pytest tests/integration/ -v -m integration` | Integration tests |

---

## 3. Environment Constraints

### Platform

- **Primary dev environment:** Windows + VS Code + Docker Desktop (WSL2)
- **Python version:** 3.11+ (per `Makefile`)
- **SQL Server:** MSSQL 2025 Developer Edition in Docker, port `1433`

### Dependency Management

- **Approach:** `requirements.txt` (flat pip, no Poetry/PDM)
- **Root deps:** `pyodbc==5.3.0`, `python-dotenv==1.2.1`, `PyYAML==6.0.3`, `requests==2.32.5`, `certifi`, `charset-normalizer`, `idna`, `urllib3`
- **Ingest deps:** `src/ingest/requirements.txt` (additional ingest-specific packages)
- **Test deps:** `pytest`, `pytest-env` (installed via `make install`)
- **No `pyproject.toml` or `setup.py`** — pure requirements.txt approach

### SQL Server Connectivity

- **Driver:** `ODBC Driver 18 for SQL Server`
- **Host (from host):** `localhost:1433`
- **Host (from containers):** `sql2025:1433`
- **Auth:** SQL auth, user `sa`, password via `MSSQL_SA_PASSWORD` env var
- **TLS:** `TrustServerCertificate=yes` (local dev only)
- **Database:** `Holocron`
- **Python lib:** `pyodbc` with ODBC connection strings

### LLM / GPU Tooling

- **Ollama** as local LLM runtime (Docker service, port `11434`)
- **Model:** `llama3.2` (default)
- **GPU:** Optional NVIDIA GPU via WSL2 (commented out in compose); works CPU-only
- **From host:** `http://localhost:11434`
- **From containers:** `http://ollama:11434`

### Existing Notebooks

- **None.** No `.ipynb` files exist in the repository today.

---

## 4. Notebook Use-Case Inventory

### A. Learning Walkthrough Notebooks

#### A1. Hello Pipeline — Connect & Query
| Field | Value |
|-------|-------|
| **What** | Connect to the Holocron DB, query a few core dimension tables (`DimCharacter`, `DimWork`, `DimEra`), display results, explain the dimensional/bridge model |
| **Who** | New contributors, learners |
| **Inputs** | `.env` with SQL connection params |
| **Outputs** | Table displays, row counts, schema diagram annotations |
| **Dependencies** | `pyodbc`, `python-dotenv`, running SQL Server |
| **What to avoid** | Hardcoding connection strings; excessive data pulls |
| **Effort** | **S** |

#### A2. Entity / Relationship Model Tour
| Field | Value |
|-------|-------|
| **What** | Pull example entities from `DimEntity`, traverse relationships via bridge tables, show evidence lineage from `llm.evidence_bundle` → `llm.evidence_item` |
| **Who** | Learners, data modelers |
| **Inputs** | `.env`, sample entity key or GUID |
| **Outputs** | Entity detail display, relationship graph (text or simple viz), evidence chain |
| **Dependencies** | `pyodbc`, `python-dotenv`, seed data loaded |
| **What to avoid** | Pulling entire tables; building complex visualizations prematurely |
| **Effort** | **M** |

#### A3. LLM + Provenance Tour
| Field | Value |
|-------|-------|
| **What** | Walk through how LLM requests/responses/evidence are stored: `llm.job` → `llm.run` → `llm.artifact` → `llm.evidence_bundle`. Show example payloads from the lake (`lake/llm_runs/`) |
| **Who** | Learners, contributors working on LLM subsystem |
| **Inputs** | `.env`, at least one completed LLM run in DB |
| **Outputs** | Job lifecycle display, artifact JSON samples, evidence linkage |
| **Dependencies** | `pyodbc`, `python-dotenv`, `json`, LLM tables populated |
| **What to avoid** | Triggering actual LLM calls; showing raw prompts with PII |
| **Effort** | **M** |

#### A4. SQL Learning Exercises — Interactive Companion
| Field | Value |
|-------|-------|
| **What** | Interactive companion to `docs/lessons/` (10 lesson sets). Provide the exercises in executable cells with hints, then reveal answers |
| **Who** | SQL learners |
| **Inputs** | `.env`, seed data loaded |
| **Outputs** | Query results inline, progressive difficulty |
| **Dependencies** | `pyodbc`, `python-dotenv`, learn-schema views |
| **What to avoid** | Duplicating lesson content — reference `docs/lessons/` and add interactivity only |
| **Effort** | **M** |

---

### B. Operational Runbook Notebooks

#### B1. Start & Verify Local Stack
| Field | Value |
|-------|-------|
| **What** | Step-by-step: `docker compose up`, health checks, DB connectivity test, Ollama status check |
| **Who** | Operations, new contributors |
| **Inputs** | `.env`, Docker running |
| **Outputs** | Health status table, pass/fail indicators per service |
| **Dependencies** | `pyodbc`, `requests`, `subprocess` (for docker commands), `python-dotenv` |
| **What to avoid** | Automating `docker compose` fully in a notebook (fragile); keep as guided verification |
| **Effort** | **S** |

#### B2. Run a Single Ingestion Job
| Field | Value |
|-------|-------|
| **What** | Execute a controlled ingestion run with explicit parameters. Call into `src/ingest/` modules, show before/after row counts |
| **Who** | Operations, debugging |
| **Inputs** | `.env`, ingest config YAML, source identifier |
| **Outputs** | Ingest status, row counts before/after, error log if any |
| **Dependencies** | `pyodbc`, `python-dotenv`, `PyYAML`, ingest modules |
| **What to avoid** | Running large ingestions; mutating production-like data without rollback plan |
| **Effort** | **M** |

#### B3. Run Embedding Generation (Small Slice)
| Field | Value |
|-------|-------|
| **What** | Trigger embedding generation for a small, controlled set of records. Show vector storage results |
| **Who** | Operations, LLM subsystem contributors |
| **Inputs** | `.env`, entity keys or filter criteria, Ollama running |
| **Outputs** | Embedding status, vector counts, sample similarity check |
| **Dependencies** | `pyodbc`, `requests`, `python-dotenv`, vector subsystem modules |
| **What to avoid** | Processing entire corpus; GPU-dependent steps without fallback |
| **Effort** | **M** |

#### B4. Validate Stored Procedure with Sample Payloads
| Field | Value |
|-------|-------|
| **What** | Call stored procedures (`dbo.usp_batch_insert_entities`, `llm.usp_enqueue_job`, etc.) with controlled sample data, verify results |
| **Who** | Operations, database contributors |
| **Inputs** | `.env`, sample JSON payloads |
| **Outputs** | Return values, affected row counts, validation queries |
| **Dependencies** | `pyodbc`, `python-dotenv`, `json` |
| **What to avoid** | Running destructive operations without transaction wrapping; using production-sized payloads |
| **Effort** | **S** |

#### B5. Checkpoint & Re-run (Idempotent Steps)
| Field | Value |
|-------|-------|
| **What** | Demonstrate idempotent pipeline execution: run a step, show state, re-run from checkpoint, verify no duplicates |
| **Who** | Operations, debugging |
| **Inputs** | `.env`, job ID or checkpoint identifier |
| **Outputs** | State snapshots, diff between runs, duplicate check results |
| **Dependencies** | `pyodbc`, `python-dotenv`, LLM/ingest modules |
| **What to avoid** | Complex multi-step orchestration; use simple linear flows |
| **Effort** | **L** |

---

### C. Data Exploration Notebooks

#### C1. Lightweight SQL Queries
| Field | Value |
|-------|-------|
| **What** | A scratchpad for ad-hoc SQL queries with inline results. Pre-loaded with useful starter queries against sem/learn/mart views |
| **Who** | Analysts, learners, anyone |
| **Inputs** | `.env`, query text |
| **Outputs** | Result sets displayed as tables |
| **Dependencies** | `pyodbc`, `python-dotenv`; optionally `pandas` for DataFrame display |
| **What to avoid** | Storing sensitive query results in notebook output cells |
| **Effort** | **S** |

#### C2. Data Profiling — Counts, Nulls, Duplicates
| Field | Value |
|-------|-------|
| **What** | Automated profiling: row counts per table, null rates by column, duplicate detection, referential integrity checks |
| **Who** | Data quality, analytics |
| **Inputs** | `.env`, list of tables/schemas to profile |
| **Outputs** | Summary tables, highlight anomalies |
| **Dependencies** | `pyodbc`, `python-dotenv`; optionally `pandas` |
| **What to avoid** | Running against all tables at once (slow); profiling large text columns |
| **Effort** | **M** |

#### C3. Sample & Explore — Entities, Claims, Evidence
| Field | Value |
|-------|-------|
| **What** | "Show me examples" queries: sample entities by type, claims with evidence bundles, relationship chains |
| **Who** | Learners, data modelers, debuggers |
| **Inputs** | `.env`, entity type or filter |
| **Outputs** | Sample rows, formatted JSON for nested structures |
| **Dependencies** | `pyodbc`, `python-dotenv`, `json` |
| **What to avoid** | Displaying copyrighted full-text content; pulling unbounded result sets |
| **Effort** | **S** |

---

### D. Debug / Observability Notebooks

#### D1. Pipeline State Dashboard
| Field | Value |
|-------|-------|
| **What** | Query LLM job tables (`llm.job`, `llm.run`) to show: queued/running/completed/failed counts, retry counts, recent errors |
| **Who** | Operations, debugging |
| **Inputs** | `.env`, optional time window filter |
| **Outputs** | Status summary table, error message excerpts, recent job timeline |
| **Dependencies** | `pyodbc`, `python-dotenv`; optionally `pandas` |
| **What to avoid** | Exposing full error stack traces with sensitive info |
| **Effort** | **S** |

#### D2. Queue Health & Aged Jobs
| Field | Value |
|-------|-------|
| **What** | Call `llm.usp_get_queue_health_summary`, display results. Flag jobs stuck beyond thresholds. Show escalation candidates (`llm.usp_escalate_aged_jobs`) |
| **Who** | Operations |
| **Inputs** | `.env`, age threshold |
| **Outputs** | Health summary, aged job list, recommended actions |
| **Dependencies** | `pyodbc`, `python-dotenv` |
| **What to avoid** | Auto-escalating without confirmation; modifying job state silently |
| **Effort** | **S** |

#### D3. Before/After Run Comparison
| Field | Value |
|-------|-------|
| **What** | Snapshot key table counts before and after a pipeline run, compute diffs. Useful for validating ingestion or LLM batch runs |
| **Who** | Operations, debugging |
| **Inputs** | `.env`, two run IDs or timestamps |
| **Outputs** | Diff table (added/removed/changed counts), highlight anomalies |
| **Dependencies** | `pyodbc`, `python-dotenv`; optionally `pandas` |
| **What to avoid** | Row-level diffs on large tables (use aggregates) |
| **Effort** | **M** |

#### D4. Artifact & Lake Inspector
| Field | Value |
|-------|-------|
| **What** | Browse LLM run artifacts: list runs by date, show artifact metadata from `llm.artifact`, optionally load and display lake files (`request.json`, `response.json`, `evidence.json`) |
| **Who** | Debugging, LLM contributors |
| **Inputs** | `.env`, run ID or date range |
| **Outputs** | Artifact listing, formatted JSON display, file tree |
| **Dependencies** | `pyodbc`, `python-dotenv`, `json`, `pathlib` |
| **What to avoid** | Loading very large artifacts into memory; displaying raw LLM responses with PII |
| **Effort** | **M** |

---

### E. Future Analytics / Metrics Notebooks

#### E1. Pipeline Throughput & Latency Metrics
| Field | Value |
|-------|-------|
| **What** | Compute and display: jobs/hour, average run duration, success/failure rates over time windows |
| **Who** | Analytics, operations |
| **Inputs** | `.env`, time window |
| **Outputs** | Summary metrics, time-series tables (optional charts) |
| **Dependencies** | `pyodbc`, `python-dotenv`, `pandas`; optionally `matplotlib` |
| **What to avoid** | Over-engineering dashboards; building production monitoring in notebooks |
| **Effort** | **M** |

#### E2. Data Coverage & Completeness
| Field | Value |
|-------|-------|
| **What** | Measure: % of entities with relationships, % of claims with evidence, entity type distribution, temporal coverage |
| **Who** | Analytics, data quality |
| **Inputs** | `.env` |
| **Outputs** | Coverage metrics, distribution tables |
| **Dependencies** | `pyodbc`, `python-dotenv`, `pandas` |
| **What to avoid** | Defining "quality" without clear criteria; creating dashboards that rot |
| **Effort** | **M** |

#### E3. Data Quality Checks (Automated)
| Field | Value |
|-------|-------|
| **What** | Reusable data quality checks: orphan detection, constraint violations, schema drift detection (compare live schema vs DDL files) |
| **Who** | Data quality, CI/CD (future) |
| **Inputs** | `.env`, DDL file paths |
| **Outputs** | Pass/fail per check, detail on failures |
| **Dependencies** | `pyodbc`, `python-dotenv`, `scripts/verify_schema_alignment.py` (call as module) |
| **What to avoid** | Replacing proper CI checks; running expensive checks on every notebook open |
| **Effort** | **L** |

#### E4. R Integration Placeholder
| Field | Value |
|-------|-------|
| **What** | Placeholder for future R-based analytics (e.g., statistical modeling, advanced visualization). Keep Python-first; add R only when a concrete use case arises |
| **Who** | Analytics (future) |
| **Inputs** | TBD |
| **Outputs** | TBD |
| **Dependencies** | `rpy2` or R kernel; not recommended unless specific need |
| **What to avoid** | Adding R infrastructure prematurely; dual-language maintenance burden |
| **Effort** | **L** (when needed) |

---

## 5. Technology Recommendations

### 5.1 Running SQL Inside Notebooks

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **`pyodbc` + helper function** | Already a project dependency; no new libs; portable; full control | More boilerplate per query | **Recommended.** Create a shared `db_connect()` helper that reads `.env` and returns a connection. |
| **`sqlalchemy`** | ORM features, DataFrame integration via `pandas.read_sql()` | New dependency; heavier; not currently used in repo | **Optional.** Only add if `pandas` DataFrames become standard. |
| **`pymssql`** | Pure Python; no ODBC driver needed | Less feature-rich; not currently used | **Not recommended.** `pyodbc` is already established. |
| **Notebook SQL magics** (`%%sql`, `ipython-sql`) | Convenient inline SQL | Portability risk; hides connection logic; extra dependency | **Not recommended.** Prefer explicit Python calls for reproducibility. |

**Proposed pattern:**

```python
# Cell 1: imports + connection (every notebook)
import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    return pyodbc.connect(
        f"Driver={{{os.getenv('SEED_SQLSERVER_DRIVER')}}};"
        f"Server={os.getenv('SEED_SQLSERVER_HOST')},{os.getenv('SEED_SQLSERVER_PORT', '1433')};"
        f"Database={os.getenv('SEED_SQLSERVER_DATABASE')};"
        f"UID={os.getenv('SEED_SQLSERVER_USER')};"
        f"PWD={os.getenv('SEED_SQLSERVER_PASSWORD')};"
        f"TrustServerCertificate=yes;"
    )
```

> **Note:** This helper should eventually live in a shared module (e.g., `src/common/db.py`) that notebooks import, rather than being copy-pasted.

### 5.2 Displaying Results

| Approach | When to Use |
|----------|-------------|
| **`cursor.fetchall()` + print** | Quick checks, small result sets, no extra deps |
| **`pandas.DataFrame`** | Tabular display, filtering, aggregation, export |
| **`json.dumps(..., indent=2)`** | Nested/JSON data (artifacts, evidence bundles) |
| **`matplotlib` / `seaborn`** | Time-series, distributions (future analytics only) |

**Recommendation:** Start with `pyodbc` cursor + print. Add `pandas` as an optional dependency when DataFrame display adds clear value (profiling, metrics). Do not require `pandas` for basic notebooks.

### 5.3 Parameterization

| Approach | Description | Recommendation |
|----------|-------------|----------------|
| **Environment variables** (`.env`) | Already used everywhere; load with `python-dotenv` | **Primary method** for connection params and config |
| **Notebook variables at top** | Plain Python variables in a "Parameters" cell | **Use for per-run inputs** (entity key, date range, limit) |
| **`papermill`** parameterization | CLI-driven notebook execution with parameter injection | **Future option** for automated runbook execution; not needed yet |
| **`ipywidgets`** | Interactive dropdowns, sliders, text inputs | **Avoid** unless building a specific interactive demo; adds complexity |

### 5.4 Secrets Handling

**Rules (aligned with `agents/policies/20_security-and-secrets.md`):**

1. **Never commit credentials** — `.env` is already in `.gitignore`
2. **Always use `.env` loading** — `load_dotenv()` in every notebook's first cell
3. **Strip outputs before commit** — connection strings, passwords, and auth tokens can leak into cell outputs
4. **No inline passwords** — even in Markdown cells or comments
5. **Document the pattern** — each notebook should have a "Prerequisites" cell explaining what `.env` vars are needed

**Future options:** OS keychain (`keyring` library), Azure Key Vault, or Docker secrets. Not needed for local dev today.

### 5.5 Reproducibility

| Practice | Description |
|----------|-------------|
| **Pinned deps** | Use a `notebooks/requirements.txt` with pinned versions (extend root `requirements.txt`) |
| **Deterministic seeds** | When sampling, use `ORDER BY` + `TOP N` or explicit `WHERE` filters rather than `NEWID()` |
| **Idempotent cells** | Each cell should be safe to re-run without side effects (use `IF NOT EXISTS`, transactions) |
| **Kernel restart test** | Every notebook should work with "Restart & Run All" |
| **Clear outputs before commit** | Use `nbstripout` or pre-commit hook to remove cell outputs |

### 5.6 Artifacts

**Proposed convention (do not create yet):**

```
artifacts/              # gitignored — runtime outputs
  notebooks/            # notebook-generated exports
    YYYY-MM-DD/         # date-partitioned
      profile_report.csv
      coverage_metrics.json

docs/notebooks/         # committed — documentation & plans
  NOTEBOOK_INVENTORY.md # this file
```

- **Do not commit** large data exports, screenshots, or generated reports to `docs/`.
- **Do commit** small, curated reference outputs if they serve as documentation.
- The existing `artifacts/` entry in `.gitignore` already covers runtime outputs.

---

## 6. Notebook Fit: What Works vs What Doesn't

### Great Fits ✅

| Use Case | Why Notebooks Work Well |
|----------|------------------------|
| **Interactive exploration** | Immediate feedback; see data as you query |
| **Learning walkthroughs** | Narrative + code + output in one document |
| **Controlled single runs** | Parameterize, execute, inspect — ideal for runbooks |
| **Validation harnesses** | Run a sproc, check results, document the test |
| **Data profiling** | Quick stats, null checks, sample rows |
| **Debugging investigations** | Ad-hoc queries to diagnose a specific issue |

### Borderline ⚠️

| Use Case | Guidance |
|----------|----------|
| **Long-running jobs** (>5 min) | Can work but risk kernel timeout; prefer calling module functions with progress output |
| **Multi-step pipelines** | OK if each cell is a clear step; but complex orchestration belongs in Python modules |
| **Scheduled/recurring runs** | Possible with `papermill` + cron, but not the best tool; prefer scripts or runners |
| **Team-shared state** | Notebooks are personal artifacts; don't rely on them for shared truth |

### Poor Fits ❌

| Use Case | Why Notebooks Are Wrong |
|----------|------------------------|
| **Always-on services** | Notebooks aren't daemons; use Docker services or systemd |
| **Production orchestration** | No retry logic, no monitoring, no alerting |
| **Secret-heavy flows** | Output cells can leak secrets; difficult to audit |
| **Concurrent/parallel processing** | Notebooks are single-threaded; use `concurrent_runner.py` |
| **Elevated-privilege operations** | DBA operations (DROP, ALTER) should go through migration scripts, not notebooks |
| **Large data transfers** | Memory-bound; use `sqlcmd` bulk operations or BCP |

### Logic Placement Guidance

| Pattern | When |
|---------|------|
| **Notebook calls Python module** (preferred) | Logic is reusable, testable, or complex. Import from `src/` and call functions. |
| **Logic directly in notebook** (discouraged) | Only for tiny glue code: connection setup, display formatting, one-off queries. |
| **Notebook as thin orchestrator** (ideal) | Notebook provides narrative + parameters + display; all logic lives in `src/` modules. |

**Example:**

```python
# Good: notebook calls existing module
from llm.jobs.queue import inspect_queue
results = inspect_queue(conn, status="failed", limit=10)
display(results)

# Bad: notebook reimplements queue inspection
cursor.execute("SELECT * FROM llm.job WHERE Status = 'Failed' ORDER BY ...")
# ... 30 lines of processing logic ...
```

---

## 7. Proposed Repository Conventions

### Folder Structure

```
notebooks/
├── README.md                    # Overview, setup instructions, conventions
├── _templates/                  # Notebook template(s)
│   └── starter.ipynb            # Standard imports, env loading, connection helper
├── learning/                    # Category A: Learning walkthroughs
│   ├── 01_hello_pipeline.ipynb
│   ├── 02_entity_relationship_tour.ipynb
│   ├── 03_llm_provenance_tour.ipynb
│   └── 04_sql_exercises_companion.ipynb
├── runbooks/                    # Category B: Operational runbooks
│   ├── 01_verify_local_stack.ipynb
│   ├── 02_single_ingestion_run.ipynb
│   ├── 03_embedding_generation.ipynb
│   ├── 04_validate_stored_procedure.ipynb
│   └── 05_checkpoint_rerun.ipynb
├── exploration/                 # Category C: Data exploration
│   ├── 01_sql_scratchpad.ipynb
│   ├── 02_data_profiling.ipynb
│   └── 03_sample_explorer.ipynb
├── debug/                       # Category D: Debug & observability
│   ├── 01_pipeline_state.ipynb
│   ├── 02_queue_health.ipynb
│   ├── 03_before_after_diff.ipynb
│   └── 04_artifact_inspector.ipynb
└── analytics/                   # Category E: Future analytics
    ├── 01_throughput_latency.ipynb
    ├── 02_coverage_completeness.ipynb
    └── 03_data_quality_checks.ipynb
```

### Naming Conventions

- **Prefix ordering:** `01_`, `02_`, etc. within each category for logical progression
- **Lowercase with underscores:** `01_hello_pipeline.ipynb` (no spaces, no camelCase)
- **Category folders match inventory sections:** `learning/`, `runbooks/`, `exploration/`, `debug/`, `analytics/`

### Notebook Template Concept

Every notebook should start with a standard preamble:

```python
# Cell 1: Metadata (Markdown)
"""
# Notebook Title
**Category:** Learning | Runbook | Exploration | Debug | Analytics
**Prerequisites:** Docker stack running, .env configured
**Last verified:** YYYY-MM-DD
"""

# Cell 2: Environment & Connection
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Connect to Holocron SQL Server using .env credentials."""
    return pyodbc.connect(
        f"Driver={{{os.getenv('SEED_SQLSERVER_DRIVER')}}};"
        f"Server={os.getenv('SEED_SQLSERVER_HOST')},{os.getenv('SEED_SQLSERVER_PORT', '1433')};"
        f"Database={os.getenv('SEED_SQLSERVER_DATABASE')};"
        f"UID={os.getenv('SEED_SQLSERVER_USER')};"
        f"PWD={os.getenv('SEED_SQLSERVER_PASSWORD')};"
        f"TrustServerCertificate=yes;"
    )

# Cell 3: Parameters (editable per run)
LIMIT = 10
# ENTITY_TYPE = "character"
```

> **Future improvement:** Extract `get_connection()` into `src/common/db.py` and import it. Keep the template simple for now.

### Output Stripping Policy

- **Pre-commit hook (recommended):** Use [`nbstripout`](https://github.com/kynan/nbstripout) to automatically strip cell outputs before commit
- **Manual alternative:** "Cell → All Output → Clear" before committing
- **CI check (optional):** Add a lint step that fails if `.ipynb` files contain output cells
- **Rationale:** Outputs can contain secrets, large data dumps, or non-deterministic content that bloats diffs

**Setup (when ready):**

```bash
pip install nbstripout
nbstripout --install           # adds git filter
# OR add to .gitattributes:
# *.ipynb filter=nbstripout
```

### `.gitignore` Addition (when ready)

```gitignore
# Jupyter
.ipynb_checkpoints/
```

### Dependencies (when ready)

Create `notebooks/requirements.txt`:

```
jupyter>=1.0
notebook>=7.0
ipykernel>=6.0
nbstripout>=0.7
# Optional (add when needed):
# pandas>=2.0
# matplotlib>=3.8
```

---

## 8. Risks & Anti-Patterns

| Risk | Mitigation |
|------|------------|
| **Secrets in output cells** | Strip outputs before commit; use `nbstripout`; never print connection strings |
| **Notebooks as production code** | Keep logic in `src/` modules; notebooks are thin callers |
| **Stale notebooks** | Add "Last verified" date; periodically "Restart & Run All" |
| **Unbounded queries** | Always use `TOP N` or `LIMIT`; never `SELECT *` on large tables |
| **Copyrighted content display** | Only show metadata, summaries, and computed attributes — not source text (per `agents/policies/10_ip-and-data.md`) |
| **Kernel state pollution** | Each cell should be independently re-runnable; avoid mutable global state |
| **Duplicate logic** | If you write >20 lines of logic in a notebook, extract it to a module in `src/` |
| **Large binary diffs** | `.ipynb` files are JSON; outputs + images create huge diffs. Strip outputs. |
| **Dependency drift** | Pin notebook-specific deps in `notebooks/requirements.txt`; don't modify root `requirements.txt` for notebook-only needs |
| **Over-engineering early** | Start with the simplest notebooks (C1, A1, D1); add complexity only when needed |

---

## 9. Next Actions Checklist

The top highest-value notebooks to create first, ordered by impact and effort:

- [ ] **1. `exploration/01_sql_scratchpad.ipynb`** (S) — Immediate value for anyone querying the DB. Lowest effort, highest reuse.
- [ ] **2. `learning/01_hello_pipeline.ipynb`** (S) — Onboarding essential. Connect, query dimensions, explain the star schema.
- [ ] **3. `debug/01_pipeline_state.ipynb`** (S) — Operational quick-win. Query `llm.job`/`llm.run` status tables.
- [ ] **4. `debug/02_queue_health.ipynb`** (S) — Call `llm.usp_get_queue_health_summary`, display results.
- [ ] **5. `runbooks/01_verify_local_stack.ipynb`** (S) — Guided stack verification replaces ad-hoc troubleshooting.
- [ ] **6. `exploration/02_data_profiling.ipynb`** (M) — Row counts, null rates, referential integrity across schemas.
- [ ] **7. `learning/02_entity_relationship_tour.ipynb`** (M) — Deep dive into dimensional model with live examples.
- [ ] **8. `learning/03_llm_provenance_tour.ipynb`** (M) — Walk the LLM lineage chain (job → run → artifact → evidence).
- [ ] **9. `runbooks/04_validate_stored_procedure.ipynb`** (S) — Test sprocs with sample payloads in a controlled notebook.
- [ ] **10. `exploration/03_sample_explorer.ipynb`** (S) — "Show me examples" for entities, claims, evidence bundles.

### Before creating any notebooks

- [ ] Create `notebooks/` folder structure (as proposed in Section 7)
- [ ] Create starter template (`notebooks/_templates/starter.ipynb`)
- [ ] Add `notebooks/requirements.txt` with Jupyter and core deps
- [ ] Add `.ipynb_checkpoints/` to `.gitignore`
- [ ] Set up `nbstripout` for output stripping
- [ ] Extract `get_connection()` into a shared module (`src/common/db.py` or similar)
- [ ] Update `docs/DOCS_INDEX.md` with a notebooks section

---

*This document is the deliverable for the notebook inventory and planning phase. No notebooks, code, or infrastructure changes are included.*
