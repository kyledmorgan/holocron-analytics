# SQL-First Artifact Content Storage

## Current State Findings

### Tables and Key Columns

| Table | Schema | Purpose | Key Columns |
|-------|--------|---------|-------------|
| `llm.job` | 0005 | Queue of LLM derive jobs | `job_id`, `interrogation_key`, `input_json`, `evidence_ref_json`, `model_hint` |
| `llm.run` | 0005 | Individual run attempts | `run_id`, `job_id`, `model_name`, `options_json`, `metrics_json`, `error` |
| `llm.artifact` | 0005 | Artifact inventory per run | `artifact_id`, `run_id`, `artifact_type`, `content_sha256`, `byte_count`, `lake_uri` |
| `llm.evidence_bundle` | 0007 | Evidence bundle metadata | `bundle_id`, `policy_json`, `summary_json`, `lake_uri` |
| `llm.evidence_item` | 0007 | Individual evidence items | `item_id`, `bundle_id`, `evidence_id`, `evidence_type`, `lake_uri`, `content_sha256` |
| `llm.run_evidence` | 0007 | Junction: run ↔ bundle | `run_id`, `bundle_id` |

### What Was Stored in SQL (Before This Change)

| Data | Stored in SQL? | Notes |
|------|---------------|-------|
| Run metadata (model, worker, timing) | ✅ Yes | Full metadata in `llm.run` |
| Job config (input, priority, interrogation) | ✅ Yes | Full config in `llm.job` |
| Artifact inventory (type, hash, size) | ✅ Yes | Metadata only — no content |
| Rendered prompt text | ❌ No | Only `lake_uri` pointer |
| Request JSON (to Ollama) | ❌ No | Only `lake_uri` pointer |
| Response JSON (from Ollama) | ❌ No | Only `lake_uri` pointer |
| Parsed output JSON | ❌ No | Only `lake_uri` pointer |
| Evidence bundle JSON | ❌ No | Only `lake_uri` + policy/summary metadata |
| Evidence item content | ❌ No | Only `lake_uri` + hash |
| SHA256 / byte_count | ✅ Yes | Already tracked per artifact |

### Critical Gap

**SQL was a metadata index pointing to the lake. The literal payloads lived exclusively in the filesystem.** If the lake was lost, run contents could not be reconstructed from SQL alone.

---

## Gaps / Risks Addressed

1. **Single point of failure**: Lake loss = data loss for artifact content
2. **No SQL-only restore**: Impossible to reconstruct a run from SQL alone
3. **No content queryability**: Cannot search/filter by artifact content in SQL
4. **Storage flags missing**: No way to track where content lives (SQL vs lake vs both)

---

## Future State (SQL Schema Additions + Relationships)

### Migration 0035: `0035_artifact_content_sql_first.sql`

#### A) `llm.artifact` — Content Column + Storage Flags

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `content` | `NVARCHAR(MAX)` NULL | NULL | Literal artifact payload (JSON or text) |
| `stored_in_sql` | `BIT` NOT NULL | 0 | Flag: content is persisted in SQL |
| `mirrored_to_lake` | `BIT` NOT NULL | 0 | Flag: content is also in the lake |
| `lake_uri` | Changed to **nullable** | — | Lake is optional when SQL-first |

**Index added**: `IX_llm_artifact_content_sha256` on `content_sha256` for dedupe-by-hash queries.

**Backfill**: Existing rows get `stored_in_sql = 0, mirrored_to_lake = 1` (they are lake-only).

#### B) `llm.evidence_bundle` — Bundle JSON

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `bundle_json` | `NVARCHAR(MAX)` NULL | NULL | Full evidence.json content in SQL |
| `lake_uri` | Changed to **nullable** | — | Lake is optional when SQL-first |

#### C) `llm.evidence_item` — Content Column

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `content` | `NVARCHAR(MAX)` NULL | NULL | Evidence item text/content in SQL |

#### D) Updated Stored Procedure: `usp_create_artifact`

New parameters: `@content`, `@content_mime_type`, `@stored_in_sql`, `@mirrored_to_lake`

The stored procedure inserts all columns including the literal content in a single atomic operation.

### Relationships & Lineage Queries

```
llm.job (1) ──→ llm.run (N)
llm.run (1) ──→ llm.artifact (N)     ← now includes content
llm.run (N) ──→ llm.evidence_bundle (M)  via llm.run_evidence
llm.evidence_bundle (1) ──→ llm.evidence_item (N)  ← now includes content

Lineage query: run → artifacts (with content) → evidence items → upstream source refs
```

---

## Proposed Code Touchpoints

### SQL
- `db/migrations/0035_artifact_content_sql_first.sql` — **New migration** (created)

### Python — Storage Layer
- `src/llm/storage/sql_job_queue.py` — **Modified**
  - `create_artifact()`: Added `content`, `content_mime_type`, `stored_in_sql`, `mirrored_to_lake` params
  - `create_evidence_bundle()`: Added `bundle_json` param, made `lake_uri` optional

### Python — Runners
- `src/llm/runners/phase1_runner.py` — **Modified**
  - All `create_artifact()` calls now pass literal content + storage flags
  - `create_evidence_bundle()` call now passes `bundle_json`
- `src/llm/runners/dispatcher.py` — **Modified**
  - All `create_artifact()` calls in `_execute_generic()` and `_complete_run()` now pass literal content

### Tests
- `tests/unit/llm/test_sql_first_artifact_storage.py` — **New test file**
  - 6 unit tests covering content storage, backward compatibility, SQL-only mode

---

## Migration / Backfill Considerations

1. **Idempotent**: Migration uses `IF NOT EXISTS` checks — safe to run multiple times
2. **Non-breaking**: All new columns are `NULL`-able. Existing code continues to work
3. **Backfill strategy**: Existing artifact rows are flagged `stored_in_sql=0, mirrored_to_lake=1`
4. **Future backfill**: A separate script could read lake files and populate `content` for historical rows
5. **Constraint relaxation**: `lake_uri` is made nullable on `llm.artifact` and `llm.evidence_bundle` since SQL is now the primary store
