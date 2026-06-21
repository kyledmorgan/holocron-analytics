# LLM-Derived Data: Lineage and Provenance

> **Status:** Active — Lineage schema extensions implemented in migrations 0033 and 0034.

---

## Overview

This document defines how data lineage and provenance are tracked for LLM-derived artifacts, enabling traceability from source evidence through to final DVO outputs.

The system splits provenance into two layers:

- **Extractor provenance**: "Which run/model/prompt produced this output?" (Ollama as extraction source)
- **Evidence provenance**: "Which real-world sources were included in the curated input bundle?" (articles, PDFs, SQL results, etc.)

---

## Lineage Graph

```
Evidence Sources (articles, PDFs, SQL results, transcripts, etc.)
       │
       ▼
┌──────────────────┐
│  Evidence Items  │  ← Source documents with selectors, roles, ordinals
│  (content_sha256)│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Evidence Bundle  │  ← Curated collection for a single derivation
│ (bundle_sha256)  │     bundle_kind, created_by, notes
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   LLM Run        │  ← Execution with prompt, model, and artifact pointers
│  (run_fingerprint│     request/response/output artifacts
│   parent_run_id) │     prompt_template_ref + prompt_hash
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ DVO Records      │  ← Facts, claims, bridges, relations
│ (EvidenceBundleGuid) ← Traces back to evidence context
└──────────────────┘
```

---

## Key Design Principles

### Ollama as Extraction Source

Ollama is treated as a **source system** that produces derived interpretations. It is:

- **Not deterministic** — output may vary across runs
- **Not the identity authority** — true origins are the underlying evidence sources

Convention for DVO records:
- `SourceSystem = 'ollama'`
- `SourceRef = 'run:{run_id}'`
- `EvidenceBundleGuid = {bundle_id}` (when derived from curated evidence)

### Evidence Bundles as the Anchor

An evidence bundle is deterministic when we store:
- The ordered membership (items with ordinals)
- Content hashes for each item
- A deterministic bundle fingerprint (`bundle_sha256`)

---

## Schema Extensions

### LLM Tables (Migration 0033)

#### `llm.run` — Artifact Pointers and Run Chaining

| Column | Type | Purpose |
|--------|------|---------|
| `request_artifact_id` | UNIQUEIDENTIFIER NULL | FK → artifact for the request body sent to Ollama |
| `response_artifact_id` | UNIQUEIDENTIFIER NULL | FK → artifact for the raw response from Ollama |
| `output_artifact_id` | UNIQUEIDENTIFIER NULL | FK → artifact for the validated JSON output |
| `prompt_rendered_artifact_id` | UNIQUEIDENTIFIER NULL | FK → artifact for the final rendered prompt |
| `prompt_template_ref` | NVARCHAR(200) NULL | Stable identifier of the prompt template |
| `prompt_template_version` | NVARCHAR(50) NULL | Version of the prompt template |
| `prompt_hash` | NVARCHAR(64) NULL | SHA256 hash of the rendered prompt text |
| `parent_run_id` | UNIQUEIDENTIFIER NULL | Self-FK for chained runs (classification → extraction) |
| `run_fingerprint` | NVARCHAR(64) NULL | Deterministic hash for deduping identical reruns |

#### `llm.artifact` — Content Type Metadata

| Column | Type | Purpose |
|--------|------|---------|
| `content_mime_type` | NVARCHAR(100) NULL | Helps interpret artifact payloads |
| `schema_version` | NVARCHAR(50) NULL | Version of output contract if applicable |

Expanded `artifact_type` values: `prompt_template`, `prompt_rendered`, `llm_request`, `llm_response_raw`, `llm_output_json`, `llm_output_validation_report`, `merge_payload`, `merge_result_report`.

#### `llm.evidence_item` — Source Identifiers, Selectors, Roles

| Column | Type | Purpose |
|--------|------|---------|
| `source_system` | NVARCHAR(100) NULL | Origin system (wikipedia, youtube, pdf, sql, etc.) |
| `source_uri` | NVARCHAR(2000) NULL | Canonical URL for external sources |
| `source_ref` | NVARCHAR(400) NULL | Source-native identifier (page_id, revision_id, etc.) |
| `selector_json` | NVARCHAR(MAX) NULL | Structured selection details (offsets, page ranges, etc.) |
| `ordinal` | INT NULL | Ordering within the bundle for deterministic assembly |
| `role` | NVARCHAR(50) NULL | How the evidence is used (primary/supporting/counter/context) |
| `excerpt_hash` | NVARCHAR(64) NULL | Hash of the excerpt used if different from full content |
| `created_utc` | DATETIME2(3) NOT NULL | Audit timestamp for evidence item creation |

