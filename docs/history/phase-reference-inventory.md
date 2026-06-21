# Phase-Reference Inventory

This report inventories ambiguous, unqualified feature-development phase references
across the repository and records how each is being resolved. It was produced as
the first step of the repository-wide phase-naming cleanup, before any broad
replacement.

- Naming rules: [`docs/contributing/feature-series-convention.md`](../contributing/feature-series-convention.md)
- Reconstructed series: [`docs/history/feature-series/README.md`](feature-series/README.md)

## Method

References were found with a case-insensitive search for `phase <n>`, `phase_<n>`,
`phase-<n>`, `phase zero/one/…`, and the qualifiers `next/future/later/subsequent/
previous/earlier/final/cleanup/scaffolding/implementation phase`. Each match was
reviewed in context. Genuine domain/technical uses of "phase" were excluded from
replacement.

## Confidence and action legend

- **Confidence:** `High` / `Medium` / `Low` / `Unresolved`.
- **Recommended action:**
  - `Replace` — qualify with a canonical series ID.
  - `Qualify-comment` — add the canonical series ID to a code comment/docstring.
  - `Qualify-TODO` — convert an outstanding placeholder into `TODO(<series>_phase_<n>)`.
  - `Keep (identifier)` — stable importable code symbol/filename/tag; renaming would
    break the public API and tests, so it is intentionally retained.
  - `Keep (domain)` — legitimate technical/domain terminology.
  - `Keep (history)` — historical archive that must not be rewritten.
  - `Keep (program)` — program-level roadmap milestone, not a PR feature series.

## Series key

| Series ID | Short name |
| --- | --- |
| `2026_01_llm_derived_data` | LLM-Derived Data subsystem (runner/evidence/retrieval) |
| `2026_02_entity_extraction` | Entity & relationship extraction expansion (FGA) |
| `2026_02_vector_runtime_split` | Chat/vector schema split |
| `2026_02_openalex_lake` | OpenAlex lake ingest |

---

## A. SQL migrations (the core conflation)

`0005`/`0007`/`0008` belong to `2026_01_llm_derived_data`; `0026`–`0029`/`0032`
belong to `2026_02_entity_extraction`. They reuse the same phase numbers, which is
the central ambiguity. Migration headers have been qualified in place.

| File | Line | Reference | Series | Confidence | Action |
| --- | ---: | --- | --- | --- | --- |
| `db/migrations/0005_create_llm_tables.sql` | 1 | `Phase 1` | `2026_01_llm_derived_data` | High | Qualify-comment |
| `db/migrations/0007_evidence_bundle_tables.sql` | 1 | `Phase 2` | `2026_01_llm_derived_data` | High | Qualify-comment |
| `db/migrations/0008_create_retrieval_tables.sql` | 1 | `Phase 3` | `2026_01_llm_derived_data` | High | Qualify-comment |
| `db/migrations/0023_create_vector_schema.sql` | 1, 5 | `Phase 1` | `2026_02_vector_runtime_split` | High | Qualify-comment |
| `db/migrations/0024_deprecate_llm_vector_tables.sql` | 1 | `Phase 2 Cutover` | `2026_02_vector_runtime_split` | High | Qualify-comment |
| `db/migrations/0026_batch_entity_insert.sql` | 1, 12, 13 | `Phase 1/2/3` | `2026_02_entity_extraction` | High | Qualify-comment |
| `db/migrations/0027_create_relationship_bridges.sql` | 1, 5, 15–17, 186, 279, 360, 451, 530 | `Phase 2/3/4/6` | `2026_02_entity_extraction` | High | Qualify-comment / Qualify-TODO (Phase 6 placeholders) |
| `db/migrations/0028_batch_relationship_insert.sql` | 1, 12, 13 | `Phase 2/3/4` | `2026_02_entity_extraction` | High | Qualify-comment |
| `db/migrations/0029_queue_health_views.sql` | 2, 10 | `Phase 3/4/7` | `2026_02_entity_extraction` | High | Qualify-comment |
| `db/migrations/0032_schema_standardization_full.sql` | 226, 228 | `Phase 6 Placeholder` | `2026_02_entity_extraction` | High | Qualify-comment |
| `db/legacy_snapshots/llm_vector_subsystem_snapshot.sql` | 9, 37, 295, 301, 306 | `Phase 0/1/2/3` | `2026_01_llm_derived_data` + `2026_02_vector_runtime_split` | High | Keep (history) — snapshot is a historical artifact |

## B. LLM-Derived Data source (`2026_01_llm_derived_data`)

