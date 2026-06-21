# Recommendations and Next Steps

**Status:** Phase 0 — Documentation Only  
**Date:** 2026-02-12  
**Purpose:** Provide a phased implementation roadmap for the LLM expansion pipeline with explicit decision points, milestones, and success criteria.

---

## Overview

This document outlines a pragmatic, incremental approach to building the LLM-driven knowledge expansion pipeline. The plan prioritizes:
- **Minimal scaffolding** before building end-to-end flows
- **One concrete contract** validated end-to-end before generalizing
- **Iterative expansion** from single entity type → relationships → broader coverage
- **Clear decision gates** between phases

---

## Phased Implementation Plan

### Phase 0: Minimal Scaffolding (LLM Job Type + Logging + Dry-Run Storage)

**Goal:** Set up infrastructure for new LLM job types without implementing full pipeline

**Duration:** 3-5 days  
**Prerequisites:** None  
**Success Criteria:** Can enqueue a new job type, run dry-run processing, and write test artifacts to lake

#### Tasks

| # | Task | Deliverable | Effort |
|---|------|-------------|--------|
| 0.1 | Create job type registry | `src/llm/jobs/registry.py` with `JobTypeDefinition` dataclass | 1 day |
| 0.2 | Create dispatcher framework | `src/llm/runners/dispatcher.py` that routes job types to handlers | 1 day |
| 0.3 | Add structured JSON logging | Configure `python-json-logger`, add correlation IDs | 1 day |
| 0.4 | Create dry-run mode | CLI flag `--dry-run` that skips DB writes, only writes to lake | 0.5 day |
| 0.5 | Add idempotency key to llm.job | Migration to add `dedupe_key` column + unique constraint | 0.5 day |

**Example Job Type Definition:**
```python
# src/llm/jobs/registry.py
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class JobTypeDefinition:
    job_type: str
    display_name: str
    prompt_template_path: str
    input_schema_path: str
    output_schema_path: str
    handler_function: Callable
    max_attempts: int = 3
    priority: int = 100

# Registry
JOB_TYPE_REGISTRY = {
    'page_classification': JobTypeDefinition(
        job_type='page_classification',
        display_name='Page Classification',
        prompt_template_path='src/llm/prompts/page_classification.py',
        input_schema_path='src/llm/contracts/page_classification_v1_input.json',
        output_schema_path='src/llm/contracts/page_classification_v1_schema.json',
        handler_function=handle_page_classification,
        max_attempts=3,
        priority=100
    ),
    # Future job types added here
}
```

**Validation:**
- Register new job type `entity_extraction_droid` with dummy handler
- Enqueue job via CLI: `python -m src.llm.cli.enqueue --job-type=entity_extraction_droid --source-page-id=abc123 --dry-run`
- Verify job written to `llm.job` table with `dedupe_key`
- Run dispatcher: `python -m src.llm.runners.dispatcher --once --dry-run`
- Verify dry-run artifacts written to `lake/llm_runs/{yyyy}/{mm}/{dd}/{run_id}/` with correlation ID in logs

---

### Phase 1: One Contract End-to-End (Droid Entity Subtype)

**Goal:** Implement full pipeline for single entity subtype (Droids) from page classification → entity extraction → entity insertion → verification

**Duration:** 1-2 weeks  
**Prerequisites:** Phase 0 complete  
**Success Criteria:** Can extract droid entities from pages, insert into `dbo.DimEntity`, verify in database

#### Tasks

| # | Task | Deliverable | Effort |
|---|------|-------------|--------|
| 1.1 | Define entity extraction contract | `src/llm/contracts/entity_extraction_v1_schema.json` with `EntityRecord` array | 2 days |
| 1.2 | Create prompt template | `src/llm/prompts/entity_extraction_droid.py` with few-shot examples | 2 days |
| 1.3 | Create batch entity insertion stored proc | `dbo.usp_batch_insert_entities` accepting JSON array | 1 day |
| 1.4 | Create entity extraction handler | `src/llm/handlers/entity_extraction_handler.py` that calls stored proc | 1 day |
| 1.5 | Register job type | Add `entity_extraction_droid` to job type registry | 0.5 day |
| 1.6 | Create seed data | 5-10 droid pages in `sources/seed/droids.json` | 0.5 day |
| 1.7 | End-to-end test | Enqueue jobs → process → verify entities in DB | 1 day |

**Entity Extraction Contract (v1) — Illustrative Example:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EntityExtractionV1Output",
  "type": "object",
  "required": ["entities"],
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "type", "confidence"],
        "properties": {
          "name": {"type": "string", "maxLength": 500},
          "type": {
            "type": "string",
            "description": "Open-ended type string, not limited to enumerated examples. Can be any dimension, fact, or knowledge type."
          },
          "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
          "attributes": {
            "type": "object",
            "additionalProperties": true,
            "description": "Flexible JSON for any extracted attributes. Schema evolves with domain knowledge."
          }
        }
      }
    },
    "relationships": {
      "type": "array",
      "description": "Optional: relationships extracted alongside entities",
      "items": {
        "type": "object",
        "required": ["from_entity", "to_entity", "relation_type", "confidence"],
        "properties": {
          "from_entity": {"type": "string"},
          "to_entity": {"type": "string"},
          "relation_type": {
            "type": "string",
            "description": "Open-ended relationship type, not enumerated. Examples: owned_by, member_of, located_in, appeared_in, etc."
          },
          "start_date": {"type": ["string", "null"]},
          "end_date": {"type": ["string", "null"]},
          "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
        }
      }
    }
  }
}
```

**Note:** This is an **illustrative example**. Actual contract should be flexible:
- `type` is open string, not fixed enum (examples: "Droid", "PersonCharacter", "Event", "Concept", "Appearance", etc.)
- Supports multiple output families: dimensions, facts, bridges, attributes, time-scoped assertions
- Schema should be discovered from repository (`src/llm/contracts/`), not derived from this example

**Example Prompt Template:**
```python
# src/llm/prompts/entity_extraction_droid.py
SYSTEM_PROMPT = """You are an expert in Star Wars lore. Extract all droid entities mentioned in the provided text.

For each droid, provide:
- name: Full droid name or designation (e.g., "R2-D2", "C-3PO")
- type: "Droid" (or more specific if known)
- confidence: 0.0-1.0 (1.0 if explicitly named, <0.8 if vague mention)
- attributes: JSON object with any mentioned details (model, affiliation, owner, etc.)

Optionally extract relationships if mentioned (e.g., "owned_by", "accompanied_by").

Output ONLY valid JSON. No markdown formatting."""

