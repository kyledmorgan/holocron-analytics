# Debug Report: `classify_entities --mode resume` Returned 0 Candidates

Date: February 28, 2026  
Scope: `python -m llm.cli.classify_entities --mode resume --batch-size 200`

## Root Cause

`--mode resume` selects candidates from `dbo.DimEntity` (active/latest rows), not from `ingest.*` tables.  
In the current `Holocron` database state, all active/latest `DimEntity` rows already have `EntityType` populated, so the default resume predicate (`EntityType IS NULL`) returns zero rows.

There was also a masking issue in CLI behavior: query/connection failures were being caught and converted to empty candidate lists (`[]`), which could incorrectly look like a valid "0 candidates" run. This has been fixed so candidate discovery errors are reported as failures.

## Code Path and Candidate Query

Entrypoint:
- `src/llm/cli/classify_entities.py`

Log line:
- `Found {n} candidate entities (mode=...)` at `EntityClassificationService.run()`

Candidate source method:
- `EntityClassificationService.get_candidates()`

Default `resume` query shape:

```sql
SELECT TOP (?)
  e.EntityKey, e.EntityGuid, e.DisplayName, e.EntityType,
  e.DisplayNameNormalized, e.SortName, e.AliasCsv,
  e.IsLatest, e.IsActive, e.ExternalKey, e.SourcePageId
FROM dbo.DimEntity e
WHERE e.IsLatest = 1
  AND e.IsActive = 1
  AND (missing-field predicate)
ORDER BY e.EntityKey ASC;
```

`only failed` path:
- joins `dbo.DimEntity` to `llm.job` on dedupe key `entity_classify:{EntityKey}`
- filters `llm.job.status IN ('FAILED', 'DEADLETTER')`

## Source-of-Candidates Clarification

Candidates come from:
- `dbo.DimEntity` (default/fresh/rerun-by-keys)
- `dbo.DimEntity` + `llm.job` (resume `--only failed`)

Candidates do not come directly from:
- `ingest.IngestRecords`
- `ingest.work_items`

## SQL Reality Checks (Executed Against `Holocron`)

### A) DimEntity totals and unclassified

```sql
SELECT
  COUNT(*) AS total_dim_entities,
  SUM(CASE WHEN EntityType IS NULL THEN 1 ELSE 0 END) AS missing_entity_type,
  SUM(CASE WHEN EntityType IS NOT NULL THEN 1 ELSE 0 END) AS has_entity_type
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1;
```

Result:
- `total_dim_entities = 15637`
- `missing_entity_type = 0`
- `has_entity_type = 15637`

### B) Missing normalization and alias fields

```sql
SELECT
  SUM(CASE WHEN EntityType IS NULL THEN 1 ELSE 0 END) AS missing_entity_type,
  SUM(CASE WHEN DisplayNameNormalized IS NULL THEN 1 ELSE 0 END) AS missing_normalized,
  SUM(CASE WHEN SortName IS NULL THEN 1 ELSE 0 END) AS missing_sort,
  SUM(CASE WHEN AliasCsv IS NULL THEN 1 ELSE 0 END) AS missing_aliascsv
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1;
```

Result:
- `missing_entity_type = 0`
- `missing_normalized = 0`
- `missing_sort = 0`
- `missing_aliascsv = 15637`

### C) Ingest and queue counts

```sql
SELECT COUNT(*) AS ingest_records_total
FROM ingest.IngestRecords;

SELECT COUNT(*) AS ingest_records_no_work_item
FROM ingest.IngestRecords
WHERE work_item_id IS NULL;

SELECT status, COUNT(*) AS cnt
FROM ingest.work_items
GROUP BY status
ORDER BY cnt DESC;
```

Result:
- `ingest_records_total = 99970`
- `ingest_records_no_work_item = 0`
- `ingest.work_items`: `completed = 799040`, `in_progress = 10`

Additional mapping check:

```sql
SELECT COUNT(*) AS dimentity_externalkey_notnull
FROM dbo.DimEntity
WHERE IsLatest = 1 AND IsActive = 1 AND ExternalKey IS NOT NULL;

SELECT COUNT(DISTINCT resource_id) AS ingest_distinct_resource_id
FROM ingest.IngestRecords;
```

Result:
- `dimentity_externalkey_notnull = 0`
- `ingest_distinct_resource_id = 49985`

Interpretation:
- ingest has substantial data, but this CLI does not use ingest tables for candidate discovery.
- there is no `ExternalKey` bridge populated from ingest resource IDs into `DimEntity` in current data.

## True Cause Determination

Primary true cause:
- `resume` is operating as implemented, and the data satisfies the "already classified" condition (`EntityType` present on all active/latest rows), so there are no default resume candidates.

Secondary defect (fixed):
- candidate query failures were suppressed as empty candidate sets.

## Implemented Fixes

File: `src/llm/cli/classify_entities.py`

1. Resume candidate predicate now honors strict flags in SQL:
- `--require-normalization` includes rows missing `DisplayNameNormalized` or `SortName`
- `--require-tags` includes rows missing `AliasCsv`
- `--fill-missing-only` remains supported

2. Added explicit observability logs:
- candidate source table(s)
- effective predicate summary
- category counts: total, missing type, missing normalization, missing sort, missing alias

3. Removed silent query swallowing:
- candidate discovery failures now return run failure (`failed=1`) with `candidate_discovery_failed` in error list

4. Updated mode help text:
- `resume` is described as "active/latest rows missing required fields (EntityType by default)"

Tests updated:
- `tests/unit/llm/test_classify_entities.py`
- added tests for `--require-tags` and `--require-normalization` query behavior
- added test for candidate discovery failure handling

## CLI Usage After Fix

Default missing type:

```bash
python -m llm.cli.classify_entities --mode resume --batch-size 200
```

Missing normalization:

```bash
python -m llm.cli.classify_entities --mode resume --require-normalization --batch-size 200
```

Missing tags/aliases:

```bash
python -m llm.cli.classify_entities --mode resume --require-tags --batch-size 200
```

Any missing fields:

```bash
python -m llm.cli.classify_entities --mode resume --fill-missing-only --require-tags --require-normalization --batch-size 200
```

## Notes

- Current shell environment still shows a local ODBC connectivity issue for direct Python `pyodbc` calls, but SQL checks were executed successfully against the running `sql2025` container using `sqlcmd`.
- This report reflects database state observed on February 28, 2026.
