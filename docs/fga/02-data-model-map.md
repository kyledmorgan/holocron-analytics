# Data Model Map

**Status:** Phase 0 — Documentation Only  
**Date:** 2026-02-12  
**Purpose:** Comprehensive data model overview for Holocron Analytics with emphasis on LLM expansion pipeline readiness.

---

## Overview

This document provides a data warehouse-style view of the Holocron Analytics database, including:
- **Dimension tables** (entities, tags, embedding spaces)
- **Fact tables** (ingestion records, LLM runs, retrieval queries)
- **Bridge tables** (tag assignments, tag relations, run-evidence linkage)
- **Staging tables** (semantic classification, page signals)
- **Queue tables** (work items, LLM jobs, vector jobs)

The model is organized into **four logical schemas** with clear separation of concerns:
1. **ingest** — Raw data acquisition and work queue
2. **llm** — Chat/interrogation runtime (text-in → text-out)
3. **vector** — Embedding/retrieval runtime (text-in → vectors-out)
4. **sem** — Semantic staging and classification
5. **dbo** — Core dimensional model (entities, tags)

---

## High-Level Architecture

### Schema Relationships

```mermaid
graph TB
    subgraph "Acquisition Layer"
        WI[ingest.work_items<br/>Work Queue]
        IR[ingest.IngestRecords<br/>Raw HTTP Responses]
    end
    
    subgraph "Semantic Staging Layer"
        SP[sem.SourcePage<br/>Page Identity]
        PS[sem.PageSignals<br/>Extracted Cues]
        PC[sem.PageClassification<br/>Type Inference]
    end
    
    subgraph "LLM Runtime Layer"
        LJ[llm.job<br/>LLM Job Queue]
        LR[llm.run<br/>Job Executions]
        LA[llm.artifact<br/>Lake Artifacts]
    end
    
    subgraph "Vector Runtime Layer"
        VES[vector.embedding_space<br/>Model Identity]
        VC[vector.chunk<br/>Content Chunks]
        VE[vector.embedding<br/>Vector Storage]
    end
    
    subgraph "Core Dimension Layer"
        DE[dbo.DimEntity<br/>Entity Dimension]
        DT[dbo.DimTag<br/>Tag Vocabulary]
        BTA[dbo.BridgeTagAssignment<br/>Tag Assignments]
    end
    
    WI -->|work_item_id| IR
    IR -->|ingest_id| SP
    SP -->|page_id| PS
    SP -->|page_id| PC
    PC -->|llm_run_id| LR
    PC -->|source_page_id| DE
    LJ -->|job_id| LR
    LR -->|run_id| LA
    VC -->|chunk_id| VE
    VES -->|space_id| VE
    DE -->|entity_id| BTA
    DT -->|tag_id| BTA
    
    style WI fill:#e1f5ff
    style IR fill:#e1f5ff
    style SP fill:#fff4e1
    style PS fill:#fff4e1
    style PC fill:#fff4e1
    style LJ fill:#f0e1ff
    style LR fill:#f0e1ff
    style LA fill:#f0e1ff
    style VES fill:#e1ffe1
    style VC fill:#e1ffe1
    style VE fill:#e1ffe1
    style DE fill:#ffe1e1
    style DT fill:#ffe1e1
    style BTA fill:#ffe1e1
```

**Legend:**
- 🔵 Blue: Acquisition (ingest)
- 🟡 Yellow: Semantic Staging (sem)
- 🟣 Purple: LLM Runtime (llm)
- 🟢 Green: Vector Runtime (vector)
- 🔴 Red: Core Dimensions (dbo)

---

## Detailed Entity-Relationship Diagrams

### 1. Ingestion & Work Queue Schema (ingest)

