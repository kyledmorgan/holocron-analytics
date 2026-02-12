# Functional Gap Analysis

**Status:** Phase 0 — Documentation Only  
**Date:** 2026-02-12  
**Purpose:** Compare current capabilities against the LLM expansion pipeline requirements (north star goal) and identify gaps with actionable remediation paths.

---

## Overview

This document analyzes the gap between **what exists today** and **what's needed** for the LLM-driven knowledge expansion pipeline described in the problem statement. The north star goal is:

> Take an **Entity/Page** + **Source Page ID** + **raw content** (possibly chunked), "interrogate" the source with an LLM, and produce **multi-pronged outputs**: new or enriched dimension records, relationships via bridge tables, and potentially new tables/bridges when content requires it. Route outputs to correct tables via **stored procedures** using a **JSON input contract**, not direct ad hoc inserts.

---

## Gap Analysis Summary

### High-Level Capability Matrix

| Capability Area | Status | Readiness |
|----------------|--------|-----------|
| **Work Queue Reuse** | 🟢 Mature | LLM job queue operational, can be extended for new job types |
| **LLM Contract Definition** | 🟡 Partial | Page classification contract exists, but multi-entity/relationship contracts missing |
| **Chunking Strategy** | 🔴 Stub | Vector schema has chunk tables, but no production chunking pipeline |
| **Multi-Entity Extraction** | 🔴 Missing | No support for extracting N entities from single source |
| **Relationship/Bridge Creation** | 🔴 Missing | No entity-entity, entity-event, or entity-work bridges populated |
| **Stored Procedure Routing** | 🔴 Missing | No stored procedures that accept JSON payloads and route to multiple tables |
| **Observability** | 🟡 Partial | Logging exists, but no structured metrics, tracing, or dashboards |
| **Idempotency** | 🟡 Partial | Ingest queue idempotent, LLM queue has basic retry, but no dedupe for multi-entity outputs |
| **Governance** | 🟡 Partial | Confidence scoring in PageClassification, but no human review UI or escalation workflow |

**Legend:**
- 🟢 **Green:** Mature, production-ready
- 🟡 **Yellow:** Partial implementation or scaffolded
- 🔴 **Red:** Missing or stub-only

---

## Detailed Gap Analysis

### 1. Work Queue Reuse for LLM Jobs

#### Current State

✅ **Exists:**
- `llm.job` table with status management (NEW/RUNNING/SUCCEEDED/FAILED/DEADLETTER)
- Stored procedures for atomic job claiming (`llm.usp_claim_next_job`)
- Backoff logic for exponential retry
- `Phase1Runner` operational for page classification jobs

**Evidence:**
- File: `db/migrations/0005_create_llm_tables.sql` (llm.job table definition)
- File: `db/migrations/0006_llm_indexes_sprocs.sql` (stored procedures)
- File: `src/llm/runners/phase1_runner.py` (runner implementation)

#### Gap

❌ **Missing:**
- **Job Type Extensibility:** Current system supports `page_classification` job type. Need formalized approach for adding new job types (e.g., `entity_extraction`, `relationship_extraction`, `entity_merge`)
- **Job Routing Logic:** No dispatcher that routes job types to appropriate prompt templates and output handlers
- **Job Priority Management:** Priority column exists but not actively used (no utility to escalate priority, no SLA-based auto-escalation)

#### Impact

**Medium** — Can enqueue new job types manually, but no structured framework for adding new LLM operations

#### Recommended Solution

- **Create Job Type Registry:** `src/llm/jobs/registry.py` with job type definitions, prompt templates, output schemas, and handlers
- **Implement Dispatcher:** `src/llm/runners/dispatcher.py` that routes job types to handlers
- **Add Priority Utilities:** `src/llm/utils/priority.py` with functions to bump priority, SLA checks, and auto-escalation

**Effort:** Small (S)  
**Dependencies:** None

---

### 2. LLM Contract Definition (Input/Output)

#### Current State

✅ **Exists:**
- **Page Classification Contract:**
  - Input: `JobInputEnvelope` with `job_type`, `source_page_id`, `evidence_refs`
  - Output: `PageClassificationV1` with `PrimaryType`, `TypeSet`, `Confidence`, `DescriptorSentence`
  - JSON Schema: `src/llm/contracts/page_classification_v1_schema.json`
