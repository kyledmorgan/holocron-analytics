# Seed Data Expansion Framework (Additive Synthetic Seeds)

## Purpose

This document defines a repeatable, tool-agnostic process for expanding synthetic JSON seed datasets. The goal is to add breadth and/or depth to the modeled dimensions/facts/bridges while:

- Remaining **additive-only** (no edits/removals of existing rows)
- Maintaining **referential integrity** across tables
- Staying **tool-agnostic** (Codex CLI, GitHub Copilot, ChatGPT-style tools, etc.)
- Recording **provenance** for every new row (which tool/session generated it)

This framework is designed for:

- **Short-term**: quickly maturing seed files for learning and demonstration
- **Long-term**: evolving into a community-facing "promptable seed generator" workflow (likely integrated into a future website/UI)

---

## Non-Negotiables

### Additive-only

- Do **not** modify or delete existing rows.
- Only append new rows to the `rows` array for one or more seed files.

### Synthetic data only

- No verbatim dialogue lines, script excerpts, or long narrative plot descriptions.
- Proper nouns are allowed (names of characters/places/assets), but keep descriptions short and factual-ish.
- Any "summary" fields should be compact and non-derivative.

### Best-effort duplicate avoidance (soft rule)

- Attempt not to create exact duplicates of an existing entity (same canonical name + same continuity frame + same work context).
- If duplicates happen, that is acceptable for now. **Do not block delivery**. We will address deduping downstream.

### Preserve loader compatibility

- Seed JSON must conform to the current seed loader expectations.
- Respect required columns, datatypes, and reference conventions (GUID-based linking, etc.).
- Do not introduce schema changes in seeds (no new columns).

---

## Seed File Structure Standard

Each seed JSON file follows the established structure in `src/db/seeds/data/` (refer to existing files for exact schema). The framework assumes:

- A `target` identifying the destination schema/table.
- An `options` section (file-level options for loader behavior).
- A `rows` section (data payload).

### File-level metadata (required)

Add/update (without breaking current loader) the following file-level fields:

| Field | Description | Example |
|-------|-------------|---------|
| `seedVersion` | Semantic version of the seed file | `"0.3.0"` |
| `generatedUtc` | ISO timestamp | `"2026-01-16T22:10:00Z"` |

If adding new metadata fields, ensure the loader tolerates unknown keys. Prefer file-level metadata first.

### Row-level provenance (required)

Every new row appended must include provenance info, using whichever column(s) already exist in the table schema and seeds. Preference order:

1. **Explicit provenance fields**: If the table has fields like `SourceSystem`, `SourceRef`, `CreatedBy`, `UpdatedBy`, `ProvenanceJson`, `ExtraJson`, `AttributesJson`, etc., put provenance there.

2. **Extras JSON field**: If the table has only an "extras" JSON field, put provenance inside that JSON object under a stable key:

```json
"ExtraJson": {
  "_provenance": {
    "tool": "copilot-agent",
    "session_id": "2026-01-16_trenchrun_v1",
    "prompt_intent": "deep scene drill-down",
    "generated_utc": "2026-01-16T22:10:00Z"
  }
}
```

3. **Notes field fallback**: If no appropriate field exists, use the shortest available "Notes" field to include a provenance marker (keep it short).

---

## Identity + Referencing Rules

### Keys

- The database uses integer identity keys as PKs (`*Key`). Seeds should typically NOT provide those unless the loader explicitly supports identity inserts.
- Every row must include the table's GUID column (unique, stable).
- GUID uniqueness is mandatory.

### References

For FKs between tables:

- Prefer GUID-based linking (e.g., `FranchiseGuid`, `WorkGuid`, `SceneGuid`, etc.) if the loader supports it.
- If the loader expects FK integer keys, only use that approach where deterministic and already used in existing seed patterns.

### SCD-style columns

Where present, populate with reasonable defaults for new rows:

- `IsActive = true`
- `IsLatest = true`
- `ValidFromUtc` / `CreatedUtc` / `UpdatedUtc` set to reasonable timestamps

Any checksum/hash column: follow the existing seed convention (populate if required; otherwise omit if computed later).

---

## Quality Targets (Guidance, not a hard-stop)

### Breadth-first targets

- Every table should have "enough" records to be queryable and educational.
- Aim: >= 100 rows per table where it makes sense.
- Naturally small tables (e.g., `DimFranchise`) can remain small but complete.

### Depth targets (high-value tables)

Prefer to be in the hundreds for:

- Characters, Species
- Works, Scenes
- Tech assets/instances (Droids, Ships, Weapons)
- FactEvent + bridges (participants/assets)
- Claims and continuity issues (moderate scale is fine)

---

## Event Modeling Guidance

When expanding events:

- Use a coherent `DimEventType` taxonomy; create new event types as needed (additive).
- Every `FactEvent` should have:
  - Work + Scene context (where possible)
  - Continuity frame
  - Event type
  - An ordinal (sequence)
  - A short summary (non-narrative)
- Every meaningful event should link to participants via `BridgeEventParticipant` and assets via `BridgeEventAsset` where relevant.

---

## Additive Expansion Modes

Choose one mode per expansion run:

| Mode | Goal | Description |
|------|------|-------------|
| **Mode A: Breadth Expansion** | Coverage | Expand across the franchise (more works/scenes/entities), shallow events |
| **Mode B: Depth Expansion** | Dense sequences | Dense, ordered event sequences within a constrained scope (e.g., a single fight or chase) |
| **Mode C: Theme Expansion** | Cross-cutting | Generate data around a property or theme spanning works (e.g., "droid memory wipes", "lightsaber injuries", "ship models and variants") |
| **Mode D: Hybrid** | Balanced | A bounded breadth expansion plus one or two deep drill-downs |

---

## Prompt Template (Tool-Agnostic)

Copy/paste this into your agent of choice, adjusting the bracketed sections:

```
PROMPT START
You are an AI coding/data agent working inside this repo. Your task is to append synthetic seed rows to existing JSON seed files under src/db/seeds/data/.

Mode: [Breadth | Depth | Theme | Hybrid]
Franchise: Star Wars (primary), but keep structures generic where possible.
Continuity Frame(s): [Canon only | Canon + Legends]
Scope Focus:
- Breadth coverage across: [Episodes I–VI | Episode IV heavy | add shows]
- Deep drill-down targets (if Depth/Hybrid):
  - [Episode IV — Trench Run, spaceflight-only, exclude control-room intercuts]
  - [Episode I — "Duel of the Fates" fight segment, doors open → Maul severed/falls]

Constraints:
- Additive-only: do not edit/delete existing rows.
- Synthetic only: no dialogue lines, no script excerpts, no long narrative plot descriptions.
- Best-effort duplicate avoidance (soft rule).
- Maintain referential integrity across all tables.
- Preserve loader compatibility: do not change code or DDL; update seed JSON only.

Provenance (required for every new row):
- tool: [codex-cli | copilot-agent | other]
- session_id: [e.g., 2026-01-16_trenchrun_v1]
- generated_utc: use current UTC
- prompt_intent: short string describing this run

Row count targets (guidance):
- Minimum: ~100 rows per table where sensible.
- High-value tables (characters, scenes, events, species, tech) should be in the hundreds.

Process:
1. Read all existing seed JSON files to understand current records and reference conventions (GUID linking, etc.).
2. Identify missing/underpopulated tables and append rows accordingly.
3. Ensure new rows reference existing rows where appropriate (e.g., new events reference existing scenes/works).
4. Append deep sequences for the specified drill-down targets:
   - Trench Run: only spaceflight participants/assets/locations.
   - Duel of the Fates segment: action events, force use, injuries, separations/rejoins; minimal dialogue.
5. Run the existing seed loader to validate the new data loads successfully into SQL Server without FK/constraint errors.
6. If there are load failures, fix the seed data (not code) until it loads successfully.
7. Summarize what you added (rough counts and which files changed) in a short PR-style note.

Output:
- Commit only the updated JSON seed files.
- No other repo changes.
PROMPT END
```

---

## Run Configuration Checklist

Before running a seed expansion:

- [ ] Decide mode (Breadth vs Depth vs Theme)
- [ ] Pick 1–2 "deep targets" at most per run
- [ ] Define `session_id` and tool name
- [ ] Confirm you are not changing code/DDL
- [ ] Validate by running the loader at the end

---

## Suggested Prompt Parameters (Rubric)

Use these knobs to define a run:

| Parameter | Options |
|-----------|---------|
| `mode` | `breadth` \| `depth` \| `theme` \| `hybrid` |
| `focus_works` | List of works to emphasize |
| `focus_scenes` | List of scenes or scene windows |
| `event_density` | `low` \| `medium` \| `high` |
| `entity_targets` | Characters/species/orgs/tech focus |
| `time_modeling` | `none` \| `scene seconds` \| `date dimension` |
| `continuity_frames` | `canon only` \| `canon + legends` |
| `provenance` | Tool + session_id |

---

## Future-facing Vision (Placeholder)

Longer-term, this framework may be rendered into the website as:

- A "prompt builder" UI for seed expansion runs
- Curated scenario templates (battle drill-down, character lifecycle, tech asset lineage)
- A community contribution model that produces additive synthetic datasets with provenance and review workflows

For now, treat this file as the single source of truth for how we expand seeds safely and repeatably.
