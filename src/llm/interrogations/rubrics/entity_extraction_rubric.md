# Entity Extraction Rubric

## Overview

This rubric provides guidance for filling fields in the Entity Extraction interrogation. It is used by prompt engineers and for LLM instruction.

**Interrogation ID:** `entity_extraction_v1`  
**Version:** 1.0.0  
**Status:** Example (Phase 0 placeholder)

---

## Field Rubrics

### `entity_name` (Required)

**What to extract:** The primary name of the entity as it appears in the evidence.

**Rules:**
- Use the most complete form of the name found in evidence
- Prefer formal names over nicknames
- If multiple names exist, use the most frequently used one
- Do not infer or construct names not present in evidence

**Examples:**
- ✅ "Luke Skywalker" (found in evidence)
- ❌ "Skywalker, Luke" (reformatted, not as found)
- ❌ "The Jedi" (descriptive, not a name)

---

### `entity_type` (Required)

**What to extract:** The category of the entity from the controlled vocabulary.

**Allowed Values:**
| Value | Use When |
|-------|----------|
| `person` | Individual human or humanoid character |
| `place` | Geographic location, planet, building |
| `organization` | Group, company, government, faction |
| `event` | Historical event, battle, ceremony |
| `concept` | Abstract idea, force, technology |
| `other` | Does not fit other categories |

**Rules:**
- Choose the single most appropriate type
- Use `other` only when no other type applies
- Do not create new types

---

### `description` (Optional)

**What to extract:** A brief factual description from the evidence.

**Rules:**
- Maximum 200 characters
- State facts from evidence only
- Do not include opinions or interpretations
- Use `null` if no description is available in evidence

---

### `aliases` (Optional)

**What to extract:** Alternative names, titles, or spellings found in evidence.

**Rules:**
- Include only names/titles explicitly found in evidence
- Do not include the primary `entity_name`
- Order by frequency of appearance
- Use `null` if no aliases are present

**Examples:**
- ✅ `["Darth Vader", "Lord Vader", "The Chosen One"]`
- ❌ `["Anakin's evil form"]` (description, not an alias)

---

### `attributes` (Optional)

**What to extract:** Additional entity-specific attributes found in evidence.

**Rules:**
- Include only attributes explicitly stated in evidence
- Use a flat key-value structure
- Keys should be descriptive (e.g., `birth_year`, `homeworld`)
- Values must be from evidence, not inferred
- Use `null` for the entire field if no attributes found

---

### `evidence_refs` (Required)

**What to extract:** References to the evidence items that support this entity.

**Rules:**
- Include at least one evidence reference
- Use the `source_ref` from the evidence bundle
- List all evidence items that mention this entity
- Do not cite evidence that doesn't mention the entity

---

### `confidence` (Required)

**What to assign:** Your confidence level in the extraction accuracy.

**Anchors:**
| Level | When to Use |
|-------|-------------|
| `high` | Entity is clearly named and described in evidence |
| `medium` | Entity is mentioned but some attributes are unclear |
| `low` | Entity is only indirectly referenced or partially visible |
| `unknown` | Cannot assess confidence (should be rare) |

---

## Null Handling

When a field cannot be extracted:

1. Set the field value to `null`
2. Add an entry to `nulls_with_reasons` explaining why

**Valid Reasons:**
- `not_found_in_evidence` — Information not present
- `ambiguous_in_evidence` — Multiple conflicting values
- `extraction_failed` — Technical issue during extraction
- `not_applicable` — Field doesn't apply to this entity
- `redacted` — Value removed for policy reasons

---

## Related Documentation

- [Entity Extraction Definition](../definitions/entity_extraction.yaml)
- [Glossary](../../../../docs/llm/glossary.md)
- [Derived Output Schema](../../contracts/derived_output_schema.json)
