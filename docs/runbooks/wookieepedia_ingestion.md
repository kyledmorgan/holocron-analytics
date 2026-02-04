# Wookieepedia Ingestion Runbook

## Overview

This runbook covers running the MediaWiki ingestion pipeline for Wookieepedia (Star Wars wiki) data.

## Prerequisites

- Python environment configured
- SQL Server running (via Docker Compose)
- SQL Server state store configured (see `.env.example`)
- Configuration file at `config/ingest.example.yaml` or custom config

## Running Ingestion

### Process from Existing Queue

Run ingestion on items already in the SQL Server queue:

```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --max-items 10000 --verbose
```

**Parameters:**
- `--config`: Path to configuration YAML file
- `--max-items`: Maximum number of items to process (e.g., 10000)
- `--verbose` or `-v`: Enable debug logging

### Seed New Items First

To add new seed pages before processing:

```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --seed --max-items 10000 --verbose
```

**Parameters:**
- `--seed`: Add seed items from config before processing

### Check Queue Statistics

View current queue status without processing:

```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --stats
```

## Configuration

The Wookieepedia source is configured in `config/ingest.example.yaml`:

```yaml
sources:
  - name: "wookieepedia"
    type: "mediawiki"
    api_url: "https://starwars.fandom.com/api.php"
    rate_limit_delay: 1.0
    timeout: 30
    max_retries: 3
    
    discovery:
      enabled: true
      discover_links: true
      max_depth: 3

seeds:
  - source: "wookieepedia"
    resource_type: "page"
    titles:
      - "Luke Skywalker"
      - "Darth Vader"
      - "Yoda"
      - "Obi-Wan Kenobi"
      - "Han Solo"
    priority: 10
```

## Output Locations

### Data Lake
Raw API responses stored at:
```
local/data_lake/mediawiki/wookieepedia/page/
```

### State Database
Processing state tracked at:
```
local/state/ingest_state.db
```

## Common Patterns

### Small Test Run
```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --max-items 10
```

### Medium Batch
```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --max-items 100
```

### Large Production Run
```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --max-items 10000 --verbose
```

### Resume Interrupted Run
The runner automatically resumes from the queue - just run the command again:
```powershell
python src/ingest/ingest_cli.py --config config/ingest.example.yaml --max-items 10000
```

## Monitoring

### Check Progress
Monitor the terminal output for:
- Items processed count
- Success/failure rates
- Discovered links
- Error messages

### Verify Results
```powershell
# Count files in data lake
Get-ChildItem -Path "local/data_lake/mediawiki/wookieepedia/page" -Recurse -File | Measure-Object

# View recent file
Get-ChildItem -Path "local/data_lake/mediawiki/wookieepedia/page" -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

## Troubleshooting

### Rate Limiting
If hitting rate limits, increase `rate_limit_delay` in config:
```yaml
rate_limit_delay: 2.0  # Slow down to every 2 seconds
```

### Connection Timeouts
Increase timeout value:
```yaml
timeout: 60  # 60 second timeout
```

### Queue Exhausted
Add more seeds or check discovery settings:
```yaml
discovery:
  enabled: true
  discover_links: true
  max_depth: 3  # Increase depth
```

## See Also

- [Ingestion Framework README](../../src/ingest/README.md)
- [Quick Start Guide](../../src/ingest/QUICKSTART.md)
- [Configuration Example](../../config/ingest.example.yaml)
- [Docker Local Dev](docker_local_dev.md)
