# Repository Concept Inventory

Discovery inventory of important concepts, objects, and entry points found in the
owned repository. Built during the cross-reference navigation effort and
maintained going forward (see
[Documentation and links](../contributing/documentation-and-links.md)).

**Kinds:** concept, SQL schema, SQL table, SQL view, SQL procedure, Python
module, Python class, CLI, job, lake dataset, artifact, process, configuration,
runbook, architecture document, feature series.

**Status values:** active, planned, deprecated, superseded, experimental,
unknown. Relationships listed are supported by repository evidence; no inferred
relationships are recorded as confirmed.

## Core dimensional model

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `dbo.DimEntity` | SQL table | [def](data-model.md#dbodimentity) | [`009_DimEntity.sql`](../../src/db/ddl/01_dimensions/009_DimEntity.sql) | active | SCD Type 2 entity registry. |
| `dbo.FactEvent` | SQL table | [ERD](../diagrams/mermaid/ERD_Explained.md) | [`001_FactEvent.sql`](../../src/db/ddl/02_facts/001_FactEvent.sql) | active | Core event fact. |
| `dbo.FactClaim` | SQL table | [ERD](../diagrams/mermaid/ERD_Explained.md) | [`003_FactClaim.sql`](../../src/db/ddl/02_facts/003_FactClaim.sql) | active | Claim fact (continuity). |
| Bridges (`Bridge*`) | SQL table | [ERD](../diagrams/mermaid/ERD_Explained.md) | [`src/db/ddl/03_bridges/`](../../src/db/ddl/03_bridges) | active | Event/asset/claim links. |

## Ingest and orchestration

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `ingest.work_items` | SQL table | [def](data-model.md#ingestwork_items) | [`0002_create_tables.sql`](../../db/migrations/0002_create_tables.sql) | active | Resumable work queue. |
| `ingest.IngestRecords` | SQL table | [def](data-model.md#ingestingestrecords) | [`002_IngestRecords.sql`](../../src/db/ddl/00_ingest/002_IngestRecords.sql) | active | Raw fetch payloads. |
| `WorkItem` / `IngestRecord` | Python class | [terminology](terminology.md) | [`models.py`](../../src/ingest/core/models.py) | active | In-code models. |
| Ingest runner | job | [def](jobs-and-runners.md#ingest-runner) | [`ingest_runner.py`](../../src/ingest/runner/ingest_runner.py) | active | Single-worker. |
| Concurrent ingest runner | job | [def](jobs-and-runners.md#concurrent-ingest-runner) | [`concurrent_runner.py`](../../src/ingest/runner/concurrent_runner.py) | active | Lease-based claims. |
| Ingest CLI | CLI | [def](cli-reference.md#ingest-cli) | [`ingest_cli.py`](../../src/ingest/ingest_cli.py) | active | Config-driven. |

## Entity classification and resolution

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Entity classification | process | [resume doc](../llm/entity-classification-resume.md) | [`classify_entities.py`](../../src/llm/cli/classify_entities.py) | active | Resumable. |
| `classify_entities` | CLI | [def](cli-reference.md#classify_entities) | [`classify_entities.py`](../../src/llm/cli/classify_entities.py) | active | fresh/resume/rerun. |
| `sem.PageClassification` | SQL table | [def](data-model.md#sempageclassification) | [`0017_sem_page_classification.sql`](../../db/migrations/0017_sem_page_classification.sql) | active | Page type inference. |
| Semantic CLI | CLI | [def](cli-reference.md#semantic-classification-cli) | [`semantic/cli.py`](../../src/semantic/cli.py) | active | Rules-based. |
| Entity resolution | process | [terminology](terminology.md) | [`entity_matcher.py`](../../src/ingest/discovery/entity_matcher.py) | active | Candidate dedup. |
| `usp_get_unclassified_entities` | SQL procedure | [data-model](data-model.md#dbodimentity) | [proc](../../src/db/dml/stored_procedures/dbo.usp_get_unclassified_entities.sql) | active | Resume candidates. |

## Evidence, provenance, and LLM runners

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `llm.job` | SQL table | [def](data-model.md#llmjob) | [`0005_create_llm_tables.sql`](../../db/migrations/0005_create_llm_tables.sql) | active | Work queue. |
| `llm.run` | SQL table | [def](data-model.md#llmrun) | [`0033_llm_provenance_lineage.sql`](../../db/migrations/0033_llm_provenance_lineage.sql) | active | Execution + provenance. |
| `llm.artifact` | SQL table | [def](data-model.md#llmartifact) | [`0035_artifact_content_sql_first.sql`](../../db/migrations/0035_artifact_content_sql_first.sql) | active | SQL-first storage. |
| `llm.evidence_bundle` | SQL table | [def](data-model.md#llmevidence_bundle) | [`0007_evidence_bundle_tables.sql`](../../db/migrations/0007_evidence_bundle_tables.sql) | active | Bounded evidence. |
| `usp_claim_next_job` | SQL procedure | [jobs](jobs-and-runners.md#phase-1-llm-runner) | [proc](../../src/db/dml/stored_procedures/llm.usp_claim_next_job.sql) | active | READPAST claim. |
| Phase 1 runner | job | [def](jobs-and-runners.md#phase-1-llm-runner) | [`phase1_runner.py`](../../src/llm/runners/phase1_runner.py) | active | Derive flow. |
| Job dispatcher | Python class | [def](jobs-and-runners.md#job-dispatcher) | [`dispatcher.py`](../../src/llm/runners/dispatcher.py) | active | Handler routing. |
| Artifact version / provenance | concept | [def](lake-and-artifacts.md#artifact-version-and-provenance) | [`0033_llm_provenance_lineage.sql`](../../db/migrations/0033_llm_provenance_lineage.sql) | active | `content_sha256` + chain. |

## OpenAlex, lake, and artifacts

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Lake raw layer | lake dataset | [def](lake-and-artifacts.md#lake-raw-layer) | [`file_lake.py`](../../src/ingest/storage/file_lake.py) | active | Writers active. |
| Decompressed OpenAlex snapshot | lake dataset | [def](lake-and-artifacts.md#decompressed-openalex-snapshot) | [`decompress_gz_tree.py`](../../scripts/lake/decompress_gz_tree.py) | active | Tooling. |
| OpenAlex work | concept | [def](lake-and-artifacts.md#openalex-work) | [`openalex_connector.py`](../../src/ingest/connectors/openalex/openalex_connector.py) | planned | No SQL schema yet. |
| PDF artifact | artifact | [def](lake-and-artifacts.md#pdf-artifact) | [lake arch](../lake/openalex_lake_architecture.md) | planned | Target state. |

## Operational tooling and configuration

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `db_init` | CLI | [reference index](README.md#operational-tooling) | [`db_init.py`](../../tools/db_init.py) | active | Migration runner. |
| LLM job utilities | CLI | [def](cli-reference.md#llm-job-utilities) | [`scripts/`](../../scripts) | active | enqueue/inspect/smoke. |
| Lake utilities | CLI | [def](cli-reference.md#lake-utilities) | [`scripts/lake/`](../../scripts/lake) | active | Decompression. |
| Ingest config | configuration | [CLI](cli-reference.md#ingest-cli) | [`config/ingest.example.yaml`](../../config/ingest.example.yaml) | active | YAML-driven. |
| Markdown link checker | Python module | [validation](../contributing/documentation-and-links.md#validation) | [`check_markdown_links.py`](../../scripts/quality/check_markdown_links.py) | active | This effort. |

## Feature series

| Name | Kind | Canonical definition | Implementation | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `2026_01_llm_derived_data` | feature series | [feature-series](feature-series.md) | [history](../history/feature-series/2026_01_llm_derived_data.md) | active | LLM derived data. |
| `2026_02_entity_extraction` | feature series | [feature-series](feature-series.md) | [history](../history/feature-series/2026_02_entity_extraction.md) | active | Entity extraction. |
| `2026_02_openalex_lake` | feature series | [feature-series](feature-series.md) | [history](../history/feature-series/2026_02_openalex_lake.md) | planned | OpenAlex lake. |
| `2026_02_vector_runtime_split` | feature series | [feature-series](feature-series.md) | [history](../history/feature-series/2026_02_vector_runtime_split.md) | active | Vector split. |

---

## Vector subsystem (superseded)

The `vector.*` schema and [`src/vector/`](../../src/vector) runtime are
**superseded** by the `llm` schema. See
[Vector runtime overview](../vector/README.md) and
[docs hygiene: LLM vs. vector](../vector/docs-hygiene-llm-vs-vector.md).

## Excluded paths

Not scanned or cataloged (generated/external/payload data): `.git/`, virtual
environments, caches, vendored deps, build output (`bin/`, `obj/`), immutable
OpenAlex source data, lake payloads (`local/data_lake/`, `/lake/`), decompressed
JSONL, downloaded PDFs, and binaries. See
[excluded paths](../contributing/documentation-and-links.md#excluded-paths).
