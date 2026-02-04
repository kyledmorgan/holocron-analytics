# Phase 2: Evidence Assembly + Packaging - Implementation Summary

## Overview

Phase 2 implements a robust **evidence assembly system** for the LLM-Derived Data subsystem. It provides deterministic, bounded, and auditable evidence bundles that feed into Phase 1's runner.

**Status:** ✅ **COMPLETE**

## What Was Implemented

### A. Evidence Object Model (Pydantic Contracts)

**File:** `src/llm/contracts/evidence_contracts.py`

- **`EvidencePolicy`** - Bounding rules configuration
  - Global limits (max items, max total bytes)
  - Per-item limits (max bytes per item)
  - SQL-specific limits (max rows, max columns)
  - Sampling strategies (first_only, first_last, stride)
  - Redaction toggle

- **`EvidenceItem`** - Individual evidence piece
  - Deterministic evidence_id (e.g., `inline:0`, `sql:abc123:0`)
  - Evidence type (inline_text, lake_text, lake_http, sql_result, etc.)
  - Bounded content with SHA256 hash
  - Metadata tracking bounding decisions
  - Optional full_ref for unbounded artifacts

- **`EvidenceBundle`** - Complete evidence collection
  - Unique bundle_id (UUID)
  - Build version tracking
  - Policy and summary metadata
  - List of evidence items

- **Helper functions:**
  - `generate_evidence_id()` - Stable, deterministic IDs
  - `compute_content_hash()` - SHA256 content hashing

### B. Evidence Bundle Builder

**Core:** `src/llm/evidence/builder.py`

- **`EvidenceBundleBuilder`** class
- **`build_evidence_bundle()`** convenience function
- Orchestrates loading from multiple sources
- Applies bounding and redaction
- Computes bundle summary statistics

### C. Source Adapters

**Directory:** `src/llm/evidence/sources/`

1. **`inline_source.py`** - Job-provided evidence
   - Loads text from job payload
   - Deterministic inline:N naming

2. **`lake_text_source.py`** - Text artifacts from lake
   - Reads plain text files
   - Bounded to max_item_bytes

3. **`lake_http_source.py`** - HTTP response artifacts
   - Extracts headers and body
   - Formats as readable text

4. **`sql_result_source.py`** - SQL query results
   - **Mode D1:** Load existing result artifacts
   - **Mode D2:** Execute SELECT queries (guarded)
   - Row/column sampling
   - Bounded textual representation

5. **`sql_query_source.py`** - Query definitions
   - Stores query text as evidence
   - Provides transparency

### D. Bounding System

**File:** `src/llm/evidence/bounding.py`

- **`apply_item_bounding()`** - Per-item byte limits
  - Truncates content to max_item_bytes
  - Handles UTF-8 boundaries
  - Records truncation metadata

- **`apply_bundle_bounding()`** - Global bundle limits
  - Enforces max_items
  - Enforces max_total_bytes
  - Drops items from end if over limit
  - Records dropped items

- **`validate_policy()`** - Policy validation
  - Checks for invalid configurations
  - Returns list of errors

### E. Text Extractors

**File:** `src/llm/evidence/text_extractors.py`

- **`extract_plain_text()`** - Bounded plain text
- **`extract_json()`** - Pretty-printed JSON
- **`extract_http_response()`** - HTTP headers + body
- **`extract_sql_result_text()`** - SQL tabular format
  - Column headers and types
  - Row sampling (first_only, first_last, stride)
  - Sampling metadata

### F. Redaction System

**File:** `src/llm/evidence/redaction.py`

- **`RedactionRule`** class - Pattern-based redaction
- **`redact()`** function - Apply redaction rules
- **Default rules:**
  - Email addresses
  - Phone numbers
  - Social Security Numbers (US)
  - Credit card patterns
  - Secret markers (password=, api_key=, etc.)

- **Features:**
  - Toggle on/off via policy
  - Records all redactions in metadata
  - Case-insensitive pattern matching
  - Custom rule creation

### G. SQL Server Schema

**File:** `db/migrations/0007_evidence_bundle_tables.sql`

**Tables:**
1. **`llm.evidence_bundle`**
   - bundle_id (PK)
   - created_utc
   - build_version
   - policy_json
   - summary_json
   - lake_uri

2. **`llm.run_evidence`**
   - run_id (FK to llm.run)
   - bundle_id (FK to llm.evidence_bundle)
   - attached_utc

3. **`llm.evidence_item`** (optional tracking)
   - item_id (PK)
   - bundle_id (FK)
   - evidence_id
   - evidence_type
   - lake_uri
   - byte_count
   - content_sha256
   - metadata_json

**Indexes:** Optimized for lookups by bundle_id, run_id, and evidence_type

### H. Runner Integration

**Updated:** `src/llm/runners/phase1_runner.py`

- **`_build_evidence_bundle()`** - Now uses Phase 2 builder
  - Configures EvidencePolicy
  - Calls `build_evidence_bundle()`
  - Returns Phase 2 EvidenceBundle

- **`_render_prompt()`** - Updated for Phase 2
  - Uses evidence_bundle.items (not snippets)
  - Includes evidence_type in prompt

- **Evidence persistence:**
  - Writes bundle JSON to lake
  - Records bundle metadata to SQL Server
  - Links run to evidence bundle via run_evidence table

**Updated:** `src/llm/storage/sql_job_queue.py`

- **`create_evidence_bundle()`** - Insert evidence_bundle record
- **`link_run_to_evidence_bundle()`** - Insert run_evidence link

### I. Documentation

1. **`docs/llm/evidence.md`** - Evidence bundle format
   - Bundle structure
   - Evidence types
   - Evidence IDs
   - Bounding policy
   - Usage examples

