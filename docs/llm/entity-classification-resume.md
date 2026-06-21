# Entity Classification Resume / Checkpoint

This document describes the **resume / checkpoint** capability added to the entity classification runner. The runner identifies entities in `dbo.DimEntity` that need type classification and enqueues LLM jobs for them, with full support for resumable, idempotent processing.

## Overview

The `classify-entities` CLI tool:

1. Queries `dbo.DimEntity` for rows missing classification (e.g., `EntityType IS NULL`).
2. Cross-references the `llm.job` queue using idempotent dedupe keys to avoid duplicate work.
3. Enqueues LLM jobs only for entities that truly need processing.
4. Tracks statistics: attempted, skipped, succeeded, failed.

## How "Completion" Is Determined

An entity is considered **classified** when:

```
EntityType IS NOT NULL AND IsLatest = 1 AND IsActive = 1
```

This predicate can be made stricter with CLI flags:

| Flag | Additional requirement |
|---|---|
| `--require-normalization` | `DisplayNameNormalized IS NOT NULL AND SortName IS NOT NULL` |
| `--require-tags` | `AliasCsv IS NOT NULL` |

## Resume Behavior

- **Default (`--mode resume`):** Only processes entities where `EntityType IS NULL` (unclassified). Already-classified entities are skipped.
- **Idempotent enqueue:** Each entity gets a dedupe key (`entity_classify:{EntityKey}`). If a job already exists for that key, the runner detects it and skips.
- **Interrupted runs:** If the runner is stopped mid-run and restarted with `--mode resume`, it will:
  - Skip entities that were successfully classified.
  - Skip entities with an in-progress or queued job.
  - Pick up entities that still lack classification.

## Run Modes

| Mode | Behavior |
|---|---|
| `resume` (default) | Skip classified entities, process only unclassified |
| `fresh` | Process all active/latest entities (idempotent enqueue prevents duplicates) |
| `rerun` | Process specific entities by key (ignores classification state) |

## How to Re-run / Revalidate

### Retry only failed entities
```bash
python -m llm.cli.classify_entities --mode resume --only failed
```

### Force re-classification of specific entities
```bash
python -m llm.cli.classify_entities --mode rerun --entity-keys 123 456 789
```

### Re-validate all (even already classified)
```bash
python -m llm.cli.classify_entities --mode resume --revalidate-existing
```

### Fill only missing fields (don't overwrite)
```bash
python -m llm.cli.classify_entities --mode resume --fill-missing-only
```

## Example Commands

```bash
# Start fresh classification run
python -m llm.cli.classify_entities --mode fresh --batch-size 200

# Resume from last checkpoint (skip already-classified)
python -m llm.cli.classify_entities --mode resume --batch-size 200

# Resume but only retry failed entities
python -m llm.cli.classify_entities --mode resume --only failed

# Force re-run specific entities
python -m llm.cli.classify_entities --mode rerun --entity-keys 123 456 789

# Fill missing fields only (don't overwrite existing)
python -m llm.cli.classify_entities --mode resume --fill-missing-only

# Dry run (preview what would be processed)
python -m llm.cli.classify_entities --mode resume --dry-run

# Require tags and normalization before considering "done"
python -m llm.cli.classify_entities --mode resume --require-tags --require-normalization

# Verbose logging
python -m llm.cli.classify_entities --mode resume -v
```

## Database Objects

### Stored Procedures

| Procedure | Purpose |
|---|---|
| `dbo.usp_get_unclassified_entities` | Returns entities missing classification fields |
| `dbo.usp_get_entity_classification_status` | Returns classification state for entities (including LLM job status) |

### Migration

`db/migrations/0036_entity_classification_checkpoint.sql` — creates the stored procedures above.

## Architecture

```
classify-entities CLI
    │
    ├── EntityClassificationService.get_candidates()
    │   └── Queries DimEntity for unclassified rows
    │
    ├── is_entity_classified() predicate
    │   └── Checks EntityType, IsLatest, IsActive, optional normalization/tags
    │
    └── SqlJobQueue.enqueue_job_idempotent()
        └── Idempotent enqueue with dedupe_key = "entity_classify:{EntityKey}"
            └── Existing llm.job queue handles claim/run/complete lifecycle
```

The classify-entities runner does **not** execute the LLM classification itself — it enqueues jobs into the existing `llm.job` queue. The Phase 1 runner (`phase1_runner.py`) or dispatcher processes the actual LLM calls.

## Observability

The runner outputs a JSON summary on completion:

```json
{
  "attempted": 150,
  "skipped": 50,
  "succeeded": 145,
  "failed": 5,
  "already_classified": 50,
  "dry_run_would_process": 0,
  "error_count": 5,
  "errors": ["EntityKey=42: Connection timeout", "..."]
}
```

Exit codes:
- `0` — all succeeded
- `1` — some failures occurred
