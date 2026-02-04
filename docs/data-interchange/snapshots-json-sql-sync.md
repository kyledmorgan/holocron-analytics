# Snapshot / Replay / Sync: JSON ⇄ SQL Data Interchange

This document describes the snapshot mechanism for portable, replayable data interchange between JSON files and SQL Server.

## Overview

The snapshot system provides a **replayable, portable data interchange layer** that enables:

1. **Ingest from previously-captured JSON** without re-calling external APIs
2. **Export from SQL to JSON** and **import JSON to SQL** with incremental delta sync
3. **Machine-to-machine migration**, truncate/rebuild, and cold storage
4. **Bidirectional reconciliation** using stable content hashes

### Key Concepts

- **ExchangeRecord**: Universal envelope format for any data exchange (HTTP, MediaWiki, OpenAlex, LLM, etc.)
- **Snapshot Pack**: Human-browsable directory structure containing NDJSON files and index
- **Content Hash**: SHA256 over canonicalized content for deduplication and change detection
- **Sync Engine**: Bidirectional delta reconciliation with conflict resolution

## ExchangeRecord Envelope

The `ExchangeRecord` is the portable unit that can be stored as JSON and mirrored in SQL.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `exchange_id` | UUID | Unique identifier for this record |
| `exchange_type` | string | Type: `http`, `mediawiki`, `openalex`, `llm`, `file`, etc. |
| `source_system` | string | System identifier: `wookieepedia`, `openalex`, `local_llm` |
| `entity_type` | string | Entity type: `page`, `work`, `completion` |
| `natural_key` | string? | Stable identifier if available (page_id, DOI) |
| `request` | object? | Request payload, URL, headers, params, prompt |
| `response` | any? | Response payload (JSON/text) plus metadata |
| `observed_at_utc` | ISO timestamp | When the data was observed |
| `provenance` | object? | Runner name, host, git SHA, connector version |
| `content_sha256` | string | SHA256 over canonicalized hash input |
| `schema_version` | int | Version of envelope schema |
| `tags` | array | Optional categorization tags |
| `redactions_applied` | array | List of redaction rules applied |

### Content Hashing

The `content_sha256` is computed over the **canonical JSON representation** of:

- `exchange_type`
- `source_system`
- `entity_type`
- `natural_key`
- `request`
- `response`

**Note**: `observed_at_utc` is explicitly excluded from the hash to allow re-fetching the same content without hash collision.

Canonicalization ensures:
- Keys sorted recursively at all levels
- Unicode normalized (NFC form)
- No insignificant whitespace
- Consistent null/boolean handling

## File System Layout

Snapshot packs use a human-browsable directory structure:

```
data/snapshots/
└── my-dataset/
    ├── manifest.json          # Dataset configuration
    ├── index.jsonl            # Hash + key lookup index
    └── records/
        └── 2024/
            └── 2024-01-15/
                ├── chunk-0001.ndjson
                └── chunk-0002.ndjson
```

### Manifest

The `manifest.json` defines dataset mapping and policies:

```json
{
  "dataset_name": "wookieepedia-pages",
  "description": "Star Wars wiki page snapshots",
  "owner": "data-team",
  "exchange_type": "mediawiki",
  "source_system": "wookieepedia",
  "entity_type": "page",
  "sql_target": {
    "schema": "lake",
    "table": "RawExchangeRecord",
    "natural_key_column": "natural_key",
    "hash_column": "content_sha256"
  },
  "sync_policy": {
    "direction_default": "bidirectional",
    "conflict_strategy": "prefer_newest"
  },
  "redaction_policy": {
    "enabled": true,
    "headers_to_redact": ["authorization", "cookie", "x-api-key"]
  },
  "encryption_policy": {
    "enabled": false,
    "algorithm": "aes-256-gcm",
    "key_source": "env"
  }
}
```

### Index

The `index.jsonl` provides fast lookup without scanning all NDJSON files:

```jsonl
{"h":"abc123...","k":"wookieepedia|page|Luke_Skywalker","id":"uuid-1","t":"2024-01-15T10:30:00Z","f":"records/2024/2024-01-15/chunk-0001.ndjson"}
{"h":"def456...","k":"wookieepedia|page|Darth_Vader","id":"uuid-2","t":"2024-01-15T10:31:00Z","f":"records/2024/2024-01-15/chunk-0001.ndjson"}
```

## SQL Mirror Table

Records are mirrored in SQL Server in the `lake.RawExchangeRecord` table:

