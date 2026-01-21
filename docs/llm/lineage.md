# LLM-Derived Data: Lineage

> **Status:** Placeholder — This document outlines the lineage tracking approach to be implemented in Phase 7.

---

## Overview

This document will define how data lineage is tracked for LLM-derived artifacts, enabling traceability from source evidence through to final outputs.

---

## Lineage Graph Concept

The intended lineage graph follows this structure:

```
Evidence Sources
       │
       ▼
┌──────────────────┐
│  Evidence Items  │  ← Source documents, SQL results, HTTP responses
│  (with hashes)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Evidence Bundle  │  ← Curated collection for a single derivation
│  (bundle_hash)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Derive Run     │  ← LLM execution with manifest tracking
│   (manifest_id)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Derived Artifact │  ← Structured JSON output
│ (artifact_hash)  │
└──────────────────┘
```

---

## Traceability Requirements

### Forward Tracing

From a given evidence source, answer:

- What bundles include this evidence?
- What derive runs used those bundles?
- What artifacts were produced?

### Backward Tracing

From a given derived artifact, answer:

- What manifest produced this artifact?
- What evidence bundle was used?
- What were the original evidence sources?
- What model configuration was used?

---

## Planned Implementation

### Phase 0–1 (Current)

- Manifests store evidence bundle references
- Artifacts link to source manifest IDs
- Hashes enable integrity verification

### Phase 7 (Planned)

- SQL Server tables for lineage relationships
- Query APIs for forward/backward tracing
- Visualization of lineage graphs
- Impact analysis for evidence changes

---

## Key Entities

| Entity | Identifier | Tracked In |
|--------|------------|------------|
| Evidence Item | `source_ref` + `content_hash` | Manifest |
| Evidence Bundle | `bundle_id` + `bundle_hash` | Manifest |
| Derive Run | `manifest_id` | Manifest file |
| Derived Artifact | `artifact_path` + `artifact_hash` | Manifest result |
| LLM Config | Provider + Model + Temperature | Manifest |
| Prompt Template | `prompt_template_ref` + hash | Manifest |

---

## Integrity Verification

Content hashes enable verification at each stage:

1. **Evidence Item Hash** — Verify source content unchanged
2. **Bundle Hash** — Verify bundle composition unchanged
3. **Artifact Hash** — Verify output unchanged

Re-hashing and comparing allows detection of:

- Tampered evidence
- Corrupted artifacts
- Unauthorized modifications

---

## Related Documentation

- [Vision and Roadmap](vision-and-roadmap.md) — Project roadmap
- [Governance](governance.md) — Retention and audit policies
- [Manifest Schema](../../src/llm/contracts/manifest_schema.json) — Manifest structure
- [Glossary](glossary.md) — Core terminology
