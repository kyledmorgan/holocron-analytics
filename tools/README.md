# Tools Directory

This directory contains standalone tools and utilities for database initialization and system maintenance. These are foundational tools used by scripts, tests, and Docker entrypoints.

---

## Tools Overview

### `db_init.py`

**Purpose:** Database initialization tool for SQL Server. Applies versioned migration scripts to initialize or update the database schema.

**Key Features:**
- Idempotent migrations (safe to run multiple times)
- Automatic database creation if it doesn't exist
- Version tracking via `SchemaVersion` table
- Dry-run mode for testing
- Connection retry logic with configurable timeout

**Usage:**

```bash
# Initialize database with default migrations directory
python -m tools.db_init

# Specify custom migrations directory
python -m tools.db_init --migrations-dir db/migrations

# Dry-run mode (show what would be executed without making changes)
python -m tools.db_init --dry-run

# Use with Makefile
make db-init
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `INGEST_SQLSERVER_HOST` | `localhost` | SQL Server hostname |
| `INGEST_SQLSERVER_PORT` | `1433` | SQL Server port |
| `INGEST_SQLSERVER_DATABASE` | `Holocron` | Database name |
| `INGEST_SQLSERVER_USER` | `sa` | SQL Server username |
| `INGEST_SQLSERVER_PASSWORD` | *(required)* | SQL Server password |
| `INGEST_SQLSERVER_DRIVER` | `ODBC Driver 18 for SQL Server` | ODBC driver |
| `MSSQL_SA_PASSWORD` | *(fallback)* | Alternative password variable |

**How It Works:**

1. **Connection Check** — Waits for SQL Server to be ready (up to 60 seconds by default)
2. **Database Creation** — Creates the database if it doesn't exist
3. **Schema Version Table** — Creates or validates the `SchemaVersion` tracking table
4. **Migration Discovery** — Scans the migrations directory for `.sql` files
5. **Version Check** — Skips already-applied migrations based on filename version
6. **Execution** — Applies pending migrations in order
7. **Version Tracking** — Records each applied migration with timestamp

**Migration File Naming Convention:**

```
V001__initial_schema.sql
V002__add_indexes.sql
V003__seed_data.sql
```

- Must start with `V` followed by zero-padded version number
- Double underscore `__` separator
- Descriptive name
- `.sql` extension

**Exit Codes:**
- `0`: Success (all migrations applied)
- `1`: Failure (connection error, migration error, or missing password)

**Example Output:**

```
2026-02-02 04:00:00 [INFO] Waiting for SQL Server at localhost:1433...
2026-02-02 04:00:02 [INFO] ✓ SQL Server is ready
2026-02-02 04:00:02 [INFO] Database 'Holocron' exists
2026-02-02 04:00:02 [INFO] SchemaVersion table exists
2026-02-02 04:00:02 [INFO] Found 3 migration files
2026-02-02 04:00:02 [INFO] ✓ V001__initial_schema.sql (already applied)
2026-02-02 04:00:02 [INFO] → V002__add_indexes.sql (applying...)
2026-02-02 04:00:03 [INFO] ✓ V002__add_indexes.sql (applied successfully)
2026-02-02 04:00:03 [INFO] → V003__seed_data.sql (applying...)
2026-02-02 04:00:04 [INFO] ✓ V003__seed_data.sql (applied successfully)
2026-02-02 04:00:04 [INFO] Database initialization complete
```

---

## Dependencies

These tools require the following Python packages:

```bash
pip install pyodbc
```

The `pyodbc` package also requires the ODBC driver to be installed on the system:
- **Windows:** Install "ODBC Driver 18 for SQL Server" from Microsoft
- **Linux:** Follow [Microsoft's ODBC installation guide](https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)
- **macOS:** Use Homebrew or follow Microsoft's guide

---

## Usage in Docker

The `db_init.py` tool is used automatically in the Docker setup:

```yaml
# docker-compose.yml
services:
  init-db:
    build: .
    command: python -m tools.db_init --migrations-dir db/migrations
    depends_on:
      - sqlserver
```

See [Docker Local Dev Runbook](../docs/runbooks/docker_local_dev.md) for more details.

---

## Development

### Adding New Tools

When adding new tools to this directory:

1. Create a descriptive filename (e.g., `backup_restore.py`)
2. Add a comprehensive module docstring with:
   - Purpose
   - Usage examples
   - Environment variables
   - Exit codes
3. Use the `if __name__ == "__main__"` pattern for direct execution
4. Make it importable as a module with `python -m tools.<name>`
5. Include logging with timestamps
6. Handle errors gracefully with clear messages
7. Document in this README

### Code Style

- Use type hints for function signatures
- Include docstrings for all public functions
- Use logging instead of print statements
- Return proper exit codes (0 = success, non-zero = failure)
- Make tools idempotent when possible

---

## Related Documentation

- [Root README](../README.md) — Project overview
- [Makefile](../Makefile) — Development commands (uses db_init)
- [Docker Local Dev Runbook](../docs/runbooks/docker_local_dev.md) — Docker setup
- [DDL Ordering and Manifest](../agents/playbooks/db/ddl_ordering_and_manifest.md) — Migration file organization
- [Scripts README](../scripts/README.md) — Higher-level scripts that may use these tools

---

## Troubleshooting

### "pyodbc module not found"

```bash
pip install pyodbc
```

### "ODBC Driver not found"

Install the ODBC driver for your platform:
- Windows: Download from [Microsoft](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Linux: `sudo apt-get install msodbcsql18` (Ubuntu/Debian)
- macOS: `brew install msodbcsql18`

### "Login failed for user 'sa'"

Check that:
1. `MSSQL_SA_PASSWORD` or `INGEST_SQLSERVER_PASSWORD` is set
2. Password meets SQL Server complexity requirements (8+ chars, mixed case, numbers, symbols)
3. SQL Server container is running: `docker compose ps`

### "Connection timeout"

- Increase timeout: Tools have built-in retry logic (60s default)
- Check SQL Server is running: `docker compose logs sqlserver`
- Verify connection settings in environment variables

---

## Future Tools

Planned tools for this directory:

- `backup_restore.py` — Database backup and restore utilities
- `schema_compare.py` — Compare schemas across environments
- `data_quality_check.py` — Run data quality validations
- `migration_rollback.py` — Rollback migration utilities
