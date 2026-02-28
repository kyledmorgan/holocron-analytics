# Scripts Directory

This directory contains utility scripts for working with the Holocron Analytics project. These scripts are organized by functional area and provide tools for database operations, LLM workflows, testing, and development tasks.

---

## Directory Structure

```
scripts/
├── db/              # Database-related scripts
├── dev/             # Development utilities (placeholder)
├── lake/            # Data lake utilities
├── pipeline/        # Data pipeline scripts (placeholder)
├── test/            # Test runner scripts
├── llm_enqueue_job.py
├── llm_inspect_jobs.py
├── llm_smoke_test.py
└── ollama_capture_models.py
```

---

## Database Scripts (`db/`)

### `db_smoketest.py`

**Purpose:** Verifies SQL Server connectivity and basic operations.

**Usage:**
```bash
python scripts/db/db_smoketest.py
```

**What it tests:**
- Connection to SQL Server can be established
- Schema and tables can be created
- Basic read/write operations work
- Dedupe logic functions correctly

**Exit codes:**
- `0`: All tests passed
- `1`: Connection or test failure

**Environment Variables:**
- `INGEST_SQLSERVER_HOST` (default: localhost)
- `INGEST_SQLSERVER_PORT` (default: 1433)
- `INGEST_SQLSERVER_DATABASE` (default: Holocron)
- `INGEST_SQLSERVER_USER` (default: sa)
- `INGEST_SQLSERVER_PASSWORD` (required)
- `INGEST_SQLSERVER_DRIVER` (default: ODBC Driver 18 for SQL Server)

---

## LLM Scripts

### `llm_smoke_test.py`

**Purpose:** Validates Ollama connectivity and basic LLM functionality.

**Usage:**
```bash
# Default Ollama endpoint
python scripts/llm_smoke_test.py

# Custom Ollama endpoint
python scripts/llm_smoke_test.py --base-url http://192.168.1.100:11434

# Specify model
python scripts/llm_smoke_test.py --model mistral
```

**Environment Variables:**
- `LLM_BASE_URL` (default: http://localhost:11434)
- `LLM_MODEL` (default: llama3.2)

**Exit Codes:**
- `0`: Success
- `1`: Provider unreachable or JSON parse failure

---

### `llm_enqueue_job.py`

**Purpose:** Enqueue LLM derive jobs for the Phase 1 runner without writing SQL directly.

**Usage:**
```bash
# Enqueue a job with inline evidence
python scripts/llm_enqueue_job.py \
    --entity-type character \
    --entity-id luke_skywalker \
    --evidence "Luke Skywalker was a human male Jedi born on Tatooine in 19 BBY."

# Enqueue a job with evidence from file
python scripts/llm_enqueue_job.py \
    --entity-type planet \
    --entity-id tatooine \
    --evidence-file evidence.txt

# Enqueue with custom priority and model
python scripts/llm_enqueue_job.py \
    --entity-type character \
    --entity-id vader \
    --evidence "Darth Vader was a Sith Lord." \
    --priority 200 \
    --model llama3.1
```

**Environment Variables:**
- `LLM_SQLSERVER_HOST`
- `LLM_SQLSERVER_PASSWORD`
- Falls back to `INGEST_SQLSERVER_*` or `MSSQL_*` vars

---

### `llm_inspect_jobs.py`

**Purpose:** Inspect LLM derive jobs and runs in the queue.

**Usage:**
```bash
# List recent jobs
python scripts/llm_inspect_jobs.py --list

# Show details for a specific job
python scripts/llm_inspect_jobs.py --job-id abc123

# Show queue statistics
python scripts/llm_inspect_jobs.py --stats
```

**Environment Variables:**
- `LLM_SQLSERVER_HOST`
- `LLM_SQLSERVER_PASSWORD`

---

### `ollama_capture_models.py`

**Purpose:** Capture available Ollama models and their metadata for documentation and testing.

**Usage:**
```bash
python scripts/ollama_capture_models.py
```

---

## Test Scripts (`test/`)

These scripts provide different test execution entry points. For most cases, use the **Makefile targets** instead (see root [Makefile](../Makefile)).

### `test_unit.sh`

Run unit tests only (no external dependencies).

```bash
bash scripts/test/test_unit.sh
```

### `test_sqlserver.sh` / `test_e2e.sh`

Run SQL Server integration and end-to-end tests.

```bash
bash scripts/test/test_sqlserver.sh
bash scripts/test/test_e2e.sh
```

### `verify_sqlserver.sh`

One-command verification of SQL Server integration (starts container, initializes DB, runs tests).

```bash
bash scripts/test/verify_sqlserver.sh
```

**💡 Tip:** Use `make verify-sqlserver` instead for better output formatting.

---

## Lake Scripts (`lake/`)

### `decompress_gz_tree.py`

**Purpose:** Bulk decompress `.gz` archives into a parallel directory tree, preserving folder structure. Designed for OpenAlex snapshot data but works with any `.gz` tree.

**Usage:**
```bash
# Decompress everything (idempotent — skips existing)
python scripts/lake/decompress_gz_tree.py

# Dry-run
python scripts/lake/decompress_gz_tree.py --dry-run

# Force re-decompress, limited to 10 files, 4 workers
python scripts/lake/decompress_gz_tree.py --force --max-files 10 --workers 4
```

**Exit Codes:**
- `0`: All files processed successfully
- `1`: One or more failures (unless `--continue-on-error`)

See [docs/lake/openalex_decompression.md](../docs/lake/openalex_decompression.md) for full documentation.

### `decompress_gz_tree.ps1`

**Purpose:** PowerShell alternative using .NET `GzipStream` for Windows-native usage.

**Usage:**
```powershell
.\scripts\lake\decompress_gz_tree.ps1 -DryRun
.\scripts\lake\decompress_gz_tree.ps1 -Force -MaxFiles 5
```

---

## Development Scripts (`dev/`)

Currently a placeholder directory for future development utilities.

---

## Pipeline Scripts (`pipeline/`)

Currently a placeholder directory for future data pipeline scripts.

---

## Best Practices

1. **Use Makefile targets when available** — Most scripts have corresponding `make` commands with better error handling and output formatting
2. **Set environment variables** — Most scripts rely on environment variables for configuration; use `.env` file or export them
3. **Check exit codes** — All scripts use proper exit codes for CI/CD integration
4. **Read script docstrings** — Each script has detailed usage information in its header

---

## Related Documentation

- [Root README](../README.md) — Project overview and quick start
- [Makefile](../Makefile) — Development commands and tasks
- [Docker Local Dev Runbook](../docs/runbooks/docker_local_dev.md) — Docker setup guide
- [LLM Module README](../src/llm/README.md) — LLM module overview
- [Seed Data Framework](../src/db/seeds/README.md) — Seed data documentation

---

## Contributing

When adding new scripts:

1. Place them in the appropriate subdirectory (`db/`, `test/`, etc.)
2. Include a comprehensive docstring with usage examples
3. Use proper exit codes (0 = success, 1 = failure)
4. Document required environment variables
5. Add entry to this README
6. Consider adding a Makefile target for common use cases
