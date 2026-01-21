# OpenAlex Integration Guide

## Overview

OpenAlex is a free and open catalog of the world's scholarly literature. This integration adds OpenAlex as an ingestion source to the Holocron Analytics framework, enabling controlled discovery and ingestion of academic works and their citation networks.

## Features

### ✅ What's Included

- **OpenAlex API Connector**: HTTP-based connector with polite pool support
- **Reference Discovery**: Automatically discover and follow citations from works
- **Entity Matching**: Control expansion by matching works against known entities
- **Depth Control**: Limit citation traversal to prevent unbounded expansion
- **Deduplication**: Automatic deduplication by OpenAlex ID and DOI
- **Data Lake Storage**: Stores raw API responses in the same format as other sources

### 🎯 Key Capabilities

1. **Fetch by ID**: Retrieve specific works by OpenAlex ID or DOI
2. **Search & Discover**: Execute searches and seed from results
3. **Citation Mining**: Extract and follow referenced works
4. **Controlled Expansion**: Only enqueue works matching known entities
5. **Polite Pool Access**: Optionally use email for faster API responses

## Quick Start

### 1. Basic Configuration

Create or update `config/ingest.yaml`:

```yaml
sources:
  - name: "openalex"
    type: "openalex"
    email: "your-email@example.com"  # Optional, for polite pool
    rate_limit_delay: 0.1             # 10 req/sec
    
    discovery:
      enabled: true
      discover_references: true
      max_depth: 1
    
    entity_matching:
      entities:
        - "Machine Learning"
        - "Artificial Intelligence"
      case_sensitive: false

seeds:
  - source: "openalex"
    resource_type: "work"
    work_ids:
      - "W2741809807"
    priority: 10
```

### 2. Seed the Queue

```bash
cd /home/runner/work/holocron-analytics/holocron-analytics
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --seed
```

### 3. Run Ingestion

```bash
# Process 10 works
python3 src/ingest/ingest_cli.py --config config/ingest.yaml --max-items 10
```

### 4. Check Results

```bash
# View data lake structure
ls -R local/data_lake/openalex/

# Inspect a work
cat local/data_lake/openalex/openalex/work/*.json | python3 -m json.tool | head -100
```

## Configuration Reference

### Source Configuration

```yaml
sources:
  - name: "openalex"
    type: "openalex"
    
    # API settings
    email: "your-email@example.com"  # Optional: enables polite pool
    rate_limit_delay: 0.1             # Seconds between requests
    timeout: 30                       # Request timeout
    max_retries: 3                    # Retry failed requests
    
    # Discovery settings
    discovery:
      enabled: true
      discover_references: true       # Follow citations
      discover_related: false         # Related works (future)
      max_depth: 1                    # Citation depth limit
    
    # Entity matching (prevents drift)
    entity_matching:
      entities:
        - "Topic 1"
        - "Topic 2"
      identifiers:
        doi: []
        openalex_id: []
      case_sensitive: false
```

### Seed Definitions

#### Seed by Work ID

```yaml
seeds:
  - source: "openalex"
    resource_type: "work"
    work_ids:
      - "W2741809807"
      - "W1234567890"
    priority: 10
```

#### Seed by DOI

```yaml
seeds:
  - source: "openalex"
    resource_type: "work"
    dois:
      - "10.1038/nature.2016.20657"
      - "10.1126/science.aaa1234"
    priority: 10
```

#### Seed by Search

```yaml
seeds:
  - source: "openalex"
    resource_type: "search"
    search_query: "machine learning"
    filters:
      - "type:article"
      - "is_oa:true"
      - "publication_year:>2020"
      - "cited_by_count:>50"
    per_page: 25
    priority: 20
```

## How It Works

### 1. Work Item Flow

```
Seed Work → Fetch from OpenAlex API → Store in Data Lake
                ↓
        Extract References → Filter by Entity Match → Enqueue if:
                                                        - Within max_depth
                                                        - Matches known entity
                                                        - Not already processed
```

### 2. Entity Matching

The entity matcher prevents "six degrees of Kevin Bacon" drift by only enqueuing works that match known entities:

- **Title matching**: Checks if work title contains entity names
- **Identifier matching**: Checks DOI or OpenAlex ID against known IDs
- **Concept matching**: Checks OpenAlex concepts/topics against entities

### 3. Depth Control

```
Depth 0: Seed works (manually configured)
Depth 1: Works cited by seeds
Depth 2: Works cited by depth-1 works (if max_depth >= 2)
```

### 4. Deduplication

Works are deduplicated using the standard framework mechanism:

```
dedupe_key = f"openalex:openalex:work:{openalex_id}"
```

