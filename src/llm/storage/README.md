# LLM Storage

## Overview

This directory contains storage implementations for LLM-derived artifacts and job queue management. Storage follows the "SQL holds metadata; lake holds blobs" convention.

## Storage Strategy

### Two-Tier Storage

The LLM module uses a two-tier storage approach:

| Tier | Purpose | Implementation |
|------|---------|----------------|
| **Data Lake** | Raw responses, derived artifacts, manifests | Filesystem (local or cloud) |
| **SQL Server** | Job queue, run metadata, artifact pointers | Database tables (TBD) |

This separation enables:
- Efficient blob storage for large artifacts
- Fast querying for job management
- Scalable retrieval of metadata

### Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Filesystem Store | ✅ Implemented | `artifact_store.py` |
| SQL Queue Store | 🔶 Stub | `sql_queue_store.py` (in-memory) |

---

## Components

### `artifact_store.py`

Filesystem-based storage for LLM-derived artifacts.

**Directory Structure:**
```
{base_dir}/
├── manifests/          # Manifest files for reproducibility
│   └── {manifest_id}.json
├── artifacts/          # Derived output artifacts
│   └── {task_type}/
│       └── {timestamp}_{manifest_id}.json
└── raw_responses/      # Raw LLM responses (for debugging)
    └── {timestamp}_{manifest_id}.txt
```

**Usage:**
```python
from src.llm.storage import ArtifactStore
from pathlib import Path

store = ArtifactStore(Path("local/llm_artifacts"))

# Write manifest
store.write_manifest(manifest)

# Write artifact
store.write_artifact(manifest_id, "entity_extraction", data)

# Write raw response
store.write_raw_response(manifest_id, raw_text)
```

### `sql_queue_store.py`

SQL Server-based queue and metadata store for LLM derive jobs.

**Status:** Stub implementation (in-memory storage for interface validation)

**Planned Schema (TBD):**
```sql
-- Job queue
CREATE TABLE llm.DeriveJobs (
    job_id UNIQUEIDENTIFIER PRIMARY KEY,
    manifest_id UNIQUEIDENTIFIER NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority INT DEFAULT 100,
    created_at_utc DATETIME2 NOT NULL,
    ...
);

-- Manifest metadata
CREATE TABLE llm.DeriveManifests (
    manifest_id UNIQUEIDENTIFIER PRIMARY KEY,
    manifest_version VARCHAR(20) NOT NULL,
    llm_provider VARCHAR(50),
    llm_model VARCHAR(100),
    status VARCHAR(50) NOT NULL,
    artifact_path NVARCHAR(500),
    ...
);
```

**Usage:**
```python
from src.llm.storage import SqlQueueStore
from src.llm.core.types import DeriveJobStatus

store = SqlQueueStore()

# Enqueue job
job_id = store.enqueue(manifest)

# Dequeue next job
job = store.dequeue()

# Update status
store.update_status(job_id, DeriveJobStatus.COMPLETED)
```

---

## Configuration

Storage paths are configured in `config/llm.yaml`:

```yaml
storage:
  artifact_lake:
    enabled: true
    base_dir: "local/llm_artifacts"
    pretty_print: true
  
  sql_server:
    enabled: false
    schema: "llm"
```

---

## SQL Server Schema (TBD)

The exact SQL Server schema for job queue and run metadata is **TBD**. Current stub provides:

- **Interface validation** — Ensures the API is correct before implementing DB
- **Testing support** — Enables testing without a database
- **Pattern exploration** — Identifies required operations

Full implementation is planned for **Phase 1**.

---

## Related Documentation

- [LLM Module README](../README.md) — Module overview
- [Contracts README](../contracts/README.md) — JSON schema documentation
- [Configuration Reference](../config/config.md) — Storage configuration