```sql
CREATE TABLE lake.RawExchangeRecord (
    exchange_id UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    exchange_type NVARCHAR(50) NOT NULL,
    source_system NVARCHAR(100) NOT NULL,
    entity_type NVARCHAR(100) NOT NULL,
    natural_key NVARCHAR(500) NULL,
    observed_at_utc DATETIME2 NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    payload_json NVARCHAR(MAX) NOT NULL,
    schema_version INT NOT NULL DEFAULT 1,
    created_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- Indexes for fast delta sync
CREATE UNIQUE INDEX IX_RawExchangeRecord_ContentHash 
    ON lake.RawExchangeRecord (content_sha256);
CREATE INDEX IX_RawExchangeRecord_NaturalKey 
    ON lake.RawExchangeRecord (source_system, entity_type, natural_key)
    WHERE natural_key IS NOT NULL;
```

## CLI Commands

### Initialize a New Dataset

```bash
python snapshot_cli.py init \
    --name wookieepedia-pages \
    --source wookieepedia \
    --entity page \
    --type mediawiki \
    --description "Wookieepedia page snapshots" \
    --out data/snapshots/
```

### Import JSON to SQL

Import records from a snapshot into SQL Server:

```bash
# Dry run to see what would be imported
python snapshot_cli.py import \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --dry-run

# Actual import
python snapshot_cli.py import \
    --manifest data/snapshots/wookieepedia-pages/manifest.json

# With specific conflict strategy
python snapshot_cli.py import \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --conflict prefer_newest
```

### Export SQL to JSON

Export records from SQL to a snapshot:

```bash
python snapshot_cli.py export \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --dry-run
```

### Bidirectional Sync

Full reconciliation between JSON and SQL:

```bash
# Default bidirectional sync
python snapshot_cli.py sync \
    --manifest data/snapshots/wookieepedia-pages/manifest.json

# Specific direction
python snapshot_cli.py sync \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --direction json_to_sql

# With JSON output for automation
python snapshot_cli.py sync \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --json
```

### Pack for Cold Storage

Create a compressed archive for backup/migration:

```bash
# Plain zip
python snapshot_cli.py pack \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --out backups/wookieepedia-2024-01.zip

# With encryption (requires SNAPSHOT_ENCRYPTION_KEY env var)
python snapshot_cli.py pack \
    --manifest data/snapshots/wookieepedia-pages/manifest.json \
    --out backups/wookieepedia-2024-01.zip \
    --encrypt
```

### Unpack Archive

Extract a snapshot archive:

```bash
python snapshot_cli.py unpack \
    --in backups/wookieepedia-2024-01.zip \
    --out data/snapshots/
```

## Common Workflows

### Truncate and Rebuild from Snapshot

1. Export current SQL data to snapshot (backup):
   ```bash
   python snapshot_cli.py export \
       --manifest data/snapshots/backup/manifest.json
   ```

2. Truncate SQL table:
   ```sql
   TRUNCATE TABLE lake.RawExchangeRecord;
   ```

3. Import from snapshot:
   ```bash
   python snapshot_cli.py import \
       --manifest data/snapshots/backup/manifest.json
   ```

### Migrate to New Machine

1. Pack the snapshot on the source machine:
   ```bash
   python snapshot_cli.py pack \
       --manifest data/snapshots/my-dataset/manifest.json \
       --out migration-pack.zip
   ```

2. Transfer `migration-pack.zip` to the new machine

3. Unpack on the target machine:
   ```bash
   python snapshot_cli.py unpack \
       --in migration-pack.zip \
       --out data/snapshots/
   ```

4. Import to SQL:
   ```bash
   python snapshot_cli.py import \
       --manifest data/snapshots/my-dataset/manifest.json
   ```

### Offline Replay

To replay ingestion without network access:

1. Ensure you have a snapshot of previously-captured data
2. Import directly to SQL:
   ```bash
   python snapshot_cli.py import \
       --manifest data/snapshots/my-dataset/manifest.json
   ```

No outbound network calls are made - all data comes from local JSON files.

### Cold Storage / Archival

For long-term storage:

```bash
# Create encrypted archive
export SNAPSHOT_ENCRYPTION_KEY="your-secure-key"
python snapshot_cli.py pack \
    --manifest data/snapshots/my-dataset/manifest.json \
    --out archive/my-dataset-$(date +%Y%m%d).zip \
    --encrypt

# Move to cold storage
mv archive/my-dataset-*.zip.enc /path/to/cold-storage/
```

## Conflict Resolution

When a record exists with the same natural key but different content hash:

| Strategy | Behavior |
|----------|----------|
| `prefer_newest` | Keep the record with the more recent `observed_at_utc` |
| `prefer_sql` | Keep the SQL record, skip JSON import |
| `prefer_json` | Overwrite SQL with JSON record |
| `fail` | Abort import with error |

Conflicts are always logged in the sync report.

## Reconciliation Report

The sync report provides:

