# Phase 1 Runner - End-to-End LLM Derive Pipeline

## Overview

The Phase 1 Runner implements the first end-to-end execution path for the LLM-Derived Data subsystem. It provides:

- **Job Queue**: SQL Server-based priority queue with atomic claiming
- **Evidence Bundling**: Assembles evidence from job inputs or file references
- **Structured Output**: Uses Ollama's native structured output (JSON schema)
- **Artifact Storage**: Writes all artifacts to a filesystem lake
- **Telemetry Capture**: Records timing metrics, token counts, and model info
- **Retry Logic**: Automatic retry with exponential backoff, deadlettering

## What Phase 1 Does

✅ **Enqueue jobs** with input parameters and evidence references  
✅ **Claim and process jobs** atomically from SQL Server  
✅ **Build evidence bundles** from inline data or file references  
✅ **Render prompts** from interrogation definitions  
✅ **Call Ollama** with structured output (JSON schema in `format`)  
✅ **Validate responses** against contract schemas  
✅ **Write artifacts** to the lake (request, response, evidence, prompt, output)  
✅ **Record metadata** to SQL Server (runs, artifacts, metrics)  
✅ **Retry failures** with backoff, deadletter after max attempts  

## What Phase 1 Does NOT Do

❌ **RAG / Embeddings**: Evidence is provided, not retrieved  
❌ **Web Browsing**: No live data fetching  
❌ **Multi-model Comparison**: Single model per job  
❌ **Human-in-the-loop**: Fully automated  
❌ **Production Hardening**: MVP focus, not production-ready  

## Quick Start

### Prerequisites

1. Docker Desktop with WSL2 (Windows) or Docker Engine (Linux/Mac)
2. SQL Server running (via `docker compose up sql2025`)
3. Ollama running with a model pulled (via `docker compose up ollama`)

### 1. Start the Stack

```bash
# Start SQL Server and Ollama
docker compose up -d sql2025 ollama

# Wait for SQL Server to be ready
docker compose up initdb

# Pull a model (one-time)
docker exec -it holocron-ollama ollama pull llama3.2
```

### 2. Enqueue a Test Job

Using the helper script (recommended):

```bash
python scripts/llm_enqueue_job.py \
    --entity-type character \
    --entity-id luke_skywalker \
    --evidence "Luke Skywalker was a human male Jedi who was instrumental in defeating the Galactic Empire during the Galactic Civil War. Born on Tatooine in 19 BBY, Luke was the son of Anakin Skywalker and Padmé Amidala."
```

Using SQL:

```sql
-- Connect to SQL Server and run:
EXEC [llm].[usp_enqueue_job]
    @priority = 100,
    @interrogation_key = 'sw_entity_facts_v1',
    @input_json = '{"entity_type": "character", "entity_id": "luke_skywalker", "source_refs": [], "extra_params": {"evidence": [{"evidence_id": "e1", "source_uri": "wookieepedia", "text": "Luke Skywalker was a human male Jedi who was instrumental in defeating the Galactic Empire during the Galactic Civil War. Born on Tatooine in 19 BBY, Luke was the son of Anakin Skywalker and Padmé Amidala."}]}}',
    @evidence_ref_json = NULL,
    @model_hint = 'llama3.2';
```

Or using Python:

```python
from src.llm.storage.sql_job_queue import SqlJobQueue, QueueConfig
import json

queue = SqlJobQueue(QueueConfig.from_env())

input_data = {
    "entity_type": "character",
    "entity_id": "luke_skywalker",
    "source_refs": [],
    "extra_params": {
        "evidence": [{
            "evidence_id": "e1",
            "source_uri": "wookieepedia",
            "text": "Luke Skywalker was a human male Jedi who was instrumental in defeating the Galactic Empire during the Galactic Civil War. Born on Tatooine in 19 BBY, Luke was the son of Anakin Skywalker and Padmé Amidala."
        }]
    }
}

job_id = queue.enqueue_job(
    interrogation_key="sw_entity_facts_v1",
    input_json=json.dumps(input_data),
    priority=100,
    model_hint="llama3.2"
)

print(f"Enqueued job: {job_id}")
```

### 3. Run the Runner

**Option A: In Docker (recommended for container-to-container networking)**

```bash
# Run once (process single job)
docker compose run llm-runner python -m src.llm.runners.phase1_runner --once --verbose

# Or start in loop mode
docker compose --profile llm up llm-runner
```

**Option B: On Host (requires ODBC drivers and local Ollama access)**

```bash
# Set environment
export OLLAMA_BASE_URL=http://localhost:11434
export LLM_SQLSERVER_HOST=localhost
export LLM_SQLSERVER_PASSWORD=YourPassword

# Run once
python -m src.llm.runners.phase1_runner --once --worker-id local-worker --verbose

# Or run in loop mode
python -m src.llm.runners.phase1_runner --loop --poll-seconds 10
```

### 4. Inspect Results

**Check job status in SQL:**

```sql
SELECT job_id, status, attempt_count, last_error, created_utc
FROM [llm].[job]
ORDER BY created_utc DESC;
```

**Check run details:**

```sql
SELECT r.run_id, r.job_id, r.status, r.model_name, r.started_utc, r.completed_utc,
       r.metrics_json, r.error
FROM [llm].[run] r
ORDER BY r.started_utc DESC;
```

**Check artifacts:**

```sql
SELECT a.artifact_id, a.run_id, a.artifact_type, a.lake_uri, a.byte_count
FROM [llm].[artifact] a
ORDER BY a.created_utc DESC;
```

**Using the helper script:**