FEW_SHOT_EXAMPLES = [
    {
        "input": "R2-D2 is an astromech droid owned by Luke Skywalker.",
        "output": {
            "entities": [
                {
                    "name": "R2-D2",
                    "type": "Droid",
                    "confidence": 1.0,
                    "attributes": {
                        "model": "astromech",
                        "owner": "Luke Skywalker"
                    }
                }
            ],
            "relationships": [
                {
                    "from_entity": "R2-D2",
                    "to_entity": "Luke Skywalker",
                    "relation_type": "owned_by",
                    "confidence": 1.0
                }
            ]
        }
    }
]
```

**Validation:**
1. **Dry-Run Test:** Process 5 droid pages in dry-run mode, verify JSON output matches schema
2. **Insertion Test:** Process 1 droid page, verify entity inserted into `dbo.DimEntity` with:
   - `EntityName` = extracted name
   - `PrimaryTypeInferred` = "Droid" (or other type)
   - `PromotionState` = "staged"
   - `AdjudicationRunId` = LLM run ID
3. **Idempotency Test:** Re-enqueue same page, verify duplicate prevented by `dedupe_key`

---

### Phase 2: Relationships + Multi-Output Routing

**Goal:** Extend pipeline to extract entity relationships and route outputs to multiple tables (entities + relationships)

**Duration:** 2-3 weeks  
**Prerequisites:** Phase 1 complete  
**Success Criteria:** Can extract droid entities + their relationships (e.g., "R2-D2 owned by Luke Skywalker") and insert into `dbo.DimEntity` + `dbo.BridgeEntityRelation`

#### Tasks

| # | Task | Deliverable |
|---|------|-------------|
| 2.1 | Create relationship tables | Migration `0027_create_relationship_bridges.sql` for `BridgeEntityRelation`, `DimEvent`, `BridgeEntityEvent`, `DimWork`, `BridgeEntityWork` |
| 2.2 | Define relationship extraction contract | `src/llm/contracts/relationship_extraction_v1_output.json` |
| 2.3 | Create relationship prompt template | `src/llm/interrogations/definitions/relationship_extraction.py` |
| 2.4 | Create relationship insertion stored proc | `dbo.usp_batch_insert_entity_relations` accepting JSON array |
| 2.5 | Create relationship extraction handler | `src/llm/handlers/relationship_extraction.py` that validates and persists relationships |
| 2.6 | Register relationship job type | Add `relationship_extraction` to job type registry |
| 2.7 | End-to-end test | Extract entities + relationships from 5 pages, verify both tables populated |

**Relationship Extraction Contract (v1) — Illustrative Example:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RelationshipExtractionV1Output",
  "type": "object",
  "required": ["relationships"],
  "properties": {
    "relationships": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["from_entity", "to_entity", "relation_type", "confidence"],
        "properties": {
          "from_entity": {"type": "string", "maxLength": 500},
          "to_entity": {"type": "string", "maxLength": 500},
          "relation_type": {
            "type": "string",
            "description": "Open-ended relationship type. Examples: owned_by, member_of, ally_of, enemy_of, created_by, located_in, participated_in, visited_in, trained_by, accompanied_by, appeared_in, etc. Taxonomy evolves; not limited to these examples."
          },
          "start_date": {"type": ["string", "null"]},
          "end_date": {"type": ["string", "null"]},
          "work_context": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional: works/media where relationship is depicted or mentioned"
          },
          "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
        }
      }
    }
  }
}
```

**Note:** This is an **illustrative example**. Actual contract should be flexible:
- `relation_type` is open string, **not fixed enum**
- Relationship taxonomy evolves; examples are not exhaustive
- Supports broad relationship types: associations, participation, location, membership, ownership, appearance, time-bounded states
- Time-scoped assertions encouraged (start/end dates or work context)

**Combined Stored Procedure:**
```sql
-- dbo.usp_process_combined_extraction_output
CREATE PROCEDURE dbo.usp_process_combined_extraction_output
    @EntitiesJson NVARCHAR(MAX),
    @RelationshipsJson NVARCHAR(MAX),
    @LLMRunID UNIQUEIDENTIFIER,
    @SourcePageID UNIQUEIDENTIFIER
AS
BEGIN
    BEGIN TRANSACTION;
    
    -- 1. Insert entities (return IDs)
    DECLARE @EntityIDs TABLE (Name NVARCHAR(500), EntityID INT);
    
    -- Parse entities JSON, insert, capture IDs
    -- (detailed implementation omitted for brevity)
    
    -- 2. Resolve entity name → EntityID for relationships
    -- 3. Insert relationships
    INSERT INTO dbo.BridgeEntityRelation (FromEntityID, ToEntityID, RelationType, ...)
    SELECT ...;
    
    COMMIT TRANSACTION;
END
```