```
Sync Report (bidirectional)
  Dry run: False
  Duration: 2.3s

  JSON → SQL:
    Inserted: 150
    Updated: 12
    Skipped: 1000

  SQL → JSON:
    Inserted: 25
    Skipped: 1137

  Conflicts: 3
  Errors: 0

  JSON records: 1162
  SQL records: 1187
```

Use `--json` flag for machine-readable output.

## Security Considerations

### Redaction

The redaction system automatically scrubs sensitive data:

- **Headers**: Authorization, Cookie, API keys, tokens
- **Payloads**: JWT tokens, AWS keys, generic secrets (best-effort patterns)

Configure in manifest:
```json
{
  "redaction_policy": {
    "enabled": true,
    "headers_to_redact": ["authorization", "cookie", "x-api-key"],
    "patterns": ["custom-secret-pattern"]
  }
}
```

### Encryption

For sensitive datasets, enable encryption:

1. Set encryption key via environment:
   ```bash
   export SNAPSHOT_ENCRYPTION_KEY="32-byte-key-for-aes-256"
   ```

2. Enable in manifest or use `--encrypt` flag

**Never** hardcode encryption keys. Use:
- Environment variables
- Key files (with proper permissions)
- Runtime prompts for interactive use

### Provenance

Every record includes provenance fields:
- `runner_name`: Which process created the record
- `host`: Machine hostname
- `git_sha`: Git commit if available
- `connector_version`: Connector version

This enables audit trails and lineage tracking.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `INGEST_SQLSERVER_CONN_STR` | Full SQL Server connection string |
| `INGEST_SQLSERVER_HOST` | SQL Server hostname |
| `INGEST_SQLSERVER_PORT` | SQL Server port (default: 1434) |
| `INGEST_SQLSERVER_DATABASE` | Database name |
| `INGEST_SQLSERVER_USER` | Database user |
| `INGEST_SQLSERVER_PASSWORD` | Database password |
| `INGEST_SQLSERVER_DRIVER` | ODBC driver name |
| `SNAPSHOT_ENCRYPTION_KEY` | Encryption key for pack/unpack |

## Troubleshooting

### "Manifest not found"

Ensure the manifest.json exists at the specified path. Use `init` command to create a new dataset.

### "Failed to connect to SQL Server"

Check:
1. SQL Server is running
2. Connection string or discrete env vars are set
3. Network connectivity to the server
4. ODBC driver is installed

### Hash Mismatch After Round-Trip

If hashes don't match after export/import:
1. Check for floating-point precision issues
2. Verify unicode normalization is consistent
3. Check for JSON serialization differences

### Conflict Resolution Not Working

Ensure `observed_at_utc` is set on records - `prefer_newest` requires timestamps to compare.

## API Usage

For programmatic access:

```python
from ingest.snapshot import (
    ExchangeRecord,
    SnapshotManifest,
    SnapshotWriter,
    SnapshotReader,
    SyncEngine,
    SyncDirection,
    ConflictStrategy,
)

# Create records
record = ExchangeRecord.create(
    exchange_type="http",
    source_system="my-api",
    entity_type="response",
    natural_key="endpoint-123",
    request={"url": "https://api.example.com/data"},
    response={"result": "success"},
)

# Write to snapshot
manifest = SnapshotManifest.create_default(
    dataset_name="my-dataset",
    exchange_type="http",
    source_system="my-api",
    entity_type="response",
)

writer = SnapshotWriter(
    base_dir=Path("data/snapshots"),
    manifest=manifest,
)
writer.write(record)
writer.close()

# Read from snapshot
reader = SnapshotReader(Path("data/snapshots/my-dataset"))
for record in reader.read_all():
    print(record.content_sha256)
```

## Files Created/Modified

| Path | Description |
|------|-------------|
| `src/ingest/snapshot/` | Snapshot module package |
| `src/ingest/snapshot/models.py` | ExchangeRecord and Provenance models |
| `src/ingest/snapshot/canonical.py` | Canonical JSON serialization and hashing |
| `src/ingest/snapshot/manifest.py` | Manifest handling |
| `src/ingest/snapshot/file_snapshot.py` | NDJSON file read/write |
| `src/ingest/snapshot/index.py` | Index management |
| `src/ingest/snapshot/sql_mirror.py` | SQL Server operations |
| `src/ingest/snapshot/sync_engine.py` | Bidirectional sync logic |
| `src/ingest/snapshot/redaction.py` | Sensitive data scrubbing |
| `src/ingest/snapshot/pack.py` | Pack/unpack for cold storage |
| `src/ingest/snapshot_cli.py` | CLI entry point |
| `src/db/ddl/00_ingest/003_RawExchangeRecord.sql` | SQL table DDL |
| `src/ingest/tests/test_snapshot_*.py` | Unit tests |