Importable identifiers (`phase1_runner.py`, `Phase1Runner`, `phase1_contracts`,
`from ..contracts.phase1_contracts import …`) are retained as stable names. Their
descriptive docstrings/comments are qualified.

| File | Line(s) | Reference | Confidence | Action |
| --- | --- | --- | --- | --- |
| `src/llm/runners/phase1_runner.py` | filename, 2, 4, 67, 90–129, 529–594, 718–793 | `Phase 1` / `Phase1Runner` / `Phase 2 builder` | High | Keep (identifier) for symbols; Qualify-comment for module docstring |
| `src/llm/contracts/phase1_contracts.py` | filename, 2, 5 | `Phase 1 Contracts` | High | Keep (identifier); Qualify-comment for docstring |
| `src/llm/contracts/evidence_contracts.py` | 2, 5, 7 | `Phase 2` | High | Qualify-comment |
| `src/llm/contracts/retrieval_contracts.py` | 2, 5, 7 | `Phase 3` | High | Qualify-comment |
| `src/llm/evidence/__init__.py`, `evidence/builder.py` | 2 | `Phase 2` | High | Qualify-comment |
| `src/llm/evidence/redaction.py` | 4, 5 | `Phase 2` / `future Phase 7 hardening` | High | Qualify-comment / Qualify-TODO |
| `src/llm/retrieval/__init__.py`, `evidence_converter.py` | 2, 4, 32 | `Phase 3` / `Phase 2` | High | Qualify-comment |
| `src/llm/retrieval/indexer.py`, `search.py` | 10, 45, 137, 172 | `Phase 2` (vector cutover) | High | Qualify-comment → `2026_02_vector_runtime_split` |
| `src/llm/runners/derive_runner.py` | 5, 40 | `planned for Phase 1` | High | Qualify-comment |
| `src/llm/runners/dispatcher.py` | 30, 336, 432, 536 | `Phase1` patterns / import | High | Keep (identifier) |
| `src/llm/storage/sql_queue_store.py` | 5 | `later phases` | Medium | Qualify-comment |
| `.env.example` | 86, 88 | `Phase 1` | High | Qualify-comment |
| `docker-compose.yml` | 164, 176, 210 | `Phase 1 Derive Runner` / `phase1_runner` | High | Qualify-comment (text); Keep (identifier) for module path |
| `scripts/llm_enqueue_job.py` | 5 | `Phase 1 runner` | High | Qualify-comment |
| `tests/unit/llm/test_phase1_*`, `test_evidence_contracts.py`, `test_retrieval_*`, `test_chunking.py` | various | `Phase 1/2/3`, `Phase1Runner` | High | Keep (identifier) for symbols; tests reference stable APIs |

## C. Entity extraction source (`2026_02_entity_extraction`)

| File | Line(s) | Reference | Confidence | Action |
| --- | --- | --- | --- | --- |
| `src/llm/handlers/relationship_extraction.py` | 13, 14 | `Phase 2` / `Phase 3/4 foundation` | High | Qualify-comment / Qualify-TODO |
| `src/llm/handlers/entity_extraction_generic.py` | 4 | `Phase 3` | High | Qualify-comment |
| `src/llm/interrogations/definitions/entity_extraction_droid.py` | 5, 317 | `Phase 1` | High | Qualify-comment |
| `src/llm/interrogations/definitions/entity_extraction_generic.py` | 4, 519 | `Phase 3` | High | Qualify-comment |
| `src/llm/interrogations/definitions/relationship_extraction.py` | 5, 347 | `Phase 2` | High | Qualify-comment |
| `src/llm/interrogations/registry.py` | 136, 141 | `Phase 2/3` | High | Qualify-comment |
| `src/llm/jobs/registry.py` | 190, 200, 201, 204, 214, 215, 218, 228, 229 | `Phase 1/2/3`, tags `phase1/2/3` | High | Qualify-comment (descriptions); Keep (identifier) for tags |
| `src/llm/cli/backfill.py`, `cli/priority.py` | 4 | `Phase 3` | High | Qualify-comment |
| `src/llm/contracts/entity_extraction_v1_output.json` | 5, 24, 54, 104 | `Phase 1` | High | Qualify-comment (descriptions) |
| `tests/fixtures/droid_extraction_golden_set.json` | 2 | `Phase 1` | High | Qualify-comment |
| `tests/unit/llm/test_entity_extraction_generic.py` | 34, 302–306 | `Phase 3`, `phase3` tag | High | Keep (identifier) — asserts on stable tag/description |

