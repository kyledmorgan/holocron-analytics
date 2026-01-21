# LLM-Derived Data

## Overview

The **LLM-Derived Data** subsystem generates structured JSON artifacts from evidence bundles using Large Language Models (LLMs). It is designed for **reproducibility** (via manifests), **traceability** (via evidence linking), and **validation** (via JSON schema enforcement).

## What This Subsystem Is

### Evidence-Led Structured Extraction

This subsystem transforms unstructured or semi-structured evidence into validated, structured data:

1. **Evidence Bundles**: Collections of source materials (internal docs, web snapshots, SQL result sets, raw HTTP responses)
2. **LLM Interrogation**: Prompting models to extract structured data according to predefined schemas
3. **Artifact Persistence**: Storing derived outputs with full lineage tracking

### Reproducibility Through Manifests

Every derive operation produces a **manifest** that captures:
- All input evidence (with content hashes)
- LLM configuration (provider, model, temperature)
- Prompt template used
- Output artifact references
- Timing and status information

This enables:
- Re-running derivations with the same inputs
- Auditing what evidence led to what outputs
- Comparing results across models or configurations

## What This Subsystem Is NOT

### Not Ground Truth

LLM-derived data is **interpreted data**, not authoritative source data. It:
- May contain errors due to model limitations
- Should be validated against schemas and, where possible, verified by humans
- Is subject to the quality of the input evidence

### Not Synthetic Data Generation

This is **not** synthetic data generation in the statistical/ML sense:
- No random sampling or probabilistic generation
- No simulation of new data points
- Purely extraction/interpretation from existing evidence

### Not a Replacement for Authoritative Sources

Derived data supplements, but does not replace:
- Primary data sources
- Human-verified records
- Authoritative databases

## Core Concepts

### Evidence Bundles

An **evidence bundle** is a collection of source materials used for a single derivation:

```
Evidence Bundle
├── Item 1: Ingest record (Wikipedia page JSON)
├── Item 2: SQL result (query output)
└── Item 3: Document (internal markdown)
```

Each item has:
- **Source type**: `ingest_record`, `sql_result`, `http_response`, `document`
- **Source reference**: Path, ID, or query hash
- **Content hash**: SHA256 for integrity verification
- **Metadata**: Additional context

### Manifests

A **manifest** tracks everything about a derive operation:

```json
{
  "manifest_id": "uuid",
  "evidence_bundle": { "items": [...], "bundle_hash": "..." },
  "llm_config": { "provider": "ollama", "model": "llama3.2", ... },
  "prompt_template_ref": "entity_extraction_v1",
  "status": "completed",
  "result": { "artifact_path": "...", "artifact_hash": "..." }
}
```

### Raw Response vs Parsed JSON

Each derive operation produces:
1. **Raw response**: Exact text returned by the LLM (for debugging)
2. **Parsed JSON**: Validated, structured output (the artifact)

Both are persisted for auditability.

### Schema Validation

Output validation is **fail-closed**:
- Missing required fields → operation fails
- Invalid JSON → operation fails
- Schema mismatches → operation fails

**Nulls with reasons** are allowed:
```json
{
  "entity_name": "Luke Skywalker",
  "birth_date": null,
  "nulls_with_reasons": [
    {
      "field_path": "birth_date",
      "reason": "not_found_in_evidence",
      "details": "No birth date mentioned in source documents"
    }
  ]
}
```

## Module Location

The LLM-Derived Data module lives at `src/llm/`:

```
src/llm/
├── contracts/      # JSON schemas
├── core/           # Types, exceptions, logging
├── prompts/        # Prompt templates
├── providers/      # LLM provider clients
├── runners/        # Orchestration logic
├── storage/        # Artifact and queue persistence
└── config/         # Configuration management
```

## Roadmap Placeholder

> **Note**: Detailed phase descriptions are TBD. The following are placeholder headings for future planning.

### Phase 0: Foundation (Current)

- Repository scaffolding and documentation
- Core interfaces and types
- Provider client stubs
- Manifest and schema definitions

### Phase 1: MVP Runner

- End-to-end derive workflow
- Basic prompt templates
- Filesystem artifact storage
- CLI for manual derivation

### Phase 2: Evidence Assembly

- Ingest record integration
- SQL query result bundling
- Evidence hash verification
- Bundle size management

### Phase 3: Multi-Model Benchmarking

- Model comparison framework
- Output consistency metrics
- Cost/latency tracking
- Model selection guidance

### Phase 4+: Hardening / Lineage / Governance

- Full SQL Server persistence
- Data lineage visualization
- Access controls and audit logs
- Quality metrics and monitoring

## TBD Items

The following decisions are documented as open:

| Item | Description | Status |
|------|-------------|--------|
| API Mode | Native Ollama vs OpenAI-compatible endpoints | TBD |
| Validation Library | `jsonschema`, `pydantic`, or other | TBD |
| SQL Schema | Exact tables and columns for queue/metadata | TBD |
| Vector Store | Embedding strategy for evidence retrieval | TBD |
| Prompt Management | Template versioning and A/B testing | TBD |

## Related Documentation

- [Ollama Integration Guide](ollama.md) — API documentation and configuration
- [LLM Module README](../../src/llm/README.md) — Source code overview
- [Contracts README](../../src/llm/contracts/README.md) — JSON schema documentation
- [Configuration Reference](../../src/llm/config/config.md) — Configuration options

## See Also

- [Ingest Framework](../../../src/ingest/README.md) — Related ingestion patterns
- [Project Vision](../vision/ProjectVision.md) — Long-term project goals
