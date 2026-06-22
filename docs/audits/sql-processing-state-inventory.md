# SQL Processing State Inventory

Generated: 2026-06-21

## Executive summary

This was a read-only source, configuration, Ollama, and local artifact-lake investigation. Current live SQL Server counts could not be collected from this Codex session: spawning docker, python, git, and sqlcmd was blocked with EPERM, and the Node runtime has no SQL Server client package. The configured target database is clear, but current live row counts, drift, failures, and duplicate groups must be verified by running the companion read-only SQL file.

Configured SQL target: service sql2025, container sql2025, host port 1433, database Holocron. Ollama is reachable at http://localhost:11434 and has llama3.2:latest installed.

Historical SQL evidence from docs/llm/classify-entities-resume-zero-candidates-debug-2026-02-28.md reported 15,637 active/latest dbo.DimEntity rows, 0 missing EntityType, 15,637 missing AliasCsv, 99,970 ingest.IngestRecords rows, 799,040 completed ingest.work_items, and 10 ingest.work_items in progress. These are historical counts, not current counts.

The source-level finding is that the previous classify_entities resume command returned zero because it only looks for active/latest dbo.DimEntity rows missing EntityType. It does not inspect ingest.IngestRecords, sem.SourcePage, or queued source work. Lower-level entity/relationship backfill exists, but the current runner/handler wiring is not safe for broad live processing.

## Environment discovered

| Item | Finding |
| --- | --- |
| Compose file | docker-compose.yml |
| SQL Server service/container | sql2025 / sql2025 |
| SQL Server image | mcr.microsoft.com/mssql/server:2025-latest |
| SQL host port | 1433 |
| Database | Holocron |
| Init service | initdb runs docker/init-db.sql, src/db/ddl, and db/migrations |
| Seed service | seed runs python src/ingest/seed_loader.py --all --verbose --no-file-log |
| Ollama service | holocron-ollama, bound to 127.0.0.1:11434 |
| LLM runner service | llm-runner, profile llm, runs src.llm.runners.phase1_runner loop |
| Native SQL env | .env points INGEST and SEED connection strings at localhost/Holocron |

Ollama model list from a non-inference API call:

| Model | Digest prefix | Modified |
| --- | --- | --- |
| llama3.2:latest | a80c4f17 | 2026-02-21 |
| deepseek-r1:8b | 6995872b | 2026-02-10 |
| gemma3:12b | f4031aab | 2026-02-01 |
| gpt-oss:120b-cloud | 56966220 | 2026-02-01 |
| gpt-oss:20b-cloud | 875e8e3a | 2026-02-01 |

## Repository pipeline inventory

| Pipeline | CLI/module | Input | Output | Resume behavior | Idempotency | Maturity |
| --- | --- | --- | --- | --- | --- | --- |
| Entity Classification CLI | python -m llm.cli.classify_entities | dbo.DimEntity | llm.job | mode resume selects missing DimEntity fields; default is EntityType IS NULL | enqueue_job_idempotent with dedupe key entity_classify:{EntityKey} | Enqueue layer is usable with constraints; downstream job type is not yet safe |
| LLM Backfill CLI | python -m src.llm.cli.backfill | sem.SourcePage and sem.PageClassification | llm.job | No true resume; filter-based bulk enqueue | Insufficient; code calls enqueue_job without a dedupe key | Unsafe for broad runs |
| Phase1Runner | python -m src.llm.runners.phase1_runner | llm.job | llm.run, llm.artifact, lake files | Queue claim/retry | Queue-based; artifacts per run | Performs inference and artifacts, not domain routing |
| JobDispatcher | python -m src.llm.runners.dispatcher | llm.job | llm.run, llm.artifact, optional handler writes | Queue claim/retry, has dry-run | Handler-dependent | Unsafe for broad live use; generic path does not call Ollama |
| Ingest runner | src.ingest.ingest_cli / concurrent_runner | ingest.work_items | ingest.IngestRecords, lake payloads | Queue status/leases | work item dedupe_key | Likely active, but live stuck work must be checked |

### Pipeline status matrix

