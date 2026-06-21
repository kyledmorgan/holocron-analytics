# Page Classification Taxonomy v1.1 - Expansion Summary

## Overview
This document describes the expansion of the PrimaryType taxonomy for page classification, implemented to reduce "Unknown" classifications and add second-layer metadata for WorkMedia pages.

## Motivation
Analysis showed a material number of pages were being classified as `Unknown` due to:
1. Legitimate meta/reference/list/disambiguation pages that didn't fit existing buckets
2. Taxonomy gaps for vehicles, items/gear, and droids/tech causing the model to default to Unknown

## Changes

### New PrimaryType Values (v1.1)

#### 1. Droid
- **Purpose**: Named droids as individuals OR droid model lines/types
- **Examples**: 
  - "R2-D2" (named droid individual)
  - "R2-series astromech droid" (model line)
  - "Protocol droid" (type/class)
- **Rationale**: Previously, droids were ambiguous between PersonCharacter and ObjectArtifact. This type clarifies the distinction.

#### 2. VehicleCraft
- **Purpose**: Starships, starfighters, shuttles, freighters, battle stations, vehicles with specs/class/manufacturer
- **Examples**:
  - "Millennium Falcon" (named craft)
  - "X-wing starfighter" (model)
  - "Death Star" (battle station)
- **Rationale**: Distinguishes vehicles with technical specifications from general objects.

#### 3. ObjectItem
- **Purpose**: Physical objects: weapons, lightsabers, blasters, armor, helmets, clothing, insignia, gear, relics
- **Examples**:
  - "Anakin's lightsaber"
  - "Clone trooper armor"
  - "Mandalorian helmet"
  - "Jedi robes"
- **Rationale**: Provides a specific category for handheld/worn items vs. vehicles or general artifacts.

#### 4. ReferenceMeta
- **Purpose**: Lists, indexes, timelines, disambiguation, guides, reference aggregations
- **Examples**:
  - "List of Star Wars films"
  - "Timeline of galactic history"
  - "Skywalker (disambiguation)"
- **Rationale**: Meta pages were being misclassified. This type makes their purpose explicit.
- **Note**: Renamed from `MetaReference` for consistency.

### Retained Types

#### ObjectArtifact
- **Status**: Kept for backward compatibility
- **Usage**: Legacy general objects; prefer VehicleCraft or ObjectItem for new classifications

#### Unknown
- **Status**: Renamed from "Other"
- **Usage**: Only when no category applies with any confidence

### WorkMedia Second-Layer Metadata

When `primary_type == "WorkMedia"`, two additional fields are now required:

#### work_medium
- **Values**: film | tv | game | book | comic | reference | episode | short | other | unknown
- **Purpose**: Distinguishes the format/medium of creative works
- **Examples**:
  - "Star Wars (film)" → work_medium: "film"
  - "The Empire Strikes Back" → work_medium: "film"
  - "Knights of the Old Republic" → work_medium: "game"

#### canon_context
- **Values**: canon | legends | both | unknown
- **Purpose**: Indicates whether the work is part of Canon, Legends, both, or unknown
- **Examples**:
  - "The Mandalorian" → canon_context: "canon"
  - "Thrawn Trilogy" → canon_context: "legends"
  - "Star Wars: The Clone Wars" → canon_context: "both" (if it spans continuities)

## Decision Rubric

The prompt now includes a 14-step priority decision order:

1. **ReferenceMeta** - Lists/timelines/disambiguation first
2. **VehicleCraft** - Craft with specs/class/manufacturer
3. **ObjectItem** - Physical objects/gear/weapons
4. **Droid** - Named droids or droid models
5. **PersonCharacter** - Sentient individuals with biography
6. **LocationPlace** - Physical places
7. **Species** - Biological species or groups
8. **Organization** - Groups/governments/militaries
9. **EventConflict** - Battles/wars/missions
10. **WorkMedia** - Films/episodes/novels/comics
11. **TimePeriod** - Eras/ages/periods
12. **Concept** - Abstract ideas/systems
13. **TechnicalSitePage** - Wiki infrastructure
14. **Unknown** - Only if none apply

Each type includes:
- Clear definition (1-2 sentences)
- Strong cues to look for
- Examples (including Legends cases)
- NOT this: explicit exclusions

## Database Schema Changes

### Migration 0022
File: `db/migrations/0022_expand_page_classification_taxonomy.sql`

**New columns on `sem.PageClassification`:**
- `work_medium` NVARCHAR(20) NULL
  - CHECK constraint: film|tv|game|book|comic|reference|episode|short|other|unknown
- `canon_context` NVARCHAR(20) NULL
  - CHECK constraint: canon|legends|both|unknown