#### `llm.evidence_bundle` — Deterministic Fingerprint

| Column | Type | Purpose |
|--------|------|---------|
| `bundle_sha256` | NVARCHAR(64) NULL | Deterministic hash of ordered membership + content hashes |
| `bundle_kind` | NVARCHAR(50) NULL | Bundle category (llm_input, human_review_packet, etc.) |
| `created_by` | NVARCHAR(200) NULL | Worker/user identifier that assembled the bundle |
| `notes` | NVARCHAR(2000) NULL | Optional human commentary about the bundle |
| `assembly_artifact_id` | UNIQUEIDENTIFIER NULL | Pointer to the assembled input text artifact |

#### `llm.run_evidence` — Attachment Purpose

| Column | Type | Purpose |
|--------|------|---------|
| `role` | NVARCHAR(50) NULL | Why the bundle is attached (input/output_support/human_override/comparison) |
| `attached_by` | NVARCHAR(200) NULL | Worker/user identifier |
| `attached_reason` | NVARCHAR(500) NULL | Optional short text explaining the linkage |

#### `llm.job` — Evidence and Prompt Intent at Enqueue Time

| Column | Type | Purpose |
|--------|------|---------|
| `input_bundle_id` | UNIQUEIDENTIFIER NULL | FK → evidence_bundle for intended input context |
| `prompt_template_ref` | NVARCHAR(200) NULL | Intended prompt contract |
| `prompt_template_version` | NVARCHAR(50) NULL | Version of the intended prompt contract |
| `contract_version` | NVARCHAR(50) NULL | Version of JSON schema expected from the LLM |
| `requested_output_types` | NVARCHAR(500) NULL | Which DVO object families are expected |
| `job_fingerprint` | NVARCHAR(64) NULL | Deterministic hash for dedupe standardization |

### DVO Tables (Migration 0034)

All DVO fact and bridge tables gain a nullable `EvidenceBundleGuid`:

| Table | Column Added |
|-------|-------------|
| `dbo.FactEvent` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |
| `dbo.FactClaim` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |
| `dbo.ContinuityIssue` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |
| `dbo.BridgeEventParticipant` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |
| `dbo.BridgeEventAsset` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |
| `dbo.BridgeContinuityIssueClaim` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |
| `dbo.BridgeEntityRelation` | `EvidenceBundleGuid UNIQUEIDENTIFIER NULL` |

Each column has a filtered index for efficient lookups where the value is not null.

---

## Traceability Queries

### Forward Tracing

From a given evidence source, answer:

- What bundles include this evidence?
- What derive runs used those bundles?
- What artifacts were produced?
- What DVO records were created/updated?

### Backward Tracing

From a given derived DVO record, answer:

- What evidence bundle influenced this record? (`EvidenceBundleGuid`)
- What run produced it? (`SourceRef = 'run:{run_id}'`)
- What model/prompt/options were used? (via `llm.run`)
- What were the original evidence sources? (via `llm.evidence_item`)

### Impact Tracking

Given an `EvidenceBundleGuid`, retrieve:

1. **Inputs** — evidence_bundle + evidence_items + selectors + roles
2. **LLM Execution** — run row (model digest/options/metrics) + request/response/output artifacts
3. **Database Impact** — DVO rows tagged with that EvidenceBundleGuid across all tables

---

## Python Contract Extensions

The `EvidenceItem` dataclass gains optional provenance fields:
- `source_system`, `source_uri`, `selector_json`, `ordinal`, `role`, `excerpt_hash`

The `EvidenceBundle` dataclass gains:
- `bundle_sha256`, `bundle_kind`, `created_by`, `notes`
- `compute_bundle_hash()` method for deterministic fingerprinting

All new fields are optional with `None` defaults for backward compatibility.

---

## Integrity Verification

Content hashes enable verification at each stage:

1. **Evidence Item Hash** — Verify source content unchanged
2. **Bundle Hash** (`bundle_sha256`) — Verify bundle composition unchanged
3. **Artifact Hash** — Verify request/response/output unchanged
4. **Run Fingerprint** — Detect identical reruns

---

## Related Documentation

- [Evidence](evidence.md) — Phase 2 evidence assembly system
- [Contracts](contracts.md) — JSON contract schemas
- [Governance](governance.md) — Retention and audit policies
- [Vision and Roadmap](vision-and-roadmap.md) — Project roadmap
- [Glossary](glossary.md) — Core terminology