| Pipeline | Input | Output | Eligible | Completed | Remaining | Failed | Duplicate risk | Resume category |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Ingest runner | ingest.work_items | ingest.IngestRecords | unverified | historical 799,040 completed | historical 10 in progress | unverified | Low/medium; lease state needs check | C |
| classify_entities default | dbo.DimEntity | llm.job | historical 0 | historical 15,637 had EntityType | historical 0 by default | unverified | Low for enqueue, medium downstream | B/C |
| classify_entities strict tags | dbo.DimEntity | llm.job | historical 15,637 | unverified | historical 15,637 missing AliasCsv | unverified | Medium/high because downstream handler path is questionable | C/D |
| backfill entities | sem.SourcePage | llm.job | unverified | unverified | unverified | unverified | High; no dedupe key and handler dependency gap | D |
| backfill relationships | sem.SourcePage | llm.job | unverified | unverified | unverified | unverified | High; candidate query does not anti-join successful relationship runs | D |
| dispatcher live generic | llm.job | llm.run/artifact | queue unverified | unverified | unverified | unverified | High; can mark success without LLM | D |
| relationship handler | llm.job input content | artifacts, optional BridgeEntityRelation | local lake 10 dirs | local lake has 2 full outputs plus partials | unverified | unverified | High; no relationship store injected by default | D |

## Repository-to-database object map

Repository-defined processing objects include:

| Schema | Important objects found in source |
| --- | --- |
| ingest | work_items, IngestRecords, ingest_runs, seen_resources, worker_heartbeats, run_metrics, queue views |
| sem | SourcePage, PageSignals, PageClassification, current/candidate/review views |
| llm | job, run, artifact, evidence_bundle, run_evidence, evidence_item, queue health views, legacy retrieval objects |
| dbo | DimEntity, DimTag, BridgeTagAssignment, BridgeEntityRelation, BridgeEntityEvent, BridgeEntityWork, core facts/dimensions |
| vector | embedding/retrieval runtime tables from the vector split |

Processing flow:

ingest.work_items -> ingest.IngestRecords -> sem.SourcePage -> sem.PageClassification -> dbo.DimEntity -> classify_entities -> llm.job -> phase1_runner/dispatcher -> llm.run + llm.artifact + lake/llm_runs. Relationship and entity domain writes are intended to go to dbo.BridgeEntityRelation and dbo.DimEntity, but the default handlers do not currently wire those stores.

## Drift and compatibility findings

Live drift could not be measured. Source-level compatibility risks are confirmed:

| Risk | Evidence | Operational impact |
| --- | --- | --- |
| Missing page classification handler | Job registry references src.llm.handlers.page_classification.handle, but no such file exists | page_classification jobs are unsafe |
| Dispatcher generic live path does not call Ollama | dispatcher.py returns prompt_rendered success in live generic path | jobs can be marked successful without derived output |
| Entity extraction generic/droid handlers lack dependencies by default | module-level handle creates handlers with no Ollama client and no entity_store | live jobs fail or cannot persist entities |
| Relationship handler lacks relationship_store by default | module-level handle passes Ollama client, lake writer, queue only | relationship jobs can produce artifacts but no BridgeEntityRelation rows |
| Backfill relationship candidate SQL does not anti-join prior successful relationship runs | code comment says it does; query does not | reruns can enqueue duplicate logical work |
| Backfill catches query failures and returns empty candidates | source returns [] on exceptions | false no-work result possible |
| BridgeEntityRelation has no hard natural unique constraint in source DDL | migration 0027 creates indexes, not uniqueness | duplicate relationship rows are possible if inserted outside anti-join path |

## Current database state

Current live counts are blocked. Historical 2026-02-28 counts:

| Object | Row count | Completion indicator | Incomplete count | Notes |
| --- | ---: | --- | ---: | --- |
| dbo.DimEntity active/latest | 15,637 | EntityType populated | 0 missing EntityType | Historical only |
| dbo.DimEntity aliases | 15,637 active/latest | AliasCsv populated | 15,637 missing AliasCsv | Historical only |
| ingest.IngestRecords | 99,970 | work_item_id populated | 0 without work_item_id | Historical only |
| ingest.work_items | 799,040 completed | terminal status | 10 in_progress | Historical only |
| llm.job | unverified | terminal status | unverified | Run SQL diagnostics |
| llm.run | unverified | terminal status | unverified | Run SQL diagnostics |
| llm.artifact | unverified SQL, 40 local lake files | artifact_type/content hash | several partial local dirs | SQL likely has more/less |
| dbo.BridgeEntityRelation | unverified | natural tuple | unverified | Needs duplicate baseline |