2. **`docs/llm/sql-evidence.md`** - SQL packaging guide
   - Mode D1 and D2
   - SQL result artifact format
   - Bounding rules
   - Sampling strategies
   - Best practices

3. **`docs/llm/redaction.md`** - Redaction hooks
   - Design philosophy
   - Default rules
   - Enable/disable toggle
   - Redaction metadata
   - Custom rules
   - Future enhancements

4. **`docs/llm/status.md`** - Updated implementation status
   - Phase 2 marked as COMPLETE
   - Comprehensive checklist

### J. Tests

**120 total unit tests** (64 new for Phase 2)

1. **`test_evidence_contracts.py`** - 22 tests
   - EvidencePolicy serialization
   - EvidenceItem creation and validation
   - EvidenceBundle operations
   - Deterministic evidence_id generation
   - Content hashing

2. **`test_evidence_bounding.py`** - 14 tests
   - Item-level bounding
   - Bundle-level bounding
   - Policy validation
   - Bounding metadata

3. **`test_evidence_redaction.py`** - 17 tests
   - Redaction rules
   - Pattern matching
   - Enable/disable toggle
   - Metadata recording
   - Default rules

4. **`test_sql_text_extraction.py`** - 11 tests
   - SQL result formatting
   - Row/column sampling
   - Sampling strategies
   - Metadata structure

All tests pass ✅

## Key Features

### Deterministic Bounding
- Same inputs + same policy = same output
- All bounding decisions recorded
- Reproducible results

### Auditable
- Content hashing (SHA256)
- Stable evidence IDs
- Bounding metadata
- Redaction metadata
- SQL Server tracking

### Extensible
- Easy to add new source adapters
- Custom redaction rules
- Configurable policies
- Plugin-friendly design

### Safe SQL Execution
- SELECT-only validation
- Query timeouts
- Read-only connections preferred
- Full query logging

## Usage Example

```python
from llm.evidence.builder import build_evidence_bundle
from llm.contracts.evidence_contracts import EvidencePolicy

# Configure policy
policy = EvidencePolicy(
    max_items=30,
    max_total_bytes=75000,
    max_sql_rows=50,
    enable_redaction=False
)

# Job input with inline evidence
job_input = {
    "entity_type": "character",
    "entity_id": "luke_skywalker",
    "extra_params": {
        "evidence": [
            {"text": "Luke Skywalker is a Jedi...", "source_uri": "wookieepedia"}
        ]
    }
}

# Evidence references
evidence_refs = {
    "lake_text": ["docs/character_bio.md"],
    "sql_results": [
        {
            "lake_uri": "results/character_facts.json",
            "query_key": "character_facts"
        }
    ]
}

# Build bundle
bundle = build_evidence_bundle(
    job_input=job_input,
    evidence_refs=evidence_refs,
    policy=policy,
    lake_root="lake"
)

print(f"Bundle {bundle.bundle_id} with {len(bundle.items)} items")
# Output: Bundle 550e8400-... with 15 items
```

## What's Next

Phase 2 is complete and integrated with Phase 1. The system is now ready for:

- **Phase 3:** RAG / Embeddings (evidence retrieval)
- **Phase 4:** Web browsing / snapshot integration
- **Phase 5:** Multi-model adjudication
- **Phase 6+:** Advanced governance and lineage

## Files Changed

**New files:**
- `src/llm/contracts/evidence_contracts.py`
- `src/llm/evidence/__init__.py`
- `src/llm/evidence/builder.py`
- `src/llm/evidence/bounding.py`
- `src/llm/evidence/redaction.py`
- `src/llm/evidence/text_extractors.py`
- `src/llm/evidence/sources/__init__.py`
- `src/llm/evidence/sources/inline_source.py`
- `src/llm/evidence/sources/lake_text_source.py`
- `src/llm/evidence/sources/lake_http_source.py`
- `src/llm/evidence/sources/sql_result_source.py`
- `src/llm/evidence/sources/sql_query_source.py`
- `db/migrations/0007_evidence_bundle_tables.sql`
- `tests/unit/llm/test_evidence_contracts.py`
- `tests/unit/llm/test_evidence_bounding.py`
- `tests/unit/llm/test_evidence_redaction.py`
- `tests/unit/llm/test_sql_text_extraction.py`
- `docs/llm/evidence.md`
- `docs/llm/sql-evidence.md`
- `docs/llm/redaction.md`

**Modified files:**
- `src/llm/runners/phase1_runner.py`
- `src/llm/storage/sql_job_queue.py`
- `docs/llm/status.md`

**Total:** 23 new files, 3 modified files

## Test Coverage

```
tests/unit/llm/
├── test_evidence_contracts.py       22 tests ✅
├── test_evidence_bounding.py        14 tests ✅
├── test_evidence_redaction.py       17 tests ✅
├── test_sql_text_extraction.py      11 tests ✅
├── test_phase1_contracts.py         25 tests ✅
├── test_interrogation_registry.py   11 tests ✅
└── test_ollama_client.py            20 tests ✅

Total: 120 tests, all passing
```

## Summary

Phase 2 successfully implements a production-ready evidence assembly system with:
- ✅ Deterministic, bounded evidence bundles
- ✅ Multiple source adapters (inline, lake, SQL)
- ✅ SQL evidence packaging with sampling
- ✅ Pattern-based redaction hooks
- ✅ SQL Server tracking and lineage
- ✅ Full Phase 1 integration
- ✅ Comprehensive documentation
- ✅ 64 new unit tests (120 total)

The system is now ready for Phase 3 (RAG/embeddings) and beyond.
