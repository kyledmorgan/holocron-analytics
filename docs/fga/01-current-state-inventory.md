# Current State Inventory

**Status:** Phase 0 — Documentation Only  
**Date:** 2026-02-12  
**Purpose:** Comprehensive inventory of existing Holocron Analytics infrastructure to support LLM expansion pipeline planning.

---

## Overview

This document provides a complete inventory of the current Holocron Analytics repository structure, SQL artifacts, and Python codebase. It serves as the foundation for gap analysis and implementation planning for the LLM-driven knowledge expansion pipeline.

**Important:** This is a snapshot of what exists today. No new functionality is implemented as part of this documentation effort.

---

## Repository Structure

### Top-Level Organization

```
holocron-analytics/
├── agents/              # Agent instructions and policies
├── config/              # Configuration files
├── db/                  # Database migrations and schemas
│   ├── migrations/      # Sequential SQL migrations (0001-0024)
│   └── legacy_snapshots/# Historical schema snapshots
├── docker/              # Docker build and init scripts
├── docs/                # Documentation (you are here)
├── exercises/           # Training/demo materials
├── logs/                # Runtime logs (gitignored)
├── prompts/             # Prompt templates for LLM operations
├── scripts/             # Utility scripts and tooling
├── sources/             # Source data and seed files
├── src/                 # Python source code
│   ├── common/          # Shared utilities
│   ├── db/              # Database utilities
│   ├── ingest/          # Ingestion framework
│   ├── llm/             # LLM-Derived Data subsystem
│   ├── load/            # Data loaders
│   ├── quality/         # Data quality tools
│   ├── semantic/        # Semantic staging and classification
│   ├── transform/       # Data transformations
│   └── vector/          # Vector/embedding runtime
├── tests/               # Test suites
├── tools/               # External tools (Bruno API tests, etc.)
└── web/                 # Web UI (if present)
```

