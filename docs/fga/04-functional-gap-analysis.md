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

### 1. Universal Work Queue for Multiple Job Types

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
- **Universal Multi-Tenant Queue:** Current queue supports multiple job types but is not explicitly designed as a universal backlog where:
  - Multiple job types coexist in the same queue simultaneously
  - Multiple runners/contexts can pull different job types concurrently
  - Operators can bump priorities to pull specific jobs into "current batch"
  - Each job type has its own contract and handler path for routing and persistence
- **Job Routing Logic:** No dispatcher that routes job types to appropriate prompt templates and output handlers
- **Flexible Priority Management:** Priority column exists but not actively used for:
  - Dynamic priority bumping (operators elevating specific jobs)
  - Batch selection (pulling high-priority jobs into immediate processing)
  - Runner dispatching (different runners processing different job types)

#### Impact

**Medium** — Can enqueue new job types manually, but no structured framework for managing a universal multi-job-type backlog

#### Recommended Solution

- **Clarify Queue Model as Universal Backlog:** Document that `llm.job` is a **multi-tenant, multi-job-type** queue where:
  - Jobs of many types (entity extraction, relationship extraction, dedupe, classification, etc.) exist simultaneously
  - Runners can filter by job type or process mixed types
  - Priority is used to control batch selection and processing order
  - Each job type defines its own contract (input/output schemas) and routing path
- **Create Job Type Registry:** `src/llm/jobs/registry.py` with job type definitions mapping to:
  - Prompt templates
  - Input/output schemas (contracts)
  - Handler functions for persistence routing
  - Default priority levels
- **Implement Dispatcher:** `src/llm/runners/dispatcher.py` that:
  - Claims jobs from queue (optionally filtered by job type)
  - Routes to appropriate handler based on job type
  - Supports concurrent runners processing different job types
- **Add Priority Management Utilities:** `src/llm/utils/priority.py` with functions to:
  - Bump priority for specific job types or source patterns
  - Select batches based on priority thresholds
  - Auto-escalate based on SLA (time in queue)

**Effort:** Small (S)  
**Dependencies:** None

---

### 2. LLM Contracts: Broad Multi-Pronged Knowledge Extraction

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
- **Multi-Pronged Knowledge Extraction Contracts:** Current contracts limited to classification. Need contracts that extract **multiple output families** from a single source:
  - **Dimensions:** Entities, events, works, locations, time periods, concepts (not limited to the enumerated examples)
  - **Facts:** Assertions, measurements, attributes, descriptors, time-scoped states
  - **Bridges:** Relationships, associations, participation, ownership, appearance, membership, location linkages
  - **Time-Bounded Assertions:** Relationships or facts that are valid only within specific timeframes or work contexts
  - **Future Extensibility:** New dimension/fact/bridge types can be introduced (e.g., appearance descriptors, costume details, visual characteristics)
  
- **Flexible Entity Representation:** Extracted entities from pages may not be permanent canonical entities. They may represent:
  - Timeframes or periods
  - Events or occurrences
  - Continuity branches or alternative timelines
  - Appearances or manifestations
  - Facts or assertions about entities
  - Transient relationships
  
- **Example Contracts Missing:**
  - Multi-entity extraction (N entities from one source)
  - Relationship extraction (entity↔entity, entity↔event, entity↔work, entity↔location, entity↔timeline)
  - Entity dedupe/merge (identifying duplicates)
  - Event extraction with participants
  - Work extraction with appearances
  
**Important:** Contract universe is **not limited** to specific entity types (Droid, PersonCharacter, etc.) or relationship types. Examples are illustrative only; actual contracts should support extensibility and evolving taxonomies.

#### Impact

**High** — Cannot implement multi-pronged knowledge extraction without broadly-defined contracts

#### Recommended Solution

- **Create Flexible Multi-Entity Contract:** `src/llm/contracts/entity_extraction_v1_schema.json`
  - Output: Array of extracted knowledge items
  - Each item: `name`, `type` (extensible, not enum), `confidence`, `attributes` (flexible JSON)
  - Support for multiple output types in single extraction (dimensions + facts + bridges)
  