```mermaid
erDiagram
    work_items ||--o{ IngestRecords : "produces"
    ingest_runs ||--o{ work_items : "coordinates"
    seen_resources ||--o{ work_items : "deduplicates"
    
    work_items {
        nvarchar work_item_id PK
        nvarchar source_system
        nvarchar source_name
        nvarchar resource_type
        nvarchar resource_id
        nvarchar request_uri
        nvarchar status "pending/in_progress/completed/failed/skipped"
        int priority
        int attempt
        nvarchar run_id FK
        nvarchar discovered_from FK
        datetime2 created_at
        datetime2 updated_at
        nvarchar error_message
        nvarchar dedupe_key UK
    }
    
    IngestRecords {
        uniqueidentifier ingest_id PK
        nvarchar source_system
        nvarchar source_name
        nvarchar resource_type
        nvarchar resource_id
        nvarchar request_uri
        int status_code
        nvarchar payload "JSON/HTML response body"
        datetime2 fetched_at_utc
        nvarchar hash_sha256
        uniqueidentifier run_id
        uniqueidentifier work_item_id FK
        int attempt
        int duration_ms
    }
    
    ingest_runs {
        uniqueidentifier run_id PK
        datetime2 started_at
        datetime2 completed_at
        nvarchar status
        int total_items
        int successful_items
        int failed_items
    }
    
    seen_resources {
        uniqueidentifier seen_id PK
        nvarchar source_system
        nvarchar resource_id
        nvarchar dedupe_key UK
        datetime2 first_seen_at
        datetime2 last_seen_at
        int occurrence_count
    }
```

**Key Relationships:**
- **work_items → IngestRecords:** 1:N (one work item produces multiple ingest records on retries)
- **ingest_runs → work_items:** 1:N (one run coordinates many work items)
- **seen_resources → work_items:** 1:N (one resource may be requested multiple times, but dedupe_key prevents duplicates)

**Deduplication Strategy:**
- `dedupe_key` = HASH(source_system + resource_id + request_uri)
- Unique constraint on `work_items.dedupe_key` prevents duplicate work items
- `seen_resources` tracks first/last seen times for analytics

---

### 2. Semantic Staging Schema (sem)

```mermaid
erDiagram
    SourcePage ||--o{ PageSignals : "has"
    SourcePage ||--o{ PageClassification : "has"
    SourcePage ||--o| DimEntity : "promotes to"
    PageClassification }o--|| llm_run : "optionally derived by"
    
    SourcePage {
        uniqueidentifier PageID PK
        nvarchar SourceSystem
        nvarchar ResourceID
        nvarchar Variant "html/json"
        nvarchar Namespace
        nvarchar Title
        nvarchar URI
        nvarchar ContentHash
        datetime2 FetchedAt
        uniqueidentifier IngestRecordID FK
    }
    
    PageSignals {
        uniqueidentifier SignalID PK
        uniqueidentifier PageID FK
        nvarchar ContentFormat "wikitext/html/json"
        nvarchar LeadExcerptText
        int LeadExcerptLen
        nvarchar InfoboxType
        nvarchar CategoryNames "JSON array"
        bit IsDisambiguation
        bit IsListPage
        bit IsTimeline
        bit IsRedirect
        datetime2 ExtractedAt
    }
    
    PageClassification {
        uniqueidentifier ClassificationID PK
        uniqueidentifier PageID FK
        nvarchar PrimaryType "PersonCharacter/LocationPlace/etc."
        nvarchar TypeSet "JSON multi-label with weights"
        decimal Confidence
        nvarchar Method "rules/llm/hybrid/manual"
        datetime2 ClassifiedAt
        uniqueidentifier LLMRunID FK "nullable"
        nvarchar DescriptorSentence
        bit NeedsReview
        nvarchar WorkMedium "nullable (WorkMedia only)"
        nvarchar CanonContext "nullable (WorkMedia only)"
    }
```

**Key Relationships:**
- **SourcePage → PageSignals:** 1:N (multiple signal extractions over time)
- **SourcePage → PageClassification:** 1:N (multiple classifications, e.g., rules then LLM adjudication)
- **PageClassification → llm.run:** N:1 (optional, when LLM-derived)
- **SourcePage → DimEntity:** 1:1 (promoted pages become entities)

**Semantic Flow:**
1. HTTP response → `ingest.IngestRecords`
2. Parse metadata → `sem.SourcePage`
3. Extract cues → `sem.PageSignals` (rules-based)
4. Classify type → `sem.PageClassification` (rules, LLM, or hybrid)
5. Promote → `dbo.DimEntity` (high-confidence, valid types)

---

### 3. LLM Runtime Schema (llm)

