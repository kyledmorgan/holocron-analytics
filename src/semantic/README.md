# Semantic Staging Module

## Overview

The **Semantic Staging** module provides a pipeline for classifying ingested wiki pages and preparing them for promotion into the dimensional model (`dbo.DimEntity`). This is a critical step between raw ingestion and analytics-ready data.

## Purpose

- **Classify pages** by type (character, location, work, event, etc.) using title patterns, content signals, and LLM inference
- **Extract minimal signals** from page content without processing full payloads
- **Stage entities** with promotion states for adjudication workflow
- **Apply tags** for flexible categorization and filtering

## Pipeline Stages

### Stage 0: Title-Only Routing (Rules)

The cheapest and fastest classification method. Uses title patterns to:

- Detect **namespace** from prefix (`User:`, `Module:`, `Forum:`, etc.)
- Detect **continuity hint** from suffix (`/Legends`, `/Canon`)
- Classify **technical pages** (namespaced wiki pages)
- Identify **meta/reference pages** (`Timeline of...`, `List of...`)
- Recognize **time periods** (`19 BBY`, `4 ABY`)

```python
from src.semantic import RulesClassifier

classifier = RulesClassifier()
result = classifier.classify("Module:ArchiveAccess/SW")
# result.primary_type = PageType.TECHNICAL_SITE_PAGE
# result.confidence = 1.0
```

### Stage 1: Signals Extraction (Minimal Peek)

For pages that can't be confidently classified by title alone:

- Extract **lead sentence** (first paragraph)
- Detect **infobox type** (character, planet, etc.)
- Parse **categories** for additional context
- Set **boolean flags** (is_list_page, is_disambiguation, etc.)

```python
from src.semantic import SignalsExtractor

extractor = SignalsExtractor()
signals = extractor.extract(source_page, payload)
# signals.lead_sentence = "Anakin Skywalker was a human male..."
# signals.infobox_type = "Character"
# signals.categories = ["Jedi", "Humans", "Skywalker family"]
```

### Stage 2: LLM Classification (Ollama Local)

For ambiguous pages requiring deeper understanding:

- Uses the existing `llm.job` queue framework
- Interrogation key: `page_classification_v1`
- Input: title, namespace, continuity hint, lead sentence, infobox type, categories
- Output: primary type, secondary types with weights, confidence score, rationale

### Stage 3: Promotion Workflow

Entities flow through promotion states:

| State | Description |
|-------|-------------|
| `staged` | Initial state after classification. Not visible downstream. |
| `candidate` | High-confidence classification ready for adjudication. |
| `adjudicated` | Human-reviewed and confirmed. |
| `promoted` | Fully visible in downstream views/marts. |
| `suppressed` | Intentionally hidden (technical pages, duplicates). |
| `merged` | Merged into another entity. |

## Page Type Taxonomy (v1)

### In-Universe Entities
- `PersonCharacter` - Individual persons/characters
- `LocationPlace` - Planets, regions, buildings
- `Organization` - Factions, governments, corporations
- `Species` - Species or races
- `Technology` - Devices, inventions
- `Vehicle` - Ships, transports
- `Weapon` - Weapons, armaments

### Narrative Elements
- `EventConflict` - Battles, wars, political events
- `Concept` - Abstract ideas, philosophies
- `WorkMedia` - Films, books, games

### Meta/Reference
- `MetaReference` - Lists, timelines, disambiguation
- `TimePeriod` - Specific years/eras (BBY/ABY)

### Technical
- `TechnicalSitePage` - Wiki maintenance pages
- `Unknown` - Cannot determine

## Database Schema

### New Tables (sem schema)

