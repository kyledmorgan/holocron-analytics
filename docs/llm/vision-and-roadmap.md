# LLM-Derived Data: Vision and Roadmap

> **Feature series:** `2026_01_llm_derived_data` (began January 2026). The phases
> below are the phases of this single series; each is written in canonical form
> `2026_01_llm_derived_data_phase_<n>`. See
> [feature-series convention](../contributing/feature-series-convention.md) and the
> [series history](../history/feature-series/2026_01_llm_derived_data.md).

## Overview

This document establishes the vision, purpose, and phased roadmap for the **LLM-Derived Data** subsystem within Holocron Analytics.

---

## What This Subsystem Is

### Evidence-Led Structured Extraction

The LLM-Derived Data subsystem converts **evidence bundles** (internal docs, web snapshots, SQL result sets, raw HTTP responses, transcripts, and other harvested artifacts) into **structured, schema-bound JSON outputs** ("derived artifacts") that are reproducible and auditable.

The core goal is to produce **queryable, standardized derived information**—facts, classifications, measures, relationships, and data-quality signals—**anchored to citeable evidence**, not freeform narrative.

This is not a conversational agent; each run is **autonomous** (no chat history), but is still **oriented** through:

- Consistent interrogation definitions ("prompt families")
- Evidence bundles with stable IDs
- Strict JSON contracts and rubrics
- Explicit provenance and run manifests

### Why This Matters

| Benefit | Description |
|---------|-------------|
| **Scales Curation** | Turns a growing corpus of harvested content into structured outputs at scale |
| **Evidence-Led, Audit-Ready** | Outputs are treated as **claims**, with citations to evidence bundle IDs |
| **Benchmarkable Across Models** | Supports multi-model comparisons (quality, speed, schema validity, citation integrity) |
| **Reproducible by Design** | Every run stores inputs, evidence IDs, model config, prompt hash, and raw response |

### What This System Produces

The subsystem produces several categories of structured outputs:

1. **Atomic Claims** — Falsifiable statements with evidence IDs
2. **Closed-Set Classifications** — Labels from controlled vocabularies
3. **Rubric-Anchored Measures/Scores** — Numeric outputs with explicit anchors
4. **Relationship Candidates** — Graph edges / bridge outputs
5. **Data-Quality Signals** — Contradictions, ambiguity flags, low-evidence warnings
6. **Backlog Generation** — New questions/jobs to resolve gaps

---

## What This Subsystem Is NOT

### Not Ground Truth

LLM-derived data is **interpreted data**, not authoritative source data. Outputs:

- May contain errors due to model limitations
- Should be validated against schemas and, where possible, verified by humans
- Are subject to the quality of the input evidence
- Are **candidate claims** until verified

### Not Synthetic Data Generation

This is **not** synthetic data generation in the statistical/ML sense:

- No random sampling or probabilistic generation
- No simulation of new data points
- Purely extraction/interpretation from existing evidence

These outputs are best described as **LLM-derived structured artifacts / annotations**.

### Not a Conversational System

- Each job is **autonomous and independent** (no chat history, no memory across runs)
- Not a replacement for interactive assistants or chatbots
- Designed for batch processing and scheduled runs

### Not a Replacement for Authoritative Sources

Derived data supplements, but does not replace:

- Primary data sources
- Human-verified records
- Authoritative databases

---

## Core Concepts

### Interrogation

A repeatable question pattern with:

- A defined **JSON contract** (output schema)
- **Rubric rules** for how to fill fields
- A **prompt template** that assembles evidence and instructions

See: [Glossary](glossary.md) for detailed definitions.

### Evidence Bundle

A curated collection of evidence objects with stable IDs. The model cites only these IDs—no external references are allowed.

Each item in a bundle has:

- **Source type**: `ingest_record`, `sql_result`, `http_response`, `document`, `other`
- **Source reference**: Path, ID, or query hash
- **Content hash**: SHA256 for integrity verification

### Manifest

Run metadata capturing:

- Versions and timestamps
- Input evidence references and hashes
- Model configuration
- Timing and status
- Raw output references
- Validation results