```mermaid
erDiagram
    job ||--o{ run : "has attempts"
    run ||--o{ artifact : "produces"
    run ||--o{ run_evidence : "uses"
    evidence_bundle ||--o{ evidence_item : "contains"
    evidence_bundle ||--o{ run_evidence : "linked to runs"
    
    job {
        uniqueidentifier job_id PK
        nvarchar job_type "page_classification/entity_facts/etc."
        nvarchar status "NEW/RUNNING/SUCCEEDED/FAILED/DEADLETTER"
        int priority
        int max_attempts
        int current_attempt
        datetime2 backoff_until "exponential backoff"
        datetime2 created_at
        datetime2 updated_at
        nvarchar claimed_by "worker_id"
        datetime2 claimed_at
        nvarchar input_json "job-specific input"
    }
    
    run {
        uniqueidentifier run_id PK
        uniqueidentifier job_id FK
        datetime2 started_at
        datetime2 completed_at
        nvarchar status "running/succeeded/failed"
        nvarchar model_name
        int prompt_tokens
        int completion_tokens
        nvarchar error_message
        nvarchar worker_id
    }
    
    artifact {
        uniqueidentifier artifact_id PK
        uniqueidentifier run_id FK
        nvarchar artifact_type "request_json/response_json/evidence_bundle/prompt_text/parsed_output/raw_response/invalid_json_response/error_manifest"
        nvarchar lake_uri
        nvarchar content_sha256
        bigint byte_count
        datetime2 created_at
    }
    
    evidence_bundle {
        uniqueidentifier bundle_id PK
        nvarchar policy "JSON with bounding rules"
        nvarchar summary "JSON with token counts, source counts"
        nvarchar lake_uri "lake path to evidence.json"
        datetime2 created_at
    }
    
    evidence_item {
        uniqueidentifier item_id PK
        uniqueidentifier bundle_id FK
        nvarchar evidence_type "inline/lake_text/lake_http/sql_result"
        nvarchar source_identifier
        nvarchar content_preview "first 500 chars"
        nvarchar content_sha256
        bigint byte_count
        int seq "ordering within bundle"
    }
    
    run_evidence {
        uniqueidentifier run_id FK
        uniqueidentifier bundle_id FK
        datetime2 created_at
    }
```

**Key Relationships:**
- **job → run:** 1:N (multiple attempts per job, especially on failures)
- **run → artifact:** 1:N (multiple artifacts per run: request, response, evidence, prompt, output, error manifests)
- **run → evidence_bundle:** N:M (via run_evidence bridge table)
- **evidence_bundle → evidence_item:** 1:N (bundle contains multiple evidence items)

**Job Lifecycle:**
1. **Enqueue:** `llm.usp_enqueue_job()` creates job with status=NEW
2. **Claim:** Worker calls `llm.usp_claim_next_job()` → status=RUNNING, worker claims lease
3. **Execute:** Worker creates run via `llm.usp_create_run()`, calls Ollama, writes artifacts
4. **Complete:** `llm.usp_complete_run()` + `llm.usp_complete_job()` → status=SUCCEEDED or FAILED
5. **Retry:** On failure, `current_attempt++`, `backoff_until` set for exponential backoff
6. **Dead Letter:** After `max_attempts`, status=DEADLETTER (requires manual intervention)

**Stored Procedure Contract:**
- All queue operations use stored procedures for atomicity and concurrency safety
- `WITH (READPAST, UPDLOCK)` hints prevent worker contention
- Backoff logic enforced at database level (job not claimable until `backoff_until` expires)

---

### 4. Vector Runtime Schema (vector)

