# LLM-Derived Data Feature Series

**Series ID:** `2026_01_llm_derived_data`
**Status:** `partially_complete`
**Began:** January 2026
**Highest planned phase:** 7
**Highest confirmed completed phase:** 3

## Purpose

The LLM-Derived Data subsystem converts evidence bundles (internal docs, web
snapshots, SQL result sets, raw HTTP responses, transcripts) into structured,
schema-bound JSON artifacts that are reproducible and auditable. See
[`docs/llm/vision-and-roadmap.md`](../../llm/vision-and-roadmap.md) for the full
vision and [`docs/llm/status.md`](../../llm/status.md) for the live status tracker.

This is the original phased roadmap (Phases 0–7) for the subsystem. It is distinct
from [`2026_02_entity_extraction`](2026_02_entity_extraction.md), which reuses the
same phase numbers for a different body of work — see the
[collision note](README.md#phase-numbering-collision-the-core-ambiguity).

## Historical phases

| Phase | Status | Intended scope | Implemented evidence | Related PR / branch |
| --- | --- | --- | --- | --- |
| `2026_01_llm_derived_data_phase_0` | `complete` | Foundations & scaffolding: docs, contracts, interrogation skeleton, Ollama compose, agent guidance. | `docs/llm/`, `src/llm/` scaffolding, `agents/llm-derived-data.md` | PR #16, #20, #22 (`copilot/complete-phase-0-docs-scaffolding`) |
| `2026_01_llm_derived_data_phase_1` | `complete` | MVP runner: SQL Server queue, atomic claim-next, end-to-end interrogation, artifact persistence, CLI. | `src/llm/runners/phase1_runner.py`, `src/llm/contracts/phase1_contracts.py`, migration `0005`, `tests/unit/llm/test_phase1_*` | PR #23 (`copilot/implement-derived-data-pipeline-phase-1`) |
| `2026_01_llm_derived_data_phase_2` | `complete` | Evidence assembly: bundle builder, source adapters, bounding, redaction, SQL packaging. | `src/llm/evidence/`, `src/llm/contracts/evidence_contracts.py`, migration `0007`, `PHASE2_IMPLEMENTATION_SUMMARY.md` | PR #24, #25 (`copilot/implement-phase-2-evidence-assembly`) |
| `2026_01_llm_derived_data_phase_3` | `complete` | RAG / retrieval: chunking, embeddings, vector storage, retrieval, evidence integration. | `src/llm/retrieval/`, migration `0008`, `docs/llm/retrieval.md`, `docs/llm/indexing.md` | PR #26 (`copilot/implement-phase-3-retrieval-augmentation`) |
| `2026_01_llm_derived_data_phase_4` | `planned` | Web evidence: deterministic snapshotting, source allow/deny policy, citation integrity. | Planning only (`docs/llm/vision-and-roadmap.md`) | None found |
| `2026_01_llm_derived_data_phase_5` | `planned` | Multi-model benchmarking & adjudication. | Planning only | None found |
| `2026_01_llm_derived_data_phase_6` | `planned` | Interrogation catalog expansion (rubrics, vocabularies, schema evolution). | Planning only | None found |
| `2026_01_llm_derived_data_phase_7` | `planned` | Governance, lineage, operational hardening. Partly anticipated by PR #60 (provenance + lineage schema). | Planning only; partial provenance/lineage groundwork in PR #60 | PR #60 (`copilot/add-llm-provenance-lineage`), inferred — not a formal phase delivery |

## Current implemented state

Phases 0–3 are implemented and tested: the derive runner claims jobs from a SQL
Server queue, assembles bounded/redacted evidence bundles, calls Ollama, validates
output against contracts, and persists artifacts; the retrieval pipeline adds
chunking, embeddings, and vector retrieval feeding evidence assembly. The status
tracker (`docs/llm/status.md`) marks Phases 0–3 complete.

## Outstanding work

Web evidence (Phase 4), multi-model benchmarking/adjudication (Phase 5),
interrogation catalog expansion (Phase 6), and governance/lineage hardening
(Phase 7) remain planned. Provenance and lineage schema work (PR #60) advances some
Phase 7 groundwork but is not a formal completion of that phase.

## Superseded or retired assumptions

- The original vector storage built in Phase 3 (under the `llm` schema) was later
  migrated out by [`2026_02_vector_runtime_split`](2026_02_vector_runtime_split.md);
  the `llm.chunk/embedding/retrieval*` tables are now `*_legacy`.

## Source evidence

- `docs/llm/vision-and-roadmap.md` (roadmap Phases 0–7)
- `docs/llm/status.md` (phase checklists)
- `PHASE2_IMPLEMENTATION_SUMMARY.md`
- `src/llm/runners/phase1_runner.py`, `src/llm/contracts/phase1_contracts.py`
- `db/migrations/0005_create_llm_tables.sql`, `0007_evidence_bundle_tables.sql`, `0008_create_retrieval_tables.sql`
- `docs/pr_prompts_and_reports/016.md`, `020.md`, `022.md`, `023.md`, `024.md`, `025.md`, `026.md`, `060.md`