- **Evidence Bundle Contract:** `EvidenceBundleV1` with bounding policies and source metadata
- **Validation:** Fail-closed validation with multi-strategy parsing

**Evidence:**
- File: `src/llm/contracts/phase1_contracts.py`
- File: `src/llm/contracts/page_classification_v1_schema.json`

#### Gap

❌ **Missing:**
- **Multi-Entity Extraction Contract:** No schema for extracting N entities from single source
  - Example need: "List of Jedi" page → extract 50 PersonCharacter entities
  - Required fields: Entity name, type, confidence, extracted attributes (e.g., species, homeworld)
- **Relationship Extraction Contract:** No schema for entity-entity relationships
  - Example need: "Luke Skywalker is a member of Rebel Alliance"
  - Required fields: From entity, to entity, relationship type, temporal bounds (start/end date), confidence
- **Entity Merge Contract:** No schema for resolving duplicate entities
  - Example need: "Luke Skywalker" (entity_id=123) is same as "Luke Skywalker/Legends" (entity_id=456)
  - Required fields: Master entity ID, duplicate entity IDs, merge reason, confidence
- **Event/Work Extraction Contracts:** No schemas for extracting events or works

#### Impact

**High** — Cannot implement multi-entity or relationship extraction without defined contracts

#### Recommended Solution

- **Create Multi-Entity Contract:** `src/llm/contracts/entity_extraction_v1_schema.json`
  - Output: Array of `EntityRecord` with `name`, `type`, `confidence`, `attributes` (JSON)
- **Create Relationship Contract:** `src/llm/contracts/relationship_extraction_v1_schema.json`
  - Output: Array of `RelationshipRecord` with `from_entity`, `to_entity`, `relation_type`, `confidence`
- **Create Merge Contract:** `src/llm/contracts/entity_merge_v1_schema.json`
  - Output: `MergeDecision` with `master_entity_id`, `duplicate_entity_ids`, `merge_reason`
- **Versioning Strategy:** Use MAJOR.MINOR.PATCH versioning for all contracts (e.g., `entity_extraction_v1.0.0`)