```bash
# List recent jobs
python scripts/llm_inspect_jobs.py --list

# Show queue statistics
python scripts/llm_inspect_jobs.py --stats

# Show details for a specific job
python scripts/llm_inspect_jobs.py --job-id <job-id>
```

**View artifacts in the lake:**

```bash
# If running in Docker, artifacts are in the llm_lake volume
docker compose exec llm-runner ls -la /lake/llm_runs/

# If running locally, artifacts are in ./lake/llm_runs/
ls -la lake/llm_runs/
```

## Architecture

### Job Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Enqueue   │────▶│  SQL Queue  │────▶│   Runner    │
│   (Job)     │     │  (llm.job)  │     │  (Claim)    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          ▼                          │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
                    │  │   Build     │  │   Render    │  │   Call      │  │
                    │  │  Evidence   │─▶│   Prompt    │─▶│   Ollama    │  │
                    │  └─────────────┘  └─────────────┘  └──────┬──────┘  │
                    │                                          │          │
                    │  ┌─────────────┐  ┌─────────────┐  ┌─────┴───────┐  │
                    │  │   Update    │◀─│   Write     │◀─│  Validate   │  │
                    │  │    SQL      │  │   Lake      │  │   Output    │  │
                    │  └─────────────┘  └─────────────┘  └─────────────┘  │
                    │                                                      │
                    └──────────────────────────────────────────────────────┘
```

### SQL Schema

**Tables:**
- `llm.job` - Job queue with priority, status, retry tracking
- `llm.run` - Individual run attempts with model info and metrics
- `llm.artifact` - Artifact metadata pointing to lake files

**Stored Procedures:**
- `llm.usp_claim_next_job` - Atomic job claiming with READPAST/UPDLOCK
- `llm.usp_complete_job` - Mark job succeeded/failed with retry logic
- `llm.usp_enqueue_job` - Add job to queue
- `llm.usp_create_run` - Create run record
- `llm.usp_complete_run` - Complete run with metrics
- `llm.usp_create_artifact` - Record artifact metadata

### Lake Structure

```
lake/llm_runs/
└── {yyyy}/
    └── {mm}/
        └── {dd}/
            └── {run_id}/
                ├── request.json      # Full Ollama request payload
                ├── response.json     # Full Ollama response
                ├── evidence.json     # Evidence bundle used
                ├── prompt.txt        # Rendered prompt text
                └── output.json       # Parsed/validated output
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_ID` | auto-generated | Worker identifier for job locking |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | Default model |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Request timeout |
| `OLLAMA_TEMPERATURE` | `0.0` | Sampling temperature |
| `POLL_SECONDS` | `10` | Queue poll interval |
| `LAKE_ROOT` | `lake/llm_runs` | Lake directory |
| `LLM_SQLSERVER_HOST` | `localhost` | SQL Server host |
| `LLM_SQLSERVER_DATABASE` | `Holocron` | Database name |
| `LLM_SQLSERVER_USER` | `sa` | SQL username |
| `LLM_SQLSERVER_PASSWORD` | - | SQL password |
| `LLM_SQLSERVER_SCHEMA` | `llm` | Schema name |

### CLI Arguments

```
usage: phase1_runner.py [-h] (--once | --loop) [--worker-id WORKER_ID]
                        [--poll-seconds POLL_SECONDS] [--model MODEL]
                        [--ollama-url OLLAMA_URL] [--lake-root LAKE_ROOT]
                        [--verbose]

options:
  --once              Process a single job and exit
  --loop              Run continuously, polling for jobs
  --worker-id         Worker identifier
  --poll-seconds      Seconds between poll attempts (default: 10)
  --model             Override default model
  --ollama-url        Override Ollama URL
  --lake-root         Override lake directory
  --verbose, -v       Enable debug logging
```

## Interrogations

### sw_entity_facts_v1

Extracts normalized facts about Star Wars entities.

**Input:**
```json
{
  "entity_type": "character",
  "entity_id": "luke_skywalker",
  "source_refs": [],
  "extra_params": {
    "evidence": [
      {
        "evidence_id": "e1",
        "source_uri": "source",
        "text": "Evidence text here..."
      }
    ]
  }
}
```

**Output:**
```json
{
  "entity_type": "character",
  "entity_id": "luke_skywalker",
  "entity_name": "Luke Skywalker",
  "facts": [
    {
      "fact_key": "species",
      "value": "Human",
      "unit": null,
      "confidence": 1.0,
      "evidence_ids": ["e1"],
      "notes": null
    },
    {
      "fact_key": "birth_year",
      "value": 19,
      "unit": "BBY",
      "confidence": 1.0,
      "evidence_ids": ["e1"],
      "notes": null
    }
  ]
}
```

## Troubleshooting

### Job stuck in RUNNING

The runner crashed before completing. Reset the job:

```sql
UPDATE [llm].[job]
SET status = 'NEW', locked_by = NULL, locked_utc = NULL
WHERE job_id = 'your-job-id';
```

### Ollama connection refused

1. Ensure Ollama is running: `docker compose ps ollama`
2. Check the URL matches your environment:
   - From Docker: `http://ollama:11434`
   - From host: `http://localhost:11434`

### Validation errors

Check the response artifact in the lake to see the raw LLM output:

```bash
cat lake/llm_runs/2024/01/15/{run_id}/response.json
```

### No jobs available

1. Check there are jobs in NEW status:
   ```sql
   SELECT * FROM [llm].[job] WHERE status = 'NEW';
   ```
2. Check `available_utc` is not in the future (retry backoff)

## See Also

- [LLM-Derived Data Overview](derived-data.md)
- [Ollama Integration Guide](ollama.md)
- [Ollama in Docker](ollama-docker.md)
- [LLM Module README](../../src/llm/README.md)