## D. Scaffolding placeholders (`Phase 0`)

These example/placeholder definitions belong to `2026_01_llm_derived_data` Phase 0
scaffolding (now complete). They remain illustrative examples, so they are qualified
rather than deleted.

| File | Line(s) | Reference | Confidence | Action |
| --- | --- | --- | --- | --- |
| `src/llm/interrogations/definitions/entity_extraction.yaml` | 3, 12, 96, 97 | `Phase 0 placeholder` | High | Qualify-comment |
| `src/llm/interrogations/definitions/example.atomic_claims.yaml` | 3, 13, 95, 96 | `Phase 0 placeholder` | High | Qualify-comment |
| `src/llm/interrogations/vocab/entity_types.json` | 5, 55 | `Phase 0 placeholder` | High | Qualify-comment |

## E. Vector runtime split source (`2026_02_vector_runtime_split`)

| File | Line(s) | Reference | Confidence | Action |
| --- | --- | --- | --- | --- |
| `src/vector/__init__.py` | 19 | `Phase 1 of the schema refactor` | High | Qualify-comment |
| `src/llm/retrieval/indexer.py`, `search.py` | (see B) | `Phase 2` cutover | High | Qualify-comment |

## F. Living documentation

The roadmap/status docs are the canonical living references; their phase headings
are qualified with canonical IDs (readable form retained).

| File | References | Series | Confidence | Action |
| --- | --- | --- | --- | --- |
| `docs/llm/vision-and-roadmap.md` | Phases 0–7 | `2026_01_llm_derived_data` | High | Replace/qualify headings |
| `docs/llm/status.md` | Phases 0–3 + schema refactor 0–2 | `2026_01_llm_derived_data`, `2026_02_vector_runtime_split` | High | Replace/qualify headings |
| `PHASE2_IMPLEMENTATION_SUMMARY.md` | Phase 0–6 | `2026_01_llm_derived_data` | High | Add series banner; qualify |
| `docs/llm/derived-data.md` | Phase 0–4+ placeholders | `2026_01_llm_derived_data` | Medium | Qualify (older placeholders) |
| `docs/llm/phase1-runner.md` | `Phase 1` | `2026_01_llm_derived_data` | High | Qualify |
| `docs/fga/*.md` | Phases 0–7 | `2026_02_entity_extraction` | High | Qualify (roadmap) |
| `docs/vector/*.md` | Phase 1/2 + "Phase III Evaluation" | `2026_02_vector_runtime_split` | High/Medium | Qualify; note evaluation is distinct |
| `docs/lake/openalex_lake_architecture.md` | Phases 0–3 | `2026_02_openalex_lake` | High | Qualify |
| `agents/llm-derived-data.md` | `Phase 0` | `2026_01_llm_derived_data` | High | Qualify |
| `docs/DOCS_INDEX.md`, `docs/llm/*` (governance/lineage/etc.) | scattered `Phase N` | mixed | Medium | Qualify as encountered |

## G. Keep — program-level roadmap

| File | References | Disposition |
| --- | --- | --- |
| `docs/vision/Roadmap.md` | Phases 0–7 (product roadmap) | Keep (program). These are program milestones, not a single PR-delivered feature series. A clarifying note distinguishes them from feature-series phases. |

## H. Keep — legitimate domain terminology

| File | Line(s) | Reference | Disposition |
| --- | --- | --- | --- |
| `src/ingest/analysis/inbound_link_analyzer.py` | 75, 78 | `Phase 1/2` (in-function processing stages) | Keep (domain) |
| `src/ingest/analysis/ranked_queue_seeder.py` | 5, 36 | `second-phase retrieval` | Keep (domain) |

## I. Keep — historical archive

| Path | Disposition |
| --- | --- |
| `docs/pr_prompts_and_reports/*.md` | Keep (history). These are verbatim exports of historical PR prompts/reports and are the primary evidence for reconstruction. Rewriting them would destroy the audit trail. Many reference `Phase N`; they are intentionally preserved as-is. |
| `db/legacy_snapshots/llm_vector_subsystem_snapshot.sql` | Keep (history). |
| `src/sem_staging/dry_run.md` | Keep (history) — dry-run capture. |

## Unresolved / low-confidence items

No references were assigned a series on weak evidence. Any future `Phase N`
reference whose series cannot be determined from context, roadmap docs, or the PR
exports should be recorded here as `Unresolved` rather than guessed. At the time of
writing, all in-scope ambiguous references mapped to one of the four reconstructed
series, the program roadmap, domain terminology, or the historical archive.
