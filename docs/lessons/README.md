# SQL Learning Lessons

This directory contains progressive SQL learning exercises built on top of the holocron-analytics database.

## Overview

These lessons use a layered view architecture that hides the underlying warehouse schema (Dims/Facts/Bridges) from learners. All exercises query the `learn_*` tables, which are simplified, learner-friendly views.

## Available Tables

The following tables are available for learner queries:

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `learn_characters` | Character directory with species, gender, archetype | CharacterId, CharacterName, Species, RoleArchetype |
| `learn_scenes` | Scene breakdown by work | SceneId, SceneName, SceneNumber, WorkTitle, DurationSec |
| `learn_events` | Event timeline with types and confidence | EventId, EventSummary, EventType, ConfidenceScore |
| `learn_event_participants` | Who participated in which events | ParticipantName, Role, Importance, EventSummary |
| `learn_assets` | Ships, droids, weapons | AssetId, AssetName, ModelName, AssetType, Status |
| `learn_locations` | Location hierarchy | LocationId, LocationName, LocationType, ParentLocation |
| `learn_continuity_issues` | Canon conflicts and ambiguities | IssueId, IssueSummary, Severity, DisputeLevel, Status |
| `learn_claims` | Atomic assertions with evidence | ClaimId, SubjectName, Predicate, Value, ConfidenceScore |

## Module Index

### Beginner Modules (SELECT, WHERE, ORDER BY, TOP, DISTINCT)

| # | Module | Primary Tables | Skills |
|---|--------|----------------|--------|
| 01 | Character Directory | `learn_characters` | SELECT, WHERE, ORDER BY, LIKE |
| 02 | Character Appearances | `learn_characters`, `learn_scenes` | JOINs (introduction) |
| 03 | Event Timeline | `learn_events` | WHERE, ORDER BY, BETWEEN |

### Intermediate Modules (JOINs, GROUP BY, Aggregation)

| # | Module | Primary Tables | Skills |
|---|--------|----------------|--------|
| 04 | Who Met Whom | `learn_event_participants` | GROUP BY, COUNT, HAVING |
| 05 | Asset Lifecycle | `learn_assets`, `learn_events` | JOINs, filtering |
| 06 | Location Hierarchy | `learn_locations` | Self-referencing patterns, hierarchy |
| 07 | Scene Dashboards | `learn_scenes`, `learn_events` | GROUP BY, aggregation functions |

### Advanced Modules (Complex Analysis, Window Functions)

| # | Module | Primary Tables | Skills |
|---|--------|----------------|--------|
| 08 | Continuity Issues | `learn_continuity_issues`, `learn_claims` | Complex WHERE, JOINs |
| 09 | Trench Run Deep Dive | `learn_events`, `learn_event_participants` | Sequence analysis, filtering |
| 10 | Duel of Fates Deep Dive | `learn_events`, `learn_event_participants` | Timeline analysis, narrative queries |

## How to Use

1. **Read the exercise file** (`NN_module_exercises.sql`) to understand the goals and hints
2. **Write your own queries** to solve each exercise
3. **Check the answer file** (`NN_module_answers.sql`) for solutions and variations
4. **Experiment** with the commented-out variations to explore the data

## Difficulty Progression

Each module starts with simpler exercises and progresses to more complex ones:

- **Exercises 1-2**: Warm-up with basic SELECT and WHERE
- **Exercises 3-4**: Add ORDER BY, DISTINCT, TOP
- **Exercises 5-6**: Introduce grouping or joins
- **Exercises 7-8**: Combine multiple concepts
- **Exercises 9-10**: Challenge exercises with real analysis questions

## Confidence Scores

Many tables include a `ConfidenceScore` column (0.0 to 1.0) indicating data quality:

- **0.90+**: High confidence, well-sourced
- **0.70-0.89**: Good confidence, minor ambiguity
- **0.50-0.69**: Moderate confidence, some uncertainty
- **Below 0.50**: Low confidence, use with caution

Filtering by confidence is a valuable skill for working with real-world data.

## Tips for Learners

1. Start each query with `SELECT TOP 10 *` to preview data
2. Use `ORDER BY` to understand the natural ordering
3. Read column names carefully - they are designed to be self-documenting
4. Try the variations in answer keys to explore different filters
5. Don't forget `DISTINCT` when counting unique values

## View Architecture (For Instructors)

The views follow a layered architecture:

```
Physical Tables (Dim*/Fact*/Bridge*) - NOT exposed to learners
        ↓
    sem_* views (semantic layer)
        ↓
    mart_* views (story/analysis marts)
        ↓
    learn_* views (learner-facing "tables")
```

This design allows:
- Schema changes without breaking learner materials
- Progressive complexity (learners can later explore sem_/mart_ views)
- Clean separation of warehouse logic from learning exercises