```mermaid
erDiagram
    embedding_space ||--o{ embedding : "defines model for"
    embedding_space ||--o{ retrieval : "used by"
    source_registry ||--o{ chunk : "owns"
    chunk ||--o{ embedding : "has vectors in multiple spaces"
    retrieval ||--o{ retrieval_hit : "returns"
    chunk ||--o{ retrieval_hit : "ranked in results"
    job ||--o{ run : "has attempts"
    
    embedding_space {
        uniqueidentifier space_id PK
        nvarchar provider "ollama/openai/anthropic"
        nvarchar model_name "nomic-embed-text/etc."
        nvarchar model_tag "latest/v1.0/etc."
        nvarchar model_digest "sha256 hash"
        int dimensions
        nvarchar distance_metric "cosine/euclidean/dot"
        datetime2 created_at
        nvarchar metadata "JSON for model config"
    }
    
    source_registry {
        uniqueidentifier registry_id PK
        nvarchar source_type "SourcePage/HttpResponse/TextFile"
        nvarchar source_identifier
        nvarchar status "indexed/pending/error"
        datetime2 last_indexed_at
        int chunk_count
        nvarchar embedding_space_ids "JSON array of space_ids"
    }
    
    chunk {
        uniqueidentifier chunk_id PK
        uniqueidentifier source_registry_id FK
        int chunk_index
        nvarchar content "full text"
        nvarchar content_sha256
        int token_count
        datetime2 created_at
    }
    
    embedding {
        uniqueidentifier embedding_id PK
        uniqueidentifier chunk_id FK
        uniqueidentifier space_id FK
        varbinary embedding_vector "binary vector"
        int content_version "for idempotent re-embedding"
        datetime2 created_at
    }
    
    retrieval {
        uniqueidentifier retrieval_id PK
        nvarchar query_text
        varbinary query_embedding
        uniqueidentifier space_id FK
        int top_k
        decimal threshold
        datetime2 created_at
    }
    
    retrieval_hit {
        uniqueidentifier hit_id PK
        uniqueidentifier retrieval_id FK
        uniqueidentifier chunk_id FK
        decimal similarity_score
        int rank
        datetime2 created_at
    }
    
    job {
        uniqueidentifier job_id PK
        nvarchar job_type "CHUNK_SOURCE/EMBED_CHUNKS/REEMBED_SPACE/RETRIEVE_TEST/DRIFT_TEST"
        nvarchar status "NEW/RUNNING/SUCCEEDED/FAILED"
        int priority
        uniqueidentifier source_registry_id FK "nullable"
        uniqueidentifier embedding_space_id FK "nullable"
        datetime2 created_at
    }
    
    run {
        uniqueidentifier run_id PK
        uniqueidentifier job_id FK
        nvarchar status
        datetime2 started_at
        datetime2 completed_at
        int chunks_processed
        int embeddings_created
    }
```

**Key Relationships:**
- **embedding_space → embedding:** 1:N (one model defines many vectors)
- **source_registry → chunk:** 1:N (one source produces many chunks)
- **chunk → embedding:** 1:N (one chunk has embeddings in multiple spaces)
- **embedding:** Unique constraint on `(chunk_id, space_id, content_version)` for idempotency
- **retrieval → retrieval_hit:** 1:N (one query returns ranked results)
- **chunk → retrieval_hit:** 1:N (one chunk appears in many result sets)

**Embedding Space Identity:**
- **Purpose:** Prevent mixing vectors from incompatible models (different dimensions/metrics)
- **Uniqueness:** `(provider, model_name, model_tag, model_digest, dimensions)` must be unique
- **Use Case:** Re-embedding content with new model version creates new space_id, old embeddings preserved

**Content Versioning:**
- `embedding.content_version` tracks chunk content hash at embedding time
- Idempotent re-embedding: If chunk content unchanged, don't re-embed
- Supports drift detection: Compare old vs new embeddings for same content

---

### 5. Core Dimensional Model (dbo)

```mermaid
erDiagram
    DimEntity ||--o| SourcePage : "promoted from"
    DimEntity ||--o{ BridgeTagAssignment : "has tags"
    DimTag ||--o{ BridgeTagAssignment : "assigned to targets"
    DimTag ||--o{ BridgeTagRelation : "has relations"
    DimTag ||--o{ BridgeTagRelation : "related to"
    
    DimEntity {
        int EntityID PK
        nvarchar EntityName
        nvarchar PromotionState "staged/candidate/adjudicated/promoted/suppressed/merged"
        datetime2 PromotionDecisionUtc
        nvarchar PromotionDecidedBy
        nvarchar PromotionReason
        uniqueidentifier SourcePageId FK "nullable"
        nvarchar PrimaryTypeInferred
        nvarchar TypeSetJsonInferred "JSON multi-label"
        uniqueidentifier AdjudicationRunId FK "nullable, llm.run"
    }
    
    DimTag {
        int TagID PK
        nvarchar TagName UK
        nvarchar TagType "category/topic/attribute/flag"
        nvarchar Visibility "public/internal/deprecated"
        nvarchar GovernanceNotes
        datetime2 CreatedAt
    }
    
    BridgeTagAssignment {
        int AssignmentID PK
        nvarchar TargetType "SourcePage/Entity/Chunk/Claim/Event"
        nvarchar TargetID
        int TagID FK
        datetime2 AssignedAt
        nvarchar AssignedBy
        decimal Confidence
        nvarchar AssignmentMethod "manual/llm/rules"
    }
    
    BridgeTagRelation {
        int RelationID PK
        int FromTagID FK
        int ToTagID FK
        nvarchar RelationType "synonym/broader/narrower/related/replaces"
        datetime2 CreatedAt
    }
```

