# Holocron Analytics Ingestion Framework

## Overview

The **Holocron Analytics Ingestion Framework** is a Python-first data ingestion system designed to pull content from public web sources (starting with MediaWiki/Wikipedia) into a local data lake and SQL Server database.

### Key Features

- **Pluggable Connectors**: HTTP and MediaWiki API support out of the box
- **JSON-First Storage**: Store raw payloads as JSON blobs with minimal metadata
- **Crawl State Management**: Track discovered/pending/completed/failed items with resumability
- **Discovery System**: Automatically discover and queue related resources (follow links)
- **Rate Limiting & Retries**: Polite crawling with exponential backoff
- **Local-First**: Runs on local machine with SQLite state store (no cloud required)
- **Future-Friendly**: Designed for easy integration with Airflow/Prefect/Dagster later

---

## Architecture

```
┌─────────────┐
│   CLI       │ 
│ (ingest_cli)│
└──────┬──────┘
       │
       v
┌─────────────────┐
│  IngestRunner   │  ← Orchestrates workflow
└────────┬────────┘
         │
    ┌────┴────┬──────────┬───────────┐
    v         v          v           v
┌────────┐ ┌─────┐  ┌─────────┐ ┌─────────┐
│State   │ │Conn-│  │Storage  │ │Discovery│
│Store   │ │ector│  │Writers  │ │Plugins  │
│(SQLite)│ │(MW) │  │(File/DB)│ │         │
└────────┘ └─────┘  └─────────┘ └─────────┘
```

### Core Components

1. **Core Abstractions** (`src/ingest/core/`)
   - `WorkItem`: Unit of work to be processed
   - `IngestRecord`: Result of an ingestion operation
   - `Connector`: Abstract interface for fetching data
   - `StorageWriter`: Abstract interface for persisting data
   - `StateStore`: Abstract interface for queue management

2. **Connectors** (`src/ingest/connectors/`)
   - `HttpConnector`: Generic HTTP GET/POST with retries
   - `MediaWikiConnector`: MediaWiki API wrapper (pages, links, categories)

3. **Storage** (`src/ingest/storage/`)
   - `FileLakeWriter`: Writes JSON files to data lake (organized by source/type)
   - `SqlServerIngestWriter`: Writes to SQL Server `ingest.IngestRecords` table

4. **State Management** (`src/ingest/state/`)
   - `SqliteStateStore`: SQLite-based work queue with deduplication

5. **Discovery** (`src/ingest/discovery/`)
   - `MediaWikiDiscovery`: Extracts page links and categories for recursive crawling

6. **Runner** (`src/ingest/runner/`)
   - `IngestRunner`: Main orchestrator (dequeue → fetch → store → discover → repeat)

---

## Quick Start

### Prerequisites

- Python 3.11+ (3.12 recommended)
- pip

### Installation

```bash
# Install dependencies
cd src/ingest
pip install -r requirements.txt

# Optional: Install SQL Server support
pip install pyodbc
```

### Configuration

1. Copy the example config:
```bash
cp config/ingest.example.yaml config/ingest.yaml
```

2. Edit `config/ingest.yaml` to customize:
   - Data lake directory
   - Rate limits
   - User agent (required for MediaWiki etiquette)
   - Seed pages to start crawling

### Running

```bash
# Seed the queue with initial pages
python src/ingest/ingest_cli.py --config config/ingest.yaml --seed

# Run the ingestion (process 10 items)
python src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 10

# Run with discovery enabled (will follow links)
python src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 100

# Check queue statistics
python src/ingest/ingest_cli.py --config config/ingest.yaml --stats

# Verbose logging
python src/ingest/ingest_cli.py --config config/ingest.yaml --verbose
```

---

## Configuration Reference

See `config/ingest.example.yaml` for a fully commented example.

### Key Sections

**Storage**:
- `data_lake`: File-based JSON storage
- `sql_server`: Optional SQL Server storage

**State**:
- `type`: State store type (currently only `sqlite`)
- `db_path`: Path to SQLite database

**Runner**:
- `batch_size`: Items to process per batch
- `max_retries`: Retry attempts for failed items
- `enable_discovery`: Enable automatic link discovery

**Sources**:
- List of data sources (MediaWiki, HTTP, etc.)
- Each source has its own connector settings

**Seeds**:
- Initial work items to populate the queue

---

## Data Storage

### File Lake Structure

