# LLM-Derived Data: Glossary

This document defines the core terminology used in the LLM-Derived Data subsystem. These definitions establish a shared vocabulary for documentation, code, and discussion.

---

## Core Concepts

### Interrogation

A **repeatable question pattern** that produces structured output from evidence. An interrogation includes:

| Component | Description |
|-----------|-------------|
| **Prompt Template** | The text template sent to the LLM, with placeholders for evidence |
| **JSON Contract** | The expected output schema (see [contracts](../../src/llm/contracts/)) |
| **Rubric Rules** | Guidelines for how the LLM should fill each field |
| **Controlled Vocabulary** | Allowed values for classification fields |

Interrogations are versioned and identified by a unique reference (e.g., `entity_extraction_v1`).

---

### Evidence Bundle

A **curated collection of evidence objects** used as input for a single derivation. Each bundle:

- Contains one or more **evidence items**
- Has a unique **bundle ID**
- Has a **bundle hash** (combined hash of all items for integrity)
- Is the only source the LLM is allowed to cite

The model **must not** reference information outside the evidence bundle.

---

### Evidence Item

A single piece of evidence within a bundle. Each item has:

| Attribute | Description |
|-----------|-------------|
| `source_type` | Type of source: `ingest_record`, `sql_result`, `http_response`, `document`, `other` |
| `source_ref` | Reference to the source (file path, ingest ID, query hash) |
| `content_hash` | SHA256 hash of the content for integrity verification |
| `content` | The actual content (may not always be loaded) |
| `metadata` | Additional contextual information |

---

### Manifest

A **metadata record** that captures everything about a derive operation for reproducibility and auditability. A manifest includes:

| Field | Description |
|-------|-------------|
| `manifest_id` | Unique identifier (UUID) |
| `manifest_version` | Schema version for the manifest format |
| `created_at_utc` | Timestamp when the operation started |
| `evidence_bundle` | References to all evidence items used |
| `llm_config` | Provider, model, temperature, and other settings |
| `prompt_template_ref` | Reference to the prompt template used |
| `status` | Current status (`pending`, `in_progress`, `completed`, `failed`, `validation_failed`) |
| `result` | Output references, hashes, timing, and validation info |

See: [Manifest Schema](../../src/llm/contracts/manifest_schema.json)

---

### Derived Artifact

The **structured JSON output** produced by an LLM derive operation. A derived artifact:

- Conforms to a predefined JSON schema
- Links back to its source manifest
- Includes confidence indicators
- Tracks null values with reasons

See: [Derived Output Schema](../../src/llm/contracts/derived_output_schema.json)

---

## Principles

### Contract-First

The principle that **output schemas are defined before prompts are written**. This ensures:

1. Clear expectations for LLM output
2. Automated validation (fail-closed)
3. Consistent data structures across runs
4. Schema evolution tracking

Contract-first means:
- The JSON schema is the source of truth
- Prompts are written to produce schema-compliant output
- Invalid output causes the operation to fail

---

### Evidence-First

The principle that **all claims must be grounded in explicit evidence**. This ensures:

1. Traceability from output to source
2. No hallucination or unsupported inference
3. Auditability of derived data

Evidence-first means:
- The LLM can only cite evidence bundle IDs
- Fields without supporting evidence return `null`
- Each null must include a `null_reason`
- External references are not allowed

---

### Fail-Closed Validation

A validation strategy where **invalid output causes the operation to fail**:

- Missing required fields → operation fails
- Invalid JSON → operation fails
- Schema mismatches → operation fails
- Partial data is not accepted

This ensures data quality at the cost of some flexibility.

---

## Status Values

### Derive Job Status

| Status | Description |
|--------|-------------|
| `pending` | Job is queued but not started |
| `in_progress` | Job is currently running |
| `completed` | Job finished successfully |
| `failed` | Job failed due to an error |
| `validation_failed` | Job completed but output failed schema validation |

---

## Evidence Source Types

| Type | Description | Example |
|------|-------------|---------|
| `ingest_record` | Data from the ingest pipeline | Wikipedia page JSON |
| `sql_result` | Output from a SQL query | Query result set |
| `http_response` | Raw HTTP response content | API response |
| `document` | Internal document | Markdown file |
| `other` | Any other source type | Custom format |

---

## Null Reasons

When a field cannot be extracted, it returns `null` with a reason:

| Reason | Description |
|--------|-------------|
| `not_found_in_evidence` | The information was not present in the evidence |
| `ambiguous_in_evidence` | Multiple conflicting values found |
| `extraction_failed` | Technical failure during extraction |
| `not_applicable` | The field does not apply to this entity |
| `redacted` | The value was removed for privacy/security |
| `other` | Other reason (requires details) |

---

## Related Documentation

- [Vision and Roadmap](vision-and-roadmap.md) — Project vision and phases
- [LLM-Derived Data Overview](derived-data.md) — Conceptual overview
- [Contracts README](../../src/llm/contracts/README.md) — Schema documentation
