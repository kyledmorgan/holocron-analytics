# Interrogation Catalog

## Overview

This directory contains **interrogation definitions** — reusable question patterns that produce structured output from evidence. Each interrogation defines what to extract, how to format it, and the rules for filling fields.

## Concept

An **interrogation** is a repeatable extraction task with:

1. **Definition** — YAML/JSON file describing the interrogation
2. **Output Schema** — JSON schema for expected output (in `contracts/`)
3. **Rubric** — Rules for how to fill each field (in `rubrics/`)
4. **Prompt Template** — Text template for the LLM (in `prompts/templates/`)

## Directory Structure

```
interrogations/
├── README.md           # This file
├── definitions/        # Interrogation definition files (YAML/JSON)
│   └── entity_extraction.yaml
└── rubrics/            # Rubric markdown files
    └── entity_extraction_rubric.md
```

## Interrogation Definition Format

Each definition file includes:

```yaml
# Interrogation identifier
id: entity_extraction_v1
name: Entity Extraction
version: "1.0.0"

# Description
description: |
  Extract named entities with attributes from evidence documents.

# References to related files
schema_ref: contracts/derived_output_schema.json
rubric_ref: interrogations/rubrics/entity_extraction_rubric.md
prompt_template_ref: prompts/templates/entity_extraction.txt

# Output configuration
output:
  format: json
  validation: fail_closed
  
# Evidence requirements
evidence:
  min_items: 1
  max_items: 10
  allowed_types:
    - ingest_record
    - document
    - sql_result

# Controlled vocabularies (if applicable)
vocabularies:
  entity_type:
    - person
    - place
    - organization
    - event
    - other
```

## Rubric Files

Rubric files (in `rubrics/`) provide human-readable guidance for how to fill each field. They are referenced in prompts and used for:

- Training prompt engineers
- Consistency across interrogation versions
- Documentation for downstream consumers

## Planned Interrogations

| ID | Name | Status | Description |
|----|------|--------|-------------|
| `entity_extraction_v1` | Entity Extraction | Example | Extract named entities with attributes |
| `relationship_extraction_v1` | Relationship Extraction | Planned | Extract relationships between entities |
| `classification_v1` | Document Classification | Planned | Classify documents into categories |
| `summary_v1` | Evidence Summary | Planned | Summarize evidence into structured format |

## Adding New Interrogations

To add a new interrogation:

1. Create a definition file in `definitions/`
2. Create a rubric file in `rubrics/`
3. Create an output schema in `contracts/` (or use existing)
4. Create a prompt template in `prompts/templates/`
5. Document in this README

## Related Documentation

- [Glossary](../../../docs/llm/glossary.md) — Core terminology
- [Contracts README](../contracts/README.md) — JSON schemas
- [Prompts README](../prompts/README.md) — Prompt templates