**Key Relationships:**
- **DimEntity → SourcePage:** N:1 (entity promoted from page, but multiple entities may reference same page during merge resolution)
- **DimEntity → BridgeTagAssignment:** 1:N (entity has many tag assignments)
- **DimTag → BridgeTagAssignment:** 1:N (tag assigned to many targets)
- **DimTag → BridgeTagRelation:** 1:N (tag has relationships to other tags)

**Entity Promotion States:**
- **staged:** Initial state after page classification (not yet reviewed)
- **candidate:** Human or system flagged for promotion consideration
- **adjudicated:** Decision made (promote or suppress)
- **promoted:** Active entity in analytical model
- **suppressed:** Determined not to be entity (e.g., disambiguation page, list page)
- **merged:** Merged into another entity (deduplication)

**Tag Assignment Polymorphism:**
- `TargetType` enum allows tags on: SourcePage, Entity, Chunk, Claim, Event (extensible)
- `TargetID` is string identifier (UUID or integer as string)
- Supports multi-target tagging (e.g., tag both SourcePage and promoted Entity)

---

## Data Warehouse Classification

### Dimensions (Slowly Changing)

| Table | Type | Change Strategy |
|-------|------|----------------|
| **DimEntity** | SCD Type 2 (candidate) | PromotionState tracks lifecycle, PromotionDecisionUtc for temporal slicing |
| **DimTag** | SCD Type 1 | Updates in place, deprecated via Visibility='deprecated' |
| **vector.embedding_space** | SCD Type 0 | Immutable — new model version = new space_id |
| **sem.SourcePage** | SCD Type 1 | ContentHash tracks changes, but page identity (URI) immutable |

### Facts (Event-Based)

| Table | Grain | Accumulating Snapshot |
|-------|-------|----------------------|
| **ingest.IngestRecords** | One row per HTTP fetch attempt | No — immutable records |
| **llm.run** | One row per LLM job execution attempt | No — immutable records |
| **vector.retrieval** | One row per similarity search query | No — immutable audit log |
| **sem.PageClassification** | One row per classification decision | No — history preserved via ClassifiedAt |

### Bridges (Many-to-Many)

| Table | Left Entity | Right Entity | Attributes |
|-------|------------|--------------|-----------|
| **BridgeTagAssignment** | DimTag | SourcePage/Entity/Chunk | Confidence, AssignedAt, AssignmentMethod |
| **BridgeTagRelation** | DimTag | DimTag | RelationType |
| **llm.run_evidence** | llm.run | llm.evidence_bundle | (Simple linkage, no attributes) |
| **vector.retrieval_hit** | vector.retrieval | vector.chunk | similarity_score, rank |

### Staging (Transient or Semi-Persistent)

| Table | Purpose | Retention |
|-------|---------|-----------|
| **ingest.work_items** | Work queue for ingestion | Archived after completion (7+ days) |
| **llm.job** | Work queue for LLM operations | Dead-letter queue for failures, otherwise completed jobs archived |
| **vector.job** | Work queue for vector operations | Similar to llm.job |
| **sem.PageSignals** | Extracted cues for classification | Persistent (used for re-classification) |
| **sem.PageClassification** | Type inference history | Persistent (audit trail) |

---

## Subtype Modeling Patterns

### Entities by Type

**Current State:**
- **Implicit Subtyping:** `DimEntity.PrimaryTypeInferred` and `TypeSetJsonInferred` indicate entity type
- **No Physical Subtypes:** All entities stored in single table (no separate `DimPerson`, `DimLocation`, etc.)
- **Polymorphic Attributes:** No type-specific attributes yet (e.g., `birthdate` for PersonCharacter, `population` for LocationPlace)

**Example:**
```sql
-- Current: All types in one table
SELECT EntityID, EntityName, PrimaryTypeInferred
FROM dbo.DimEntity
WHERE PrimaryTypeInferred = 'PersonCharacter';

-- Missing: Type-specific attributes
-- No columns for PersonCharacter.birthdate, Species.homeworld, etc.
```

**Gap for LLM Expansion:**
- **Need:** Type-specific attribute tables (e.g., `dbo.PersonCharacterFacts`, `dbo.LocationPlaceFacts`)
- **Pattern:** 1:1 relationship with `DimEntity` via `EntityID` FK
- **Alternative:** JSON column `ExtendedAttributes` for flexible schema (less typed, harder to query)

