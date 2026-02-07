# LLM Contracts

## Overview

This directory contains JSON Schema definitions that govern the structure of manifests and derived outputs in the LLM-Derived Data subsystem.

## Schemas

### `page_classification_v1_schema.json` *(NEW)*

Defines the **standardized output schema** for page classification tasks. This is the model-agnostic contract used by the page classification runner when calling Ollama.

Key features:
- Standardized `primary_type` enum with 12 values
- Structured `notes` field for subtype handling and extensibility
- `descriptor_sentence` (≤50 words, single sentence)
- `suggested_tags` with visibility (Public/Hidden) and typed categories
- Confidence calibration guidance
- `is_candidate_new_type` flag for taxonomy evolution

Used by: `src/sem_staging/dry_run_page_classification.py`, `src/llm/prompts/page_classification.py`

### `manifest_schema.json`

Defines the structure of a **derive manifest** — the metadata record that tracks:
- Evidence bundle (inputs to the LLM)
- LLM configuration (provider, model, parameters)
- Output references (artifact paths, hashes)
- Status and error information

Manifests enable **reproducibility** by capturing everything needed to understand and potentially re-run a derivation.

### `derived_output_schema.json`

Defines the **base structure** for LLM-derived outputs. All derived artifacts should conform to this base schema and may extend it with task-specific properties in the `data` field.

Key features:
- Links back to source manifest
- Confidence indicators
- Null-with-reason tracking (fail-closed validation)
- Extraction notes for warnings and assumptions

## Schema Versioning

Schemas follow semantic versioning:
- **Major version**: Breaking changes (incompatible with previous versions)
- **Minor version**: Backward-compatible additions
- **Patch version**: Clarifications and documentation

The current version is **1.0.0** (placeholder v1).

### Version in Schema ID

Each schema includes a version in its `$id`:
```json
"$id": "https://holocron-analytics.local/schemas/llm/manifest/v1"
```

### Tracking Schema Changes

When modifying schemas:
1. Update the version number in the schema file
2. Document changes in this README
3. Ensure backward compatibility or mark as breaking change
4. Update any dependent code and tests

## Validation

Schemas are designed for **fail-closed validation**:
- Missing required fields → validation error
- Unknown fields → allowed (to support schema evolution)
- Null values → allowed but must be explained in `nulls_with_reasons`

### Validation Library (TBD)

The validation library has not been finalized. Options under consideration:
- `jsonschema` (Python standard)
- `pydantic` with JSON Schema export
- Custom validation matching existing repo patterns

See: [TBD - JSON Validation Library Decision]

## Usage Example

```python
import json
from pathlib import Path

# Load schema
schema_path = Path(__file__).parent / "manifest_schema.json"
with open(schema_path) as f:
    manifest_schema = json.load(f)

# Validate (example with jsonschema library)
# from jsonschema import validate, ValidationError
# validate(instance=my_manifest, schema=manifest_schema)
```

## Future Schemas

Planned schema additions:
- Task-specific output schemas (e.g., `entity_extraction_output.json`)
- Evidence bundle schemas (e.g., `sql_evidence.json`, `document_evidence.json`)
- Benchmark result schemas (for multi-model comparison)

## Related Documentation

- [LLM-Derived Data Overview](../../../docs/llm/derived-data.md)
- [LLM Module README](../README.md)