This ensures:
- No duplicate fetches
- No duplicate storage
- No infinite loops in citation graphs

## Data Lake Structure

OpenAlex data is stored following the existing pattern:

```
local/data_lake/
└── openalex/
    └── openalex/
        └── work/
            ├── W2741809807_20260119_143022_a1b2c3d4.json
            ├── W1234567890_20260119_143025_e5f6g7h8.json
            └── ...
```

Each JSON file contains:

```json
{
  "ingest_id": "uuid",
  "source_system": "openalex",
  "source_name": "openalex",
  "resource_type": "work",
  "resource_id": "W2741809807",
  "request_uri": "https://api.openalex.org/works/W2741809807",
  "request_method": "GET",
  "request_headers": {...},
  "status_code": 200,
  "response_headers": {...},
  "fetched_at_utc": "2026-01-19T14:30:22Z",
  "hash_sha256": "...",
  "run_id": "...",
  "work_item_id": "...",
  "attempt": 1,
  "duration_ms": 234,
  "payload": {
    // Raw OpenAlex API response
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/...",
    "title": "...",
    "publication_year": 2020,
    "referenced_works": [...],
    "concepts": [...],
    // ... full OpenAlex work metadata
  }
}
```

## Advanced Usage

### Custom Entity Lists

Load entities from a file or database:

```python
from ingest.discovery import EntityMatcher

# From config
matcher = EntityMatcher.from_config({
    "entities": ["Topic 1", "Topic 2"],
    "identifiers": {
        "doi": ["10.1234/example"],
    },
})

# Add entities at runtime
matcher.add_entity("New Topic")
matcher.add_identifier("openalex_id", "W1234567890")
```

### Programmatic Seeding

```python
from ingest.core.models import WorkItem
from ingest.runner import IngestRunner

# Create work item
work_item = WorkItem(
    source_system="openalex",
    source_name="openalex",
    resource_type="work",
    resource_id="W2741809807",
    request_uri="https://api.openalex.org/works/W2741809807",
    priority=10,
    metadata={"depth": 0},
)

# Seed
runner.seed_queue([work_item])
```

## Polite Pool vs Regular API

OpenAlex offers two access tiers:

### Regular API (no email)
- Rate limit: 10 requests/second
- No special configuration needed
- Good for testing and small jobs

### Polite Pool (with email)
- Rate limit: 100 requests/second
- Faster response times
- Better for production workloads
- Configure via `email` parameter

```yaml
sources:
  - name: "openalex"
    type: "openalex"
    email: "your-email@example.com"  # Enables polite pool
```

## Troubleshooting

### Rate Limiting

If you see 429 errors:

```yaml
sources:
  - name: "openalex"
    rate_limit_delay: 0.2  # Slow down to 5 req/sec
```

### Too Many Works Discovered

Reduce max_depth or tighten entity matching:

```yaml
discovery:
  max_depth: 0  # Only process seeds, no discovery

entity_matching:
  entities:
    - "Very Specific Topic"  # More restrictive
```

### Works Not Matching Entities

Check if entity names match work metadata:

```python
# Debug entity matching
from ingest.discovery import EntityMatcher

matcher = EntityMatcher(known_entities=["Machine Learning"])
result = matcher.matches_entity(
    title="Deep Learning for NLP",
    concepts=["Natural Language Processing"],
)
print(result)  # False - doesn't contain "Machine Learning"

# Fix: Add more entity variations
matcher.add_entity("Deep Learning")
matcher.add_entity("Natural Language Processing")
```

## Architecture Notes

### Non-Breaking Design

The OpenAlex integration is purely additive:

- ✅ No changes to existing models
- ✅ No changes to IngestRunner
- ✅ No changes to state store
- ✅ No changes to file lake writer
- ✅ Uses existing connector interface
- ✅ Uses existing discovery interface

### Extension Points

Future enhancements can add:

1. **Related works discovery**: When OpenAlex adds this feature
2. **Author-based seeding**: Seed works by author ID
3. **Institution filtering**: Filter by institution
4. **Database entity matching**: Query entities from DIM tables
5. **PDF download**: Download open-access PDFs with license awareness
6. **Citation graph analysis**: Build citation networks

## API References

- [OpenAlex API Documentation](https://docs.openalex.org/)
- [OpenAlex Works Endpoint](https://docs.openalex.org/api-entities/works)
- [OpenAlex Search Filters](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/filter-entity-lists)

## See Also

- [Framework README](../src/ingest/README.md)
- [Quick Start Guide](../src/ingest/QUICKSTART.md)
- [Configuration Example](../config/ingest.openalex.example.yaml)
