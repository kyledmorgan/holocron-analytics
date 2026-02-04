# Atomic Claims Rubric

## Overview

This rubric provides guidance for the **Atomic Claims** interrogation type. Atomic claims are falsifiable statements extracted from evidence, each with explicit source citations.

**Interrogation Type:** Atomic Claims  
**Version:** 1.0.0  
**Status:** Phase 0 placeholder

---

## What Are Atomic Claims?

An **atomic claim** is:

1. **Falsifiable** — Can be verified as true or false
2. **Self-contained** — Complete statement without context
3. **Cited** — Links to specific evidence IDs
4. **Minimal** — Single fact, not compound statements

---

## Output Fields

### `claim_text` (Required)

**What to extract:** A single, complete, falsifiable statement.

**Rules:**
- State one fact per claim
- Use present tense when possible
- Include enough context to be understood standalone
- Do not use pronouns without antecedents

**Examples:**
- ✅ "Luke Skywalker was raised on Tatooine by his aunt and uncle."
- ✅ "The Millennium Falcon completed the Kessel Run in less than 12 parsecs."
- ❌ "He was raised there." (ambiguous, lacks context)
- ❌ "Luke was a Jedi and also trained with Yoda." (compound claim)

---

### `evidence_refs` (Required)

**What to extract:** References to evidence items that support this claim.

**Rules:**
- Include at least one evidence reference
- Use the `source_ref` from the evidence bundle
- Only cite evidence that explicitly supports the claim
- Do not cite evidence that merely mentions related topics

---

### `confidence` (Required)

**What to assign:** Confidence level for this claim.

**Anchors:**

| Level | When to Use |
|-------|-------------|
| `high` | Claim is explicitly stated in evidence |
| `medium` | Claim requires minor inference from explicit evidence |
| `low` | Claim requires interpretation of ambiguous evidence |
| `unknown` | Cannot assess confidence (rare) |

---

### `claim_type` (Optional)

**What to assign:** Category of the claim.

**Allowed Values:**
- `factual` — Statement of fact
- `temporal` — Time-related statement
- `relational` — Relationship between entities
- `quantitative` — Numeric or measurement statement
- `attributive` — Property or characteristic statement

---

## Breaking Down Compound Statements

When evidence contains compound statements, break them into atomic claims:

**Original:** "Darth Vader, formerly Anakin Skywalker, was a Sith Lord who served the Galactic Empire."

**Atomic Claims:**
1. "Darth Vader was formerly known as Anakin Skywalker."
2. "Darth Vader was a Sith Lord."
3. "Darth Vader served the Galactic Empire."

---

## Null Handling

When a field cannot be extracted:

1. Set the field value to `null`
2. Add an entry to `nulls_with_reasons`

**Valid Reasons:**
- `not_found_in_evidence` — No supporting evidence
- `ambiguous_in_evidence` — Conflicting statements
- `extraction_failed` — Technical error

---

## Quality Signals

When extracting claims, also note:

- **Contradictions** — Multiple claims that conflict
- **Ambiguity** — Evidence that is unclear
- **Low coverage** — Topics with insufficient evidence

---

## Related Documentation

- [Glossary](../../../../docs/llm/glossary.md) — Core terminology
- [Derived Output Schema](../../contracts/derived_output_schema.json)
- [Vision and Roadmap](../../../../docs/llm/vision-and-roadmap.md)
