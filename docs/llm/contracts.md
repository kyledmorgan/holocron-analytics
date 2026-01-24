# LLM-Derived Data: Contracts

## Overview

This document explains the **contract-first** approach used in the LLM-Derived Data subsystem. Contracts are JSON schemas that define the expected structure of manifests and derived outputs.

---

## What Are Contracts?

Contracts are **JSON Schema** definitions that specify:

1. **Required fields** — Fields that must be present in valid data
2. **Field types** — Data types (string, number, object, array, etc.)
3. **Allowed values** — Enumerations for fields with fixed options
4. **Structure** — Nested objects and their relationships

Contracts serve as the **source of truth** for data validation.

---

## Contract Types

### Manifest Schema

**Location:** `src/llm/contracts/manifest_schema.json`

The manifest schema defines the structure of **derive manifests** — metadata records that track:

- Evidence bundle inputs (with hashes)
- LLM configuration (provider, model, temperature)
- Output references (artifact paths, hashes)
- Status and timing information
- Error details (if applicable)

Manifests enable **reproducibility** by capturing everything needed to understand or re-run a derivation.

### Derived Output Schema

**Location:** `src/llm/contracts/derived_output_schema.json`

The derived output schema defines the **base structure** for all LLM-derived artifacts:

- Links back to source manifest
- Confidence indicators
- Null-with-reason tracking
- Flexible `data` field for task-specific content
- Extraction notes for warnings/assumptions

Task-specific schemas extend this base by defining the `data` field structure.

---

## Schema Versioning

### Version Format

Schemas use semantic versioning: `MAJOR.MINOR.PATCH`

| Version Part | When to Increment | Example |
|--------------|-------------------|---------|
| MAJOR | Breaking changes (incompatible) | 1.0.0 → 2.0.0 |
| MINOR | Backward-compatible additions | 1.0.0 → 1.1.0 |
| PATCH | Clarifications, documentation | 1.0.0 → 1.0.1 |

### Version in Schema ID

Each schema includes a version in its `$id`:

```json
"$id": "https://holocron-analytics.local/schemas/llm/manifest/v1"
```

### Current Version

- Manifest Schema: **1.0.0** (placeholder v1)
- Derived Output Schema: **1.0.0** (placeholder v1)

---

## Validation Behavior

### Fail-Closed Validation

The subsystem uses **fail-closed** validation:

| Condition | Behavior |
|-----------|----------|
| Missing required field | Validation fails |
| Invalid JSON | Validation fails |
| Schema mismatch | Validation fails |
| Unknown additional fields | Allowed (for forward compatibility) |
| Null value | Allowed if explained in `nulls_with_reasons` |

### Why Fail-Closed?

Fail-closed validation ensures data quality by rejecting incomplete or malformed outputs. This is preferable to accepting partial data that may lead to downstream errors.

---

## Raw Response vs Parsed Output

Each derive operation produces two outputs:

### Raw Response

The **exact text** returned by the LLM, saved as-is:

- Purpose: Debugging, analysis, re-parsing
- Location: `raw_responses/{timestamp}_{manifest_id}.txt`
- Content: May include markdown, extra text, etc.

### Parsed Output

The **validated JSON** extracted from the raw response:

- Purpose: Downstream consumption
- Location: `artifacts/{task_type}/{timestamp}_{manifest_id}.json`
- Content: Schema-validated structured data

### Separation Benefits

1. **Debugging** — Raw response preserved for troubleshooting
2. **Re-parsing** — Can re-extract JSON if parsing logic improves
3. **Analysis** — Study LLM behavior patterns
4. **Reproducibility** — Exact LLM output is recorded

---

## Extending Schemas

### Task-Specific Schemas

The base `derived_output_schema.json` can be extended for specific tasks:

1. Create a new schema file (e.g., `entity_extraction_output.json`)
2. Use `allOf` to combine with base schema
3. Define specific `data` field structure
4. Document in `contracts/README.md`

Example structure:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://holocron-analytics.local/schemas/llm/entity-extraction/v1",
  "allOf": [
    { "$ref": "derived_output_schema.json" }
  ],
  "properties": {
    "data": {
      "type": "object",
      "properties": {
        "entities": {
          "type": "array",
          "items": { "$ref": "#/definitions/Entity" }
        }
      }
    }
  }
}
```

---

## Validation Library (TBD)

The validation library has not been finalized. Options under consideration:

| Library | Pros | Cons |
|---------|------|------|
| `jsonschema` | Python standard, well-documented | Verbose error messages |
| `pydantic` | Type safety, IDE support | Requires model definitions |
| Custom | Tailored to repo patterns | Maintenance burden |

See: [Status - TBD Decisions](status.md#tbd-decisions)

---

## Related Documentation

- [Contracts README](../../src/llm/contracts/README.md) — Schema file documentation
- [Glossary](glossary.md) — Core terminology
- [Vision and Roadmap](vision-and-roadmap.md) — Project roadmap