**Key Directories:**
- **db/migrations/**: All SQL schemas, tables, procedures, and indexes (24 migrations)
- **src/ingest/**: Work queue and HTTP acquisition framework
- **src/llm/**: LLM job queue, runners, evidence assembly, and artifact storage
- **src/semantic/**: Page classification, signals extraction, and entity promotion staging
- **src/vector/**: Embedding space management, chunking, and retrieval tracking

---

## SQL Artifact Inventory

### Schemas

| Schema | Migration | Purpose |
|--------|-----------|---------|
| **ingest** | `0001_create_schema.sql` | Raw data ingestion, work queue, and HTTP response storage |
| **llm** | `0004_create_llm_schema.sql` | LLM job queue, runs, artifacts, and evidence tracking |
| **sem** | `0014_create_sem_schema.sql` | Semantic staging for page classification and entity promotion |
| **vector** | `0023_create_vector_schema.sql` | Embedding spaces, vector storage, and retrieval evaluation |
| **dbo** | (pre-existing) | Core dimensional model (entities, tags, bridges) |

---

### Work Queue / Job Management Tables

| Table | Schema | Migration | Purpose | Key Columns |
|-------|--------|-----------|---------|-------------|
| **work_items** | ingest | `0002_create_tables.sql` | HTTP ingestion work queue | `work_item_id` (PK), `source_system`, `resource_id`, `request_uri`, `status` (pending/in_progress/completed/failed/skipped), `priority`, `attempt`, `dedupe_key` |
| **ingest_runs** | ingest | `0002_create_tables.sql` | Ingestion batch run tracking | `run_id` (PK), `started_at`, `completed_at`, `status`, `total_items`, `successful_items`, `failed_items` |
| **job** | llm | `0005_create_llm_tables.sql` | LLM derivation job queue | `job_id` (PK), `job_type`, `status` (NEW/RUNNING/SUCCEEDED/FAILED/DEADLETTER), `priority`, `max_attempts`, `current_attempt`, `backoff_until`, `created_at`, `claimed_by`, `claimed_at` |
| **run** | llm | `0005_create_llm_tables.sql` | Individual LLM job execution attempts | `run_id` (PK), `job_id` (FK), `started_at`, `completed_at`, `status`, `model_name`, `prompt_tokens`, `completion_tokens`, `error_message` |
| **job** | vector | `0023_create_vector_schema.sql` | Vector operations queue | `job_id` (PK), `job_type` (CHUNK_SOURCE/EMBED_CHUNKS/REEMBED_SPACE/RETRIEVE_TEST/DRIFT_TEST), `status`, `priority`, `source_registry_id`, `embedding_space_id` |
| **run** | vector | `0023_create_vector_schema.sql` | Vector job execution tracking | `run_id` (PK), `job_id` (FK), `status`, `started_at`, `completed_at`, `chunks_processed`, `embeddings_created` |

**Relationships:**
- `ingest.work_items` → `ingest.IngestRecords` (via `work_item_id`)
- `llm.job` → `llm.run` (1:N, multiple attempts per job)
- `llm.run` → `llm.artifact` (1:N, multiple artifacts per run)
- `vector.job` → `vector.run` (1:N, multiple execution attempts)

---

### Raw Content Storage Tables

| Table | Schema | Migration | Purpose | Key Columns |
|-------|--------|-----------|---------|-------------|
| **IngestRecords** | ingest | `0002_create_tables.sql` | Raw HTTP responses with full payload | `ingest_id` (PK), `source_system`, `resource_id`, `request_uri`, `status_code`, `payload` (NVARCHAR(MAX) JSON/HTML), `fetched_at_utc`, `hash_sha256`, `work_item_id`, `run_id` |
| **seen_resources** | ingest | `0002_create_tables.sql` | Deduplication tracking for URLs | `seen_id` (PK), `source_system`, `resource_id`, `dedupe_key`, `first_seen_at`, `last_seen_at`, `occurrence_count` |

**Storage Pattern:**
- **Database:** Full response payloads stored in `ingest.IngestRecords.payload` (JSON/HTML as NVARCHAR(MAX))
- **Filesystem:** Optional parallel storage via `FileLakeWriter` at `lake/ingest/{source_system}/{source_name}/{resource_type}/{resource_id}_{timestamp}_{ingest_id}.json`
- **Linking:** `work_item_id` and `ingest_id` provide bidirectional traceability

---

### LLM Runtime Tables

| Table | Schema | Migration | Purpose | Key Columns |
|-------|--------|-----------|---------|-------------|
| **artifact** | llm | `0005_create_llm_tables.sql` | Artifacts written to lake (prompts, requests, responses, outputs) | `artifact_id` (PK), `run_id` (FK), `artifact_type` (request_json/response_json/evidence_bundle/prompt_text/parsed_output/raw_response), `lake_uri`, `content_sha256`, `byte_count`, `created_at` |
| **evidence_bundle** | llm | `0007_evidence_bundle_tables.sql` | Evidence bundles for LLM runs | `bundle_id` (PK), `policy` (JSON with bounding rules), `summary` (token counts, source counts), `lake_uri`, `created_at` |
| **evidence_item** | llm | `0007_evidence_bundle_tables.sql` | Individual evidence snippets within bundles | `item_id` (PK), `bundle_id` (FK), `evidence_type` (inline/lake_text/lake_http/sql_result), `source_identifier`, `content_preview`, `content_sha256`, `byte_count`, `seq` (ordering) |
| **run_evidence** | llm | `0007_evidence_bundle_tables.sql` | M:M linking runs to evidence bundles | `run_id` (FK), `bundle_id` (FK), `created_at` |
| **chunk** | llm | `0008_create_retrieval_tables.sql` | **DEPRECATED** — Chunked content (moved to vector schema) | `chunk_id` (PK), `source_page_id`, `chunk_index`, `content`, `content_hash`, `created_at` |
| **embedding** | llm | `0008_create_retrieval_tables.sql` | **DEPRECATED** — Embedding vectors (moved to vector schema) | `embedding_id` (PK), `chunk_id` (FK), `model_name`, `embedding_vector`, `created_at` |
| **retrieval** | llm | `0008_create_retrieval_tables.sql` | **DEPRECATED** — Retrieval query log (moved to vector schema) | `retrieval_id` (PK), `query_text`, `model_name`, `created_at` |
| **retrieval_hit** | llm | `0008_create_retrieval_tables.sql` | **DEPRECATED** — Retrieval results (moved to vector schema) | `hit_id` (PK), `retrieval_id` (FK), `chunk_id` (FK), `similarity_score`, `rank` |
| **source_registry** | llm | `0008_create_retrieval_tables.sql` | **DEPRECATED** — Source indexing status (moved to vector schema) | `registry_id` (PK), `source_page_id`, `status`, `created_at` |

**Important Note:** Migration `0024_deprecate_llm_vector_tables.sql` renamed old vector tables to `*_legacy` and established clean separation:
- **llm schema:** Chat/interrogation operations (text-in → text-out)
- **vector schema:** Embedding/retrieval operations (text-in → vectors-out)

---

### Vector / Embedding Tables

| Table | Schema | Migration | Purpose | Key Columns |
|-------|--------|-----------|---------|-------------|
| **embedding_space** | vector | `0023_create_vector_schema.sql` | Embedding model identity and configuration | `space_id` (PK), `provider`, `model_name`, `model_tag`, `model_digest`, `dimensions`, `distance_metric`, `created_at` — **UNIQUE** on (provider, model_name, model_tag, model_digest, dimensions) |
| **chunk** | vector | `0023_create_vector_schema.sql` | Canonical chunking unit | `chunk_id` (PK), `source_registry_id` (FK), `chunk_index`, `content`, `content_sha256`, `token_count`, `created_at` |
| **embedding** | vector | `0023_create_vector_schema.sql` | Vector embeddings with idempotency | `embedding_id` (PK), `chunk_id` (FK), `space_id` (FK), `embedding_vector` (binary), `content_version`, `created_at` — **UNIQUE** on (chunk_id, space_id, content_version) |
| **retrieval** | vector | `0023_create_vector_schema.sql` | Retrieval query audit log | `retrieval_id` (PK), `query_text`, `query_embedding` (binary), `space_id` (FK), `top_k`, `threshold`, `created_at` |
| **retrieval_hit** | vector | `0023_create_vector_schema.sql` | Ranked retrieval results | `hit_id` (PK), `retrieval_id` (FK), `chunk_id` (FK), `similarity_score`, `rank`, `created_at` |
| **source_registry** | vector | `0023_create_vector_schema.sql` | Indexed source tracking | `registry_id` (PK), `source_type`, `source_identifier`, `status` (indexed/pending/error), `last_indexed_at`, `chunk_count`, `embedding_space_ids` (JSON array) |

**Key Design Patterns:**
- **Embedding Space Identity:** Prevents mixing vectors from incompatible models via unique constraints
- **Content Versioning:** Embeddings track `content_version` for idempotent re-embedding
- **Separation of Concerns:** Vector schema isolated from chat/interrogation workflows

---

### Entity / Dimension Tables

| Table | Schema | Migration | Purpose | Key Columns |
|-------|--------|-----------|---------|-------------|
| **DimEntity** | dbo | (pre-existing) | Core entity dimension | `EntityID` (PK), `EntityName`, `PromotionState` (staged/candidate/adjudicated/promoted/suppressed/merged), `SourcePageId` (FK to sem.SourcePage), `PrimaryTypeInferred`, `TypeSetJsonInferred`, `PromotionDecisionUtc`, `PromotionDecidedBy` |
| **DimTag** | dbo | `0019_dim_tag_and_bridges.sql` | Canonical tag vocabulary | `TagID` (PK), `TagName`, `TagType` (category/topic/attribute/flag), `Visibility` (public/internal/deprecated), `GovernanceNotes` |
| **BridgeTagAssignment** | dbo | `0019_dim_tag_and_bridges.sql` | Polymorphic M:M tag assignments | `AssignmentID` (PK), `TargetType` (SourcePage/Entity/Chunk/Claim/Event), `TargetID`, `TagID` (FK), `AssignedAt`, `AssignedBy`, `Confidence` |
| **BridgeTagRelation** | dbo | `0019_dim_tag_and_bridges.sql` | Tag ontology relationships | `RelationID` (PK), `FromTagID` (FK), `ToTagID` (FK), `RelationType` (synonym/broader/narrower/related/replaces) |

**Entity Promotion Flow:**
- Entities start in `PromotionState = 'staged'` (from page classification)
- Move through `candidate` → `adjudicated` → `promoted` states
- `SourcePageId` links back to `sem.SourcePage` for traceability

---

### Semantic Staging Tables

| Table | Schema | Migration | Purpose | Key Columns |
|-------|--------|-----------|---------|-------------|
| **SourcePage** | sem | `0015_sem_source_page.sql` | Page identity and provenance | `PageID` (PK), `SourceSystem`, `ResourceID`, `Variant` (html/json), `Namespace`, `Title`, `URI`, `ContentHash`, `FetchedAt`, `IngestRecordID` (FK to ingest.IngestRecords) |
| **PageSignals** | sem | `0016_sem_page_signals.sql` | Extracted page cues (rules-based) | `SignalID` (PK), `PageID` (FK), `ContentFormat` (wikitext/html/json), `LeadExcerptText`, `LeadExcerptLen`, `InfoboxType`, `CategoryNames`, `IsDisambiguation`, `IsListPage`, `IsTimeline`, `IsRedirect` |
| **PageClassification** | sem | `0017_sem_page_classification.sql` | Type inference and lineage | `ClassificationID` (PK), `PageID` (FK), `PrimaryType` (PersonCharacter/LocationPlace/WorkMedia/EventConflict/Organization/Species/ObjectArtifact/Concept/TimePeriod/ReferenceMeta/TechnicalSitePage/Unknown), `TypeSet` (JSON multi-label with weights), `Confidence`, `Method` (rules/llm/hybrid/manual), `ClassifiedAt`, `LLMRunID` (FK to llm.run), `DescriptorSentence`, `NeedsReview` (boolean flag for QA queue) |

**Semantic Flow:**
1. **Ingestion:** `ingest.IngestRecords` → `sem.SourcePage` (page identity)
2. **Signals:** Rules-based extraction → `sem.PageSignals` (features for classification)
3. **Classification:** Rules or LLM → `sem.PageClassification` (type inference)
4. **Promotion:** High-confidence pages → `dbo.DimEntity` (promoted entities)

---

### Stored Procedures

| Procedure | Schema | Migration | Purpose |
|-----------|--------|-----------|---------|
| **usp_claim_next_job** | llm | `0006_llm_indexes_sprocs.sql` | Atomically claims next available job from queue with `READPAST` locking and backoff respect |
| **usp_complete_job** | llm | `0006_llm_indexes_sprocs.sql` | Marks job completed/failed with exponential backoff for retries |
| **usp_enqueue_job** | llm | `0006_llm_indexes_sprocs.sql` | Enqueues new LLM derivation job with priority and routing |
| **usp_create_run** | llm | `0006_llm_indexes_sprocs.sql` | Creates run record for job attempt with worker tracking |
| **usp_complete_run** | llm | `0006_llm_indexes_sprocs.sql` | Completes run with status, token counts, and error details |
| **usp_create_artifact** | llm | `0006_llm_indexes_sprocs.sql` | Records artifacts written to lake with integrity hashes |

**Design Patterns:**
- **Concurrency:** `WITH (READPAST, UPDLOCK)` prevents worker contention
- **Backoff:** `backoff_until` column implements exponential retry delays
- **Idempotency:** Procedures handle re-execution without side effects

---

### Views

#### Ingest Views (Migration `0010_acquisition_views.sql`)

| View | Schema | Purpose |
|------|--------|---------|
| **vw_recent_work_items** | ingest | Recent work queue items (last 7 days) |
| **vw_archive_work_items** | ingest | Completed/archived items (older than 7 days) |
| **vw_pending_failed_work_items** | ingest | Items needing retry (pending or failed) |
| **vw_latest_successful_fetch** | ingest | Most recent successful ingestion per resource |
| **vw_recent_ingest_records** | ingest | Recent raw records (last 30 days) |
| **vw_resources_with_both_variants** | ingest | Resources with both HTML and JSON variants |
| **vw_payload_availability** | ingest | Payload existence and size information |
| **vw_queue_summary_by_source** | ingest | Queue statistics grouped by source system |

#### Semantic Views (Migration `0020_sem_views.sql`)

| View | Schema | Purpose |
|------|--------|---------|
| **vw_CurrentPageClassification** | sem | Current classification per page (latest by ClassifiedAt) |
| **vw_PagesByType** | sem | Pages grouped by inferred primary type with counts |
| **vw_PagesNeedingReview** | sem | QA queue (NeedsReview = 1) for manual adjudication |
| **vw_TechnicalPages** | sem | Pages classified as TechnicalSitePage |
| **vw_EntityCandidates** | sem | Pages staged for entity promotion (high-confidence, valid types) |
| **vw_PromotedEntities** | dbo | Entities in 'promoted' state |
| **vw_StagedEntities** | dbo | Entities in 'staged' state |
| **vw_TagAssignments** | dbo | Active tag assignments with denormalized metadata |

---

## Python Code Inventory

### Runner / Orchestration Modules

| Module | Purpose | Entry Points | DB Tables Accessed |
|--------|---------|--------------|-------------------|
| **src/ingest/runner/ingest_runner.py** | Main ingestion orchestrator (dequeue → fetch → store → discover → update state) | `IngestRunner.run()` | `ingest.work_items`, `ingest.IngestRecords`, `ingest.ingest_runs` |
| **src/ingest/runner/concurrent_runner.py** | Concurrent worker pool with lease-based work claiming and heartbeats | `ConcurrentRunner.run()` | `ingest.work_items`, `ingest.worker_heartbeats` (implied) |
| **src/llm/runners/phase1_runner.py** | End-to-end LLM derive runner (claim job → build evidence → render prompt → call LLM → validate → write artifacts) | `Phase1Runner.run()`, `--loop` / `--once` CLI modes | `llm.job`, `llm.run`, `llm.artifact`, `llm.evidence_bundle`, `llm.run_evidence` |
| **src/llm/runners/derive_runner.py** | Stub implementation for general LLM derive operations | `DeriveRunner.run()` (stub) | TBD (stub phase) |

**Key Classes:**
- `IngestRunner`: Coordinates connectors, storage writers, and discovery logic
- `ConcurrentRunner`: Thread pool executor with worker leases and expiration
- `Phase1Runner`: Full LLM derivation pipeline with Ollama integration
- `RunnerConfig`: Dataclasses for dependency injection and environment-based config

---

### Work Queue Management

| Module | Purpose | Key Methods | DB Tables |
|--------|---------|-------------|-----------|
| **src/llm/storage/sql_job_queue.py** | Production SQL Server job queue with atomic claiming | `claim_next_job()`, `mark_succeeded()`, `mark_failed()`, `create_run()`, `create_artifact()` | `llm.job`, `llm.run`, `llm.artifact` via stored procedures |
| **src/ingest/core/state_store.py** | Abstract base class for work queue state management | `enqueue()`, `dequeue()`, `update_status()`, `get_work_item()`, `exists()`, `get_stats()` | (ABC — no direct access) |
| **src/ingest/state/sqlserver_store.py** | SQL Server implementation of state store | `enqueue()`, `dequeue()`, `update_status()`, lease management | `ingest.work_items`, `ingest.work_item_leases` (implied) |
| **src/llm/storage/sql_queue_store.py** | Stub SQL Server queue for derive jobs | `enqueue()`, `dequeue()` (stub) | `llm.derive_jobs` (planned) |

**Design Patterns:**
- **Stored Procedure Calls:** Production queues (`sql_job_queue.py`) use stored procedures for atomic operations
- **Thread-Local Connections:** Ingestion state store uses thread-local connections for concurrency safety
- **Lease-Based Claiming:** Workers claim items with expiration timestamps to prevent starvation

---

### Database Interaction (Store Modules)

| Module | Purpose | Key Methods | DB Tables |
|--------|---------|-------------|-----------|
| **src/vector/store.py** | Vector schema persistence | `save_embedding_space()`, `save_chunk()`, `save_embedding()`, `save_retrieval()`, `save_retrieval_hit()` | `vector.embedding_space`, `vector.chunk`, `vector.embedding`, `vector.retrieval`, `vector.retrieval_hit` |
| **src/semantic/store.py** | Semantic staging persistence | `upsert_source_page()`, `insert_page_signals()`, `upsert_page_classification()`, `tag_assignment()` | `sem.SourcePage`, `sem.PageSignals`, `sem.PageClassification`, `dbo.BridgeTagAssignment` |
| **src/ingest/storage/sqlserver.py** | Ingestion record writer | `write(record: IngestRecord)` | `ingest.IngestRecords` |

**Connection Patterns:**
- All stores use `pyodbc` with ODBC Driver 18 for SQL Server
- Connection strings built from environment variables (`*_SQLSERVER_HOST`, `*_SQLSERVER_DATABASE`, etc.)
- Parameterized queries to prevent SQL injection

---

### Contract Definitions

| Module | Purpose | Key Classes/Schemas |
|--------|---------|-------------------|
| **src/llm/contracts/phase1_contracts.py** | Job inputs, evidence bundles, structured outputs for Phase 1 | `Job`, `JobStatus` (enum), `EvidenceSnippet`, `EvidenceBundleV1`, `JobInputEnvelope` |
| **src/llm/contracts/evidence_contracts.py** | Evidence items, bundles, bounding policies | `EvidencePolicy`, `EvidenceBundle`, `EvidenceItem` |
| **src/llm/contracts/retrieval_contracts.py** | Chunk records, embedding records, retrieval queries | `ChunkingPolicy`, `ChunkRecord`, `EmbeddingRecord`, `RetrievalQuery`, `RetrievalResult` |
| **src/vector/contracts/models.py** | Vector schema runtime models | `EmbeddingSpace`, `VectorJob`, `VectorRun`, `VectorChunk`, `VectorEmbedding`, `VectorRetrieval` |
| **src/ingest/core/models.py** | Ingestion framework models | `WorkItem`, `IngestRecord`, `WorkItemStatus` (enum), `AcquisitionVariant` (enum) |
| **src/semantic/models.py** | Semantic staging models | `PageClassification`, `PageSignals`, `SourcePage`, `PageType` (enum), `ClassificationMethod` (enum), `PromotionState` (enum) |

**JSON Schemas (Validation):**
- `src/llm/contracts/page_classification_v1_schema.json` — Page classification output schema
- `src/llm/contracts/derived_output_schema.json` — General LLM output schema
- `src/llm/contracts/manifest_schema.json` — Manifest metadata schema
- `src/llm/contracts/sw_entity_facts_v1_output.json` — Star Wars entity facts schema (experimental)

**Validation Strategy:**
- **Fail-closed:** Invalid JSON/schema violations → job fails with error artifact
- **Retry Logic:** 3 attempts with exponential backoff (250ms → 1s)
- **Multiple Parsing Strategies:** Direct, stripped whitespace, embedded extraction

---

### Raw Content Storage/Retrieval

| Module | Purpose | Storage Location |
|--------|---------|------------------|
| **src/ingest/storage/file_lake.py** | File-based JSON data lake for ingestion records | `lake/ingest/{source_system}/{source_name}/{resource_type}/{resource_id}_{timestamp}_{ingest_id}.json` |
| **src/llm/storage/lake_writer.py** | Lake writer for LLM artifacts | `lake/llm_runs/{yyyy}/{mm}/{dd}/{run_id}/` with subdirectories for `request.json`, `response.json`, `evidence.json`, `prompt.txt`, `output.json` |
| **src/llm/evidence/builder.py** | Orchestrates evidence assembly from multiple sources | (No direct storage — reads from sources) |
| **src/llm/evidence/sources/lake_text_source.py** | Loads text evidence from lake artifact files | Reads from `lake/llm_runs/**/*.txt` |
| **src/llm/evidence/sources/lake_http_source.py** | Loads HTTP response evidence from lake | Reads from `lake/ingest/**/*.json` |
| **src/llm/evidence/sources/sql_result_source.py** | Loads evidence from SQL Server result sets | Executes queries against `ingest.*`, `sem.*` tables |

**Storage Patterns:**
- **Atomic Writes:** Use `tempfile.mkstemp()` + `os.replace()` for concurrent-safe writes
- **Content Hashing:** SHA-256 hashes computed for integrity verification
- **Path Conventions:** Date-based partitioning (`yyyy/mm/dd`) for LLM artifacts, hierarchical for ingestion
- **Deduplication:** `dedupe_key` (hash of source_system + resource_id + request_uri) prevents duplicate work items

---

## Storage Conventions

### Filesystem Lake Organization

#### Ingestion Lake

**Base Path:** Configured via `data_lake_base` parameter (default: `lake/ingest`)

**Structure:**
```
lake/ingest/
├── {source_system}/                  # e.g., "wookieepedia_api"
│   └── {source_name}/                # e.g., "fandom"
│       └── {resource_type}/          # e.g., "page", "category", "article"
│           └── {resource_id}_{variant}_{timestamp}_{work_item_id}_{ingest_id}.json
```

**Example:**
```
lake/ingest/wookieepedia_api/fandom/page/Luke_Skywalker_html_20260212_143022_a3f4b8c2_9d1e4f56.json
```

**Filename Components:**
- `resource_id`: Sanitized resource identifier (max 100 chars)
- `variant`: `html` or `json` (acquisition variant)
- `timestamp`: `yyyymmdd_HHMMSS` format
- `work_item_id`: First 8 chars of work item UUID
- `ingest_id`: First 8 chars of ingest record UUID

#### LLM Artifacts Lake

**Base Path:** Configured via `LAKE_ROOT` environment variable (default: `lake/llm_runs`)

**Structure:**
```
lake/llm_runs/
├── {yyyy}/                           # Year partition
│   └── {mm}/                         # Month partition
│       └── {dd}/                     # Day partition
│           └── {run_id}/             # Run UUID
│               ├── request.json      # Full Ollama request payload
│               ├── response.json     # Full Ollama response
│               ├── evidence.json     # Evidence bundle used
│               ├── prompt.txt        # Rendered prompt text
│               ├── output.json       # Parsed/validated output
│               ├── invalid_json_response.txt  # (on failure) Raw response
│               └── error_manifest.json        # (on failure) Error details
```

**Example:**
```
lake/llm_runs/2026/02/12/f8e3c7a1-9b2d-4c5e-a3f1-8d9e2f4c1a5b/
├── request.json
├── response.json
├── evidence.json
├── prompt.txt
└── output.json
```

---

### Database Storage

#### Payload Storage

**Current State:**
- **Primary Storage:** `ingest.IngestRecords.payload` (NVARCHAR(MAX)) stores full JSON/HTML responses
- **Size:** No explicit limit, but NVARCHAR(MAX) is effectively ~2GB per row
- **Encoding:** UTF-8 with `ensure_ascii=False` for non-ASCII characters

**Linking:**
- `work_item_id` (UUID) links work items to ingest records
- `hash_sha256` (64-char hex) provides content-addressable deduplication
- `fetched_at_utc` (DATETIME2) for temporal ordering

#### Artifact Storage

**Current State:**
- **Metadata Only:** `llm.artifact` table stores `lake_uri`, `content_sha256`, `byte_count` — not full content
- **Content Location:** Actual artifacts stored in filesystem lake at `lake_uri` path
- **Traceability:** `run_id` links artifacts back to job execution

---

## Configuration and Orchestration

### Environment Variables

**SQL Server Connection (Ingestion State Store):**
```bash
INGEST_SQLSERVER_HOST=localhost
INGEST_SQLSERVER_DATABASE=Holocron
INGEST_SQLSERVER_USER=sa
INGEST_SQLSERVER_PASSWORD=Password1!
INGEST_SQLSERVER_PORT=1433
INGEST_SQLSERVER_DRIVER=ODBC Driver 18 for SQL Server
INGEST_SQLSERVER_SCHEMA=ingest
```

**SQL Server Connection (LLM Job Queue):**
```bash
LLM_SQLSERVER_HOST=localhost
LLM_SQLSERVER_DATABASE=Holocron
LLM_SQLSERVER_USER=sa
LLM_SQLSERVER_PASSWORD=Password1!
LLM_SQLSERVER_PORT=1433
LLM_SQLSERVER_DRIVER=ODBC Driver 18 for SQL Server
LLM_SQLSERVER_SCHEMA=llm
```

**Ollama / LLM Configuration:**
```bash
OLLAMA_BASE_URL=http://ollama:11434          # From Docker Compose containers
OLLAMA_HOST_BASE_URL=http://localhost:11434  # From host machine
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_STREAM=false
OLLAMA_TEMPERATURE=0.0
```

**LLM Runner Configuration:**
```bash
WORKER_ID=llm-runner-local
POLL_SECONDS=10
LAKE_ROOT=lake/llm_runs
```

**File References:**
- `.env.example` — Template with all required variables and documentation
- `docker-compose.yml` — Service definitions with environment variable injection

---

### Docker Compose Services

**File:** `docker-compose.yml`

| Service | Image | Purpose | Ports | Volumes |
|---------|-------|---------|-------|---------|
| **sql2025** | `mcr.microsoft.com/mssql/server:2025-latest` | SQL Server Developer Edition | 1433:1433 | `W:/Docker/SQL2025/data`, `W:/Docker/SQL2025/log`, `W:/Docker/SQL2025/backup`, tmpfs for tempdb |
| **initdb** | `mcr.microsoft.com/mssql-tools` | Database initialization (runs migrations) | (none) | `./db/migrations` (read-only) |
| **seed** | Custom Dockerfile (`docker/Dockerfile.seed`) | Seed data loader | (none) | `./src` (read-only) |
| **ollama** | `ollama/ollama:latest` | Local LLM runtime | 127.0.0.1:11434:11434 | `ollama_data` (persisted models) |
| **llm-runner** | Custom Dockerfile (`docker/Dockerfile.seed`) | Phase 1 LLM derive runner | (none) | `./src` (read-only), `llm_lake` (artifact storage) |

**Startup Sequence:**
1. `sql2025` starts and runs healthcheck
2. `initdb` waits for SQL Server healthy, then runs migrations
3. `seed` waits for initdb completion, then loads seed data
4. `ollama` starts independently (no dependencies)
5. `llm-runner` waits for initdb + ollama healthy, then begins polling

**Healthchecks:**
- SQL Server: `bash -c "echo > /dev/tcp/localhost/1433"` (TCP connection test)
- Ollama: `bash -c 'echo > /dev/tcp/localhost/11434' || exit 1` (TCP connection test)

---

## Key Observations

### What Exists Today

✅ **Strong Foundations:**
- Mature ingestion framework with work queue, deduplication, and retry logic
- LLM job queue with atomic claiming, backoff, and stored procedure routing
- Semantic staging for page classification (rules + LLM hybrid)
- Vector schema for embedding space management and retrieval tracking
- File-based artifact lake with content hashing and integrity verification
- Docker Compose orchestration for local development

✅ **Operational Patterns:**
- Concurrent workers with lease-based claiming (prevents contention)
- Evidence assembly from multiple sources (inline, lake, SQL)
- Ollama integration with structured output and retry resilience
- Tag assignments for polymorphic relationships (SourcePage, Entity, Chunk)

### What's Missing for LLM Expansion Pipeline

❌ **Not Yet Implemented:**
- **Multi-entity extraction:** No support for extracting multiple entities from single source
- **Relationship/bridge creation:** No automated bridge table population from LLM outputs
- **Chunking strategy:** No production chunking pipeline (only stubs in vector schema)
- **JSON contract routing:** No stored procedures that accept JSON payloads and route to multiple tables
- **Dedupe/identity resolution:** No entity deduplication or merge logic
- **Confidence scoring:** PageClassification has confidence, but no systematic confidence thresholds or escalation
- **Human review hooks:** `NeedsReview` flag exists, but no UI or workflow tooling
- **Idempotency for LLM jobs:** No explicit idempotency keys or re-run safety
- **Backfill tooling:** No bulk re-processing or priority escalation utilities

---

## Related Documentation

- [02-data-model-map.md](02-data-model-map.md) — ERD and data warehouse design
- [03-workflow-and-runner-map.md](03-workflow-and-runner-map.md) — End-to-end process flows
- [04-functional-gap-analysis.md](04-functional-gap-analysis.md) — Gap analysis for LLM expansion
- [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md) — Implementation roadmap
- [../llm/phase1-runner.md](../llm/phase1-runner.md) — Phase 1 runner deep dive
- [../llm/contracts.md](../llm/contracts.md) — Contract definitions and validation
- [../REPO_STRUCTURE.md](../REPO_STRUCTURE.md) — High-level repository guide
