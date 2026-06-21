# Cross-Reference Implementation Summary

Completion report for the repository-wide concept catalog, cross-reference
navigation, and documentation-linking standard. This is the canonical record of
what the navigation system delivered and where the gaps remain.

## Documentation structure created

A new link-first reference layer under [`docs/reference/`](README.md):

| File | Role |
| --- | --- |
| [`README.md`](README.md) | Central concept catalog grouped by domain. |
| [`terminology.md`](terminology.md) | Cross-domain term → canonical location. |
| [`data-model.md`](data-model.md) | Canonical SQL object definitions. |
| [`cli-reference.md`](cli-reference.md) | Command-line entry points. |
| [`jobs-and-runners.md`](jobs-and-runners.md) | Long-running workers/orchestration. |
| [`lake-and-artifacts.md`](lake-and-artifacts.md) | Lake datasets, OpenAlex, artifacts. |
| [`feature-series.md`](feature-series.md) | Multi-PR effort identifiers and history. |
| [`repository-concept-inventory.md`](repository-concept-inventory.md) | Full discovery inventory table. |
| [`cross-reference-implementation-summary.md`](cross-reference-implementation-summary.md) | This report. |

Governance and tooling:

- [`docs/contributing/documentation-and-links.md`](../contributing/documentation-and-links.md)
  — the documentation-linking standard.
- [`scripts/quality/check_markdown_links.py`](../../scripts/quality/check_markdown_links.py)
  — Markdown link/anchor validator, with tests at
  [`tests/unit/test_check_markdown_links.py`](../../tests/unit/test_check_markdown_links.py).
- [`AGENTS.md`](../../AGENTS.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), and
  [`docs/DOCS_INDEX.md`](../DOCS_INDEX.md) updated to point at the new layer.
- [`.vscode/settings.json`](../../.vscode/settings.json) — Markdown validation and
  link-completion settings (merged, not overwritten).

## Most important canonical concepts identified

- [`dbo.DimEntity`](data-model.md#dbodimentity) — canonical entity dimension.
- [`ingest.work_items`](data-model.md#ingestwork_items) and
  [`ingest.IngestRecords`](data-model.md#ingestingestrecords).
- [`llm.job`](data-model.md#llmjob), [`llm.run`](data-model.md#llmrun),
  [`llm.artifact`](data-model.md#llmartifact),
  [`llm.evidence_bundle`](data-model.md#llmevidence_bundle).
- [`sem.PageClassification`](data-model.md#sempageclassification).
- Processes: [entity classification](../llm/entity-classification-resume.md),
  [artifact version and provenance](lake-and-artifacts.md#artifact-version-and-provenance).
- Entry points: [`classify_entities`](cli-reference.md#classify_entities),
  [Phase 1 runner](jobs-and-runners.md#phase-1-llm-runner),
  [ingest runner](jobs-and-runners.md#ingest-runner).

## Major implementation links added

Canonical definitions link to primary implementation files (DDL, migrations,
stored procedures, CLI modules, runners), and code/SQL entry points link back to
documentation:

| Entry point | Reference added |
| --- | --- |
| [`src/llm/cli/classify_entities.py`](../../src/llm/cli/classify_entities.py) | CLI reference, behavior, data model. |
| [`src/llm/runners/phase1_runner.py`](../../src/llm/runners/phase1_runner.py) | Runner reference, usage, operations. |
| [`src/ingest/runner/ingest_runner.py`](../../src/ingest/runner/ingest_runner.py) | Runner reference, runbook, data model. |
| [`src/ingest/core/models.py`](../../src/ingest/core/models.py) | Data-model anchors for `WorkItem`/`IngestRecord`. |
| [`src/db/ddl/01_dimensions/009_DimEntity.sql`](../../src/db/ddl/01_dimensions/009_DimEntity.sql) | Data-model + catalog. |
| [`src/db/dml/stored_procedures/llm.usp_claim_next_job.sql`](../../src/db/dml/stored_procedures/llm.usp_claim_next_job.sql) | Runner + data model. |

Selective "Related reference" blocks were added to high-value existing docs:
[entity classification resume](../llm/entity-classification-resume.md),
[Wookieepedia runbook](../runbooks/wookieepedia_ingestion.md),
[evidence bundles](../llm/evidence.md), and the
[OpenAlex lake architecture](../lake/openalex_lake_architecture.md).

## Counts

- **Markdown files scanned:** 181 (excluding the paths below).
- **New reference/standard documents:** 10 (8 under `docs/reference/`, 1
  contributing standard, 1 this report).
- **Markdown links in new reference docs:** ~340 repository-relative links/anchors.
- **Code/SQL entry points annotated with doc references:** 6.
- **Existing docs given selective reference blocks:** 6.
- **Pre-existing broken links fixed:** 3 (see below).
- **Validation tests added:** 20 (link checker).

## Broken links fixed

Detected by the new checker and corrected:

1. [`docs/llm/derived-data.md`](../llm/derived-data.md) — wrong relative depth to
   `src/ingest/README.md` (`../../../` → `../../`).
2. [`docs/llm/governance.md`](../llm/governance.md) — stale heading anchor for the
   governance section of the LLM roadmap.
3. [`docs/vector/README.md`](../vector/README.md) — link to a dependency inventory
   that had moved from `docs/vector/` to `docs/llm/`.

## Excluded paths

Not scanned or modified: `.git/`, virtual environments, caches, vendored
dependencies, build output (`bin/`, `obj/`), immutable OpenAlex source data, lake
payloads (`local/data_lake/`, `/lake/`), decompressed JSONL, downloaded PDFs, and
binary artifacts. Enforced by the checker (`EXCLUDED_DIRS`/`EXCLUDED_PATH_PARTS`)
and documented in
[excluded paths](../contributing/documentation-and-links.md#excluded-paths).

## Validation performed

- `python scripts/quality/check_markdown_links.py` — passes across all 181 owned
  Markdown files (no broken local file links or heading anchors).
- `python -m pytest tests/unit/test_check_markdown_links.py` — 20 tests pass.

## Unresolved concepts and recommended future improvements

- **OpenAlex work / PDF artifact** are **planned**, not implemented (no `openalex`
  SQL schema yet). They are cataloged with explicit `planned` status; promote to
  active canonical definitions when the schema lands.
- **Vector subsystem** (`vector.*`, `src/vector/`) is **superseded** by the `llm`
  schema; retained for back-compat. Consider a deprecation timeline.
- **CI integration:** the link checker is not yet wired into CI (the repository
  has no `.github/workflows/`). Recommended next step: add a workflow that runs
  the checker and the unit tests on documentation changes.
- **Coverage/backlink report** (optional Part 17) was not generated to avoid
  noise; it can be added later if automation stays simple.
- **Architecture index:** there is no `docs/architecture/` tree; current
  architecture content lives in `docs/llm/`, `docs/lake/`, and `docs/fga/`. The
  reference layer links to these in place rather than relocating them.

## Areas intentionally excluded to avoid noise

- No hyperlinking of every code-formatted term or every repeated occurrence.
- No catalog entries for private helper functions (native Go to Definition /
  Find References is sufficient).
- No documentation comments added to trivial SQL statements or helper modules.
- No hardcoded GitHub URLs for current-state links.