---

### Pages by Type

**Current State:**
- **Explicit Subtyping:** `sem.PageClassification.PrimaryType` with 15 distinct types
- **Type-Specific Attributes:** `WorkMedium` and `CanonContext` columns for WorkMedia pages only
- **Extensibility:** Additional type-specific columns added via migrations (see migration 0022)

**Example:**
```sql
-- Type-specific query
SELECT pc.PageID, sp.Title, pc.WorkMedium, pc.CanonContext
FROM sem.PageClassification pc
JOIN sem.SourcePage sp ON pc.PageID = sp.PageID
WHERE pc.PrimaryType = 'WorkMedia';
```

**Pattern:**
- **Sparse Columns:** Type-specific attributes stored as nullable columns (works for 2-3 attributes per type)
- **Future Consideration:** If many types need >5 attributes each, consider vertical partitioning or JSON

---

## Missing Relationships (Gaps for LLM Expansion)

### 1. Entity-to-Entity Relationships

**Current State:** ❌ No entity relationship tables exist

**Needed for LLM Expansion:**
- `dbo.BridgeEntityRelation` — Many-to-many entity relationships
  - Columns: `RelationID`, `FromEntityID`, `ToEntityID`, `RelationType` (member_of/ally_of/enemy_of/created_by/located_in), `StartDate`, `EndDate`, `Confidence`, `SourceLLMRunID`
- Use Cases: "Luke Skywalker is a member of Rebel Alliance", "Tatooine is located in Outer Rim"

**Example (Missing Table):**
```sql
-- This table does not exist yet
CREATE TABLE dbo.BridgeEntityRelation (
    RelationID INT IDENTITY(1,1) PRIMARY KEY,
    FromEntityID INT NOT NULL FOREIGN KEY REFERENCES dbo.DimEntity(EntityID),
    ToEntityID INT NOT NULL FOREIGN KEY REFERENCES dbo.DimEntity(EntityID),
    RelationType NVARCHAR(50) NOT NULL,
    StartDate NVARCHAR(100),  -- Fuzzy dates (e.g., "22 BBY", "approximately 0 BBY")
    EndDate NVARCHAR(100),
    Confidence DECIMAL(5,4),
    SourceLLMRunID UNIQUEIDENTIFIER,
    CreatedAt DATETIME2 DEFAULT SYSUTCDATETIME()
);
```

---

### 2. Entity-to-Event Relationships

**Current State:** ❌ No event dimension or entity-event bridge exists

**Needed for LLM Expansion:**
- `dbo.DimEvent` — Event dimension (battles, treaties, births, deaths)
  - Columns: `EventID`, `EventName`, `EventType`, `EventDate`, `EventLocation`, `EventDescription`
- `dbo.BridgeEntityEvent` — Entity participation in events
  - Columns: `EntityID`, `EventID`, `ParticipationRole` (combatant/commander/victim/witness)

**Use Cases:** "Luke Skywalker participated in Battle of Yavin as pilot", "Anakin Skywalker born on Tatooine in 41 BBY"

---

### 3. Entity-to-Work Relationships

**Current State:** ❌ No work dimension or entity-work bridge exists

**Needed for LLM Expansion:**
- `dbo.DimWork` — Creative works dimension (films, TV episodes, novels, comics)
  - Columns: `WorkID`, `WorkName`, `WorkType`, `ReleaseDate`, `CanonStatus`
- `dbo.BridgeEntityWork` — Entity appearances in works
  - Columns: `EntityID`, `WorkID`, `AppearanceType` (main_character/supporting/mentioned)

**Use Cases:** "Luke Skywalker appears in 'A New Hope' as main character", "Death Star appears in 'A New Hope' as location"

---

### 4. Multi-Output Fact Tables

**Current State:** ❌ No tables for multi-entity extractions from single source

**Needed for LLM Expansion:**
- **Problem:** Single LLM run may extract N entities from one page (e.g., "List of Jedi" extracts 50 PersonCharacter entities)
- **Need:** Fact table linking `llm.run` → N `dbo.DimEntity` with extracted attributes
- **Pattern:** `dbo.FactEntityExtraction` with columns: `ExtractionID`, `LLMRunID`, `EntityID`, `ExtractedAttributes` (JSON), `Confidence`

