# Quick Start Guide - Ingestion Framework

## 5-Minute Tutorial

### Step 1: Install Dependencies

```bash
cd /home/runner/work/holocron-analytics/holocron-analytics
pip install -r src/ingest/requirements.txt
```

### Step 2: Create Config

```bash
# Copy example config
cp config/ingest.example.yaml config/ingest.yaml

# Edit if needed (the defaults work out of the box)
# nano config/ingest.yaml
```

### Step 3: Seed the Queue

```bash
# Add initial pages to the queue
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --seed
```

Expected output:
```
INFO Configuration loaded
INFO Building components...
INFO Seeding queue...
INFO Seeded 3 items
```

### Step 4: Check Queue Status

```bash
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --stats
```

Expected output:
```
INFO Queue statistics:
INFO   Queue: {'pending': 3}
```

### Step 5: Run Ingestion (Dry Run - Limited Items)

```bash
# Process just 3 items to test
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 3
```

Expected output:
```
INFO Starting ingestion run: <run-id>
INFO Processing batch of 3 items
INFO Processing: mediawiki:wikipedia:page:Star Wars
INFO Successfully processed: Star Wars
INFO Processing: mediawiki:wikipedia:page:The Empire Strikes Back
INFO Successfully processed: The Empire Strikes Back
INFO Processing: mediawiki:wikipedia:page:Return of the Jedi
INFO Successfully processed: Return of the Jedi
INFO Run complete!
```

### Step 6: Check the Results

```bash
# List the data lake directory
ls -R local/data_lake/

# View a specific file
cat local/data_lake/mediawiki/wikipedia/page/Star_Wars_*.json | python3 -m json.tool | head -50
```

### Step 7: Inspect State Database

```bash
# Use Azure Data Studio or SQL Server Management Studio to inspect
# Or use pyodbc/sqlcmd from command line:

# Example with sqlcmd (if installed):
sqlcmd -S localhost -U sa -P "YourPassword" -d Holocron -Q "SELECT source_name, resource_type, resource_id, status FROM ingest.work_items ORDER BY created_at DESC;"

# Or via Python:
python scripts/sqlserver_state_admin.py
```

---

## What Just Happened?

1. **Seeding**: Added 3 Wikipedia pages to the work queue
2. **Processing**: Fetched each page via MediaWiki API
3. **Storage**: Saved raw JSON payloads to `local/data_lake/`
4. **Discovery**: Extracted links from each page (if enabled)
5. **State Tracking**: Updated SQL Server database with completion status

---

## Next Steps

### Enable Discovery (Crawl More Pages)

Edit `config/ingest.yaml`:
```yaml
runner:
  enable_discovery: true

sources:
  - name: "wikipedia"
    discovery:
      enabled: true
      discover_links: true
      max_depth: 2
```

Then run:
```bash
# Process up to 50 items (will discover and follow links)
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 50
```

### Add More Seeds

Edit `config/ingest.yaml`:
```yaml
seeds:
  - source: "wikipedia"
    resource_type: "page"
    titles:
      - "Star Wars"
      - "Luke Skywalker"
      - "Darth Vader"
      - "Millennium Falcon"
      - "Tatooine"
    priority: 10
```

Then seed again:
```bash
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --seed
```

### Enable SQL Server Storage

1. Ensure SQL Server is running
2. Run the schema creation script:
```bash
# Execute the DDL files
sqlcmd -S localhost,1434 -U sa -P YourPassword -d Holocron -i src/db/ddl/00_ingest/001_schema.sql
sqlcmd -S localhost,1434 -U sa -P YourPassword -d Holocron -i src/db/ddl/00_ingest/002_IngestRecords.sql
```

3. Update `config/ingest.yaml`:
```yaml
storage:
  sql_server:
    enabled: true
    host: localhost
    port: 1434
    database: Holocron
    user: sa
    # Set password via environment variable
    # password: ${INGEST_SQLSERVER_PASSWORD}
```

4. Set environment variable:
```bash
export INGEST_SQLSERVER_PASSWORD="YourPassword"
```

5. Run ingestion:
```bash
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 10
```

---

## Monitoring & Debugging

### View Logs

All operations are logged to stdout. For detailed debugging:
```bash
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 5 --verbose
```

### Check Queue Stats

```bash
# Real-time queue statistics
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --stats
```

### Inspect Failed Items

```sql
-- Use SQL Server client or Azure Data Studio
SELECT resource_id, status, error_message 
FROM ingest.work_items 
WHERE status = 'failed'
ORDER BY updated_at DESC;
```

### Reset a Failed Item

```sql
-- Use SQL Server client or Azure Data Studio
UPDATE ingest.work_items 
SET status = 'pending', 
    error_message = NULL,
    attempt = 0,
    updated_at = GETUTCDATE()
WHERE resource_id = 'SomeFailedPage';
```

See `scripts/sqlserver_state_admin.py` for helper functions and more examples.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'ingest'"

Make sure you're running from the repository root:
```bash
cd /home/runner/work/holocron-analytics/holocron-analytics
python3 src/ingest/ingest_cli.py ...
```

### "No such file or directory: config/ingest.yaml"

Copy the example config first:
```bash
cp config/ingest.example.yaml config/ingest.yaml
```

### Rate Limiting / HTTP 429

MediaWiki servers may rate limit. Increase the delay in config:
```yaml
sources:
  - name: "wikipedia"
    rate_limit_delay: 2.0  # 2 seconds between requests
```

---

## Summary

You've now:
- ✅ Set up the ingestion framework
- ✅ Configured sources and seeds
- ✅ Run your first ingestion
- ✅ Stored JSON data in the data lake
- ✅ Tracked state in SQL Server

Next, explore the full [README](README.md) for advanced features!
