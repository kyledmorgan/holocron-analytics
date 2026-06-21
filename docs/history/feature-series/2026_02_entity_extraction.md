# Entity Extraction Feature Series

**Series ID:** `2026_02_entity_extraction`
**Status:** `partially_complete`
**Began:** February 2026
**Highest planned phase:** 7
**Highest confirmed completed phase:** 3

## Purpose

This series implements the Functional Gap Analysis (FGA) plan to grow LLM-based
entity extraction from a single subtype to a general, multi-output pipeline. The
phased plan is defined in
[`docs/fga/05-recommendations-and-next-steps.md`](../../fga/05-recommendations-and-next-steps.md).

It is **distinct** from [`2026_01_llm_derived_data`](2026_01_llm_derived_data.md)
even though both number their phases 1/2/3. This series builds on the derive runner
delivered by that earlier series. See the
[collision note](README.md#phase-numbering-collision-the-core-ambiguity).

## Historical phases

| Phase | Status | Intended scope | Implemented evidence | Related PR / branch |
| --- | --- | --- | --- | --- |
| `2026_02_entity_extraction_phase_0` | `complete` | Minimal scaffolding: LLM job type, structured logging, dry-run storage. | `docs/fga/05-recommendations-and-next-steps.md`, `agents/llm-derived-data.md` | PR #48 (`copilot/implement-minimal-scaffolding`) |
| `2026_02_entity_extraction_phase_1` | `complete` | One contract end-to-end: droid entity extraction + batch insert. | `src/llm/interrogations/definitions/entity_extraction_droid.py`, `src/llm/handlers/entity_extraction_droid.py`, migration `0026` | PR #49 (`copilot/implement-droid-entity-pipeline`) |
| `2026_02_entity_extraction_phase_2` | `complete` | Relationships + multi-output routing (entity-entity with temporal bounds). | `src/llm/handlers/relationship_extraction.py`, migrations `0027`, `0028` | PR #51 (`copilot/extend-multi-output-routing`) |
| `2026_02_entity_extraction_phase_3` | `complete` | Broader coverage: generic multi-type extraction, automated backfill CLI, queue health monitoring. | `src/llm/interrogations/definitions/entity_extraction_generic.py`, `src/llm/handlers/entity_extraction_generic.py`, `src/llm/cli/backfill.py`, `db/migrations/0029_queue_health_views.sql` | PR #52 (`copilot/expand-phase-3-coverage`) |
| `2026_02_entity_extraction_phase_4` | `planned` | Governance + human review UI for relationship assertions (optional). | Planning only (FGA roadmap) | None found |
| `2026_02_entity_extraction_phase_5` | `planned` | Advanced chunking + vector retrieval integration. | Planning only | None found |
| `2026_02_entity_extraction_phase_6` | `planned` | Event + work extraction (DimEvent/DimWork bridges scaffolded). | Bridge tables scaffolded in migration `0027`; extraction not implemented | None found |
| `2026_02_entity_extraction_phase_7` | `planned` | Automated testing + CI/CD for the pipeline. | Planning only | None found |

## Current implemented state

Phases 0–3 are implemented: scaffolding, droid extraction, relationship extraction
with multi-output routing, and generic multi-type extraction with backfill tooling
and queue health views. The `DimEvent`/`DimWork` bridge tables exist as scaffolding
(migration `0027`) ahead of Phase 6 event/work extraction.

## Outstanding work

Governance/human-review UI (Phase 4), vector retrieval integration (Phase 5), event
and work extraction (Phase 6), and automated testing/CI (Phase 7) remain planned.

## Superseded or retired assumptions

- None recorded. The FGA roadmap's later phases remain the current plan of record.

## Source evidence

- `docs/fga/05-recommendations-and-next-steps.md` (phased implementation plan, Phases 0–7)
- `db/migrations/0026_batch_entity_insert.sql`, `0027_create_relationship_bridges.sql`, `0028_batch_relationship_insert.sql`
- `src/llm/interrogations/definitions/entity_extraction_droid.py`, `entity_extraction_generic.py`
- `src/llm/handlers/relationship_extraction.py`
- `docs/pr_prompts_and_reports/048.md`, `049.md`, `051.md`, `052.md`