**Effort:** Medium (M)  
**Dependencies:** Job Type Registry (#1)

---

### 3. Chunking Strategy + Traceability

#### Current State

✅ **Exists:**
- **Vector Schema:** `vector.chunk` table with `chunk_index`, `content`, `content_sha256`, `token_count`
- **Source Registry:** `vector.source_registry` tracks indexed sources and chunk counts
- **Chunking Models:** `src/vector/contracts/models.py` defines `VectorChunk` dataclass

❌ **Missing:**
- **Production Chunking Pipeline:** No active runner that chunks sources and writes to `vector.chunk`
- **Chunking Strategy Configuration:** No configurable chunk size, overlap, or boundary detection (e.g., sentence boundaries, paragraph boundaries)
- **Traceability Back to Source:** `vector.chunk` has `source_registry_id` FK, but no direct link to `ingest.IngestRecords` or `sem.SourcePage`

**Evidence:**
- File: `db/migrations/0023_create_vector_schema.sql` (vector.chunk table)
- File: `src/vector/contracts/models.py` (VectorChunk model)

#### Gap

❌ **Missing:**
- **Chunker Module:** No `src/vector/chunker.py` with configurable chunking strategies (fixed-size, sentence-based, semantic)
- **Chunk Job Type:** No `vector.job` with `job_type = 'CHUNK_SOURCE'` actively enqueued
- **Chunk-to-Source Linking:** No clear linkage from chunk back to original `ingest.IngestRecords.ingest_id`

#### Impact

**Medium** — Cannot use chunking for LLM evidence assembly or vector retrieval without production pipeline

#### Recommended Solution

- **Implement Chunker:** `src/vector/chunker.py` with:
  - Fixed-size chunking (e.g., 1000 tokens with 200-token overlap)
  - Sentence-boundary-aware chunking
  - Configurable via `ChunkingPolicy` dataclass
- **Create Chunk Runner:** `src/vector/runners/chunk_runner.py` that:
  - Dequeues `vector.job` with `job_type = 'CHUNK_SOURCE'`
  - Loads source content from `ingest.IngestRecords` or lake
  - Chunks content and writes to `vector.chunk`
  - Updates `vector.source_registry` status
- **Add Source Traceability:** Extend `vector.chunk` with:
  - `source_page_id` FK to `sem.SourcePage` (for page sources)
  - `ingest_record_id` FK to `ingest.IngestRecords` (for raw HTTP sources)

**Effort:** Medium (M)  
**Dependencies:** None

---

### 4. Multi-Entity Extraction + Dedupe/Identity Resolution

#### Current State

✅ **Exists:**
- **Entity Dimension:** `dbo.DimEntity` with promotion states
- **Entity Promotion:** Pages can be promoted to entities (1:1 mapping)

❌ **Missing:**
- **Multi-Entity Extraction:** No code path for extracting N entities from single source
- **Identity Resolution:** No fuzzy matching or LLM-based dedupe for entity names
- **Entity Merge Logic:** No code to merge duplicate entities (update FKs, set `PromotionState = 'merged'`)

**Evidence:**
- File: `db/migrations/0018_dim_entity_promotion.sql` (PromotionState column)
- File: `src/semantic/store.py` (single-entity promotion logic)

#### Gap

❌ **Missing:**
- **Batch Entity Insertion:** No stored procedure or utility to insert N entities in single transaction
- **Dedupe Strategy:** No algorithm for:
  - Exact match (case-insensitive name comparison)
  - Fuzzy match (Levenshtein distance, phonetic matching)
  - LLM-based identity resolution (call LLM to decide if "Luke Skywalker" == "Luke Skywalker (Jedi)")
- **Merge Workflow:** No code to:
  - Identify duplicate entity candidates
  - Enqueue merge jobs for LLM adjudication
  - Execute merge (update FKs, mark merged entity as suppressed)

#### Impact

**High** — Cannot build "List of X" extraction pipeline without multi-entity support and dedupe

#### Recommended Solution

**Phase 1: Multi-Entity Extraction**
- **Create Stored Procedure:** `dbo.usp_batch_insert_entities`
  - Input: JSON array of `EntityRecord` (name, type, attributes, source_page_id, llm_run_id)
  - Output: Array of inserted `EntityID` values
  - Logic: Insert N entities in single transaction, set `PromotionState = 'staged'`
- **Create Entity Writer:** `src/semantic/entity_writer.py` that calls stored procedure

**Phase 2: Identity Resolution**
- **Exact Match:** Query `DimEntity` for exact name match (case-insensitive)
- **Fuzzy Match:** Use Python `difflib` or `fuzzywuzzy` for Levenshtein distance
- **LLM Adjudication:** If fuzzy match score 0.7-0.9, enqueue LLM job with contract:
  - Input: Candidate entity names, attributes
  - Output: `MergeDecision` (same_entity=true/false, confidence)

**Phase 3: Merge Execution**
- **Create Merge Stored Procedure:** `dbo.usp_merge_entities`
  - Input: Master entity ID, duplicate entity IDs
  - Logic: Update all FKs to point to master, set duplicates to `PromotionState = 'merged'`

**Effort:** Large (L)  
**Dependencies:** Multi-Entity Contract (#2), Stored Procedure Routing (#6)

---

### 5. Relationship/Bridge Creation Patterns

#### Current State

✅ **Exists:**
- **Tag Assignment Bridge:** `dbo.BridgeTagAssignment` with polymorphic target types (SourcePage, Entity, Chunk)
- **Tag Relation Bridge:** `dbo.BridgeTagRelation` for tag ontology (synonym, broader, narrower)

❌ **Missing:**
- **Entity-Entity Relationships:** No `dbo.BridgeEntityRelation` table
- **Entity-Event Relationships:** No `dbo.DimEvent` or `dbo.BridgeEntityEvent` tables
- **Entity-Work Relationships:** No `dbo.DimWork` or `dbo.BridgeEntityWork` tables

**Evidence:**
- File: `db/migrations/0019_dim_tag_and_bridges.sql` (BridgeTagAssignment table)

#### Gap

❌ **Missing:**
- **Relationship Tables:** See "Missing Relationships" section in `02-data-model-map.md`
- **Relationship Insertion Logic:** No stored procedures or utilities to insert relationships
- **Relationship Extraction Runner:** No LLM runner that extracts relationships from text

#### Impact

**High** — Cannot capture entity relationships, events, or work appearances without these tables

#### Recommended Solution

**Phase 1: Create Tables**
- **Migration:** `db/migrations/0025_create_relationship_bridges.sql`
  - `dbo.BridgeEntityRelation` (FromEntityID, ToEntityID, RelationType, StartDate, EndDate, Confidence, SourceLLMRunID)
  - `dbo.DimEvent` (EventID, EventName, EventType, EventDate, EventLocation, EventDescription)
  - `dbo.BridgeEntityEvent` (EntityID, EventID, ParticipationRole, Confidence)
  - `dbo.DimWork` (WorkID, WorkName, WorkType, ReleaseDate, CanonStatus)
  - `dbo.BridgeEntityWork` (EntityID, WorkID, AppearanceType, Confidence)

**Phase 2: Create Insertion Stored Procedures**
- `dbo.usp_insert_entity_relation` (single relationship)
- `dbo.usp_batch_insert_entity_relations` (N relationships from JSON array)
- `dbo.usp_insert_entity_event` (entity-event linkage)

**Phase 3: Create Extraction Runner**
- **Job Type:** `relationship_extraction`
- **Contract:** Input = source_page_id, Output = Array of RelationshipRecord
- **Prompt Template:** `src/llm/prompts/relationship_extraction.py`
- **Handler:** `src/llm/handlers/relationship_handler.py` that calls batch insertion stored procedure

**Effort:** Large (L)  
**Dependencies:** Multi-Entity Contract (#2), Job Type Registry (#1)

---

### 6. Stored Procedure Routing from JSON Payload

#### Current State

✅ **Exists:**
- **LLM Job Queue Stored Procedures:** `llm.usp_claim_next_job`, `llm.usp_complete_job`, etc. (queue management only)
- **Parameterized Queries:** All SQL interactions use parameterized queries (no SQL injection risk)

❌ **Missing:**
- **JSON-to-Table Routing:** No stored procedures that accept JSON payload and route to multiple tables
- **Transactional Multi-Table Writes:** No single stored procedure that inserts entities + relationships + tags in one transaction

**Evidence:**
- File: `db/migrations/0006_llm_indexes_sprocs.sql` (queue management stored procedures)

#### Gap

❌ **Missing:**
- **Routing Stored Procedures:** Examples needed:
  - `dbo.usp_process_entity_extraction_output`
    - Input: JSON array of `EntityRecord` + `RelationshipRecord`
    - Output: Inserted entity IDs and relationship IDs
    - Logic: Parse JSON, insert entities, insert relationships, link to LLM run
  - `dbo.usp_process_event_extraction_output`
    - Input: JSON with event details + entity participants
    - Output: Inserted event ID and entity-event linkages
  - `dbo.usp_process_page_classification_output`
    - Input: JSON with page classification result
    - Output: Updated `sem.PageClassification` row

#### Impact

**High** — Without stored procedure routing, Python code must orchestrate multi-table writes (more error-prone, less atomic)

#### Recommended Solution

**Phase 1: Create Template Stored Procedure**
- **Example:** `dbo.usp_process_entity_extraction_output`
  ```sql
  CREATE PROCEDURE dbo.usp_process_entity_extraction_output
      @InputJson NVARCHAR(MAX),
      @LLMRunID UNIQUEIDENTIFIER,
      @SourcePageID UNIQUEIDENTIFIER
  AS
  BEGIN
      BEGIN TRANSACTION;
      
      -- Parse JSON into temp table
      DECLARE @Entities TABLE (
          Name NVARCHAR(500),
          Type NVARCHAR(100),
          Confidence DECIMAL(5,4),
          Attributes NVARCHAR(MAX)
      );
      
      INSERT INTO @Entities (Name, Type, Confidence, Attributes)
      SELECT 
          JSON_VALUE(value, '$.name'),
          JSON_VALUE(value, '$.type'),
          JSON_VALUE(value, '$.confidence'),
          JSON_QUERY(value, '$.attributes')
      FROM OPENJSON(@InputJson, '$.entities');
      
      -- Insert entities
      INSERT INTO dbo.DimEntity (EntityName, PrimaryTypeInferred, PromotionState, SourcePageId, AdjudicationRunId)
      OUTPUT INSERTED.EntityID
      SELECT Name, Type, 'staged', @SourcePageID, @LLMRunID
      FROM @Entities;
      
      COMMIT TRANSACTION;
  END
  ```

**Phase 2: Implement in Python**
- **Handler:** `src/llm/handlers/entity_extraction_handler.py`
  ```python
  def handle_output(run_id, output_json, source_page_id):
      conn = get_db_connection()
      cursor = conn.cursor()
      cursor.execute(
          "EXEC dbo.usp_process_entity_extraction_output @InputJson=?, @LLMRunID=?, @SourcePageID=?",
          json.dumps(output_json), run_id, source_page_id
      )
      conn.commit()
  ```

**Phase 3: Error Handling**
- Catch SQL exceptions in Python, write error artifacts to lake
- Retry on transient errors (deadlock, timeout)
- Dead-letter on permanent errors (constraint violation, invalid JSON)

**Effort:** Medium (M)  
**Dependencies:** Multi-Entity Contract (#2), Relationship Tables (#5)

---

### 7. Observability (Logging, Metrics, Run History)

#### Current State

✅ **Exists:**
- **Plaintext Logging:** `logs/ingest_{timestamp}.log`, `logs/llm_runner_{timestamp}.log`
- **Run History:** `llm.run` table tracks all LLM executions with token counts, duration, errors
- **Queue Views:** `ingest.vw_queue_summary_by_source`, `sem.vw_PagesNeedingReview`

❌ **Missing:**
- **Structured Logging:** Logs are plaintext, not JSON (harder to parse, no log aggregation)
- **Metrics Export:** No Prometheus metrics endpoint, no time-series metrics
- **Distributed Tracing:** No correlation IDs across runner → LLM → storage
- **Dashboards:** No Grafana dashboards for queue health, LLM performance, error rates

**Evidence:**
- File: `src/llm/runners/phase1_runner.py` (plaintext logging via Python `logging` module)
- File: `db/migrations/0005_create_llm_tables.sql` (llm.run table for run history)

#### Gap

❌ **Missing:**
- **Structured Logging:** Need JSON logs with fields: `timestamp`, `level`, `message`, `correlation_id`, `job_id`, `run_id`, `worker_id`, `duration_ms`
- **Metrics Instrumentation:** Need:
  - Counter: `llm_runs_total{status="succeeded|failed"}`
  - Histogram: `llm_duration_seconds{job_type="page_classification"}`
  - Gauge: `llm_queue_depth{status="NEW|RUNNING"}`
- **Tracing:** Need correlation ID that flows: job enqueue → job claim → LLM call → artifact write
- **Alerting:** No alerts on:
  - Queue depth > threshold (backlog building up)
  - Error rate > threshold (LLM degraded)
  - Dead-letter queue growing (manual intervention needed)

#### Impact

**Medium** — System operational without metrics, but troubleshooting harder and no proactive alerts

#### Recommended Solution

**Phase 1: Structured Logging**
- **Add Python Package:** `python-json-logger` or `structlog`
- **Configure Logging:** Output JSON logs with correlation IDs
  ```python
  import logging
  from pythonjsonlogger import jsonlogger
  
  handler = logging.FileHandler("logs/llm_runner.json")
  formatter = jsonlogger.JsonFormatter()
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  ```

**Phase 2: Metrics Export**
- **Add Prometheus Client:** `prometheus_client` Python package
- **Instrument Code:** Add counters, histograms, gauges
  ```python
  from prometheus_client import Counter, Histogram
  
  llm_runs_total = Counter('llm_runs_total', 'Total LLM runs', ['status'])
  llm_duration_seconds = Histogram('llm_duration_seconds', 'LLM duration', ['job_type'])
  
  # In runner:
  start_time = time.time()
  # ... process job ...
  llm_duration_seconds.labels(job_type).observe(time.time() - start_time)
  llm_runs_total.labels(status='succeeded').inc()
  ```
- **Expose Endpoint:** HTTP endpoint at `:9090/metrics` for Prometheus scraping

**Phase 3: Dashboards**
- **Grafana Dashboards:** Import pre-built dashboards or create custom:
  - Queue health: Depth by status, backlog age
  - LLM performance: Duration percentiles (p50, p95, p99), token usage
  - Error rates: Failure rate by job type, dead-letter queue size

**Effort:** Medium (M)  
**Dependencies:** None

---

### 8. Idempotency + Re-Runs + Backfills

#### Current State

✅ **Exists:**
- **Ingestion Idempotency:** `ingest.work_items.dedupe_key` prevents duplicate enqueues
- **LLM Retry Logic:** Backoff and max attempts prevent infinite retries
- **Content Versioning:** `vector.embedding.content_version` supports idempotent re-embedding

❌ **Missing:**
- **LLM Job Idempotency Keys:** No idempotency key for LLM jobs (can enqueue duplicate jobs for same source)
- **Re-Run Safety:** No check to prevent re-processing already-processed entities
- **Backfill Utilities:** No CLI or UI to bulk re-enqueue jobs for specific entity types or date ranges

**Evidence:**
- File: `db/migrations/0002_create_tables.sql` (dedupe_key in work_items)
- File: `db/migrations/0023_create_vector_schema.sql` (content_version in embedding)

#### Gap

❌ **Missing:**
- **LLM Job Dedupe Key:** Need `llm.job` to have:
  - `dedupe_key` column (hash of job_type + source_page_id + contract_version)
  - Unique constraint to prevent duplicate enqueues
- **Re-Run Detection:** Before enqueuing entity extraction job, check if entity already extracted for that source
- **Backfill CLI:** Need `src/llm/cli/backfill.py` with commands:
  - `backfill entities --entity-type=PersonCharacter --confidence<0.8` (re-process low-confidence entities)
  - `backfill relationships --date-range=2024-01-01..2024-12-31` (re-extract relationships)

#### Impact

**Medium** — Can manually avoid duplicate enqueues, but no automated safeguards or backfill tooling

#### Recommended Solution

**Phase 1: Idempotency Key**
- **Migration:** Add `dedupe_key` column to `llm.job`
  ```sql
  ALTER TABLE llm.job ADD dedupe_key NVARCHAR(800);
  CREATE UNIQUE INDEX UX_job_dedupe_key ON llm.job(dedupe_key) WHERE dedupe_key IS NOT NULL;
  ```
- **Compute Key:** `hash(job_type + source_page_id + contract_version)`
- **Enforce in Enqueue:** `llm.usp_enqueue_job` checks for existing dedupe_key before inserting

**Phase 2: Re-Run Safety**
- **Check Before Enqueue:** Query `dbo.FactEntityExtraction` for existing extraction:
  ```sql
  SELECT COUNT(*) FROM dbo.FactEntityExtraction
  WHERE SourcePageID = @source_page_id AND ContractVersion = @contract_version;
  ```
- **If Exists:** Skip enqueue or flag as re-run (with `is_rerun` boolean column)

**Phase 3: Backfill CLI**
- **Create CLI Module:** `src/llm/cli/backfill.py`
  ```python
  @click.command()
  @click.option('--entity-type', help='Entity type to re-process')
  @click.option('--confidence-threshold', type=float, help='Confidence threshold')
  def backfill_entities(entity_type, confidence_threshold):
      # Query low-confidence entities
      # Enqueue LLM jobs for re-classification
      pass
  ```

**Effort:** Small (S)  
**Dependencies:** None

---

### 9. Governance: Confidence Scoring, Human Review Hooks

#### Current State

✅ **Exists:**
- **Confidence Scoring:** `sem.PageClassification.Confidence` (0.0-1.0 scale)
- **Review Queue:** `sem.PageClassification.NeedsReview` boolean flag
- **Review View:** `sem.vw_PagesNeedingReview` for QA queue

❌ **Missing:**
- **Confidence Thresholds:** No formalized thresholds for auto-promotion vs manual review
- **Human Review UI:** No web UI or CLI tool for reviewing flagged pages
- **Approval Workflow:** No code to mark entities as "adjudicated" after human review
- **Audit Trail:** No history of human decisions (who approved, when, why)

**Evidence:**
- File: `db/migrations/0017_sem_page_classification.sql` (NeedsReview column)
- File: `db/migrations/0020_sem_views.sql` (vw_PagesNeedingReview view)

#### Gap

❌ **Missing:**
- **Threshold Configuration:** Need environment variable or config file:
  ```yaml
  governance:
    auto_promote_threshold: 0.9  # Confidence >= 0.9 → auto-promote
    manual_review_threshold: 0.7  # Confidence < 0.7 → manual review required
  ```
- **Review UI:** Need web interface (or CLI) to:
  - Display page content, LLM classification, confidence
  - Allow human to approve/reject/override
  - Capture decision rationale
- **Approval Stored Procedure:** `dbo.usp_adjudicate_entity`
  - Input: EntityID, Decision (approve/reject/override), DecidedBy, Reason
  - Output: Update `PromotionState` to 'adjudicated', record decision timestamp

#### Impact

**Low** — System functional without human review workflow, but governance/audit requirements may mandate it

#### Recommended Solution

**Phase 1: Formalize Thresholds**
- **Configuration:** Add to `.env` or `config/governance.yaml`
- **Apply in Code:** In entity promotion logic:
  ```python
  if confidence >= AUTO_PROMOTE_THRESHOLD:
      promotion_state = 'promoted'
  elif confidence >= MANUAL_REVIEW_THRESHOLD:
      promotion_state = 'candidate'
      needs_review = True
  else:
      promotion_state = 'suppressed'
  ```

**Phase 2: Build Review UI (Optional)**
- **Web App:** Simple Flask/FastAPI app with:
  - `/review/queue` — List pages needing review (paginated)
  - `/review/{page_id}` — Display page details, LLM output, approve/reject buttons
  - POST `/review/{page_id}/adjudicate` — Submit decision
- **CLI Alternative:** `python -m src.llm.cli.review` for terminal-based review

**Phase 3: Audit Trail**
- **Create Audit Table:** `dbo.AuditEntityAdjudication`
  - Columns: AdjudicationID, EntityID, Decision, DecidedBy, DecidedAt, Reason
- **Log All Decisions:** Every adjudication writes to audit table

**Effort:** Medium (M) — UI development is largest component  
**Dependencies:** None

---

## Summary Table: Capability vs Gap

| # | Capability Area | Current State | Gap | Impact | Solution Direction | Effort | Dependencies |
|---|----------------|---------------|-----|--------|-------------------|--------|--------------|
| 1 | **Work Queue Reuse** | LLM job queue operational | No job type registry or dispatcher | Medium | Create job type registry + dispatcher | S | None |
| 2 | **LLM Contract Definition** | Page classification contract exists | Multi-entity, relationship, merge contracts missing | High | Define JSON schemas for new contracts | M | #1 |
| 3 | **Chunking Strategy** | Vector schema scaffolded | No production chunking pipeline | Medium | Implement chunker + chunk runner | M | None |
| 4 | **Multi-Entity Extraction** | Single-entity promotion works | No N-entity extraction or dedupe | High | Batch insertion stored proc + dedupe logic | L | #2, #6 |
| 5 | **Relationship/Bridge Creation** | Tag assignment bridge exists | No entity-entity, entity-event, entity-work bridges | High | Create bridge tables + insertion stored procs | L | #1, #2 |
| 6 | **Stored Procedure Routing** | Queue management stored procs exist | No JSON-to-table routing stored procs | High | Template stored proc + Python handler | M | #2, #5 |
| 7 | **Observability** | Plaintext logging + run history table | No structured metrics, tracing, dashboards | Medium | Add Prometheus metrics + JSON logging | M | None |
| 8 | **Idempotency** | Ingestion dedupe + LLM retry logic | No LLM job dedupe key or backfill CLI | Medium | Add dedupe_key to llm.job + backfill utility | S | None |
| 9 | **Governance** | Confidence scoring + review flag exist | No review UI, approval workflow, audit trail | Low | Formalize thresholds + review UI + audit table | M | None |

**Effort Key:**
- **S (Small):** 1-3 days, single developer
- **M (Medium):** 1-2 weeks, single developer or pair
- **L (Large):** 2-4 weeks, team effort

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **LLM JSON Parsing Failures** | Medium | Medium | Already mitigated with multi-strategy parsing + retry logic |
| **Database Deadlocks** | Low | Medium | Use stored procedures with proper locking hints (READPAST, UPDLOCK) |
| **Entity Dedupe Accuracy** | High | High | Use phased approach: exact match → fuzzy match → LLM adjudication |
| **Backfill Performance** | Medium | Low | Chunk backfill jobs into batches, use priority queue to avoid starvation |
| **Storage Scalability** | Low | Medium | Monitor `ingest.IngestRecords` table size, archive old records to cold storage |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Worker Crashes** | Medium | Low | Already mitigated with lease expiration + auto-release |
| **Queue Backlog** | Medium | Medium | Implement queue depth monitoring + alerting |
| **Dead-Letter Queue Growth** | Low | Medium | Periodic manual review + re-enqueue utilities |
| **Human Review Bottleneck** | High | Low | Set high auto-promote threshold (0.9+) to minimize manual review volume |

---

## Decision Points (Must Choose Before Implementation)

### 1. JSON Schema for LLM Outputs

**Options:**
- **A) Strict Schema:** Pre-define all entity types and attributes (e.g., PersonCharacter has `birthdate`, `species`, `homeworld`)
- **B) Flexible Schema:** Use JSON `attributes` field for any key-value pairs (less typed, easier to extend)
- **C) Hybrid:** Core attributes typed, extended attributes in JSON

**Recommendation:** **C) Hybrid** — Balance between type safety and flexibility

