# Evidence Bundles - Phase 2 Evidence Assembly

## Overview

Evidence bundles are **deterministic, bounded, and auditable** collections of source materials that feed into LLM interrogations. Phase 2 implements a robust evidence assembly system that:

- Loads evidence from multiple sources (inline, lake artifacts, SQL results)
- Applies deterministic bounding rules to fit within model context limits
- Records all bounding and redaction decisions for auditability
- Generates stable evidence IDs for reproducibility

## Evidence Bundle Structure

An evidence bundle consists of:

1. **Bundle Metadata**
   - `bundle_id`: Unique identifier (UUID)
   - `created_utc`: Creation timestamp
   - `build_version`: Evidence builder version
   - `policy`: Bounding policy used
   - `summary`: Statistics (item counts, total bytes, approximate tokens)

2. **Evidence Items** - List of individual evidence pieces
   - Each item has a deterministic `evidence_id`
   - Content is bounded and optionally redacted
   - Full metadata tracks bounding decisions

3. **Evidence Policy** - Bounding rules applied
   - Global limits (max items, max total bytes)
   - Per-item limits (max bytes per item)
   - SQL-specific limits (max rows, max columns)
   - Sampling strategies for oversized data

## Evidence Types

### inline_text
Evidence provided directly in the job payload.
- Simple text snippets
- No external references

### lake_text
Text files stored in the artifact lake.
- Markdown documents
- Plain text files
- Bounded to `max_item_bytes`

### lake_http
Raw HTTP response artifacts.
- Headers + body
- Status codes and metadata
- Body bounded to fit within limits

### sql_result
SQL query result sets (tabular data).
- Row/column bounded
- Deterministic sampling (first/last/stride)
- Formatted as readable text for LLM

### sql_query_def
SQL query definitions (for transparency).
- Shows what queries were run
- Provides context for results

### doc_chunk, transcript_chunk
Chunked document or transcript segments.
- For large documents split across multiple items
- Chunk index tracked in evidence_id

## Evidence IDs (Deterministic Naming)

Evidence IDs follow stable conventions:

- **inline:N** - Inline evidence at index N
- **lake:PREFIX:CHUNK** - Lake artifact with SHA256 prefix and chunk index
- **sql:PREFIX:CHUNK** - SQL result with query key hash and chunk index
- **doc:PREFIX:CHUNK** - Document chunk with document ID hash
- **sqldef:PREFIX** - SQL query definition

**Example:**
```
inline:0
lake:a1b2c3d4e5f6:0
sql:query_hash:0:0-100
doc:doc123abc:2
```

IDs are stable for the same inputs and policy.

## Bounding Policy

The `EvidencePolicy` defines limits and sampling rules:

### Global Limits
- `max_items` (default: 50) - Maximum evidence items in bundle
- `max_total_bytes` (default: 100,000) - Maximum total bytes across all items

### Per-Item Limits
- `max_item_bytes` (default: 10,000) - Maximum bytes per individual item

### SQL-Specific Limits
- `max_sql_rows` (default: 100) - Maximum rows to include from SQL results
- `max_sql_cols` (default: 20) - Maximum columns to include

### Sampling Strategies
When SQL results exceed row limits, use deterministic sampling:

- **first_only** - First N rows
- **first_last** - First N/2 and last N/2 rows
- **stride** - Every Kth row (K = total_rows / max_rows)

### Chunking (for future use)
- `chunk_size` (default: 5,000) - Bytes per chunk for large documents
- `chunk_overlap` (default: 200) - Overlap between chunks

### Redaction
- `enable_redaction` (default: false) - Toggle redaction hooks

## Bounding Process

1. **Load Evidence** - Source adapters load raw content
2. **Apply Redaction** (if enabled) - Pattern-based redaction
3. **Bound Item** - Truncate to `max_item_bytes`
4. **Bound Bundle** - Drop items if over `max_items` or `max_total_bytes`
5. **Record Metadata** - All bounding decisions logged

### Bounding Metadata

Each item's metadata includes:
```json
{
  "bounding": {
    "applied": true,
    "original_size": 50000,
    "bounded_size": 10000,
    "truncation_point": 10000,
    "note": "Truncated to 10000 byte limit"
  }
}
```

Bundle summary includes:
```json
{
  "bundle_bounding": {
    "applied": true,
    "original_count": 100,
    "final_count": 50,
    "items_dropped": 50,
    "total_bytes": 95000,
    "note": "Dropped 50 items to meet bundle limits"
  }
}
```

## Full vs Bounded Artifacts

For large artifacts that must be truncated:

1. **Full artifact** is persisted to the lake (if not already there)
2. **Bounded content** is included in the evidence bundle
3. **full_ref** pointer links to the full artifact

```json
{
  "evidence_id": "sql:abc123:0",
  "content": "... bounded text ...",
  "byte_count": 10000,
  "full_ref": {
    "lake_uri": "results/query_abc123.json",
    "row_count": 10000,
    "col_count": 50
  }
}
```

## Bundle Artifact Format

Evidence bundles are persisted as JSON artifacts in the lake:

```json
{
  "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_utc": "2024-01-15T10:30:00Z",
  "build_version": "2.0",
  "policy": {
    "max_items": 50,
    "max_total_bytes": 100000,
    "max_item_bytes": 10000,
    "max_sql_rows": 100,
    "sampling_strategy": "first_last"
  },
  "items": [
    {
      "evidence_id": "inline:0",
      "evidence_type": "inline_text",
      "source_ref": {"source_uri": "job_input"},
      "content": "...",
      "content_sha256": "...",
      "byte_count": 1234,
      "metadata": {}
    }
  ],
  "summary": {
    "item_count": 15,
    "type_counts": {
      "inline_text": 5,
      "sql_result": 8,
      "lake_text": 2
    },
    "total_bytes": 85000,
    "approx_tokens": 21250
  }
}
```

## Usage Example

```python
from llm.evidence.builder import build_evidence_bundle
from llm.contracts.evidence_contracts import EvidencePolicy

# Define policy
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

# Bundle ready for LLM interrogation
print(f"Bundle {bundle.bundle_id} with {len(bundle.items)} items")
```

## SQL Server Tracking

Evidence bundles are tracked in SQL Server:

- `llm.evidence_bundle` - Bundle metadata and lake URI
- `llm.run_evidence` - Links runs to evidence bundles
- `llm.evidence_item` (optional) - Individual item tracking

This enables:
- Finding which bundles were used for which runs
- Auditing evidence usage
- Debugging failed runs

## See Also

- [SQL Evidence Packaging](sql-evidence.md) - Detailed SQL result handling
- [Redaction Hooks](redaction.md) - PII redaction system
- [Phase 1 Runner](phase1-runner.md) - How bundles are consumed
- [LLM-Derived Data](derived-data.md) - Overall subsystem vision