```
local/data_lake/
├── mediawiki/
│   └── wikipedia/
│       └── page/
│           ├── Star_Wars_20260119_120000_abc12345.json
│           ├── Luke_Skywalker_20260119_120005_def67890.json
│           └── ...
```

Each JSON file contains:
- Full metadata (source, resource ID, timestamps, etc.)
- Complete response payload from the API

### SQL Server Schema

The `ingest.IngestRecords` table stores:
- Metadata columns (source_system, resource_id, status_code, etc.)
- `payload` column (NVARCHAR(MAX)) with full JSON
- Indexes for deduplication and temporal queries

See: `src/db/ddl/00_ingest/002_IngestRecords.sql`

---

## State Management

The SQLite state store (`local/state/ingest_state.db`) tracks:

- **Pending**: Items in the queue waiting to be processed
- **In Progress**: Currently being fetched
- **Completed**: Successfully processed
- **Failed**: Failed after max retries

### Resumability

If the ingestion process stops (crash, Ctrl+C), simply run again:
- Completed items won't be re-fetched (deduplicated)
- Failed items can be retried manually or by resetting their status

---

## Discovery & Crawling

Discovery plugins analyze ingestion results and enqueue new work items.

### MediaWiki Discovery

Configured in `config/ingest.yaml`:

```yaml
discovery:
  enabled: true
  discover_links: true       # Follow page links
  discover_categories: false # Follow categories
  max_depth: 2               # Limit crawl depth
```

**Example Flow**:
1. Seed: "Star Wars" page
2. Fetch page → Store JSON
3. Discover links: "Luke Skywalker", "Han Solo", etc.
4. Enqueue discovered pages (if not already processed)
5. Repeat

---

## Extending the Framework

### Adding a New Connector

1. Create a new class in `src/ingest/connectors/`
2. Inherit from `Connector` abstract class
3. Implement `fetch()` and `get_name()` methods
4. Register in `ingest_cli.py` `build_connectors()`

### Adding a New Storage Writer

1. Create a new class in `src/ingest/storage/`
2. Inherit from `StorageWriter` abstract class
3. Implement `write()` and `get_name()` methods
4. Register in `ingest_cli.py` `build_storage_writers()`

### Adding a New Discovery Plugin

1. Create a new class in `src/ingest/discovery/`
2. Inherit from `Discovery` abstract class
3. Implement `discover()` and `get_name()` methods
4. Register in `ingest_cli.py` `build_discovery_plugins()`

---

## Best Practices

### MediaWiki Etiquette

- Always set a descriptive User-Agent
- Respect rate limits (1+ second between requests)
- Don't overwhelm public APIs
- Read and follow MediaWiki API guidelines

### Storage Management

- **Data Lake**: Files accumulate over time. Implement cleanup/archival as needed.
- **SQL Server**: Consider partitioning or retention policies for large datasets.
- **State Store**: Periodically clean up old completed/failed items.

### Error Handling

- Transient errors (network) are retried automatically
- Permanent errors (404, 403) fail after max retries
- Check logs and queue stats regularly

---

## Roadmap

Future enhancements:

1. **Additional Connectors**:
   - GraphQL APIs
   - RSS/Atom feeds
   - Generic web scraping (BeautifulSoup)

2. **Advanced Discovery**:
   - Breadth-first vs depth-first strategies
   - Priority scoring based on content

3. **Orchestration Integration**:
   - Airflow DAG examples
   - Prefect flow examples
   - Dagster asset definitions

4. **Performance**:
   - Async/concurrent fetching (asyncio)
   - Optional PySpark integration for large-scale processing

5. **Monitoring**:
   - Prometheus metrics export
   - Grafana dashboard templates
   - Health checks and alerting

---

## Troubleshooting

### "No connector found for: mediawiki"

- Check that your source `type` in config matches a registered connector
- Ensure connectors are being built in `ingest_cli.py`

### "Failed to connect to SQL Server"

- Verify connection string or environment variables
- Check that SQL Server is running and accessible
- Ensure the `ingest` schema and `IngestRecords` table exist

### "Work item already exists"

- This is normal (deduplication working)
- If you want to re-fetch, delete or update the state in SQLite

### High memory usage

- Reduce batch size
- Enable pagination in API calls
- Consider streaming large payloads to disk

---

## License

See repository LICENSE file.

---

## Contributing

Contributions welcome! Please:
- Follow existing code style
- Add docstrings and type hints
- Test locally before submitting PR
- Update documentation as needed

---

## Contact

For questions or issues, open a GitHub issue in the repository.
