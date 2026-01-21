# Closed-Set Classification Rubric

## Overview

This rubric provides guidance for the **Closed-Set Classification** interrogation type. Closed-set classification assigns labels from a predefined vocabulary to entities or documents.

**Interrogation Type:** Closed-Set Classification  
**Version:** 1.0.0  
**Status:** Phase 0 placeholder

---

## What Is Closed-Set Classification?

**Closed-set classification** assigns labels from a **fixed, predefined vocabulary**:

1. **No new labels** — Only allowed values can be assigned
2. **Mutually exclusive or multi-label** — Depends on task configuration
3. **Evidence-grounded** — Classification based on evidence content
4. **Fallback option** — "other" or "unknown" for edge cases

---

## Output Fields

### `label` (Required)

**What to assign:** A value from the controlled vocabulary.

**Rules:**
- Choose only from the allowed values
- Select the single best match (for single-label tasks)
- Do not create new labels
- Use "other" or "unknown" only when no label fits

**Example Vocabulary (Entity Type):**
```
person | place | organization | event | concept | other
```

---

### `evidence_refs` (Required)

**What to extract:** References to evidence that supports this classification.

**Rules:**
- Include at least one evidence reference
- Cite specific passages that justify the label
- Do not cite tangentially related evidence

---

### `confidence` (Required)

**What to assign:** Confidence in the classification.

**Anchors:**

| Level | When to Use |
|-------|-------------|
| `high` | Evidence clearly supports this label |
| `medium` | Evidence supports this label with some ambiguity |
| `low` | Evidence is insufficient but suggests this label |
| `unknown` | Cannot determine appropriate label |

---

### `rationale` (Optional)

**What to provide:** Brief explanation for the classification.

**Rules:**
- Maximum 100 characters
- Cite specific evidence features
- Do not restate the label definition

**Examples:**
- ✅ "Evidence describes founding date and member organizations."
- ❌ "This is an organization because organizations have members."

---

## Multi-Label Classification

When a task allows multiple labels:

1. Assign all applicable labels
2. Order by relevance (most relevant first)
3. Include confidence for each label
4. Do not include contradictory labels

---

## Handling Edge Cases

### Ambiguous Evidence

When evidence supports multiple labels equally:
- Choose the most specific applicable label
- Note ambiguity in `extraction_notes`
- Set confidence to `medium` or `low`

### No Clear Match

When no label fits:
- Use "other" or "unknown" (as defined in vocabulary)
- Explain in `extraction_notes`
- Set confidence to `low`

### Partial Evidence

When evidence is incomplete:
- Make best determination from available evidence
- Note limitations in `extraction_notes`
- Adjust confidence accordingly

---

## Vocabulary Management

Controlled vocabularies are defined in:
- Interrogation definition YAML (`vocabularies` section)
- Vocabulary files in `interrogations/vocab/`

**Vocabulary Requirements:**
- All values must be mutually understandable
- Include a fallback option ("other" or "unknown")
- Document each value's meaning
- Version vocabularies when they change

---

## Null Handling

When classification is not possible:

1. Set `label` to `null`
2. Add entry to `nulls_with_reasons`

**Valid Reasons:**
- `not_found_in_evidence` — No classifiable content
- `ambiguous_in_evidence` — Cannot distinguish between labels
- `not_applicable` — Content is out of scope

---

## Related Documentation

- [Glossary](../../../../docs/llm/glossary.md) — Core terminology
- [Vocabulary Files](../vocab/) — Controlled vocabularies
- [Derived Output Schema](../../contracts/derived_output_schema.json)