**Validation:**
1. **Relationship Test:** Extract "R2-D2 owned by Luke Skywalker" relationship
2. **Verify Tables:**
   - `dbo.DimEntity`: 2 rows (R2-D2, Luke Skywalker)
   - `dbo.BridgeEntityRelation`: 1 row (R2-D2 → Luke Skywalker, relation_type='owned_by')
3. **Query Test:** `SELECT * FROM dbo.BridgeEntityRelation WHERE RelationType = 'owned_by'`

---

### Phase 3: Broader Coverage + Automated Backfill

**Goal:** Expand to all entity types (PersonCharacter, LocationPlace, etc.) and implement bulk backfill tooling

**Duration:** 3-4 weeks  
**Prerequisites:** Phase 2 complete  
**Success Criteria:** Can process all page types, bulk re-process low-confidence classifications, monitor queue health

#### Tasks

| # | Task | Deliverable |
|---|------|-------------|
| 3.1 | Generalize entity extraction prompt | `src/llm/prompts/entity_extraction_generic.py` that handles all entity types |
| 3.2 | Create backfill CLI | `src/llm/cli/backfill.py` with commands for bulk re-enqueue |
| 3.3 | Add queue depth monitoring | SQL view `llm.vw_queue_health` with depth by status and age |
| 3.4 | Implement priority escalation | Background job or CLI command to auto-escalate old jobs |
| 3.5 | Create event/work extraction contracts | `event_extraction_v1_schema.json`, `work_extraction_v1_schema.json` |
| 3.6 | Create event/work prompt templates | `src/llm/prompts/event_extraction.py`, `work_extraction.py` |
| 3.7 | Create event/work insertion stored procs | `dbo.usp_insert_event`, `dbo.usp_insert_entity_work_appearance` |
| 3.8 | Register event/work job types | Add to job type registry + handlers |
| 3.9 | Bulk backfill test | Re-process 100 low-confidence pages, verify improvements |

**Backfill CLI Example:**
```bash
# Re-process pages with confidence < 0.7
python -m src.llm.cli.backfill entities \
  --entity-type=PersonCharacter \
  --confidence-threshold=0.7 \
  --max-jobs=100

# Re-extract relationships for specific date range
python -m src.llm.cli.backfill relationships \
  --date-range=2024-01-01..2024-12-31 \
  --priority=200
```

**Queue Health View:**
```sql
-- llm.vw_queue_health
CREATE VIEW llm.vw_queue_health AS
SELECT 
    status,
    COUNT(*) AS job_count,
    AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS avg_age_minutes,
    MAX(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS max_age_minutes
FROM llm.job
GROUP BY status;
```

**Validation:**
1. **Coverage Test:** Process 10 pages of each entity type (PersonCharacter, LocationPlace, etc.)
2. **Backfill Test:** Re-enqueue 50 low-confidence pages, verify jobs created with higher priority
3. **Monitoring Test:** Query `llm.vw_queue_health`, verify queue depth < 100 and max age < 60 minutes

---

## Decision Points (Explicit Choices Required)

### Decision Point 1: JSON Schema for LLM Outputs