**New indexes:**
- `IX_sem_PageClassification_WorkMedium`: Filters by work_medium and canon_context
- `IX_sem_PageClassification_CanonContext`: Filters by canon_context and primary_type

**Note**: The `primary_type` column (NVARCHAR(100)) already accommodates new type names without schema changes. No data migration required.

## Code Changes

### Python Enums
- **File**: `src/semantic/models.py`
- **PageType enum**: Updated with new values
- **New enums**: WorkMedium, CanonContext

### JSON Schema
- **File**: `src/llm/contracts/page_classification_v1_schema.json`
- **primary_type**: Updated enum list
- **work_medium**: Added (nullable)
- **canon_context**: Added (nullable)

### Prompts
- **File**: `src/llm/prompts/page_classification.py`
- **System prompt**: Expanded with 14-step rubric, definitions, examples
- **WorkMedia rules**: Explicit instructions to populate work_medium and canon_context

### Interrogation Definitions
- **File**: `src/llm/interrogations/definitions/page_classification.py`
- **TYPE KEY**: Updated with new types and expanded definitions
- **OUTPUT_SCHEMA**: Updated enum list
- **Validator**: Works with new types dynamically

### Tests
- **Files**: 
  - `tests/unit/llm/test_page_classification_prompts.py`
  - `tests/unit/llm/test_interrogation_registry.py`
- **Coverage**: All new types validated
- **Status**: 50/50 tests passing

## Expected Impact

### Before (v1.0)
- High Unknown rate for vehicles, items, droids, and meta pages
- Ambiguous classification for droids (PersonCharacter vs ObjectArtifact)
- No distinction between different WorkMedia types

### After (v1.1)
- Explicit types for vehicles (VehicleCraft), items (ObjectItem), and droids (Droid)
- Clear category for meta/reference pages (ReferenceMeta)
- WorkMedia pages now tagged with medium and canon context
- 14-step decision rubric reduces ambiguity
- Unknown classifications should be materially reduced

## Backward Compatibility

- **ObjectArtifact**: Retained for backward compatibility; existing classifications remain valid
- **No data migration**: Existing data continues to work
- **Old types removed**: Technology, Vehicle, Weapon (never used in production)
- **Renamed**: MetaReference → ReferenceMeta, Other → Unknown

## Usage Examples

### Classification Examples

```python
# Droid classification
{
  "primary_type": "Droid",
  "confidence": 0.95,
  "rationale": "R2-D2 is a named astromech droid individual"
}

# VehicleCraft classification
{
  "primary_type": "VehicleCraft",
  "confidence": 0.92,
  "rationale": "Millennium Falcon is a named YT-1300 light freighter with technical specs"
}

# ObjectItem classification
{
  "primary_type": "ObjectItem",
  "confidence": 0.90,
  "rationale": "Anakin's lightsaber is a physical weapon wielded by multiple characters"
}

# WorkMedia with metadata
{
  "primary_type": "WorkMedia",
  "work_medium": "film",
  "canon_context": "canon",
  "confidence": 0.98,
  "rationale": "The Mandalorian is a Disney+ series in the Canon timeline"
}

# ReferenceMeta classification
{
  "primary_type": "ReferenceMeta",
  "confidence": 0.85,
  "rationale": "List of Star Wars films is a reference aggregation page"
}
```

## Migration Path

1. **Apply SQL migration**: Run `0022_expand_page_classification_taxonomy.sql`
2. **Deploy code**: Update all classification services
3. **Re-run classifications**: Re-classify pages that were previously Unknown
4. **Monitor**: Track reduction in Unknown classifications
5. **Validate**: Ensure WorkMedia pages have work_medium and canon_context populated

## Related Files

- `src/semantic/models.py` - Data models and enums
- `src/llm/contracts/page_classification_v1_schema.json` - JSON schema
- `src/llm/prompts/page_classification.py` - System prompt and rubric
- `src/llm/interrogations/definitions/page_classification.py` - Interrogation definition
- `src/sem_staging/dry_run_page_classification.py` - Dry run script
- `db/migrations/0022_expand_page_classification_taxonomy.sql` - Database migration
- `tests/unit/llm/test_page_classification_prompts.py` - Prompt tests
- `tests/unit/llm/test_interrogation_registry.py` - Registry tests

## Version History

- **v1.0**: Initial taxonomy with 9 types
- **v1.1**: Expanded taxonomy with 15 types + WorkMedia metadata (this document)

## Future Considerations

1. **TechnologySystem**: Optional type for system-level or technical concept pages not best represented as ObjectItem/VehicleCraft. Currently handled by Concept type.
2. **Performance monitoring**: Track classification accuracy and Unknown rate over time
3. **Feedback loop**: Collect examples of misclassifications to refine rubric
4. **Additional metadata**: Consider other second-layer metadata for other types (e.g., time period for EventConflict)
