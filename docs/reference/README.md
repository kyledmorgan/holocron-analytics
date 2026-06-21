# Reference Index

The **concept catalog** for Holocron Analytics: a domain-grouped map from
important concepts, objects, and entry points to their canonical definitions and
implementations.

This is a navigation layer. It complements — and does not replace — the
[Documentation Index](../DOCS_INDEX.md) (full doc inventory) or the
[ERD Explained](../diagrams/mermaid/ERD_Explained.md) (exhaustive column
dictionaries).

## How to use this index

- Each entry links to a **canonical definition**. Conceptual definitions,
  source implementations, and runbooks are separate links — none pretends to
  represent all of the others.
- Headings on the linked reference pages are **stable anchor targets**. Do not
  rename them casually.
- Links are **selective**: the first meaningful occurrence in a section, points
  where subsystems interact, and dedicated reference cards. See
  [Documentation and links](../contributing/documentation-and-links.md).

## Reference documents

| Document | Contents |
| --- | --- |
| [Terminology](terminology.md) | Cross-domain term → canonical location. |
| [Data model](data-model.md) | Canonical SQL tables (dimensions, ingest, LLM). |
| [CLI reference](cli-reference.md) | Command-line entry points. |
| [Jobs and runners](jobs-and-runners.md) | Long-running workers and orchestration. |
| [Lake and artifacts](lake-and-artifacts.md) | Lake datasets, OpenAlex, artifacts. |
| [Feature series](feature-series.md) | Multi-PR effort identifiers and history. |
| [Repository concept inventory](repository-concept-inventory.md) | Full discovery inventory table. |
| [Cross-reference implementation summary](cross-reference-implementation-summary.md) | What this navigation system delivered. |

---

## Core dimensional model

- [`dbo.DimEntity`](data-model.md#dbodimentity) — canonical entity dimension
  (SCD Type 2).
- [Schemas](data-model.md#schemas) — `dbo`, `ingest`, `llm`, `sem`, `vector`.
- [ERD Explained](../diagrams/mermaid/ERD_Explained.md) — full column
  dictionaries for dimensions, facts, and bridges.

## Ingest and orchestration

- [`ingest.work_items`](data-model.md#ingestwork_items) — durable resumable work
  unit.
- [`ingest.IngestRecords`](data-model.md#ingestingestrecords) — raw fetch
  payloads.
- [Ingest runner](jobs-and-runners.md#ingest-runner) /
  [concurrent runner](jobs-and-runners.md#concurrent-ingest-runner) — workers.
- [Ingest CLI](cli-reference.md#ingest-cli) — config-driven entry point.
- [Wookieepedia ingestion runbook](../runbooks/wookieepedia_ingestion.md).

## Entity classification and resolution

- [`dbo.DimEntity`](data-model.md#dbodimentity) — canonical entity dimension.
- [`sem.PageClassification`](data-model.md#sempageclassification) — page-level
  type inference and lineage.
- [`classify_entities` CLI](cli-reference.md#classify_entities) — resumable
  classification runner.
- [Entity classification resume](../llm/entity-classification-resume.md) —
  completion and resume rules.
- [Semantic classification CLI](cli-reference.md#semantic-classification-cli) —
  rules-based classifier.

## Evidence and provenance

- [`llm.evidence_bundle`](data-model.md#llmevidence_bundle) — bounded evidence
  for one inference.
- [Evidence bundles](../llm/evidence.md) — assembly process and evidence types.
- [Artifact version and provenance](lake-and-artifacts.md#artifact-version-and-provenance)
  — artifact identity and lineage.
- [Pipeline observability](../llm/llm-pipeline-observability-current-state.md).

## OpenAlex

- [OpenAlex work](lake-and-artifacts.md#openalex-work) — source record
  (planned thin SQL).
- [OpenAlex integration](../openalex-integration.md) — user guide.
- [OpenAlex implementation summary](../integrations/openalex-implementation-summary.md).

## Lake storage

- [Lake raw layer](lake-and-artifacts.md#lake-raw-layer) — filesystem payload
  store.
- [Decompressed OpenAlex snapshot](lake-and-artifacts.md#decompressed-openalex-snapshot).
- [OpenAlex lake-first architecture](../lake/openalex_lake_architecture.md)
  (planned).

## Artifact processing

- [`llm.artifact`](data-model.md#llmartifact) — stored run artifacts.
- [PDF artifact](lake-and-artifacts.md#pdf-artifact) (planned).
- [SQL-first artifact storage](../llm/sql-first-artifact-storage.md).

## LLM and analysis runners

- [`llm.job`](data-model.md#llmjob) / [`llm.run`](data-model.md#llmrun) — queue
  and execution.
- [Phase 1 LLM runner](jobs-and-runners.md#phase-1-llm-runner) — derive flow.
- [Job dispatcher](jobs-and-runners.md#job-dispatcher) — handler routing.
- [LLM operational guide](../llm/operational.md) ·
  [Phase 1 runner guide](../llm/phase1-runner.md).

## Operational tooling

- [LLM job utilities](cli-reference.md#llm-job-utilities) — enqueue/inspect/smoke.
- [Lake utilities](cli-reference.md#lake-utilities) — decompression tools.
- [`tools/db_init.py`](../../tools/db_init.py) — migration runner.
- [Docker local dev runbook](../runbooks/docker_local_dev.md).

## Feature-series history

- [Feature series](feature-series.md) — identifiers and history records.
- [Feature-series convention](../contributing/feature-series-convention.md).

---

## Canonical definition format

Important objects use a consistent card so readers can scan them quickly. Keep
small concepts concise — not every field is required.

```markdown
## schema.ObjectName

**Kind:** SQL table  **Domain:** ...  **Status:** Active

**Purpose:** One or two sentences.

**Primary implementation:** [`path/to/file`](../../path/to/file)

**Written by:** / **Read by:** selective links to CLIs, runners, views.

**Important invariants:** document only rules the implementation enforces.

**Related concepts:** a few links to adjacent canonical definitions.
```

**Status values:** `active`, `planned`, `deprecated`, `superseded`,
`experimental`, `unknown`. Label planned designs explicitly so they are not
mistaken for current implementation.

See [Documentation and links](../contributing/documentation-and-links.md) for the
full standard, and the
[repository concept inventory](repository-concept-inventory.md) for the complete
discovery table.