**Example (Missing Table):**
```sql
-- This table does not exist yet
CREATE TABLE dbo.FactEntityExtraction (
    ExtractionID INT IDENTITY(1,1) PRIMARY KEY,
    LLMRunID UNIQUEIDENTIFIER NOT NULL,
    EntityID INT NOT NULL FOREIGN KEY REFERENCES dbo.DimEntity(EntityID),
    ExtractedAttributes NVARCHAR(MAX),  -- JSON with LLM-derived facts
    Confidence DECIMAL(5,4),
    CreatedAt DATETIME2 DEFAULT SYSUTCDATETIME()
);
```

---

## Data Flow Diagrams

### End-to-End Data Flow (Current State)

```mermaid
flowchart LR
    A[External API<br/>wookieepedia_api] --> B[ingest.work_items<br/>Work Queue]
    B --> C[HTTP Fetch]
    C --> D[ingest.IngestRecords<br/>Raw JSON/HTML]
    D --> E[sem.SourcePage<br/>Parse Metadata]
    E --> F[sem.PageSignals<br/>Extract Cues]
    F --> G[sem.PageClassification<br/>Rules Classifier]
    G --> H{Confidence > 0.8?}
    H -->|Yes| I[dbo.DimEntity<br/>Promote to Entity]
    H -->|No| J[llm.job<br/>Enqueue for LLM]
    J --> K[llm.run<br/>LLM Classification]
    K --> L[llm.artifact<br/>Write to Lake]
    K --> G
    G --> M[dbo.BridgeTagAssignment<br/>Assign Tags]
    
    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style D fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#fff4e1
    style G fill:#fff4e1
    style I fill:#ffe1e1
    style J fill:#f0e1ff
    style K fill:#f0e1ff
    style L fill:#f0e1ff
    style M fill:#ffe1e1
```

**Key Observations:**
1. **Linear Flow:** Data flows sequentially through schemas (ingest → sem → llm → dbo)
2. **Single Entity Promotion:** One page → one entity (no multi-entity extraction)
3. **No Relationships:** No entity-to-entity, entity-to-event, or entity-to-work bridges populated
4. **Tag Assignments:** Only polymorphic target, no relationships between entities

---

### Desired LLM Expansion Flow (Future State)

```mermaid
flowchart LR
    A[llm.job<br/>Multi-Entity Extraction] --> B[llm.run<br/>LLM Call]
    B --> C[JSON Output<br/>N Entities + M Relations]
    C --> D{Stored Proc<br/>Route JSON}
    D --> E[dbo.DimEntity<br/>Insert/Update N Entities]
    D --> F[dbo.BridgeEntityRelation<br/>Insert M Relations]
    D --> G[dbo.BridgeTagAssignment<br/>Assign Tags]
    D --> H[dbo.FactEntityExtraction<br/>Link Run → Entities]
    E --> I[Identity Resolution<br/>Dedupe & Merge]
    I --> J[dbo.DimEntity<br/>PromotionState = 'promoted']
    
    style A fill:#f0e1ff
    style B fill:#f0e1ff
    style C fill:#f0e1ff
    style D fill:#ffcccc
    style E fill:#ffe1e1
    style F fill:#ffe1e1
    style G fill:#ffe1e1
    style H fill:#ffe1e1
    style I fill:#ffcccc
    style J fill:#ffe1e1
```

**Key Differences from Current State:**
1. **Multi-Output Routing:** One LLM run → N entities + M relations (not just 1:1)
2. **Stored Procedure Routing:** JSON payload → stored proc → multi-table writes (not Python ad hoc inserts)
3. **Identity Resolution:** Dedupe/merge logic before promotion (not just insert)
4. **Relationship Population:** Entity relations, events, works (not just tags)

---

## Related Documentation

- [01-current-state-inventory.md](01-current-state-inventory.md) — Repository and SQL artifact inventory
- [03-workflow-and-runner-map.md](03-workflow-and-runner-map.md) — Process flows and runner orchestration
- [04-functional-gap-analysis.md](04-functional-gap-analysis.md) — Gap analysis for LLM expansion
- [05-recommendations-and-next-steps.md](05-recommendations-and-next-steps.md) — Implementation roadmap
- [../diagrams/mermaid/ERD_Explained.md](../diagrams/mermaid/ERD_Explained.md) — Mermaid diagram conventions