```sql
-- Page identity and provenance
sem.SourcePage (
    source_page_id, source_system, resource_id, variant,
    namespace, continuity_hint, content_hash_sha256,
    latest_ingest_id, source_registry_id, ...
)

-- Extracted signals
sem.PageSignals (
    page_signals_id, source_page_id,
    lead_sentence, infobox_type, categories_json,
    is_list_page, is_disambiguation, has_timeline_markers, ...
)

-- Classification results
sem.PageClassification (
    page_classification_id, source_page_id, taxonomy_version,
    primary_type, type_set_json, confidence_score,
    method, model_name, run_id, evidence_json, ...
)
```

### Extended DimEntity Columns

```sql
-- Promotion state tracking
PromotionState, PromotionDecisionUtc, PromotionDecidedBy, PromotionReason

-- Semantic staging linkage
SourcePageId, PrimaryTypeInferred, TypeSetJsonInferred, AdjudicationRunId
```

### Tag Tables

```sql
dbo.DimTag (TagKey, TagName, TagType, Visibility, ...)
dbo.BridgeTagAssignment (TagKey, TargetType, TargetId, ...)
dbo.BridgeTagRelation (FromTagKey, ToTagKey, RelationType, ...)
```

## CLI Usage

```bash
# Classify a single title
python -m src.semantic.cli classify "Anakin Skywalker"
python -m src.semantic.cli classify "Module:ArchiveAccess/SW"
python -m src.semantic.cli classify "Timeline of galactic history"

# Classify titles from a file
python -m src.semantic.cli batch-classify titles.txt -o results.json

# Show taxonomy
python -m src.semantic.cli taxonomy

# Show promotion states
python -m src.semantic.cli promotion-states
```

## Running with Ollama

For LLM-based classification (Stage 2):

1. Ensure Ollama is running locally:
   ```bash
   ollama serve
   ```

2. Pull a recommended model:
   ```bash
   ollama pull llama3.2
   ```

3. Process pages through the pipeline (future):
   ```bash
   python -m src.semantic.cli process --limit 100
   ```

## Use Case Examples

### Character Page (Anakin Skywalker)

```
Title: Anakin Skywalker
→ Namespace: main
→ Continuity: unknown (no suffix)
→ Signals: lead_sentence mentions "human male", infobox=Character
→ Classification: PersonCharacter (confidence: 0.95)
→ Tags: namespace:main, type:person_character, role:jedi
→ Promotion: candidate
```

### Technical Page (Module)

```
Title: Module:ArchiveAccess/SW
→ Namespace: module
→ Classification: TechnicalSitePage (confidence: 1.0, rules)
→ Tags: namespace:module, type:technical_site_page
→ Promotion: suppressed
```

### Legends Variant

```
Title: Anakin Skywalker/Legends
→ Namespace: main
→ Continuity: legends (from suffix)
→ Classification: PersonCharacter
→ Tags: namespace:main, continuity:legends, type:person_character
→ Creates separate entity from Canon version
```

## Configuration

Environment variables for database connection:

```bash
SEMANTIC_SQLSERVER_HOST=localhost
SEMANTIC_SQLSERVER_PORT=1433
SEMANTIC_SQLSERVER_DATABASE=Holocron
SEMANTIC_SQLSERVER_USER=sa
SEMANTIC_SQLSERVER_PASSWORD=your_password
```

Or use shared ingest settings:

```bash
INGEST_SQLSERVER_HOST=localhost
# etc.
```

## Integration with Existing Systems

### Ingest Module
- Reads from `ingest.IngestRecords` and `ingest.vw_latest_successful_fetch`
- Creates `sem.SourcePage` records linked to `ingest_id`

### LLM Module  
- Uses `llm.job` queue for classification jobs
- Creates `llm.run` records for lineage
- Stores results in `sem.PageClassification` with `run_id` FK

### Dimensional Model
- Creates/updates `dbo.DimEntity` with promotion tracking
- Uses `dbo.DimTag` and `dbo.BridgeTagAssignment` for tagging

## Future Enhancements

- Parallel processing with worker pool
- Incremental reprocessing on content changes
- Confidence thresholds for auto-promotion
- Entity deduplication and merge workflows
- Deep fact extraction (claims/events) from full text