### Contract-First

Output must validate against a predefined JSON schema. Nulls are allowed but must include a `null_reason`. Invalid outputs fail the operation.

### Evidence-First

Claims must cite evidence IDs. Fields without supporting evidence return null with an explanation. The model is not allowed to infer beyond what is explicitly stated in the evidence.

---

## Roadmap

### Foundations and Scaffolding — `2026_01_llm_derived_data_phase_0` ✅

**Status:** ✅ COMPLETE

**Intent:** Establish vocabulary, structure, contracts, and minimal runnable spine; avoid locking in details.

**Deliverables:**

- [x] `docs/llm/` vision, glossary, contracts, policy placeholders
- [x] Contract placeholder schemas (manifest + derived output)
- [x] `src/llm/` scaffolding aligned to later phases of this series
- [x] Interrogation catalog skeleton with rubric templates
- [x] Ollama Docker Compose service with model persistence
- [x] Agent guidance updates (`agents/llm-derived-data.md`)
- [x] Docs index updates
- [x] Smoke test for provider connectivity

**Decisions Kept Open (TBD):**

| Decision | Status | Notes |
|----------|--------|-------|
| Native Ollama API vs OpenAI-compatible endpoints | TBD | Both supported; selection via config |
| Exact SQL Server schema / stored procedures | TBD | Scaffold only |
| Vector store + embeddings strategy | TBD | Later phase of this series |
| JSON validation library | TBD | `jsonschema` or `pydantic` |

---

### MVP Runner — `2026_01_llm_derived_data_phase_1`

**Status:** 🔮 Planned

**Intent:** Single interrogation, single model, deterministic logging.

**Deliverables:**

- Minimal SQL Server queue schema + atomic claim-next semantics
- One interrogation implemented end-to-end (claims + citations)
- Artifact persistence: manifest/evidence/raw/parsed + validation results

---

### Evidence Assembly — `2026_01_llm_derived_data_phase_2`

**Status:** 🔮 Planned

**Intent:** Internal docs + SQL evidence sets.

**Deliverables:**

- Evidence bundle builders for doc chunks, SQL result artifacts, raw HTTP responses
- Bounding/sampling rules; redaction hooks

---

### RAG / Retrieval — `2026_01_llm_derived_data_phase_3`

**Status:** 🔮 Planned

**Intent:** Vector retrieval for evidence assembly.

**Deliverables:**

- Chunking + embeddings + vector retrieval to build evidence bundles
- Relevance/dedupe/token budgeting rules

---

### Web Evidence — `2026_01_llm_derived_data_phase_4`

**Status:** 🔮 Planned

**Intent:** Deterministic snapshotting + source policy.

**Deliverables:**

- Search/fetch/snapshot/extract pipeline
- Model citations must map to stored snapshots
- Domain allow/deny policy and citation integrity checks

---

### Multi-Model Benchmarking and Adjudication — `2026_01_llm_derived_data_phase_5`

**Status:** 🔮 Planned

**Intent:** Compare models on the same jobs.

**Deliverables:**

- Model registry + run groups (same job across models)
- Metrics (schema validity, citation validity, latency, disagreement)
- Optional adjudicator step (rule-based or model-based)

---

### Interrogation Catalog Expansion — `2026_01_llm_derived_data_phase_6`

**Status:** 🔮 Planned

**Intent:** Rubrics + vocabularies.

**Deliverables:**

- Catalog definitions
- Controlled vocabularies
- Schema evolution strategy

---

### Governance, Lineage, and Operational Hardening — `2026_01_llm_derived_data_phase_7`

**Status:** 🔮 Planned

**Intent:** Production readiness.

**Deliverables:**

- Retention and redaction/PII modes
- Lineage mapping
- Observability and monitoring

---

## Related Documentation

- [Glossary](glossary.md) — Core terminology
- [Ollama Integration Guide](ollama.md) — API documentation
- [Status Tracker](status.md) — Implementation progress
- [LLM-Derived Data Overview](derived-data.md) — Conceptual overview
- [LLM Module README](../../src/llm/README.md) — Source code overview