## Entity classification coverage

Confirmed source behavior:

- Default resume source: dbo.DimEntity.
- Default resume predicate: IsLatest = 1 AND IsActive = 1 AND EntityType IS NULL.
- Strict flags add missing DisplayNameNormalized, SortName, or AliasCsv predicates.
- Failed-only mode joins llm.job on dedupe key entity_classify:{EntityKey} and status FAILED or DEADLETTER.
- The CLI enqueues llm.job rows. It does not run Ollama inference or update DimEntity itself.

Historical coverage:

| Metric | Historical value |
| --- | ---: |
| Active/latest DimEntity | 15,637 |
| Missing EntityType | 0 |
| Missing DisplayNameNormalized | 0 |
| Missing SortName | 0 |
| Missing AliasCsv | 15,637 |
| Default resume candidates | 0 |

## Lower-level derivation coverage

| Interrogation/job | Contract | Intended output | Current source-level behavior |
| --- | --- | --- | --- |
| sw_entity_facts_v1 | sw_entity_facts_v1_output.json | structured facts/artifacts | Phase1 can artifact results; no confirmed domain writer |
| entity_extraction_droid_v1 | entity_extraction_v1_output.json | dbo.DimEntity | handler default lacks Ollama client/store |
| entity_extraction_generic_v1 | entity_extraction_generic_v1_schema.json | dbo.DimEntity and related observations | handler default lacks Ollama client/store |
| relationship_extraction_v1 | relationship_extraction_v1_output.json | dbo.BridgeEntityRelation | handler can call Ollama and write artifacts, but no relationship store is injected |
| page_classification_v1 | page_classification_v1_schema.json | sem.PageClassification | registered handler module is missing; dispatcher fallback is not substantive inference |

## Breadth versus depth

Breadth processing includes ingest acquisition, page classification, entity promotion/classification, first-order entity extraction, first-order relationship extraction, and evidence/artifact capture. Depth processing includes retrieval/vector enrichment, recursive relationship enrichment, adjudication/governance, temporal refinement, event/work extraction, and multi-model benchmarking.

Do not start depth processing yet. Breadth coverage and runner safety need live diagnostics and code/schema remediation first.

## Duplicate and redundancy findings

Local artifact lake inventory found 40 files in 10 run directories under lake/llm_runs. The runs are dominated by relationship_extraction_v1 experiments from 2026-02-14 through 2026-02-25.

| Object | Duplicate definition | Duplicate groups | Excess rows | Severity | Probable cause |
| --- | --- | ---: | ---: | --- | --- |
| Local lake relationship output | identical output hash across run dirs | 1 | 1 | Medium | repeated manual/experimental relationship runs |
| llm.job | same logical source/interrogation without dedupe key | unverified | unverified | High | backfill.py omits dedupe key |
| dbo.BridgeEntityRelation | same endpoints/type/time/source | unverified | unverified | High | no hard natural unique constraint in source DDL |
| llm.artifact | same run/type/content hash | unverified | unverified | Medium | artifact writes are per run; needs baseline |
| dbo.DimEntity | same normalized name/type/current row | unverified | unverified | Medium | stored proc reduces risk; live check needed |

Confirmed local duplicate output group:

- lake/llm_runs/2026/02/21/88ED08BB-7895-4EF2-B17E-F9B272A9FD70
- lake/llm_runs/2026/02/21/C2EC7900-C23E-4E59-B32E-920C49947F83
- output hash: 53dc4844a5ca2ec83efceb784e13d24868ae5b818c8cae0f180fddc4252e7bfd

## Failure and retry findings

| Failure category | Count | Retryable | Duplicate risk | Recommended safe mode |
| --- | ---: | --- | --- | --- |
| Live SQL inaccessible from this session | n/a | no | n/a | run supplied SQL manually |
| Candidate query failures masked in backfill.py | unverified | after fix | high false no-work risk | do not trust backfill dry-run alone |
| Missing page classification handler | n/a | no | high false success risk | fix before running |
| Entity handlers missing client/store | n/a | no | medium/high | fix dependency injection before running |
| Relationship handler missing store | n/a | no | high false completion risk | inject store or treat as artifact-only |
| Historical ingest in_progress rows | 10 historical | likely if expired | low/medium | verify leases before retry/reset |

