# CLI Reference

Command-line entry points for the Holocron Analytics pipeline. Headings here are
stable anchor targets used by other documents.

Most commands are Python modules run with `python -m ...` (the repository adds
`src/` to `PYTHONPATH` via [`pytest.ini`](../../pytest.ini) and runtime
configuration). For data-model objects referenced below, see
[Data model](data-model.md); for long-running workers, see
[Jobs and runners](jobs-and-runners.md).

## Contents

- [classify_entities](#classify_entities)
- [Ingest CLI](#ingest-cli)
- [Semantic classification CLI](#semantic-classification-cli)
- [LLM job utilities](#llm-job-utilities)
- [Lake utilities](#lake-utilities)

---

## classify_entities

**Kind:** CLI &nbsp; **Domain:** LLM / entity &nbsp; **Status:** Active

**Implementation:**
[`src/llm/cli/classify_entities.py`](../../src/llm/cli/classify_entities.py)

**Invocation:** `python -m llm.cli.classify_entities --mode <fresh|resume|rerun> [...]`

Identifies entities in [`dbo.DimEntity`](data-model.md#dbodimentity) that need
classification and enqueues [`llm.job`](data-model.md#llmjob) rows for them.
Supports resumable processing, dry runs, and filtering.

| Option | Purpose |
| --- | --- |
| `--mode fresh` | Classify all active/latest entities. |
| `--mode resume` | Skip already-classified entities (default checkpoint mode). |
| `--mode rerun --entity-keys ...` | Force reprocessing of specific entities. |
| `--only failed` | Retry only entities whose prior job failed. |
| `--fill-missing-only` | Populate missing fields without overwriting existing values. |
| `--dry-run` | Preview the work set without enqueuing. |
| `--batch-size N` | Limit the number of candidates per run. |

**Architecture / behavior:**
[Entity classification resume](../llm/entity-classification-resume.md)

**Tests:**
[`tests/unit/llm/test_classify_entities.py`](../../tests/unit/llm/test_classify_entities.py)

---

## Ingest CLI

**Kind:** CLI &nbsp; **Domain:** Ingest &nbsp; **Status:** Active

**Implementation:**
[`src/ingest/ingest_cli.py`](../../src/ingest/ingest_cli.py)

Config-driven orchestrator for the acquisition pipeline. Reads a YAML config
(see [`config/ingest.example.yaml`](../../config/ingest.example.yaml)),
dequeues [`ingest.work_items`](data-model.md#ingestwork_items), fetches via
connectors, and writes [`ingest.IngestRecords`](data-model.md#ingestingestrecords).

Related: [`analysis_cli.py`](../../src/ingest/analysis_cli.py),
[`snapshot_cli.py`](../../src/ingest/snapshot_cli.py).

**Runbook:** [Wookieepedia ingestion](../runbooks/wookieepedia_ingestion.md)

---

## Semantic classification CLI

**Kind:** CLI &nbsp; **Domain:** Entity classification &nbsp; **Status:** Active

**Implementation:** [`src/semantic/cli.py`](../../src/semantic/cli.py)

Rules-based page/entity classification. Subcommands: `classify` (single page),
`batch_classify` (multiple pages). Writes
[`sem.PageClassification`](data-model.md#sempageclassification).

---

## LLM job utilities

**Kind:** CLI &nbsp; **Domain:** LLM &nbsp; **Status:** Active

| Script | Purpose |
| --- | --- |
| [`scripts/llm_enqueue_job.py`](../../scripts/llm_enqueue_job.py) | Enqueue an [`llm.job`](data-model.md#llmjob) without writing SQL. |
| [`scripts/llm_inspect_jobs.py`](../../scripts/llm_inspect_jobs.py) | Inspect jobs, runs, and queue statistics. |
| [`scripts/llm_smoke_test.py`](../../scripts/llm_smoke_test.py) | Validate Ollama connectivity and basic inference. |

**Runbook / ops:** [LLM operational guide](../llm/operational.md)

---

## Lake utilities

**Kind:** CLI &nbsp; **Domain:** Lake storage &nbsp; **Status:** Active

| Script | Purpose |
| --- | --- |
| [`scripts/lake/decompress_gz_tree.py`](../../scripts/lake/decompress_gz_tree.py) | Decompress a `.gz` tree, preserving structure. |
| [`scripts/lake/decompress_gz_tree.ps1`](../../scripts/lake/decompress_gz_tree.ps1) | PowerShell equivalent for Windows. |

**Architecture:** [Lake and artifacts](lake-and-artifacts.md) &nbsp;
**Details:** [OpenAlex decompression](../lake/openalex_decompression.md)
