# Anchored Score Rubric

## Overview

This rubric provides guidance for the **Anchored Score** interrogation type. Anchored scores are numeric values assigned according to explicit criteria, with each score level having a defined meaning.

**Interrogation Type:** Anchored Score  
**Version:** 1.0.0  
**Status:** Phase 0 placeholder

---

## What Are Anchored Scores?

An **anchored score** is:

1. **Numeric** — A value on a defined scale (e.g., 1-5, 0-100)
2. **Anchored** — Each level has explicit criteria
3. **Evidence-based** — Score reflects evidence content
4. **Reproducible** — Same evidence should yield consistent scores

---

## Output Fields

### `score` (Required)

**What to assign:** A numeric value on the defined scale.

**Rules:**
- Use only valid values for the scale
- Apply anchor criteria consistently
- Do not interpolate between anchors (use defined values)
- When between anchors, round down (conservative scoring)

---

### `anchor_applied` (Required)

**What to specify:** Which anchor criterion was matched.

**Rules:**
- Reference the specific anchor from the rubric
- If between anchors, cite the lower anchor
- Include the anchor description or key

---

### `evidence_refs` (Required)

**What to extract:** References to evidence supporting this score.

**Rules:**
- Cite evidence that matches the anchor criteria
- Include all relevant evidence (not just one example)
- Order by relevance to the anchor criteria

---

### `confidence` (Required)

**What to assign:** Confidence in the score assignment.

**Anchors:**

| Level | When to Use |
|-------|-------------|
| `high` | Evidence clearly matches one anchor |
| `medium` | Evidence mostly matches an anchor with minor gaps |
| `low` | Evidence partially matches, significant interpretation needed |
| `unknown` | Cannot determine appropriate score |

---

### `rationale` (Optional)

**What to provide:** Explanation for the score assignment.

**Rules:**
- Maximum 200 characters
- Reference specific anchor criteria
- Cite evidence features that match

---

## Example: Quality Score (1-5 Scale)

### Anchor Definitions

| Score | Anchor | Criteria |
|-------|--------|----------|
| 5 | Excellent | Complete, accurate, well-sourced, no gaps |
| 4 | Good | Mostly complete, accurate, minor gaps |
| 3 | Adequate | Covers basics, some gaps or minor issues |
| 2 | Poor | Significant gaps, accuracy concerns |
| 1 | Inadequate | Minimal coverage, major issues |

### Application Example

**Evidence:** A Wikipedia article with 10 citations, covering main topics but missing some details.

**Score:** 4  
**Anchor Applied:** "Good — Mostly complete, accurate, minor gaps"  
**Rationale:** "Article covers primary topics with citations but lacks detail on early history."

---

## Example: Confidence Score (0-100 Scale)

### Anchor Definitions

| Score Range | Anchor | Criteria |
|-------------|--------|----------|
| 90-100 | Very High | Multiple authoritative sources agree |
| 70-89 | High | Authoritative source with corroboration |
| 50-69 | Moderate | Single authoritative source or multiple secondary |
| 30-49 | Low | Secondary sources only, some disagreement |
| 0-29 | Very Low | Uncertain, conflicting, or unverifiable |

---

## Handling Edge Cases

### Between Anchors

When evidence falls between two anchors:
- Apply the **lower** anchor (conservative)
- Note in `extraction_notes` why the higher anchor wasn't applied
- Adjust confidence accordingly

### No Clear Anchor Match

When evidence doesn't clearly match any anchor:
- Apply the closest lower anchor
- Set confidence to `low`
- Explain in `rationale`

### Insufficient Evidence

When evidence is too sparse to score:
- Set score to `null`
- Add `not_found_in_evidence` to `nulls_with_reasons`

---

## Scale Types

### Ordinal Scales

Fixed discrete values (1, 2, 3, 4, 5):
- Each value has a specific meaning
- Do not use decimals
- All anchors must be defined

### Continuous Scales

Range of values (0-100):
- Define anchor ranges, not just points
- Precision should match rubric granularity
- Consider rounding rules

---

## Null Handling

When a score cannot be assigned:

1. Set `score` to `null`
2. Add entry to `nulls_with_reasons`

**Valid Reasons:**
- `not_found_in_evidence` — Insufficient evidence to score
- `ambiguous_in_evidence` — Conflicting signals
- `not_applicable` — Scoring not relevant for this content

---

## Related Documentation

- [Glossary](../../../../docs/llm/glossary.md) — Core terminology
- [Derived Output Schema](../../contracts/derived_output_schema.json)
- [Vision and Roadmap](../../../../docs/llm/vision-and-roadmap.md)