---

### 2. Where Chunk Artifacts Live (DB vs File)

**Options:**
- **A) Database:** Store chunk content in `vector.chunk.content` (NVARCHAR(MAX))
- **B) Filesystem Lake:** Store chunks in lake files, DB stores only metadata + URIs
- **C) Hybrid:** Short chunks (<4KB) in DB, long chunks in lake

**Recommendation:** **A) Database** — Simplifies retrieval queries, avoids file I/O overhead for vector search

---

### 3. Identity/Dedupe Strategy

**Options:**
- **A) Exact Match Only:** Case-insensitive name comparison (fast, low accuracy)
- **B) Fuzzy Match:** Levenshtein distance + phonetic matching (medium accuracy)
- **C) LLM Adjudication:** Call LLM to decide if entities are duplicates (high accuracy, slow, costly)
- **D) Phased:** Exact match → fuzzy match → LLM adjudication (only for ambiguous cases)

**Recommendation:** **D) Phased** — Minimize LLM calls, maximize accuracy

---

### 4. Stored Proc Routing Design (One Proc vs Many)

**Options:**
- **A) One Universal Proc:** `dbo.usp_process_llm_output(@JobType, @OutputJson)` — single proc dispatches to internal logic
- **B) Many Specific Procs:** `dbo.usp_process_entity_extraction_output`, `dbo.usp_process_relationship_extraction_output`, etc.
- **C) Hybrid:** One entry proc that calls specific procs internally

**Recommendation:** **B) Many Specific Procs** — Clearer contracts, easier to test, avoid monolithic stored procedure

---

### 5. Priority Escalation Workflow/Tooling

**Options:**
- **A) Manual:** DBA manually updates `priority` column in SQL
- **B) CLI Utility:** `python -m src.llm.cli.priority bump --entity-type=PersonCharacter`
- **C) Automated SLA:** Background job auto-escalates priority if job queued >N hours
- **D) UI-Driven:** Web UI with "Escalate Priority" button

**Recommendation:** **B) CLI Utility** + **C) Automated SLA** — Balance manual control and automation

---

## Related Documentation

- [01-current-state-inventory.md](01-current-state-inventory.md) — Repository and SQL artifact inventory
- [02-data-model-map.md](02-data-model-map.md) — Data model and ERD
- [03-workflow-and-runner-map.md](03-workflow-and-runner-map.md) — Workflow and runner orchestration
- [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md) — Phased implementation plan
- [../llm/vision-and-roadmap.md](../llm/vision-and-roadmap.md) — Long-term vision for LLM subsystem