**Timeline:** Before Phase 1 starts  
**Stakeholders:** Tech Lead, LLM Engineer  
**Options:** Strict schema vs flexible schema vs hybrid (see [04-functional-gap-analysis.md](04-functional-gap-analysis.md#1-json-schema-for-llm-outputs))

**Recommendation:** **Hybrid** — Core attributes typed (name, type, confidence), extended attributes in JSON `attributes` field

**Rationale:**
- Typed fields enable SQL queries and constraints
- JSON `attributes` allows easy extension without schema migrations
- Best of both worlds: type safety + flexibility

**Decision:**
- [ ] Approved by: ___________  
- [ ] Date: ___________

---

### Decision Point 2: LLM Context Chunking & Budgeting Strategy

**Timeline:** Before Phase 1 (needed for reliable LLM extraction)  
**Stakeholders:** Tech Lead, LLM Engineer  
**Options:** Fixed-size vs sentence-boundary vs semantic chunking; static vs dynamic budgeting

**Recommendation:** **Sentence-boundary-aware fixed-size chunking with dynamic token budgeting**

**Rationale:**
- **LLM context chunking is needed regardless of vector use:** Required for reliable extraction from long sources, not just for vector retrieval
- **Dynamic budgeting accounts for model constraints:**
  - Estimate available tokens: model window - (system prompt + contract + output buffer + safety margin)
  - Adjust chunk size based on available budget
  - Degrade gracefully for smaller context models
- **Sentence boundaries prevent mid-sentence cuts:** Improves coherence and extraction quality
- **Overlap ensures no information loss** at chunk boundaries
- **Reusable for any unstructured/semi-structured source**

**Parameters:**
```yaml
chunking:
  strategy: sentence_boundary_fixed_with_budgeting
  # Dynamic calculation based on model
  model_context_window: 128000  # tokens (model-specific)
  system_prompt_tokens: 1500
  contract_overhead_tokens: 300
  output_buffer_tokens: 3000
  safety_margin_percent: 15
  # Resulting chunk parameters
  max_chunk_tokens: 8000       # Cap for reliability
  overlap_tokens: 1000
  min_chunk_tokens: 2000
  chars_per_token_estimate: 4  # Rough heuristic
```

**Note:** Chunking for LLM context is a **general strategy**, not vector-specific. Vector tables exist but are not the primary driver in Phase 0-2.

**Decision:**
- [ ] Approved by: ___________  
- [ ] Date: ___________

---

### Decision Point 3: Identity Resolution Strategy (Best-Effort)

**Timeline:** Before Phase 2 (multi-entity extraction)  
**Stakeholders:** Tech Lead, Domain Expert  
**Options:** Exact match only vs fuzzy match vs LLM adjudication vs phased best-effort

**Recommendation:** **Phased Best-Effort** — Exact match → simple fuzzy match → tolerate duplicates → future dedupe audit

**Rationale:**
- **Not a hard requirement to prevent all duplicates** in Phase 0-2
- Exact match handles most cases (case-insensitive name comparison)
- Simple fuzzy match catches obvious typos (threshold >0.95)
- **Tolerate some duplicates** in early data; noise is acceptable
- Future: LLM contracts can mine database for duplicates and optionally relate or suppress/purge redundant records

**Thresholds:**
- Exact match: Case-insensitive name comparison (fast, prevents obvious duplicates)
- Fuzzy match: High threshold only (>0.95 similarity) for obvious typos
- Accept duplicates below threshold (no blocking)
- Future: Dedupe audit job type for post-processing

**Decision:**
- [ ] Approved by: ___________  
- [ ] Date: ___________

---

### Decision Point 4: Stored Procedure Design

**Timeline:** Before Phase 1 ends  
**Stakeholders:** Tech Lead, DBA  
**Options:** One universal proc vs many specific procs vs hybrid

**Recommendation:** **Many specific procs** — One proc per job type (e.g., `dbo.usp_process_entity_extraction_output`)

**Rationale:**
- Clear contracts (each proc has well-defined input/output)
- Easier to test (unit test each proc independently)
- Avoid monolithic stored procedure with complex branching logic
- Easier to version (change one proc without affecting others)

**Naming Convention:**
```
dbo.usp_process_{job_type}_output
```

**Examples:**
- `dbo.usp_process_entity_extraction_output`
- `dbo.usp_process_relationship_extraction_output`
- `dbo.usp_process_event_extraction_output`

**Decision:**
- [ ] Approved by: ___________  
- [ ] Date: ___________

---

### Decision Point 5: Priority Escalation Workflow

**Timeline:** Before Phase 3 (backfill)  
**Stakeholders:** Tech Lead, Product Owner  
**Options:** Manual vs CLI utility vs automated SLA vs UI-driven

**Recommendation:** **CLI Utility + Automated SLA** — Balance manual control and automation

**Rationale:**
- CLI utility gives operators immediate control (e.g., "bump priority for all PersonCharacter entities")
- Automated SLA prevents starvation (jobs queued >24 hours auto-escalate)
- UI-driven workflow deferred to Phase 4 (governance)

**CLI Commands:**
```bash
# Manual priority bump
python -m src.llm.cli.priority bump --entity-type=PersonCharacter --priority=200

# Automated SLA check (run via cron)
python -m src.llm.cli.priority auto-escalate --sla-hours=24 --bump=50
```

**Decision:**
- [ ] Approved by: ___________  
- [ ] Date: ___________

---

## Success Metrics (Per Phase)

### Phase 0 Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Job types registered | ≥ 2 | Count entries in `JOB_TYPE_REGISTRY` |
| Dry-run jobs enqueued | ≥ 5 | Count rows in `llm.job` with dry-run flag |
| Artifacts written to lake | ≥ 5 runs | Count directories in `lake/llm_runs/{yyyy}/{mm}/{dd}/` |
| Correlation IDs in logs | 100% | Grep logs for `correlation_id` field |

### Phase 1 Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Droid entities extracted | ≥ 10 | Count rows in `dbo.DimEntity` where `PrimaryTypeInferred = 'Droid'` |
| Extraction success rate | ≥ 90% | `COUNT(status='SUCCEEDED') / COUNT(*)` in `llm.job` |
| Duplicate prevention | 100% | Re-enqueue same page, verify dedupe_key constraint violation |
| Average extraction time | < 30 sec | `AVG(DATEDIFF(SECOND, started_at, completed_at))` in `llm.run` |

### Phase 2 Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Relationships extracted | ≥ 20 | Count rows in `dbo.BridgeEntityRelation` |
| Multi-table write success | 100% | All relationships have valid `FromEntityID` and `ToEntityID` |
| Transaction rollback rate | < 5% | Count failed transactions in stored proc logs |

### Phase 3 Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Entity types covered | All 12 types | Count distinct `PrimaryTypeInferred` in `dbo.DimEntity` |
| Backfill throughput | ≥ 100 jobs/hour | Monitor backfill CLI output |
| Queue depth | < 100 jobs | Query `llm.vw_queue_health` |
| SLA compliance | ≥ 95% | `COUNT(age < 24 hours) / COUNT(*)` in pending jobs |

---

## Risk Mitigation Plan

### Risk 1: LLM Output Quality Degradation

**Scenario:** LLM produces low-quality outputs (wrong entity types, low confidence, hallucinations)

**Mitigation:**
- **Pre-Flight Test:** Run dry-run on 20 sample pages, manually review outputs for quality
- **Confidence Thresholds:** Set conservative thresholds (≥ 0.9 for auto-promotion, < 0.7 for manual review)
- **Few-Shot Prompts:** Include 3-5 high-quality examples in every prompt
- **Prompt Versioning:** Track prompt version in `llm.job`, allow A/B testing of prompt changes

**Monitoring:**
- Weekly review of low-confidence outputs (< 0.5)
- Plot confidence distribution histogram (expect peak at 0.9+)

---

### Risk 2: Database Performance Degradation

**Scenario:** Large-scale entity insertion causes deadlocks or slow queries

**Mitigation:**
- **Batch Insertion:** Use `dbo.usp_batch_insert_entities` for bulk inserts (not row-by-row)
- **Index Optimization:** Add indexes on `dbo.DimEntity.EntityName`, `dbo.BridgeEntityRelation.FromEntityID`, `ToEntityID`
- **Partitioning:** If `dbo.DimEntity` exceeds 1M rows, consider table partitioning by `PrimaryTypeInferred`
- **Connection Pooling:** Use SQLAlchemy connection pool to avoid connection exhaustion

**Monitoring:**
- Monitor SQL Server DMVs for slow queries (`sys.dm_exec_query_stats`)
- Set alert if average query time > 5 seconds

---

### Risk 3: Backfill Queue Overload

**Scenario:** Bulk backfill enqueues 10,000+ jobs, saturates queue

**Mitigation:**
- **Rate Limiting:** Backfill CLI enqueues max 100 jobs/minute
- **Priority Tuning:** Backfill jobs lower priority than real-time ingestion (priority = 50 vs 100)
- **Batch Processing:** Process backfill jobs in batches of 500, pause between batches
- **Circuit Breaker:** If queue depth > 1000, pause backfill until queue drains

**Monitoring:**
- Track queue depth hourly (`llm.vw_queue_health`)
- Alert if queue depth > 500 for > 1 hour

---

## Rollback Plan (Per Phase)

### Phase 0 Rollback

**Scenario:** Dispatcher or job type registry causes critical errors

**Rollback Steps:**
1. Stop all LLM runners: `docker compose stop llm-runner`
2. Revert migration `0025_add_dedupe_key.sql` (if applied): `DROP INDEX UX_job_dedupe_key ON llm.job; ALTER TABLE llm.job DROP COLUMN dedupe_key;`
3. Deploy previous code version (before Phase 0)
4. Restart runners: `docker compose start llm-runner`

**Data Loss:** Minimal (no data deleted, only new columns dropped)

---

### Phase 1 Rollback

**Scenario:** Entity extraction produces incorrect results, need to revert

**Rollback Steps:**
1. Stop all LLM runners
2. Delete extracted entities: `DELETE FROM dbo.DimEntity WHERE AdjudicationRunId IN (SELECT run_id FROM llm.run WHERE job_type = 'entity_extraction_droid');`
3. Mark jobs for re-processing: `UPDATE llm.job SET status = 'NEW', current_attempt = 0 WHERE job_type = 'entity_extraction_droid';`
4. Deploy previous code version (before Phase 1)
5. Restart runners

**Data Loss:** All droid entities extracted in Phase 1 (acceptable, can re-run)

---

### Phase 2 Rollback

**Scenario:** Relationship extraction causes foreign key violations or incorrect links

**Rollback Steps:**
1. Stop all LLM runners
2. Delete relationships: `DELETE FROM dbo.BridgeEntityRelation WHERE SourceLLMRunID IN (SELECT run_id FROM llm.run WHERE job_type = 'entity_and_relationship_extraction');`
3. Optionally delete entities if corrupted
4. Mark jobs for re-processing
5. Deploy previous code version (before Phase 2)
6. Restart runners

**Data Loss:** All relationships extracted in Phase 2 (acceptable, can re-run)

---

## Long-Term Roadmap (Post Phase 3)

### Phase 4: Governance + Human Review UI (Optional)

**Timeline:** 4-6 weeks  
**Goal:** Build web UI for human review of low-confidence entities, approval workflow, audit trail

**Tasks:**
- Build Flask/FastAPI web app with `/review/queue` and `/review/{entity_id}` endpoints
- Implement approval workflow (approve/reject/override)
- Create audit table `dbo.AuditEntityAdjudication`
- Add role-based access control (reviewer, admin)

---

### Phase 5: Advanced Chunking + Vector Retrieval

**Timeline:** 3-4 weeks  
**Goal:** Implement semantic chunking, vector embedding, and similarity search for evidence retrieval

**Tasks:**
- Implement sentence-boundary chunker
- Integrate Ollama embedding API (nomic-embed-text model)
- Populate `vector.chunk` and `vector.embedding` tables
- Implement top-K similarity search for evidence assembly

---

### Phase 6: Event + Work Extraction

**Timeline:** 4-5 weeks  
**Goal:** Extract events (battles, treaties) and works (films, novels) with entity participation

**Tasks:**
- Create `dbo.DimEvent` and `dbo.BridgeEntityEvent` tables
- Create `dbo.DimWork` and `dbo.BridgeEntityWork` tables
- Implement event/work extraction prompts and handlers
- Bulk backfill events and works from existing pages

---

### Phase 7: Automated Testing + CI/CD

**Timeline:** 2-3 weeks  
**Goal:** Add comprehensive test suite, integrate with GitHub Actions for automated testing

**Tasks:**
- Unit tests for all handlers, stored procedures, and utilities
- Integration tests for end-to-end flows
- Contract tests for JSON schemas (validate examples against schemas)
- GitHub Actions workflow for CI/CD (run tests on PR, deploy on merge)

---

## Appendix: Example Queries

### Query 1: List All Droid Entities with Confidence

```sql
SELECT 
    EntityID,
    EntityName,
    PrimaryTypeInferred,
    PromotionState,
    lr.status AS LLMRunStatus,
    lr.model_name AS Model,
    lr.prompt_tokens,
    lr.completion_tokens
FROM dbo.DimEntity de
LEFT JOIN llm.run lr ON de.AdjudicationRunId = lr.run_id
WHERE de.PrimaryTypeInferred = 'Droid'
ORDER BY de.EntityName;
```

### Query 2: List All Entity Relationships

```sql
SELECT 
    fe.EntityName AS FromEntity,
    te.EntityName AS ToEntity,
    ber.RelationType,
    ber.Confidence,
    lr.model_name AS ExtractedByModel,
    lr.completed_at AS ExtractedAt
FROM dbo.BridgeEntityRelation ber
JOIN dbo.DimEntity fe ON ber.FromEntityID = fe.EntityID
JOIN dbo.DimEntity te ON ber.ToEntityID = te.EntityID
LEFT JOIN llm.run lr ON ber.SourceLLMRunID = lr.run_id
ORDER BY ber.Confidence DESC, fe.EntityName, te.EntityName;
```

### Query 3: Queue Health Report

```sql
SELECT 
    status,
    job_type,
    COUNT(*) AS job_count,
    AVG(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS avg_age_minutes,
    MAX(DATEDIFF(MINUTE, created_at, GETUTCDATE())) AS max_age_minutes,
    MIN(priority) AS min_priority,
    MAX(priority) AS max_priority
FROM llm.job
WHERE status IN ('NEW', 'RUNNING', 'FAILED')
GROUP BY status, job_type
ORDER BY status, job_type;
```

### Query 4: LLM Performance Metrics

```sql
SELECT 
    lr.status,
    lr.model_name,
    COUNT(*) AS run_count,
    AVG(DATEDIFF(SECOND, lr.started_at, lr.completed_at)) AS avg_duration_seconds,
    AVG(lr.prompt_tokens) AS avg_prompt_tokens,
    AVG(lr.completion_tokens) AS avg_completion_tokens,
    SUM(lr.prompt_tokens + lr.completion_tokens) AS total_tokens
FROM llm.run lr
WHERE lr.started_at >= DATEADD(DAY, -7, GETUTCDATE())
GROUP BY lr.status, lr.model_name
ORDER BY lr.status, lr.model_name;
```

---

## Illustrative Examples: Multi-Pronged Extraction with Time-Awareness

**Important:** These examples are **descriptive** to demonstrate multi-output extraction patterns. They use fictional but plausible Star Wars content. Actual schemas, table structures, and contracts should be discovered from the repository, not derived from these examples.

---

### Example A: Dagobah Page (Location-Centric, Time-Bounded Relationships)

**Context:** A wiki page about Dagobah contains rich information about the location, visitors, time periods, and associated works.

#### Sample Raw Text Blob

```
Dagobah is a remote, swampy planet in the Sluis sector of the Outer Rim. 
The planet is covered in murky swamps, twisted vegetation, and is home to 
many dangerous creatures. Yoda, the Jedi Master, chose Dagobah as his place 
of exile following the fall of the Jedi Order in 19 BBY (depicted in 
"Revenge of the Sith").

During the Galactic Civil War, Luke Skywalker traveled to Dagobah in 3 ABY 
to seek training from Yoda, crash-landing his X-Wing in the swamps (events 
shown in "The Empire Strikes Back"). Luke returned briefly in 4 ABY before 
Yoda's death ("Return of the Jedi").

R2-D2 accompanied Luke on both visits. Yoda's simple dwelling, a small hut 
near the crash site, served as Luke's training ground. The planet's dark 
side cave is a focal point for Jedi trials.
```

#### Example Output JSON (Multi-Pronged)

```json
{
  "dimensions": [
    {
      "type": "Location",
      "name": "Dagobah",
      "attributes": {
        "location_type": "planet",
        "sector": "Sluis sector",
        "region": "Outer Rim",
        "terrain": "swamp, wetland",
        "notable_features": ["dark side cave", "Yoda's hut"]
      },
      "confidence": 1.0
    },
    {
      "type": "PersonCharacter",
      "name": "Yoda",
      "attributes": {
        "title": "Jedi Master",
        "affiliation": "Jedi Order"
      },
      "confidence": 1.0
    },
    {
      "type": "PersonCharacter",
      "name": "Luke Skywalker",
      "attributes": {
        "affiliation": "Rebel Alliance",
        "training": "Jedi apprentice"
      },
      "confidence": 1.0
    },
    {
      "type": "Droid",
      "name": "R2-D2",
      "attributes": {
        "model": "astromech"
      },
      "confidence": 1.0
    },
    {
      "type": "VehicleCraft",
      "name": "X-Wing",
      "attributes": {
        "vehicle_type": "starfighter"
      },
      "confidence": 0.95
    },
    {
      "type": "LocationPlace",
      "name": "Yoda's hut",
      "attributes": {
        "structure_type": "dwelling",
        "location_context": "Dagobah swamp"
      },
      "confidence": 0.9
    }
  ],
  "relationships": [
    {
      "from_entity": "Yoda",
      "to_entity": "Dagobah",
      "relation_type": "resided_in",
      "start_date": "19 BBY",
      "end_date": "4 ABY",
      "work_context": ["Revenge of the Sith", "The Empire Strikes Back", "Return of the Jedi"],
      "confidence": 1.0
    },
    {
      "from_entity": "Luke Skywalker",
      "to_entity": "Dagobah",
      "relation_type": "visited_in",
      "start_date": "3 ABY",
      "end_date": "3 ABY",
      "work_context": ["The Empire Strikes Back"],
      "confidence": 1.0
    },
    {
      "from_entity": "Luke Skywalker",
      "to_entity": "Dagobah",
      "relation_type": "visited_in",
      "start_date": "4 ABY",
      "end_date": "4 ABY",
      "work_context": ["Return of the Jedi"],
      "confidence": 1.0
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Dagobah",
      "relation_type": "visited_in",
      "start_date": "3 ABY",
      "end_date": "4 ABY",
      "work_context": ["The Empire Strikes Back", "Return of the Jedi"],
      "confidence": 0.95
    },
    {
      "from_entity": "Luke Skywalker",
      "to_entity": "Yoda",
      "relation_type": "trained_by",
      "start_date": "3 ABY",
      "end_date": "4 ABY",
      "work_context": ["The Empire Strikes Back", "Return of the Jedi"],
      "confidence": 1.0
    },
    {
      "from_entity": "Luke Skywalker",
      "to_entity": "R2-D2",
      "relation_type": "accompanied_by",
      "start_date": "3 ABY",
      "end_date": "4 ABY",
      "work_context": ["The Empire Strikes Back", "Return of the Jedi"],
      "confidence": 0.95
    },
    {
      "from_entity": "X-Wing",
      "to_entity": "Dagobah",
      "relation_type": "located_in",
      "start_date": "3 ABY",
      "end_date": null,
      "work_context": ["The Empire Strikes Back"],
      "notes": "crashed in swamp",
      "confidence": 0.9
    }
  ],
  "work_references": [
    {
      "work_name": "Revenge of the Sith",
      "work_type": "film",
      "context": "Yoda's exile to Dagobah depicted"
    },
    {
      "work_name": "The Empire Strikes Back",
      "work_type": "film",
      "context": "Luke's training on Dagobah"
    },
    {
      "work_name": "Return of the Jedi",
      "work_type": "film",
      "context": "Luke's return, Yoda's death"
    }
  ]
}
```

**Key Observations:**
- Multiple output families: Location dimension, Character dimensions, Droid dimension, Vehicle dimension, Structure dimension
- Multiple relationship types: `resided_in`, `visited_in`, `trained_by`, `accompanied_by`, `located_in`
- Time-scoped assertions: Most relationships include start/end dates or work-bounded ranges
- Work context: Relationships tied to specific films/media
- Confidence scoring: Varies based on explicitness of source text

---

### Example B: R2-D2 Ownership Over Time (Timeframe-Driven Relationships)

**Context:** A wiki page about R2-D2's ownership history demonstrates how relationships change over time.

#### Sample Raw Text Blob

```
R2-D2, an astromech droid manufactured by Industrial Automaton, has had 
several owners throughout the Star Wars saga.

Initially, R2-D2 served the Royal House of Naboo during the Trade Federation 
blockade in 32 BBY ("The Phantom Menace"). After the Battle of Naboo, R2-D2 
became the property of Padmé Amidala, serving her through the Clone Wars era 
(22-19 BBY, depicted in "Attack of the Clones" and "Revenge of the Sith").

Following Padmé's death in 19 BBY, R2-D2 came into the possession of Bail 
Organa briefly before being assigned to Captain Raymus Antilles aboard the 
Tantive IV. In 0 BBY, R2-D2 was entrusted to Princess Leia Organa with the 
Death Star plans ("A New Hope").

After the destruction of the first Death Star, R2-D2 became Luke Skywalker's 
astromech droid, serving him from 0 BBY through the end of the Galactic 
Civil War in 4 ABY ("The Empire Strikes Back", "Return of the Jedi"). 
R2-D2 remained with Luke during the formation of the New Republic and the 
Jedi Order's attempted revival.

Note: Throughout these periods, C-3PO frequently accompanied R2-D2, though 
C-3PO's ownership sometimes diverged.
```

#### Example Output JSON (Multi-Pronged, Time-Bounded)

```json
{
  "dimensions": [
    {
      "type": "Droid",
      "name": "R2-D2",
      "attributes": {
        "model": "astromech",
        "manufacturer": "Industrial Automaton",
        "designation": "R2-D2"
      },
      "confidence": 1.0
    },
    {
      "type": "Organization",
      "name": "Royal House of Naboo",
      "attributes": {
        "type": "government",
        "planet": "Naboo"
      },
      "confidence": 0.95
    },
    {
      "type": "PersonCharacter",
      "name": "Padmé Amidala",
      "attributes": {
        "title": "Queen, Senator",
        "affiliation": "Galactic Republic"
      },
      "confidence": 1.0
    },
    {
      "type": "PersonCharacter",
      "name": "Bail Organa",
      "attributes": {
        "title": "Senator",
        "affiliation": "Rebel Alliance"
      },
      "confidence": 0.95
    },
    {
      "type": "PersonCharacter",
      "name": "Raymus Antilles",
      "attributes": {
        "title": "Captain",
        "affiliation": "Rebel Alliance"
      },
      "confidence": 0.9
    },
    {
      "type": "PersonCharacter",
      "name": "Princess Leia Organa",
      "attributes": {
        "title": "Princess",
        "affiliation": "Rebel Alliance"
      },
      "confidence": 1.0
    },
    {
      "type": "PersonCharacter",
      "name": "Luke Skywalker",
      "attributes": {
        "title": "Jedi Knight",
        "affiliation": "Rebel Alliance"
      },
      "confidence": 1.0
    },
    {
      "type": "Droid",
      "name": "C-3PO",
      "attributes": {
        "model": "protocol droid"
      },
      "confidence": 0.95
    }
  ],
  "relationships": [
    {
      "from_entity": "R2-D2",
      "to_entity": "Royal House of Naboo",
      "relation_type": "owned_by",
      "start_date": "32 BBY",
      "end_date": "32 BBY",
      "work_context": ["The Phantom Menace"],
      "notes": "During Trade Federation blockade",
      "confidence": 0.95
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Padmé Amidala",
      "relation_type": "owned_by",
      "start_date": "32 BBY",
      "end_date": "19 BBY",
      "work_context": ["Attack of the Clones", "Revenge of the Sith"],
      "notes": "Through Clone Wars era",
      "confidence": 1.0
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Bail Organa",
      "relation_type": "owned_by",
      "start_date": "19 BBY",
      "end_date": "19 BBY",
      "work_context": ["Revenge of the Sith"],
      "notes": "Briefly after Padmé's death",
      "confidence": 0.9
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Raymus Antilles",
      "relation_type": "assigned_to",
      "start_date": "19 BBY",
      "end_date": "0 BBY",
      "work_context": ["A New Hope"],
      "notes": "Aboard Tantive IV",
      "confidence": 0.85
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Princess Leia Organa",
      "relation_type": "entrusted_to",
      "start_date": "0 BBY",
      "end_date": "0 BBY",
      "work_context": ["A New Hope"],
      "notes": "Carrying Death Star plans",
      "confidence": 1.0
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Luke Skywalker",
      "relation_type": "owned_by",
      "start_date": "0 BBY",
      "end_date": null,
      "work_context": ["A New Hope", "The Empire Strikes Back", "Return of the Jedi"],
      "notes": "Astromech droid through Galactic Civil War and beyond",
      "confidence": 1.0
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "C-3PO",
      "relation_type": "accompanied_by",
      "start_date": "32 BBY",
      "end_date": null,
      "work_context": ["multiple"],
      "notes": "Frequently together, ownership sometimes diverged",
      "confidence": 0.9
    }
  ],
  "work_references": [
    {
      "work_name": "The Phantom Menace",
      "work_type": "film"
    },
    {
      "work_name": "Attack of the Clones",
      "work_type": "film"
    },
    {
      "work_name": "Revenge of the Sith",
      "work_type": "film"
    },
    {
      "work_name": "A New Hope",
      "work_type": "film"
    },
    {
      "work_name": "The Empire Strikes Back",
      "work_type": "film"
    },
    {
      "work_name": "Return of the Jedi",
      "work_type": "film"
    }
  ],
  "temporal_notes": [
    {
      "entity": "R2-D2",
      "assertion": "Ownership without timeframe is incomplete",
      "explanation": "R2-D2 had multiple owners across different time periods and works. Each ownership relationship requires temporal bounds (start/end dates or work context) to be meaningful."
    }
  ]
}
```

**Key Observations:**
- **Time-bounded relationships are essential:** "R2-D2 owned_by Luke" without timeframe is incomplete and potentially misleading
- Multiple relationship types: `owned_by`, `assigned_to`, `entrusted_to`, `accompanied_by`
- Overlapping timeframes: Some relationships transition directly, others overlap
- Work context provides additional temporal anchoring
- `end_date: null` indicates ongoing or open-ended relationships
- Confidence varies based on explicitness of ownership claims
- Relationship type evolves: `owned_by` vs `assigned_to` vs `entrusted_to` reflects nuanced ownership semantics

---

**Examples Summary:**

These examples demonstrate:
1. **Multi-pronged output:** Dimensions (locations, characters, droids, vehicles) + Relationships (bridges) + Work references in single extraction
2. **Time-scoped assertions:** Most relationships include temporal bounds (start/end dates or work-bounded ranges)
3. **Extensible taxonomy:** Relationship types are open-ended strings (`resided_in`, `visited_in`, `trained_by`, `owned_by`, `entrusted_to`, etc.), not fixed enums
4. **Work context anchoring:** Relationships tied to specific films/media provide additional temporal context
5. **Incomplete without time:** Examples show that assertions like "Luke owned R2-D2" are meaningless without timeframe

**Reminder:** These are **illustrative examples only**. Actual schemas, table structures, and contracts should be discovered from the repository (`db/migrations/`, `src/llm/contracts/`, etc.), not derived from these examples.

---

## Related Documentation

- [01-current-state-inventory.md](01-current-state-inventory.md) — Repository and SQL artifact inventory
- [02-data-model-map.md](02-data-model-map.md) — Data model and ERD
- [03-workflow-and-runner-map.md](03-workflow-and-runner-map.md) — Workflow and runner orchestration
- [04-functional-gap-analysis.md](04-functional-gap-analysis.md) — Gap analysis for LLM expansion
- [../llm/vision-and-roadmap.md](../llm/vision-and-roadmap.md) — Long-term vision for LLM subsystem
- [../llm/contracts.md](../llm/contracts.md) — Contract definitions and validation
- [../llm/governance.md](../llm/governance.md) — Governance and audit policies