## Ollama/model compatibility

The current default model llama3.2 is available as llama3.2:latest. Local lake runs used both llama3.2 and deepseek-r1:8b. The historical model snapshot from 2026-02-19 did not list llama3.2, while the current Ollama service does. If SQL result rows do not consistently record model digest, prompt version, and contract version, reruns can mix incompatible results under the same logical result set.

## Resume semantics findings

For python -m llm.cli.classify_entities --mode resume --batch-size 200:

| Question | Answer |
| --- | --- |
| Code branch | EntityClassificationService.get_candidates resume branch |
| Candidate table | dbo.DimEntity |
| Candidate predicate | IsLatest = 1 AND IsActive = 1 AND EntityType IS NULL by default |
| Failed predicate | join llm.job by dedupe key and status FAILED/DEADLETTER |
| Discovers new work? | yes for missing DimEntity fields only; not ingest/source pages |
| Completion predicate | EntityType populated; optional normalization/tags flags |
| Offset/checkpoint | no offset; deterministic ORDER BY EntityKey ASC; durable state is fields and dedupe job |
| Concurrency safety | enqueue depends on llm job dedupe procedure |
| Interruption behavior | enqueue is likely safe; downstream job completion must be checked |
| Can completed work be selected again? | yes with fresh, rerun, revalidate-existing, or stricter flags |
| Schema compatibility | source-compatible with modern DimEntity; live compatibility unverified |

Verified explanation for zero candidates: historical live data had no active/latest DimEntity rows with EntityType IS NULL. The command did not mean ingest was complete and did not mean lower-level extraction was complete.

## Resume decision model

| Layer | Category | Reason |
| --- | --- | --- |
| Ingest acquisition | C | likely resumable, current lease/state counts needed |
| classify_entities default missing type | B/C | enqueue is idempotent, but current counts unverified |
| classify_entities strict alias/normalization | C/D | candidate discovery works, but downstream job type is unsafe |
| Phase1Runner | C/D | real inference/artifacts, no domain routing |
| Dispatcher dry-run | C for diagnostics only | it still claims/writes queue state, so not read-only |
| Dispatcher live generic | D | can mark success without LLM |
| Backfill CLI | D | no dedupe key and incomplete handlers |
| Relationship domain persistence | D | store not injected; uniqueness weak |
| Depth processing | E/planned | not immediate |

## Recommended commands

### Option 1 - safest immediate breadth continuation

No live write/inference command is recommended yet. First run the read-only SQL diagnostics.

Working directory: W:\git\holocron-analytics

Host sqlcmd:

sqlcmd -S localhost,1433 -U sa -P <redacted> -C -d Holocron -i docs/audits/sql-processing-state-queries.sql

Container sqlcmd, if the file is copied/mounted into the container:

docker exec -i sql2025 /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P <redacted> -C -d Holocron -i /tmp/sql-processing-state-queries.sql

### Option 2 - retry known failures only

Dry-run only:

$env:PYTHONPATH="src"; python -m llm.cli.classify_entities --mode resume --only failed --batch-size 20 --dry-run -v

Purpose: count failed/deadletter classification enqueue candidates. It queries SQL, performs no inference, and should not enqueue jobs because dry-run returns before enqueue.

### Option 3 - fill missing outputs only

Dry-run only:

$env:PYTHONPATH="src"; python -m llm.cli.classify_entities --mode resume --fill-missing-only --require-tags --require-normalization --batch-size 20 --dry-run -v

Purpose: validate missing EntityType/normalization/sort/alias candidates. Do not remove dry-run until downstream processor behavior is fixed/verified.

### Option 4 - restricted validation batch

Dry-run candidate validation:

$env:PYTHONPATH="src"; python -m llm.cli.classify_entities --mode resume --require-tags --batch-size 5 --dry-run -v

Historical expected candidates: 5 from a historical pool of 15,637 missing AliasCsv. Current expected candidates must come from the SQL diagnostics.

### Option 5 - full remaining breadth batch

Not recommended yet. After remediation and diagnostics, a possible enqueue-only command would be:

$env:PYTHONPATH="src"; python -m llm.cli.classify_entities --mode resume --require-tags --batch-size 200 -v

