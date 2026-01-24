# LLM-Derived Data Module

## Overview

The **LLM-Derived Data** module provides infrastructure for generating **structured JSON artifacts** from evidence bundles using Large Language Models (LLMs). This is a subsystem within Holocron Analytics that transforms unstructured or semi-structured evidence (internal docs, web snapshots, SQL result sets, raw HTTP responses) into validated, reproducible structured data.

## What "Derived Data" Means

"Derived data" in this context refers to structured outputs that are:

1. **Evidence-Led**: Generated from explicit source materials (evidence bundles), not hallucinated
2. **Schema-Validated**: Conform to predefined JSON schemas with fail-closed validation
3. **Reproducible**: Tracked via manifests that capture inputs, configs, and hashes
4. **Traceable**: Each artifact links back to its source evidence and generation context

This is **not**:
- Ground truth data (it's LLM-interpreted, subject to model limitations)
- Synthetic data generation in the statistical sense (no random sampling or simulation)
- A replacement for authoritative sources (it's a processing/extraction layer)

## Relationship to Other Modules

### Ingest Module (`src/ingest/`)

The ingest module fetches and stores raw content from external sources. The LLM module consumes these ingested artifacts as evidence:

```
Ingest → Data Lake (raw JSON) → LLM Derive → Derived Artifacts (structured JSON)
```

Conventions and patterns from `src/ingest/` are mirrored here:
- Similar config loading patterns
- Similar storage abstractions
- Similar runner orchestration

### Database (SQL Server)

The LLM module interacts with SQL Server for:
- **Job Queue**: Track pending, in-progress, and completed derive jobs
- **Run Metadata**: Store manifest information and run statistics
- **Artifact Pointers**: Reference derived artifacts stored in the data lake

Database schemas are scaffolded but not fully implemented (see `storage/sql_queue_store.py`).

## Directory Structure

```
src/llm/
├── __init__.py           # Module initialization
├── README.md             # This file
├── contracts/            # JSON schemas for validation
│   ├── manifest_schema.json
│   ├── derived_output_schema.json
│   └── README.md
├── core/                 # Core abstractions
│   ├── types.py          # Data models (dataclasses)
│   ├── exceptions.py     # Custom exceptions
│   └── logging.py        # Logging utilities
├── interrogations/       # Interrogation catalog
│   ├── README.md
│   ├── definitions/      # YAML/JSON interrogation definitions
│   └── rubrics/          # Rubric markdown files
├── prompts/              # Prompt management
│   ├── README.md
│   └── templates/        # Prompt template files
├── providers/            # LLM provider clients
│   ├── ollama_client.py
│   └── README.md
├── runners/              # Orchestration
│   └── derive_runner.py
├── storage/              # Persistence
│   ├── artifact_store.py
│   └── sql_queue_store.py
└── config/               # Configuration
    ├── config.md
    └── llm.example.yaml
```

## Quick Start

### Prerequisites

- Python 3.11+
- Ollama running locally (or accessible via network)
- Optional: SQL Server for queue persistence

### Configuration

1. Copy the example config:
   ```bash
   cp src/llm/config/llm.example.yaml config/llm.yaml
   ```

2. Edit `config/llm.yaml` to configure:
   - Ollama base URL and model
   - Storage paths
   - Queue settings

### Running

```bash
# Run the smoke test to verify Ollama connectivity
python scripts/llm_smoke_test.py

# Capture model inventory to JSON
python scripts/ollama_capture_models.py

# Run the Phase 1 derive runner (single job)
python -m src.llm.runners.phase1_runner --once --worker-id local --verbose

# Run the Phase 1 derive runner (loop mode)
python -m src.llm.runners.phase1_runner --loop --poll-seconds 10
```

## Documentation

- [LLM-Derived Data Overview](../../docs/llm/derived-data.md) - Concepts and roadmap
- [Phase 1 Runner Guide](../../docs/llm/phase1-runner.md) - End-to-end derive pipeline
- [Ollama Integration Guide](../../docs/llm/ollama.md) - API documentation and configuration
- [Ollama in Docker](../../docs/llm/ollama-docker.md) - Docker Compose setup and networking

## Status

**Phase 1 (MVP Runner)** - End-to-end derive workflow implemented:
- SQL Server job queue with atomic claiming
- Ollama structured output with JSON schema
- Evidence bundling from inline data or file references
- Artifact storage to filesystem lake
- Retry with backoff and deadlettering
- Full telemetry capture (metrics, model info)

See [Phase 1 Runner](../../docs/llm/phase1-runner.md) for usage guide.

## License

See repository LICENSE file.