- **Create Broad Relationship Contract:** `src/llm/contracts/relationship_extraction_v1_schema.json`
  - Output: Array of relationship assertions
  - Relationship taxonomy evolves; examples only (not fixed enums)
  - Types include but not limited to: associations, participation, location, membership, ownership, appearance, time-bounded states
  - Support for temporal bounds (start/end or work-bounded)
  
- **Create Dedupe Contract:** `src/llm/contracts/entity_dedupe_v1_schema.json`
  - Output: Dedupe decisions for best-effort matching
  - Used for future "dedupe audit" capabilities
  
- **Versioning Strategy:** Use MAJOR.MINOR.PATCH versioning for all contracts (e.g., `entity_extraction_v1.0.0`)

**Key Principle:** Contracts enable multiple output families (dimensions + facts + bridges + attributes + time-scoped assertions), not just "list of entities." Future schemas may target any table structure.

**Effort:** Medium (M)  
**Dependencies:** Universal Queue Model (#1)

---

### 3. LLM Context Chunking & Dynamic Budgeting Strategy

#### Current State

✅ **Exists:**
- **Vector Schema:** `vector.chunk` table with `chunk_index`, `content`, `content_sha256`, `token_count`
- **Source Registry:** `vector.source_registry` tracks indexed sources and chunk counts
- **Chunking Models:** `src/vector/contracts/models.py` defines `VectorChunk` dataclass

❌ **Missing:**
- **Production Chunking Pipeline:** No active runner that chunks sources and writes to `vector.chunk`
- **LLM Context Management:** No chunking strategy specifically for LLM calls (independent of vector use cases)
- **Dynamic Budget Calculation:** No logic to:
  - Estimate tokens available for content given model context window
  - Account for overhead (system prompt + contract + JSON output envelope)
  - Reserve safety buffer for model output
  - Choose chunk sizes + overlap dynamically
  - Degrade gracefully when model context is smaller
- **Traceability Back to Source:** `vector.chunk` has `source_registry_id` FK, but no direct link to `ingest.IngestRecords` or `sem.SourcePage`

**Evidence:**
- File: `db/migrations/0023_create_vector_schema.sql` (vector.chunk table)
- File: `src/vector/contracts/models.py` (VectorChunk model)

#### Gap

❌ **Missing:**

**Primary Gap: LLM Context Chunking is needed for LLM calls, not primarily for vector search.**

Chunking is required **regardless of vector search** because:
- LLM calls have context window limits (measured in tokens)
- Reliable extraction requires fitting: content + system prompt + contract + output space
- Even with large context windows (128K+), chunking improves:
  - Reliability (smaller chunks = more predictable outputs)
  - Traceability (linking outputs to specific chunks)
  - Repeatability (re-running chunks independently)

**Specific Missing Capabilities:**
- **Dynamic Budgeting Logic:** Calculate available tokens for content:
  - Total model context window (e.g., 128K tokens)
  - Minus: System prompt tokens (~500-2000)
  - Minus: Contract/schema overhead (~200-500)
  - Minus: Output buffer (reserve ~2000-4000 for JSON response)
  - Minus: Safety margin (~10-20% of total)
  - Remaining: Available for content chunks
  
- **Reusable Chunker Module:** No `src/llm/chunker.py` (or `src/vector/chunker.py`) with:
  - Token estimation from text length (rough heuristic: ~4 chars/token)
  - Configurable chunk sizes based on available budget
  - Overlap configuration to prevent information loss at boundaries
  - Sentence-boundary awareness (avoid mid-sentence cuts)
  - Paragraph-boundary awareness (for semantic coherence)
  
- **Chunking Policy Configuration:**
  ```yaml
  chunking:
    strategy: sentence_boundary_fixed
    max_tokens: 8000           # Per chunk
    overlap_tokens: 1000       # Overlap between chunks
    min_chunk_tokens: 2000     # Minimum viable chunk
    estimate_chars_per_token: 4
  ```
  
- **Chunk-to-Source Linking:** No clear linkage from chunk back to original source for audit trail

**Important:** Vector tables (`vector.chunk`, `vector.embedding`) exist for embedding/retrieval use cases, but LLM context chunking is a **general strategy** for any unstructured/semi-structured source. Chunking should not be framed as vector-specific in Phase 0-2.

#### Impact

**High** — Cannot reliably process long sources with LLM without chunking and dynamic budgeting

#### Recommended Solution

**Phase 1: Create LLM Context Chunking Module**
- **Implement Chunker:** `src/llm/chunker.py` (or `src/vector/chunker.py` if shared) with:
  - `chunk_for_llm_context()` function
  - Dynamic budget calculation based on model context window
  - Token estimation (chars → tokens heuristic)
  - Sentence-boundary-aware chunking
  - Configurable via `ChunkingPolicy` dataclass
  
**Phase 2: Add Budgeting Logic**
- **Budget Calculator:** `calculate_available_tokens(model_context_window, system_prompt_len, contract_len, output_buffer, safety_margin)`
- **Example:**
  ```python
  model_window = 128000  # tokens
  system_prompt = 1500
  contract_overhead = 300
  output_buffer = 3000
  safety_margin = int(model_window * 0.15)  # 15%
  
  available = model_window - system_prompt - contract_overhead - output_buffer - safety_margin
  # Result: ~103,700 tokens available for content
  
  chunk_size = min(available, 8000)  # Cap at 8K for reliability
  overlap = 1000
  ```

**Phase 3: Integrate with Runners**
- **Modify LLM Runners:** When processing long sources:
  - Estimate source token count
  - If exceeds budget, chunk source
  - Process each chunk independently or with overlap
  - Aggregate outputs (if applicable)
  
- **Chunk Runner (Optional):** `src/vector/runners/chunk_runner.py` for pre-chunking sources:
  - Dequeues `vector.job` with `job_type = 'CHUNK_SOURCE'`
  - Loads source content
  - Chunks content and writes to `vector.chunk`
  - Updates `vector.source_registry` status
  
**Phase 4: Source Traceability**
- **Extend `vector.chunk`:** Add FK columns:
  - `source_page_id` → `sem.SourcePage` (for page sources)
  - `ingest_record_id` → `ingest.IngestRecords` (for raw HTTP sources)

**Note:** Chunking strategy is reusable for any unstructured/semi-structured source, not just for vector retrieval. Vector tables are acknowledged but not the primary driver in early phases.

**Effort:** Medium (M)  
**Dependencies:** None

---

### 4. Multi-Entity Extraction + Best-Effort Dedupe/Identity Resolution

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

**Multi-Entity Extraction:**
- **Batch Entity Insertion:** No stored procedure or utility to insert N entities in single transaction
- **Extraction Pipeline:** No runner that processes "list" or "collection" pages to extract multiple entities

**Identity Resolution (Best-Effort Approach):**

**Important:** Preventing all duplicates is **not a hard requirement** in early phases. Strategy is best-effort:
- Use **exact match** (case-insensitive name comparison)
- Use **simple fuzzy match** (Levenshtein distance, phonetic matching)
- **Tolerate some duplicates** in early data
- Plan for **future dedupe audit capabilities:** LLM contracts can mine the database for duplicates and optionally relate or suppress/purge redundant records

Current gaps:
- No algorithm for exact match (case-insensitive name comparison)
- No fuzzy match (Levenshtein distance, phonetic matching)
- No LLM-based identity resolution (for ambiguous cases in future phases)
- No "dedupe audit" job type or workflow

**Merge Workflow (Future Phase):**
- No code to identify duplicate entity candidates
- No ability to enqueue merge jobs for LLM adjudication
- No execution logic to merge entities (update FKs, mark merged entity as suppressed)

#### Impact

**High** — Cannot build "List of X" extraction pipeline without multi-entity support; duplicates will exist but are acceptable in early phases

#### Recommended Solution

**Phase 1: Multi-Entity Extraction**
- **Create Stored Procedure:** `dbo.usp_batch_insert_entities`
  - Input: JSON array of `EntityRecord` (name, type, attributes, source_page_id, llm_run_id)
  - Output: Array of inserted `EntityID` values
  - Logic: Insert N entities in single transaction, set `PromotionState = 'staged'`
  - Apply best-effort dedupe: check for exact name match before insert, skip if exists
- **Create Entity Writer:** `src/semantic/entity_writer.py` that calls stored procedure

**Phase 2: Best-Effort Identity Resolution**
- **Exact Match:** Query `DimEntity` for exact name match (case-insensitive)
  - If match found, reuse existing entity ID
- **Simple Fuzzy Match:** Use Python `difflib` or `fuzzywuzzy` for Levenshtein distance
  - If high-confidence fuzzy match (>0.95), reuse existing entity ID
  - If low-confidence match (<0.95), create new entity (tolerate duplicate)
- **No Hard Blocking:** Do not block insertion on ambiguous matches; allow duplicates

**Phase 3: Future Dedupe Audit (Post Phase 0-2)**
- **LLM Dedupe Contract:** Create contract for LLM to adjudicate duplicates
  - Input: Candidate entity names, attributes, source contexts
  - Output: `MergeDecision` (same_entity=true/false, confidence)
- **Dedupe Audit Job Type:** Job that scans `DimEntity` for potential duplicates and enqueues LLM jobs
- **Merge Execution:** `dbo.usp_merge_entities` (when ready)
  - Input: Master entity ID, duplicate entity IDs
  - Logic: Update all FKs to point to master, set duplicates to `PromotionState = 'merged'`

**Key Principle:** Early phases use best-effort strategies to minimize obvious duplicates. Deeper identity resolution and merge capabilities are planned for future phases, not requirements for Phase 0-2.

**Effort:** Large (L)  
**Dependencies:** Multi-Pronged Contracts (#2), Stored Procedure Routing (#6)

---

### 5. Relationship/Bridge Creation: Broad Taxonomy with Extensibility

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

**Relationship Tables and Broad Taxonomy:**

Current gaps assume fixed, enumerated relationship types. Need to generalize:

- **Relationship Taxonomy Evolves:** Examples provided are illustrative only, not exhaustive or prescriptive
- **Relationship types are broad and extensible:**
  - Associations (general connections, affiliations)
  - Participation (involved in events, works, organizations)
  - Location (resided in, visited, stationed at, native to)
  - Membership (member of organization, group, faction)
  - Ownership (owned by, possessed by, commanded by)
  - Appearance (appeared in work, depicted in source)
  - Time-bounded states (relationships valid only within specific timeframes or work contexts)
  - Family/kinship (parent, child, sibling, descendant)
  - Creation/authorship (created by, designed by, commissioned by)
  - Many more types as domain knowledge expands

- **Relationship extraction can target any schema** and produce **multiple bridge rows:**
  - Entity ↔ Entity (person-person, person-droid, person-organization, etc.)
  - Entity ↔ Event (participated in battle, present at treaty signing)
  - Entity ↔ Work (appeared in film, mentioned in novel)
  - Entity ↔ Location (visited planet, stationed at base)
  - Entity ↔ Timeline (existed during era, active in period)
  - Future bridge types as new dimensions are introduced

- **Time-Scoped Assertions:** Many relationships are not static:
  - "Luke owned R2-D2 from [A New Hope] to [The Last Jedi]"
  - "Anakin was a member of the Jedi Order from [The Phantom Menace] to [Revenge of the Sith]"
  - Bridges should support start/end dates or work-bounded ranges

**Specific Missing Infrastructure:**
- No tables for relationships
- No stored procedures or utilities to insert relationships
- No LLM runner that extracts relationships from text
- No extraction contract for relationship taxonomy

#### Impact

**High** — Cannot capture entity relationships, events, or work appearances without these tables and broad relationship support

#### Recommended Solution

**Phase 1: Create Extensible Relationship Tables**
- **Migration:** `db/migrations/0025_create_relationship_bridges.sql`
  - `dbo.BridgeEntityRelation` (FromEntityID, ToEntityID, RelationType [varchar, not enum], StartDate, EndDate, WorkContext, Confidence, SourceLLMRunID)
    - **RelationType is open-ended string**, not fixed enum, to support evolving taxonomy
  - `dbo.DimEvent` (EventID, EventName, EventType, EventDate, EventLocation, EventDescription)
  - `dbo.BridgeEntityEvent` (EntityID, EventID, ParticipationRole [open string], StartDate, EndDate, Confidence)
  - `dbo.DimWork` (WorkID, WorkName, WorkType, ReleaseDate, CanonStatus)
  - `dbo.BridgeEntityWork` (EntityID, WorkID, AppearanceType [open string], Confidence)
  - `dbo.BridgeEntityLocation` (EntityID, LocationID, LocationRole, StartDate, EndDate, Confidence)
  - Future bridge tables as needed (entity-timeline, entity-concept, etc.)

**Phase 2: Create Insertion Stored Procedures**
- `dbo.usp_insert_entity_relation` (single relationship)
- `dbo.usp_batch_insert_entity_relations` (N relationships from JSON array)
- `dbo.usp_insert_entity_event` (entity-event linkage)
- `dbo.usp_insert_entity_work` (entity-work appearance)
- Procedures should accept open-ended `RelationType` or `Role` strings, not validate against fixed enums

**Phase 3: Create Extraction Runner**
- **Job Type:** `relationship_extraction`
- **Contract:** Input = source_page_id, Output = Array of RelationshipRecord
  - Relationship type is open string (examples: "owned_by", "visited_in", "trained_by", "appeared_in", "member_of", etc.)
  - Support for temporal bounds (start/end dates or work context)
- **Prompt Template:** `src/llm/prompts/relationship_extraction.py`
  - Emphasize broad relationship taxonomy
  - Include examples for: associations, participation, location, membership, ownership, appearance, time-bounded states
  - Make clear that examples are not exhaustive
- **Handler:** `src/llm/handlers/relationship_handler.py` that calls batch insertion stored procedure

**Key Principle:** Relationship taxonomy evolves. Examples are illustrative, not prescriptive. Relationships are broad: associations, participation, location, membership, ownership, appearance, time-bounded states, and more. Future extraction contracts may target new bridge types as schema expands.

**Effort:** Large (L)  
**Dependencies:** Multi-Pronged Contracts (#2), Universal Queue (#1)

---

### 6. Stored Procedure Routing with Transactional Dependency Resolution

#### Current State

✅ **Exists:**
- **LLM Job Queue Stored Procedures:** `llm.usp_claim_next_job`, `llm.usp_complete_job`, etc. (queue management only)
- **Parameterized Queries:** All SQL interactions use parameterized queries (no SQL injection risk)

❌ **Missing:**
- **JSON-to-Table Routing:** No stored procedures that accept JSON payload and route to multiple tables
- **Transactional Multi-Table Writes:** No single stored procedure that inserts entities + relationships + tags in one transaction
- **Dependency Ordering:** No logic to handle insert order when dependent rows reference keys of other rows

**Evidence:**
- File: `db/migrations/0006_llm_indexes_sprocs.sql` (queue management stored procedures)

#### Gap

❌ **Missing:**

**Routing Stored Procedures:**

Need stored procedures that:
- Accept JSON payload from LLM output
- Route to multiple tables in single atomic transaction
- Handle **dependency ordering** to ensure referential integrity

**Dependency Ordering Pattern:**

When LLM output contains multiple record types (e.g., entities + relationships), insertion must be ordered:

1. **Pre-Step: Identify Existing vs New**
   - Parse incoming JSON to staging tables (table variables)
   - Check which entities/dimensions already exist (by name key, natural key, or ID lookup)
   
2. **Insert Base Dimensions First (Required Keys)**
   - Insert missing entities/dimensions (e.g., `DimEntity`, `DimLocation`, `DimEvent`)
   - Capture inserted IDs (use `OUTPUT INSERTED.EntityID`)
   
3. **Re-Resolve IDs After Insertion**
   - Build lookup table mapping names → IDs (both pre-existing and newly inserted)
   
4. **Insert Dependent Rows (Bridges/Facts)**
   - Insert bridges/facts that depend on dimension keys (e.g., `BridgeEntityRelation`, `BridgeEntityEvent`)
   - Use resolved IDs from step 3
   
5. **Commit or Rollback (All-or-None)**
   - If any step fails, rollback entire transaction
   - Ensure "all-or-none" commit semantics

**Example Dependency Chain:**
- Relationship "Luke Skywalker owned_by R2-D2" requires:
  1. Both entities exist in `DimEntity` (insert if missing)
  2. Resolve EntityIDs for "Luke Skywalker" and "R2-D2"
  3. Insert into `BridgeEntityRelation` with resolved IDs

**Current Gap:**
- No stored procedures with this dependency resolution logic
- Python would need to orchestrate multi-table writes (less atomic, more error-prone)

**Routing Examples Needed:**
- `dbo.usp_process_entity_extraction_output`
  - Input: JSON array of `EntityRecord` + optional `RelationshipRecord` array
  - Output: Inserted entity IDs and relationship IDs
  - Logic: Parse JSON → resolve existing entities → insert missing entities → insert relationships
- `dbo.usp_process_event_extraction_output`
  - Input: JSON with event details + entity participants
  - Output: Inserted event ID and entity-event linkages
  - Logic: Insert event → resolve entity IDs → insert entity-event bridges
- `dbo.usp_process_page_classification_output`
  - Input: JSON with page classification result
  - Output: Updated `sem.PageClassification` row

#### Impact

**High** — Without stored procedure routing with dependency ordering, Python code must orchestrate multi-table writes (more error-prone, less atomic, harder to maintain)

#### Recommended Solution

**Phase 1: Create Template Stored Procedure with Dependency Ordering**

Add subsection: **"Transactional Routing with Dependency Resolution"**

- **Example:** `dbo.usp_process_entity_extraction_output`
  ```sql
  CREATE PROCEDURE dbo.usp_process_entity_extraction_output
      @InputJson NVARCHAR(MAX),
      @LLMRunID UNIQUEIDENTIFIER,
      @SourcePageID UNIQUEIDENTIFIER
  AS
  BEGIN
      BEGIN TRANSACTION;
      
      -- Step 1: Parse JSON into staging table
      DECLARE @Entities TABLE (
          RowNum INT IDENTITY(1,1),
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
      
      -- Step 2: Identify existing entities (pre-step)
      DECLARE @EntityMapping TABLE (
          Name NVARCHAR(500),
          EntityID INT,
          IsNew BIT
      );
      
      INSERT INTO @EntityMapping (Name, EntityID, IsNew)
      SELECT e.Name, de.EntityID, 0
      FROM @Entities e
      LEFT JOIN dbo.DimEntity de ON LOWER(de.EntityName) = LOWER(e.Name)
      WHERE de.EntityID IS NOT NULL;
      
      -- Step 3: Insert missing base rows (dimensions first)
      INSERT INTO dbo.DimEntity (EntityName, PrimaryTypeInferred, PromotionState, SourcePageId, AdjudicationRunId)
      OUTPUT INSERTED.EntityName, INSERTED.EntityID, 1 INTO @EntityMapping
      SELECT e.Name, e.Type, 'staged', @SourcePageID, @LLMRunID
      FROM @Entities e
      WHERE NOT EXISTS (
          SELECT 1 FROM @EntityMapping em WHERE em.Name = e.Name
      );
      
      -- Step 4: Re-resolve IDs (now includes newly inserted)
      -- (Already captured in @EntityMapping from OUTPUT clause)
      
      -- Step 5: Insert dependent rows (if relationships exist in JSON)
      DECLARE @Relationships TABLE (
          FromEntityName NVARCHAR(500),
          ToEntityName NVARCHAR(500),
          RelationType NVARCHAR(100),
          Confidence DECIMAL(5,4)
      );
      
      INSERT INTO @Relationships (FromEntityName, ToEntityName, RelationType, Confidence)
      SELECT 
          JSON_VALUE(value, '$.from_entity'),
          JSON_VALUE(value, '$.to_entity'),
          JSON_VALUE(value, '$.relation_type'),
          JSON_VALUE(value, '$.confidence')
      FROM OPENJSON(@InputJson, '$.relationships');
      
      INSERT INTO dbo.BridgeEntityRelation (FromEntityID, ToEntityID, RelationType, Confidence, SourceLLMRunID)
      SELECT 
          em_from.EntityID,
          em_to.EntityID,
          r.RelationType,
          r.Confidence,
          @LLMRunID
      FROM @Relationships r
      INNER JOIN @EntityMapping em_from ON em_from.Name = r.FromEntityName
      INNER JOIN @EntityMapping em_to ON em_to.Name = r.ToEntityName;
      
      -- Step 6: Commit (all-or-none)
      COMMIT TRANSACTION;
  END
  ```

**Phase 2: Implement in Python (Minimal Logic)**
- **Handler:** `src/llm/handlers/entity_extraction_handler.py`
  ```python
  def handle_output(run_id, output_json, source_page_id):
      conn = get_db_connection()
      cursor = conn.cursor()
      
      # Validation only (JSON schema check)
      validate_json_schema(output_json, 'entity_extraction_v1_schema.json')
      
      # Pass to stored procedure (routing logic in SQL)
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
- Log correlation ID for tracing

**Key Principle:** Python does **validation + artifact logging + dispatch**. SQL stored procedures perform **atomic routing with dependency resolution**. Python avoids orchestration logic beyond validation and dispatch.

**Effort:** Medium (M)  
**Dependencies:** Multi-Pronged Contracts (#2), Relationship Tables (#5)

---

### 7. Observability: Structured Logging and Artifact Tracking

#### Current State

✅ **Exists:**
- **Plaintext Logging:** `logs/ingest_{timestamp}.log`, `logs/llm_runner_{timestamp}.log`
- **Run History:** `llm.run` table tracks all LLM executions with token counts, duration, errors
- **Queue Views:** `ingest.vw_queue_summary_by_source`, `sem.vw_PagesNeedingReview`

❌ **Missing:**
- **Structured Logging:** Logs are plaintext, not JSON (harder to parse, no log aggregation)
- **Distributed Tracing:** No correlation IDs across runner → LLM → storage
- **Artifact Logging Focus:** Need consistent artifact write patterns for inputs, outputs, errors

**Evidence:**
- File: `src/llm/runners/phase1_runner.py` (plaintext logging via Python `logging` module)
- File: `db/migrations/0005_create_llm_tables.sql` (llm.run table for run history)

#### Gap

❌ **Missing:**

**Structured Logging:**
- Need JSON logs with fields: `timestamp`, `level`, `message`, `correlation_id`, `job_id`, `run_id`, `worker_id`, `duration_ms`
- Consistent log format across all runners

**Tracing:**
- Need correlation ID that flows: job enqueue → job claim → LLM call → artifact write
- Correlation ID should appear in logs, database records, and artifact metadata

**Per-Run Artifacts (Focus Area):**
- Write structured artifacts to lake for each run:
  - Input evidence (content fed to LLM)
  - Output JSON (raw LLM response)
  - Error manifests (when failures occur)
- Artifacts should be traced back to run via correlation IDs
- Artifact paths should be consistent and discoverable

**What to Avoid:**
- **No Prometheus implementation details** in Phase 0-3 recommendations
- **No Grafana dashboard instructions** in near-term phases
- Metrics stacks are **optional future enhancements**, not near-term requirements

**Future Optional (Post Phase 3):**
- Time-series metrics collection (Prometheus or alternatives)
- Dashboards for queue health and LLM performance
- Alert rules for queue depth, error rates

#### Impact

**Medium** — System operational without advanced metrics, but troubleshooting harder without structured logs and consistent artifact trails

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
  
  # Example log
  logger.info("Job claimed", extra={
      "correlation_id": correlation_id,
      "job_id": job_id,
      "run_id": run_id,
      "worker_id": worker_id
  })
  ```

**Phase 2: Artifact Logging Consistency**
- **Per-Run Artifacts:** For each LLM run, write to lake:
  - `{run_id}/input.json` — Evidence bundle fed to LLM
  - `{run_id}/output.json` — Raw LLM response
  - `{run_id}/error.json` — Error manifest (if failed)
- **Correlation IDs:** Include in artifact metadata and database records
- **Lake Structure:** `lake/llm_runs/{yyyy}/{mm}/{dd}/{run_id}/`

**Phase 3: Tracing**
- **Generate Correlation ID:** At job enqueue time
- **Flow Through System:**
  - Written to `llm.job.correlation_id` (add column if needed)
  - Passed to runner when job claimed
  - Logged in all log entries for that job
  - Written to artifact metadata
  - Stored in `llm.run.correlation_id`

**Phase 4: Future Optional Observability (Post Phase 3)**
- **Optional Metrics Stack:** Time-series metrics (Prometheus, InfluxDB, or alternatives)
- **Optional Dashboards:** Grafana or similar for visualization
- **Optional Alerting:** Alert rules for queue health, error rates
- **Note:** Not actionable steps for Phase 0-3; deferred to future phases

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
| 1 | **Universal Work Queue** | LLM job queue operational | Need multi-tenant, multi-job-type model with priority management and batch selection | Medium | Create job type registry + dispatcher supporting concurrent runners and mixed job types | S | None |
| 2 | **LLM Contracts: Multi-Pronged** | Page classification contract exists | Need broad contracts for dimensions + facts + bridges + time-scoped assertions, not limited to examples | High | Define flexible JSON schemas for multi-pronged knowledge extraction with extensible taxonomies | M | #1 |
| 3 | **LLM Context Chunking** | Vector schema scaffolded | No dynamic budgeting or LLM-specific chunking strategy (independent of vector) | High | Implement chunking with token budgeting, overhead accounting, reusable for any source | M | None |
| 4 | **Multi-Entity + Best-Effort Dedupe** | Single-entity promotion works | No N-entity extraction; dedupe is best-effort, tolerate duplicates in early phases | High | Batch insertion + exact/fuzzy match; future dedupe audit capabilities | L | #2, #6 |
| 5 | **Relationships: Broad Taxonomy** | Tag assignment bridge exists | Need extensible bridges (not fixed enums) for associations, participation, location, time-bounded states, etc. | High | Create open-ended relationship tables + insertion procs with evolving taxonomy | L | #1, #2 |
| 6 | **Stored Proc Routing + Dependencies** | Queue management stored procs exist | No JSON-to-table routing with dependency ordering (resolve IDs, insert dimensions first, then bridges) | High | Template stored proc with atomic transaction and dependency resolution pattern | M | #2, #5 |
| 7 | **Observability: Artifacts + Logs** | Plaintext logging + run history table | No structured logs, correlation IDs, consistent artifact write patterns | Medium | Add JSON logging, correlation IDs, per-run artifacts; defer metrics to future | M | None |
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

### 3. Identity/Dedupe Strategy (Best-Effort Approach)

**Options:**
- **A) Exact Match Only:** Case-insensitive name comparison (fast, prevents obvious duplicates)
- **B) Fuzzy Match:** Levenshtein distance + phonetic matching (medium accuracy, some duplicates tolerated)
- **C) LLM Adjudication:** Call LLM to decide if entities are duplicates (high accuracy, slow, costly)
- **D) Phased Best-Effort:** Exact match → simple fuzzy match → tolerate duplicates → future dedupe audit

**Recommendation:** **D) Phased Best-Effort** — Minimize obvious duplicates in early phases, accept some noise, plan future "dedupe audit" capabilities

**Rationale:**
- Preventing all duplicates is **not a hard requirement** for Phase 0-2
- Exact match handles most cases (case-insensitive comparison)
- Simple fuzzy match catches obvious typos (high threshold >0.95)
- Tolerate remaining duplicates in early data
- Future: LLM contracts can mine database for duplicates and optionally relate or suppress/purge redundant records

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