Do not run until the processor that consumes entity_extraction_generic_v1 jobs is verified to update intended target fields and avoid duplicates.

### Unsafe commands now

| Command/mode | Reason |
| --- | --- |
| python -m src.llm.cli.backfill relationships --max-jobs N | no dedupe key; relationship candidate query does not exclude previous successful relationship runs |
| python -m src.llm.cli.backfill entities --max-jobs N | generic entity handler lacks Ollama client/entity store by default |
| python -m src.llm.cli.backfill classification --max-jobs N | page classification handler is missing |
| python -m src.llm.runners.dispatcher --once | live generic path can mark success without LLM |
| python -m src.llm.runners.dispatcher --dry-run --once | not read-only; claims jobs and writes run/artifact state |
| python -m src.llm.runners.phase1_runner --loop | starts substantive inference workload |
| classify_entities --mode fresh | selects all active/latest entities and may create broad reprocessing |
| classify_entities --mode rerun without reviewed keys | intentional reprocessing, not resume |

## Monitoring queries

Use docs/audits/sql-processing-state-queries.sql.

Before run:

- database identity
- core object presence
- DimEntity missing-field counts
- llm.job status by interrogation
- duplicate baselines for llm.job, llm.artifact, DimEntity, BridgeEntityRelation

During run:

- llm.job status by interrogation
- latest llm.run rows by model/status/error
- llm.artifact counts by artifact_type
- aged RUNNING jobs and expired ingest leases

After run:

- rerun the same candidate count
- compare target row deltas
- compare duplicate baselines
- inspect failed/deadletter rows and latest errors

## Explicit answers

1. Prior results are configured for Holocron on sql2025; historical docs say Holocron was used. Current live verification is blocked.
2. Major schemas are ingest, sem, llm, dbo, vector, and lake.
3. Actual pipelines are classify_entities, backfill, phase1_runner, dispatcher, ingest runner, entity_extraction_generic/droid, relationship_extraction, and page_classification.
4. Inputs are dbo.DimEntity, sem.SourcePage, sem.PageClassification, llm.job, and ingest.work_items.
5. Outputs are llm.job, llm.run, llm.artifact, lake/llm_runs, intended dbo.DimEntity, dbo.BridgeEntityRelation, and sem.PageClassification.
6. Current eligible counts are blocked; historical default classify eligible was 0 and strict AliasCsv candidates were 15,637.
7. Current successful counts are blocked; historical EntityType population was 15,637.
8. Current remaining counts are blocked; historical default classify remaining was 0, AliasCsv remaining was 15,637.
9. Current failed counts are blocked.
10. Historical ingest had 10 in_progress items; current stuck state blocked.
11. classify_entities zero candidates were not from never-enqueued source records; they were from the DimEntity completion predicate.
12. resume returned zero because EntityType IS NULL matched zero active/latest DimEntity rows historically.
13. resume discovers missing DimEntity fields, not ingest/source-page work.
14. Python queries appear aligned with modern source schema; live compatibility is unverified.
15. Local lake shows exact duplicate relationship output; SQL duplicates unverified.
16. llm.job is only safe when dedupe_key exists; BridgeEntityRelation lacks hard natural uniqueness; artifact uniqueness is unclear.
17. Enqueue can likely be interrupted/resumed; downstream runners are unsafe until queue/handler behavior is verified.
18. Local historical artifacts used relationship_extraction_v1 with llama3.2 and deepseek-r1:8b; SQL model/prompt history unverified.
19. Running now could mix model/digest/contract versions unless constrained and recorded.
20. First command should be the read-only SQL diagnostic file.
21. Small validation command is classify_entities --mode resume --require-tags --batch-size 5 --dry-run -v.
22. Progress should be checked with llm.job status and llm.run recent rows in the SQL file.
23. Avoid live backfill, dispatcher live, phase1 loop, fresh/rerun broad modes.
24. Remediation is required before lower-level breadth batches: handler wiring, dedupe keys, uniqueness, and live drift verification.
25. Later depth capabilities exist in retrieval/vector, event/work scaffolding, governance/adjudication, and benchmarking; do not run yet.

## Blockers

- Current SQL Server live inspection is blocked from this session.
- Docker and Python process execution is blocked from this session.
- Markdown link validation could not be run.
- Lower-level handler and backfill idempotency issues should be fixed before broad execution.
