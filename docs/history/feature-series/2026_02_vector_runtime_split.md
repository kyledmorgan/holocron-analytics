# Vector Runtime Split Feature Series

**Series ID:** `2026_02_vector_runtime_split`
**Status:** `complete`
**Began:** February 2026
**Highest planned phase:** 2
**Highest confirmed completed phase:** 2

## Purpose

A schema refactor that splits the original `llm` schema into two independent
runtimes: the chat/derive runtime (`llm.*`) and a dedicated vector/embedding runtime
(`vector.*`). The plan and impact analysis are documented in
[`docs/llm/schema-refactor-migration-notes.md`](../../llm/schema-refactor-migration-notes.md)
and [`docs/llm/dependency-inventory-vector-subsystem.md`](../../llm/dependency-inventory-vector-subsystem.md).

The vector tables were originally created under
[`2026_01_llm_derived_data`](2026_01_llm_derived_data.md) Phase 3; this series moved
them into their own schema.

## Historical phases

| Phase | Status | Intended scope | Implemented evidence | Related PR / branch |
| --- | --- | --- | --- | --- |
| `2026_02_vector_runtime_split_phase_0` | `complete` | Baseline inventory, legacy snapshot, migration notes. | `db/legacy_snapshots/llm_vector_subsystem_snapshot.sql`, `docs/llm/dependency-inventory-vector-subsystem.md` | PR #43 (`copilot/split-chat-and-vector-runtime`) |
| `2026_02_vector_runtime_split_phase_1` | `complete` | Create `vector` schema and tables in parallel with legacy `llm.*`. | `db/migrations/0023_create_vector_schema.sql`, `src/vector/` | PR #44 (`copilot/create-vector-runtime-parallel`) |
| `2026_02_vector_runtime_split_phase_2` | `complete` | Cutover: deprecate/rename legacy `llm.*` vector tables to `*_legacy`; `vector` schema becomes sole home. | `db/migrations/0024_deprecate_llm_vector_tables.sql`, `docs/vector/README.md` | PR #45 (`copilot/cutover-and-cleanup-phase-2`) |

## Current implemented state

The refactor is feature-complete. The `vector` schema is the sole home for embedding
and retrieval operations. The legacy `llm.chunk/embedding/retrieval/retrieval_hit/source_registry`
tables were renamed to `*_legacy` and retained for historical reference. The chat
runtime tables (`llm.job`, `llm.run`, `llm.artifact`, `llm.evidence_bundle`,
`llm.evidence_item`, `llm.run_evidence`) are unchanged.

## Related but distinct: vector subsystem evaluation

A separate, documentation-only effort labelled **"Phase III Vector Evaluation"**
(PR #50, `copilot/evaluate-vector-capabilities`) produced the current-state
inventory, gap analysis, and proposed work plan under `docs/vector/`. This is an
evaluation/planning effort, not a delivered phase of the runtime split (which
completed at Phase 2). Its "Phase III" label is an independent numbering and is one
of the references that motivated this cleanup. If that evaluation matures into a
delivered, multi-PR build-out, it should be tracked as its own series with its own
`YYYY_MM_*` identifier.

## Outstanding work

None for the runtime split itself. Future vector capability work should follow the
evaluation in `docs/vector/` under a new series identifier.

## Source evidence

- `db/migrations/0023_create_vector_schema.sql`, `0024_deprecate_llm_vector_tables.sql`
- `docs/llm/schema-refactor-migration-notes.md`, `docs/llm/status.md` (Schema Refactor section)
- `docs/vector/README.md`, `docs/vector/docs-hygiene-llm-vs-vector.md`
- `db/legacy_snapshots/llm_vector_subsystem_snapshot.sql`
- `docs/pr_prompts_and_reports/043.md`, `044.md`, `045.md`, `050.md`
