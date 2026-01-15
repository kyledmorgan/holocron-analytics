# Schema overview (placeholder, evolving)

This section documents the intent of the current **dimension / fact** wireframe. It is intentionally **more verbose than the column list** and is written to guide incremental modeling over time. The goal is to provide a shared vocabulary for learning, discussion, and future refactoring.

## Guiding concepts

- **Franchise-first**: Everything belongs to a franchise/universe, even if we later generalize to non-franchise domains.
- **Entity-core**: A single “entity registry” (`DimEntity`) provides a consistent identity surface across characters, organizations, locations, and built things.
- **Built things as assets + instances**: A “model” (`DimTechAsset`) is the design/class, and an “instance” (`DimTechInstance`) is the specific named thing in-world.
- **Events as the analytical spine**: `FactEvent` captures “what happened” at a level we can query and summarize without reproducing copyrighted narrative.
- **Continuity is a first-class axis**: Frames (Canon/Legends/etc.) are explicit, allowing divergent timelines without forcing a single truth.
- **Appearance is time-anchored**: Looks can change by work/scene and are modeled as observations.

---

# Core work, time, and continuity

This section details the core dimension tables that provide governance, provenance, continuity, and time anchoring. These tables are designed to be franchise-agnostic while still supporting narrative media analysis.

## Cross-cutting conventions

All dimension tables in this core set include the following governance and overflow fields:

- `SourceSystem`: Nullable string identifying the upstream system (for example, `MediaWikiAPI`).
- `SourceRef`: Nullable string for a stable external identifier or URL.
- `IngestBatchId`: Nullable string that correlates records to an ingestion run.
- `RowCreatedUtc`: UTC timestamp for initial insertion.
- `RowUpdatedUtc`: UTC timestamp for last update.
- `IsActive`: Boolean for SCD-like activation/inactivation.
- `AttributesJson`: JSON object stored as string for unmapped or emerging attributes.

### AttributesJson rules

- Must be a JSON object (not an array).
- Keys should be stable; prefer `lower_snake_case`.
- Values should be primitives or nested objects; avoid large blobs.
- Use this as the landing zone for one-off fields; promote recurring keys into first-class columns later.

## Documentation as website content

Markdown is the source of truth for docs today. A future milestone is to render these docs into the local web UI, so write with that rendering in mind (clear headings, stable anchors, and concise cross-links).

---

## DimFranchise

### What it is
A top-level container for a narrative universe or franchise.

### Why it exists
It provides a clean scope boundary so identities and works do not collide across universes, and supports multi-franchise analytics later.

### How to use it
Link every work, continuity frame, era, and era anchor to a franchise. Use it as the root for filtering and aggregation.

### Design intent
Keep franchise data stable and minimal; avoid franchise-specific columns that would block reuse across domains.

### Columns (dictionary)

- `FranchiseKey`: Surrogate primary key.
- `Name`: Display name of the franchise/universe.
- `UniverseCode`: Short code for compact references (for example, `SW`, `LOTR`).
- `FranchiseGroup`: Optional umbrella grouping for related franchises.
- `OwnerOrRightsHolder`: Nullable informational label for the rights holder.
- `DefaultContinuityFrame`: Nullable convenience label for the default continuity frame.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use one franchise per distinct universe.
- Keep `UniverseCode` short and stable to support joins and sorting.
- Use `DefaultContinuityFrame` to drive UI defaults without hard-coding in application logic.

---

## DimWork

### What it is
A catalog of published works (films, episodes, books, comics, games, shorts, or web releases).

### Why it exists
It provides provenance for observations and events, enabling "where did this come from?" queries.

### How to use it
Link scenes, events, claims, and observations to a `WorkKey`. Use release metadata for timeline analysis.

### Design intent
Support multiple work types and editions without locking into a single medium.

### Columns (dictionary)

- `WorkKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `WorkType`: Controlled string (for example, `Film`, `Episode`, `Book`, `Comic`, `Game`, `Short`, `Web`).
- `Title`: Display title.
- `TitleSort`: Nullable normalized title for ordering.
- `EditionOrCut`: Nullable edition label (for example, theatrical, director cut).
- `SeasonEpisode`: Nullable combined label (for example, `S02E05`).
- `SeasonNumber`: Nullable season number for episodic works.
- `EpisodeNumber`: Nullable episode number for episodic works.
- `VolumeOrIssue`: Nullable volume/issue for serialized works.
- `WorkCode`: Nullable internal short code.
- `ReleaseDate`: Nullable release date.
- `ReleaseDatePrecision`: Controlled string (`Exact`, `Estimated`, `Range`, `Unknown`).
- `ReleaseDateEnd`: Nullable end date for date ranges.
- `ReleaseRegion`: Nullable region label for release context.
- `RuntimeRef`: Nullable runtime string (minutes or `HH:MM:SS`).
- `SynopsisShort`: Nullable internal summary; avoid copyrighted text.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `ReleaseDatePrecision` and `ReleaseDateEnd` for uncertain or range-based releases.
- Use `WorkCode` to create short, stable identifiers for filenames or UI.
- Keep `SynopsisShort` to internal, non-copyrighted paraphrase.

---

## DimScene

### What it is
An ordered subdivision of a work (scene, sequence, act, chapter).

### Why it exists
It enables intra-work provenance and supports granular analysis of events and appearances.

### How to use it
Link events or observations to a scene when available; fall back to `DimWork` if not.

### Design intent
Support both time-based (seconds) and narrative-based segmentation.

### Columns (dictionary)

- `SceneKey`: Surrogate primary key.
- `WorkKey`: Foreign key to `DimWork`.
- `SceneOrdinal`: Ordering within a work.
- `SceneName`: Nullable descriptive label.
- `SceneType`: Controlled string (for example, `Act`, `Chapter`, `Sequence`, `Scene`).
- `StartSec`: Nullable start offset in seconds.
- `EndSec`: Nullable end offset in seconds.
- `DurationSec`: Nullable derived duration.
- `LocationHint`: Nullable coarse text hint for location context.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `SceneOrdinal` as the primary ordering mechanism.
- Keep `LocationHint` as a coarse label; resolve full location in downstream dimensions.
- Use `StartSec` and `EndSec` only when time offsets are available.

---

## DimContinuityFrame

### What it is
A definition of continuity scope (canon, legends, alternate cuts, community interpretations).

### Why it exists
It allows multiple truths to coexist without forcing a single authoritative narrative.

### How to use it
Scope events, claims, or observations to a continuity frame; use the frame as a filter for analysis.

### Design intent
Make divergence explicit and discoverable without privileging a single source.

### Columns (dictionary)

- `ContinuityFrameKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `FrameName`: Display label (for example, `Canon`, `Legends`, `AltCut`, `Fan`, `Other`).
- `FrameCode`: Short code for compact references.
- `AuthorityType`: Controlled string (for example, `Publisher`, `Creator`, `Community`).
- `AuthorityRef`: Nullable reference to organization, person, or site.
- `PolicySummary`: Nullable definition of the frame.
- `EffectiveStartDate`: Nullable start date for frame applicability.
- `EffectiveEndDate`: Nullable end date for frame applicability.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `FrameCode` for sorting and stable references in dashboards.
- Use `AuthorityType` to indicate whether the frame is official or community-driven.
- Track frame lifecycle with effective dates when known.

---

## DimEra

### What it is
A universe-relative dating system (for example, BBY/ABY-like epochs or named eras).

### Why it exists
Fictional timelines often use relative calendars; this provides structure without forcing an Earth-based timestamp.

### How to use it
Associate events or works with an `EraKey` plus a relative year range in fact tables.

### Design intent
Support range-based and relative time while remaining compatible with analytical calendar dimensions.

### Columns (dictionary)

- `EraKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `EraName`: Label for the era or epoch.
- `EraCode`: Short code for compact references.
- `AnchorYear`: Integer where `0` represents the anchor event year.
- `CalendarModel`: Controlled string (`SignedYear`, `Range`, `Relative`, `Hybrid`).
- `AnchorEventLabel`: Nullable label of the anchor event.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `CalendarModel` to clarify how relative dating is expressed.
- Treat `AnchorYear` as the zero point for signed-year offsets in fact tables.
- Keep `AnchorEventLabel` informational, not canonical.

# Supplemental calendar dimensions (Earth-anchored)

## Why we add a standard Date (and optional Time) dimension
Even when the universe timeline is fictional or uncertain, analytics tools and SQL query patterns benefit enormously from:
- a **day-grain calendar** for grouping, filtering, sorting, and indexing
- optional **time-of-day** for sequencing within a scene or within a short story arc

This repo uses an **Earth-anchored analytical calendar** as a deterministic backbone, while still preserving a separate **universe-relative timeline** via `DimEra` and signed universe-year ranges in `FactEvent`.

This approach is intentional:
- `DimEra` supports *BBY/ABY-style* and *epoch-style* descriptions.
- `DimDate`/`DimTime` support classic star-schema analytics and BI tooling.
- Events may have one, the other, both, or neither?depending on precision and available evidence.

---

## DimDate

### What it is
A classic analytical date dimension with one row per day.

### Why it exists
It enables grouping, filtering, and sorting by standard calendar dates independent of universe-relative time.

### How to use it
Join to analytic facts by `DateKey` when dates are known or estimated; use for time-series reports.

### Design intent
Provide deterministic date keys for BI tooling without implying canonical in-universe chronology.

### Columns (dictionary)

- `DateKey`: Surrogate key in `YYYYMMDD` format.
- `CalendarDate`: SQL `date` value.
- `Year`: Four-digit year.
- `Quarter`: Quarter number (1-4).
- `Month`: Month number (1-12).
- `DayOfMonth`: Day of month (1-31).
- `DayOfYear`: Day of year (1-366).
- `DayOfWeek`: Day of week (1-7; define locale-specific mapping).
- `DayName`: Day name (for example, `Monday`).
- `MonthName`: Month name (for example, `January`).
- `ISOWeek`: ISO week number.
- `IsWeekend`: Boolean weekend flag.
- `IsHoliday`: Optional holiday flag (locale-specific).
- `HolidayName`: Nullable holiday label.
- `Notes`: Freeform notes.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Keep `DateKey` aligned to `CalendarDate` for deterministic joins.
- Use `IsHoliday` only when a locale or calendar is defined.
- Use `Notes` for operational metadata, not narrative content.

---

## DimTime

### What it is
A time-of-day dimension, typically at hour or minute grain.

### Why it exists
It supports sequencing and aggregation within a day without requiring full timestamps.

### How to use it
Join to facts by `TimeKey` when time-of-day is known or inferred.

### Design intent
Offer predictable bucketing for time-of-day analytics without over-modeling precision.

### Columns (dictionary)

- `TimeKey`: Surrogate key in `HHMMSS` or `HHMM` format.
- `ClockTime`: SQL `time` value.
- `Hour`: Hour of day (0-23).
- `Minute`: Minute of hour (0-59).
- `Second`: Second of minute (0-59).
- `TimeBucket`: Controlled string (`Hour`, `Minute`, `Second`).
- `Notes`: Freeform notes.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `TimeBucket` to indicate the grain of populated rows.
- Prefer minute grain unless second precision is required.
- Keep `TimeKey` consistent with `ClockTime`.

---

## DimEraAnchor

### What it is
A bridge mapping between universe-relative time and the analytical calendar.

### Why it exists
It enables consistent conversion and comparison between fictional timelines and standard date/time dimensions.

### How to use it
Define one or more anchors per franchise/era that map universe year 0 to a specific `DimDate`/`DimTime` entry.

### Design intent
Support deterministic mapping without implying real-world chronology.

### Columns (dictionary)

- `EraAnchorKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `EraKey`: Foreign key to `DimEra`.
- `AnchorDateKey`: Foreign key to `DimDate` mapping universe year 0 to a calendar date.
- `AnchorTimeKey`: Foreign key to `DimTime` (often midnight).
- `AnchorRule`: Controlled string (`SignedYearOffset`, `RangeOffset`, `Relative`).
- `AnchorTimezoneOffsetMin`: Nullable display-only timezone offset in minutes.
- `Notes`: Freeform notes.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use one anchor per era to keep conversions predictable.
- Use `AnchorRule` to document the conversion logic.
- Keep `AnchorTimezoneOffsetMin` informational only.

## How this relates to FactEvent
`FactEvent` retains universe-relative fields (`UniverseYearMin/Max`, `EraKey`) for fidelity and uncertainty.
We add **optional** analytical keys:
- `DateKey`, `TimeKey` (start)
- `DateKeyEnd`, `TimeKeyEnd` (end, for spans)
- `TemporalPrecision` (Exact | Estimated | Range | Unknown)

This enables:
- time-series visuals (by date) even when the true in-universe time is approximate
- explicit communication of precision so consumers don't over-trust the granularity


# Entity and tech schemas

This section documents the identity registry and built-thing model/instance pattern. It is franchise-agnostic and designed to support multiple content domains without reworking the core structure.

## Cross-cutting conventions

All dimension tables in this group include the following governance and overflow fields:

- `SourceSystem`: Nullable string identifying the upstream system.
- `SourceRef`: Nullable string for a stable external identifier or URL.
- `IngestBatchId`: Nullable string that correlates records to an ingestion run.
- `RowCreatedUtc`: UTC timestamp for initial insertion.
- `RowUpdatedUtc`: UTC timestamp for last update.
- `IsActive`: Boolean for SCD-like activation/inactivation.
- `AttributesJson`: JSON object stored as string for unmapped or emerging attributes.

### AttributesJson rules

- Must be a JSON object (not an array).
- Keys should be stable; prefer `lower_snake_case`.
- Values should be small; avoid large blobs.
- Use this as the landing zone for one-off fields; promote recurring keys into first-class columns later.

### Model vs instance convention

- `DimTechAsset` = model/class/design definition.
- `DimTechInstance` = specific named instance.
- `DimEntity` represents `DimTechInstance` so tech instances can participate in events like characters or organizations.

## Documentation as website content

Markdown is the source of truth today. A future milestone is to render these docs into the local web UI, so write with that rendering in mind (clear headings, stable anchors, and concise cross-links).

---

## DimEntity

### What it is
The identity registry for anything we model: characters, organizations, species, locations, and tech instances.

### Why it exists
It provides a single surface for naming, type classification, and external linking so downstream facts can refer to one consistent identity.

### How to use it
Create one `DimEntity` row per real-world or in-universe identity. Link specialization tables (character, species, organization, location) to the appropriate `EntityKey`. Link `DimTechInstance` via its `EntityKey` to allow participation in events.

### Design intent
Centralize identity and metadata to avoid redundant naming tables and keep joins consistent across domains.

### Columns (dictionary)

- `EntityKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `EntityType`: Controlled string (`Character`, `Org`, `Species`, `Location`, `TechInstance`, `Other`).
- `DisplayName`: Primary display name.
- `DisplayNameNormalized`: Nullable normalized name for search/sort.
- `SortName`: Nullable canonical ordering (for example, `Last, First`).
- `AliasCsv`: Nullable quick aliases list for simple matching; avoid heavy parsing.
- `ExternalId`: Nullable external identifier (page id, slug).
- `ExternalIdType`: Nullable type label for `ExternalId` (for example, `MediaWikiPageId`, `Slug`, `Other`).
- `ExternalUrl`: Nullable external URL.
- `SummaryShort`: Nullable internal short summary; avoid copyrighted text.
- `SummaryLong`: Nullable internal long summary; avoid copyrighted text.
- `DescriptionSource`: Nullable provenance note for summary text.
- `ConfidenceScore`: Nullable decimal 0-1 for curation confidence.
- `IsCanonical`: Nullable boolean for convenience; do not use as strict truth.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `DisplayNameNormalized` for case-insensitive search.
- Keep `AliasCsv` short and curated; promote complex aliasing later.
- Track external references with `ExternalId` + `ExternalIdType` for stable joins.

---

## DimCharacter

### What it is
A specialization of `DimEntity` for individual characters.

### Why it exists
Character-specific attributes do not apply to other entity types and require a dedicated dimension.

### How to use it
Create a `DimCharacter` row for each character entity, linked to `DimEntity` via `EntityKey`. Reference `SpeciesKey` when known; use text refs for uncertain values.

### Design intent
Keep character traits separate from general identity while remaining franchise-agnostic.

### Columns (dictionary)

- `CharacterKey`: Surrogate primary key.
- `EntityKey`: Foreign key to `DimEntity`.
- `SpeciesKey`: Foreign key to `DimSpecies`.
- `Gender`: Nullable text as represented.
- `Pronouns`: Nullable text.
- `BirthRef`: Nullable text reference for birth information.
- `DeathRef`: Nullable text reference for death information.
- `BirthPlaceRef`: Nullable text reference for birthplace.
- `HomeworldRef`: Nullable text reference; may later become `LocationKey`.
- `SpeciesNameRef`: Nullable text for uncertain or unknown species.
- `HeightRef`: Nullable text reference.
- `MassRef`: Nullable text reference.
- `EyeColor`: Nullable text.
- `HairColor`: Nullable text.
- `SkinColor`: Nullable text.
- `DistinguishingMarks`: Nullable text (scars, tattoos, etc.).
- `RoleArchetype`: Nullable archetype label (hero, villain, support).
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `SpeciesKey` when a curated species is known; otherwise populate `SpeciesNameRef`.
- Keep physical attributes as refs until normalized into structured measurements.
- Use `RoleArchetype` as a loose categorization, not canonical truth.

---

## DimSpecies

### What it is
A specialization of `DimEntity` for species or creature types.

### Why it exists
Species-level attributes are shared across many characters and should not be duplicated per character.

### How to use it
Create one row per species and link `DimCharacter.SpeciesKey` to it. Use text references for traits when details are uncertain.

### Design intent
Support rollups by species while keeping characterization separate from individual characters.

### Columns (dictionary)

- `SpeciesKey`: Surrogate primary key.
- `EntityKey`: Foreign key to `DimEntity`.
- `Category`: Controlled string (for example, `Humanoid`, `Creature`, `Aquatic`, `Avian`, `Reptilian`, `Other`).
- `HomeworldRef`: Nullable text reference for homeworld.
- `TypicalLifespanRef`: Nullable text reference.
- `AverageHeightRef`: Nullable text reference.
- `SkinTypesRef`: Nullable text reference (scales, fur, etc.).
- `LanguageRef`: Nullable text reference.
- `DietRef`: Nullable text reference.
- `TraitsJson`: Optional curated traits (small JSON string).
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Keep `TraitsJson` compact and curated.
- Use `Category` for broad grouping and analytics.
- Defer precise numeric traits until measurement conventions are defined.

---

## DimOrganization

### What it is
A specialization of `DimEntity` for organizations, factions, and institutions.

### Why it exists
Organizations require attributes like scope and alignment that are not relevant to other entity types.

### How to use it
Create one row per organization and link events or claims to the associated entity. Use text refs for dates and headquarters until normalized.

### Design intent
Keep organization metadata consistent across franchise contexts.

### Columns (dictionary)

- `OrganizationKey`: Surrogate primary key.
- `EntityKey`: Foreign key to `DimEntity`.
- `OrgType`: Controlled string (`Government`, `Guild`, `Gang`, `Order`, `Military`, `Corp`, `Other`).
- `Scope`: Controlled string (`Local`, `Planetary`, `Sector`, `Regional`, `Galaxy`, `Intergalactic`).
- `AlignmentRef`: Nullable text reference for alignment.
- `FoundedRef`: Nullable text reference.
- `DissolvedRef`: Nullable text reference.
- `HeadquartersRef`: Nullable text reference; may later become `LocationKey`.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `Scope` to enable rollups across governance levels.
- Keep `AlignmentRef` as a loose label until a taxonomy exists.
- Prefer text refs for dates until a timeline model is defined.

---

## DimLocation

### What it is
A specialization of `DimEntity` for hierarchical locations.

### Why it exists
Locations are naturally hierarchical (region > system > planet > city > site) and benefit from rollups.

### How to use it
Create one row per location and link `ParentLocationKey` to establish hierarchy. Use rollups for geographic aggregation.

### Design intent
Enable location rollups without creating separate tables for each level.

### Columns (dictionary)

- `LocationKey`: Surrogate primary key.
- `EntityKey`: Foreign key to `DimEntity`.
- `ParentLocationKey`: Nullable self-referencing foreign key.
- `LocationType`: Controlled string (`Galaxy`, `Region`, `System`, `Planet`, `Moon`, `City`, `Site`, `Structure`).
- `RegionCode`: Nullable text label (for example, a quadrant or region).
- `LatitudeRef`: Nullable decimal reference.
- `LongitudeRef`: Nullable decimal reference.
- `ClimateRef`: Nullable text reference.
- `TerrainRef`: Nullable text reference.
- `PopulationRef`: Nullable text reference.
- `GovernmentRef`: Nullable local governance note.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `ParentLocationKey` for hierarchical rollups.
- Keep `LocationType` consistent for easier aggregation.
- Store raw coordinates in `LatitudeRef`/`LongitudeRef` until a coordinate standard is defined.

---

## DimTechAsset

### What it is
The model/class/design definition for built things.

### Why it exists
Many instances share a common model; model-level attributes should not be repeated per instance.

### How to use it
Create one row per model and link instances via `DimTechInstance.TechAssetKey`. Use subtype tables for domain-specific model attributes.

### Design intent
Keep asset models reusable across franchises and support future subtyping.

### Columns (dictionary)

- `TechAssetKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `AssetType`: Controlled string (`DroidModel`, `ShipModel`, `WeaponModel`, `StructureModel`, `ToolModel`, `Other`).
- `ModelName`: Model display name.
- `ModelNameNormalized`: Nullable normalized name for search/sort.
- `ManufacturerRef`: Nullable text reference for manufacturer.
- `ManufacturerCode`: Nullable manufacturer code.
- `EraRef`: Nullable text reference; may later become `EraKey`.
- `FirstAppearanceRef`: Nullable work reference for first appearance.
- `TechLevelRef`: Nullable text reference.
- `PowerSourceRef`: Nullable text reference.
- `MaterialRef`: Nullable text reference.
- `SafetyNotes`: Nullable safety and handling notes.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `AssetType` to decide which subtype table applies.
- Keep `ModelNameNormalized` for search and deduplication.
- Store uncertain attributes as text refs or `AttributesJson` until normalized.

---

## DimTechInstance

### What it is
A specific named instance of a built thing (ship, droid, weapon, tool).

### Why it exists
Instances accumulate history and can participate in events, distinct from their model class.

### How to use it
Create one row per instance and link to both `DimEntity` and `DimTechAsset`. Use `DimEntity` when connecting to events or claims.

### Design intent
Separate model-level truth from instance-level lifecycle.

### Columns (dictionary)

- `TechInstanceKey`: Surrogate primary key.
- `EntityKey`: Foreign key to `DimEntity`.
- `TechAssetKey`: Foreign key to `DimTechAsset`.
- `InstanceName`: Display name or call sign.
- `SerialRef`: Nullable serial or registry reference.
- `BuildRef`: Nullable build origin reference.
- `CurrentStatus`: Nullable status label (`Active`, `Destroyed`, `Unknown`).
- `LastKnownLocationRef`: Nullable location reference.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `EntityKey` to include instances in event participation.
- Store registry identifiers in `SerialRef` when available.
- Keep `CurrentStatus` as a lightweight state, not a full lifecycle history.

---

## DimDroidModel

### What it is
A droid-specific extension of `DimTechAsset`.

### Why it exists
Droid models have attributes (class, autonomy, mobility) that do not apply to other asset types.

### How to use it
Create one row per droid model and link to `DimTechAsset` via `TechAssetKey`.

### Design intent
Extend `DimTechAsset` without overloading it with droid-only attributes.

### Columns (dictionary)

- `DroidModelKey`: Surrogate primary key.
- `TechAssetKey`: Foreign key to `DimTechAsset`.
- `DroidClass`: Controlled string (`Protocol`, `Astromech`, `Battle`, `Medical`, `Labor`, `Assassin`, `Other`).
- `PrimaryFunction`: Nullable function label.
- `AutonomyLevel`: Controlled string (`Remote`, `Semi`, `Autonomous`).
- `MobilityRef`: Nullable text reference.
- `ChassisRef`: Nullable text reference.
- `SensorSuiteRef`: Nullable text reference.
- `LanguageCapabilitiesRef`: Nullable text reference or JSON pointer.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `AutonomyLevel` to support rollups by control type.
- Keep capability details in refs or `AttributesJson` until normalized.
- Store compact function labels in `PrimaryFunction` for grouping.

---

## DimDroidInstance

### What it is
A droid-specific extension of `DimTechInstance`.

### Why it exists
Individual droids have instance-only attributes (personality, memory wipes) that are not part of the model.

### How to use it
Create one row per droid instance and link to `DimTechInstance` via `TechInstanceKey`.

### Design intent
Capture droid instance traits without overloading the base instance table.

### Columns (dictionary)

- `DroidInstanceKey`: Surrogate primary key.
- `TechInstanceKey`: Foreign key to `DimTechInstance`.
- `PersonalityName`: Nullable nickname or persona label.
- `MemoryWipeRef`: Nullable text reference.
- `RestrainingBoltFlag`: Nullable boolean.
- `PrimaryLanguageRef`: Nullable text reference.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `RestrainingBoltFlag` only when explicitly known.
- Keep `PersonalityName` short and descriptive.
- Track memory events in downstream facts rather than in this table.

---

## DimShipModel

### What it is
A ship-specific extension of `DimTechAsset`.

### Why it exists
Ships have attributes (propulsion, capacity, armament) that do not apply to other asset types.

### How to use it
Create one row per ship model and link to `DimTechAsset` via `TechAssetKey`.

### Design intent
Support ship analytics without adding ship-only fields to the base asset table.

### Columns (dictionary)

- `ShipModelKey`: Surrogate primary key.
- `TechAssetKey`: Foreign key to `DimTechAsset`.
- `ShipClass`: Controlled string (`Fighter`, `Freighter`, `Capital`, `Transport`, `Speeder`, `Other`).
- `PropulsionType`: Controlled string (`Hyperdrive`, `Sublight`, `None`).
- `HyperdriveClassRef`: Nullable text reference.
- `CrewCapacityRef`: Nullable text reference.
- `PassengerCapacityRef`: Nullable text reference.
- `ArmamentRef`: Nullable text reference.
- `ShieldingRef`: Nullable text reference.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `ShipClass` for coarse analytics and filtering.
- Keep capacity fields as refs until units are standardized.
- Keep `PropulsionType` small and controlled for consistency.

---

## DimWeaponModel

### What it is
A weapon-specific extension of `DimTechAsset`.

### Why it exists
Weapons have attributes (energy type, range, rate of fire) that are not relevant to other asset types.

### How to use it
Create one row per weapon model and link to `DimTechAsset` via `TechAssetKey`.

### Design intent
Support weapon analytics without bloating `DimTechAsset`.

### Columns (dictionary)

- `WeaponModelKey`: Surrogate primary key.
- `TechAssetKey`: Foreign key to `DimTechAsset`.
- `WeaponClass`: Controlled string (`Lightsaber`, `Blaster`, `Melee`, `Explosive`, `Heavy`, `Other`).
- `EnergyType`: Controlled string (`Kyber`, `Plasma`, `Projectile`, `Chemical`, `Other`).
- `EffectiveRangeRef`: Nullable text reference.
- `AmmunitionRef`: Nullable text reference.
- `RateOfFireRef`: Nullable text reference.
- `LethalityRef`: Nullable qualitative reference.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `EnergyType` for rollups by weapon technology.
- Keep performance metrics as refs until measurement units are defined.
- Store one-off details in `AttributesJson` for later promotion.


# Appearance, event spine, and continuity meta

This section documents the appearance observations, the event spine, and the continuity meta layer used to structure claims and issues without storing narrative payloads.

## Cross-cutting conventions

Dim tables include governance columns:

- `SourceSystem`: Nullable string identifying the upstream system.
- `SourceRef`: Nullable string for a stable external identifier or URL.
- `IngestBatchId`: Nullable string that correlates records to an ingestion run.
- `RowCreatedUtc`: UTC timestamp for initial insertion.
- `RowUpdatedUtc`: UTC timestamp for last update.
- `IsActive`: Boolean for SCD-like activation/inactivation.
- `AttributesJson`: JSON object stored as string for unmapped or emerging attributes.

Fact and bridge tables include provenance columns:

- `SourceSystem`: Nullable string identifying the upstream system.
- `SourceRef`: Nullable string for a stable external identifier or URL.
- `IngestBatchId`: Nullable string that correlates records to an ingestion run.
- `RowCreatedUtc`: UTC timestamp for initial insertion.
- `RowUpdatedUtc`: UTC timestamp for last update.

Facts also include `AttributesJson` to avoid schema churn from one-off extractions.

Confidence and provenance conventions:

- `ConfidenceScore` is stored on `FactEvent` and `FactClaim` (and optionally on `DimAppearanceLook`).
- `ExtractionMethod` indicates how a row was created or updated (`AI`, `Manual`, `Rules`, `Hybrid`).

## Documentation as website content

Markdown is the source of truth today. A future milestone is to render these docs into the local web UI, so write with that rendering in mind (clear headings, stable anchors, and concise cross-links).

---

## DimAppearanceLook

### What it is
An observation of a character's appearance in a specific work/scene context.

### Why it exists
Appearances can change within a work or across works, and are not permanent attributes. This table captures look observations without asserting canonical permanence.

### How it's used
Link to `DimCharacter`, `DimWork`, and `DimScene` to document context. Multiple looks can be associated with a single scene.

### Design intent
Treat appearance as a contextual observation. Allow multiple looks per scene and mark a primary look when helpful for analytics.

### Columns (dictionary)

- `LookKey`: Surrogate primary key.
- `CharacterKey`: Foreign key to `DimCharacter`.
- `WorkKey`: Foreign key to `DimWork`.
- `SceneKey`: Foreign key to `DimScene`.
- `LookLabel`: Human-readable label for the look.
- `LookType`: Controlled string (`Robes`, `Armor`, `Uniform`, `Civilian`, `Disguise`, `Other`).
- `PrimaryColorRef`: Nullable text reference.
- `SecondaryColorRef`: Nullable text reference.
- `MaterialRef`: Nullable text reference.
- `InsigniaRef`: Nullable text reference.
- `HairStyle`: Nullable text reference.
- `HairColor`: Nullable text reference.
- `FacialHair`: Nullable text reference.
- `MakeupOrMarkingsRef`: Nullable text reference.
- `ConditionRef`: Controlled string (`Clean`, `Damaged`, `Weathered`, `Bloodied`, `Other`).
- `AccessoriesRef`: Nullable text reference for accessories.
- `Notes`: Freeform notes; avoid copyrighted text.
- `ConfidenceScore`: Nullable decimal 0-1.
- `IsPrimaryLookInScene`: Nullable boolean convenience flag.
- `EvidenceRef`: Nullable internal pointer only.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Record multiple looks for the same scene when a change occurs.
- Use `IsPrimaryLookInScene` as a convenience for UI and summaries.
- Store one-off accessories in `AttributesJson` until formalized.

---

## DimEventType

### What it is
A hierarchical taxonomy for event categories and verbs.

### Why it exists
Consistent event classification enables rollups, filtering, and aggregation across franchises and content types.

### How it's used
Use `ParentEventTypeKey` to build hierarchies. `FactEvent` references `EventTypeKey` for classification.

### Design intent
Keep the taxonomy stable and extensible, with explicit verb and polarity guidance.

### Columns (dictionary)

- `EventTypeKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `ParentEventTypeKey`: Nullable self-referencing FK for hierarchy.
- `EventTypeName`: Display label.
- `EventTypeCode`: Short code for compact references.
- `VerbClass`: Controlled string (`Physical`, `Force`, `Social`, `Technical`, `Environmental`).
- `VerbLemma`: Base verb (for example, `attack`, `heal`, `travel`).
- `PolarityDefault`: Controlled string (`Positive`, `Negative`, `Neutral`, `Mixed`).
- `GranularityGuidance`: Controlled string (`Coarse`, `Moderate`, `Fine`).
- `IsLeafType`: Nullable boolean convenience flag.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `ParentEventTypeKey` to roll up fine-grained types to broader categories.
- Keep `VerbLemma` consistent for search and clustering.
- Use `GranularityGuidance` to steer event extraction detail.

---

## FactEvent

### What it is
The analytical spine capturing actions and outcomes.

### Why it exists
Events provide a structured backbone for analysis without storing narrative scripts or quotes.

### How it's used
Link to work/scene provenance, classify via event type, and anchor to time when available. Use bridges for participants and assets.

### Design intent
Support coarse-to-moderate granularity events with optional time anchoring across multiple calendars.

### Columns (dictionary)

- `EventKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `ContinuityFrameKey`: Foreign key to `DimContinuityFrame`.
- `WorkKey`: Foreign key to `DimWork`.
- `SceneKey`: Foreign key to `DimScene`.
- `ParentEventKey`: Nullable self-referencing FK.
- `EventOrdinal`: Ordering within a scene or work.
- `EventTypeKey`: Foreign key to `DimEventType`.
- `LocationKey`: Foreign key to `DimLocation`.
- `StartSec`: Nullable start second within the scene.
- `EndSec`: Nullable end second within the scene.
- `EraKey`: Nullable foreign key to `DimEra`.
- `UniverseYearMin`: Nullable signed year lower bound.
- `UniverseYearMax`: Nullable signed year upper bound.
- `DateKey`: Nullable foreign key to `DimDate`.
- `TimeKey`: Nullable foreign key to `DimTime`.
- `EventTimestampUtc`: Nullable anchored UTC timestamp if computed.
- `SummaryShort`: Transformative summary without quoting.
- `SummaryNormalized`: Nullable normalized summary for search/dedup.
- `ConfidenceScore`: Decimal 0-1.
- `ExtractionMethod`: Controlled string (`AI`, `Manual`, `Rules`, `Hybrid`).
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `AttributesJson`: JSON object string for one-off fields.

### Common patterns / examples

- Use `EventOrdinal` for ordering within a scene.
- Populate either universe-relative time, analytical date/time, or both.
- Keep summaries descriptive and non-quoting.

---

## BridgeEventParticipant

### What it is
A many-to-many mapping between events and participating entities.

### Why it exists
Events involve multiple participants with roles and varying importance.

### How it's used
Link `FactEvent` to `DimEntity` and specify roles and weighting for analysis.

### Design intent
Capture participant roles without inflating the event record.

### Columns (dictionary)

- `EventKey`: Foreign key to `FactEvent`.
- `EntityKey`: Foreign key to `DimEntity`.
- `RoleInEvent`: Controlled string role label.
- `RoleSubtype`: Nullable role detail.
- `WeightClass`: Controlled string (`Primary`, `Secondary`, `Background`).
- `ParticipantOrdinal`: Nullable ordering within the event.
- `ParticipationScore`: Nullable weighting.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `AttributesJson`: JSON object string for one-off fields.

### Common patterns / examples

- Use `RoleInEvent` to drive role-based analytics.
- Use `WeightClass` for participation rollups.
- Keep per-event ordering in `ParticipantOrdinal` when needed.

---

## BridgeEventAsset

### What it is
A many-to-many mapping between events and tech instances involved.

### Why it exists
Events often involve specific built things as tools, assets, or targets.

### How it's used
Link `FactEvent` to `DimTechInstance` and describe asset roles.

### Design intent
Support asset lifecycle analysis without embedding assets directly in events.

### Columns (dictionary)

- `EventKey`: Foreign key to `FactEvent`.
- `TechInstanceKey`: Foreign key to `DimTechInstance`.
- `AssetRole`: Controlled string (`Used`, `Damaged`, `Destroyed`, `Operated`, `Referenced`).
- `AssetRoleDetail`: Nullable detail.
- `AssetOrdinal`: Nullable ordering within the event.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `AttributesJson`: JSON object string for one-off fields.

### Common patterns / examples

- Use `AssetRole` to analyze usage vs damage.
- Track multiple assets with `AssetOrdinal` if order matters.
- Store detailed context in `AttributesJson` until normalized.

---

## DimIssueType

### What it is
A taxonomy of continuity issue categories.

### Why it exists
Classifying issue types enables rollups and structured analysis of continuity problems.

### How it's used
Reference from `ContinuityIssue` to classify the issue.

### Design intent
Keep issue categories stable while allowing extensions.

### Columns (dictionary)

- `IssueTypeKey`: Surrogate primary key.
- `IssueTypeName`: Display label.
- `IssueTypeCode`: Short code.
- `Description`: Nullable description.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `IssueTypeCode` for dashboards and filters.
- Keep `Description` focused on classification rules.
- Add new types sparingly to avoid taxonomy bloat.

---

## ContinuityIssue

### What it is
A record of a recognized discrepancy or ambiguity.

### Why it exists
Continuity issues are part of narrative analysis and should be tracked without forcing authoritative resolution.

### How it's used
Link to issue type, continuity frame, and optional work/scene scope. Use status and severity for triage.

### Design intent
Represent issues as analyzable metadata rather than narrative content.

### Columns (dictionary)

- `ContinuityIssueKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `ContinuityFrameKey`: Foreign key to `DimContinuityFrame`.
- `IssueTypeKey`: Foreign key to `DimIssueType`.
- `IssueSummary`: Short label.
- `IssueDescription`: Nullable internal description; avoid copyrighted text.
- `Scope`: Controlled string (`Scene`, `Work`, `Franchise`).
- `WorkKey`: Nullable foreign key to `DimWork`.
- `SceneKey`: Nullable foreign key to `DimScene`.
- `SeverityScore`: Integer 0-100.
- `SeverityLabel`: Controlled string (`Low`, `Med`, `High`, `Critical`).
- `DisputeLevel`: Controlled string (`Low`, `Med`, `High`).
- `Status`: Controlled string (`Open`, `Explained`, `Retconned`, `SplitByFrame`, `Closed`).
- `ConfidenceScore`: Nullable decimal 0-1.
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `IsActive`: See cross-cutting conventions.
- `AttributesJson`: See cross-cutting conventions.

### Common patterns / examples

- Use `Scope` to drive filtering at scene/work/franchise level.
- Track lifecycle with `Status` and `SeverityScore`.
- Keep `IssueDescription` internal and non-quoting.

---

## FactClaim

### What it is
An atomic assertion extracted from sources or inferred by processing.

### Why it exists
Claims enable multiple sources and conflicting assertions to coexist with provenance and confidence.

### How it's used
Store subject/predicate/object triples with provenance. Link to continuity issues via `BridgeContinuityIssueClaim`.

### Design intent
Keep claims flexible and extensible without forcing early normalization.

### Columns (dictionary)

- `ClaimKey`: Surrogate primary key.
- `FranchiseKey`: Foreign key to `DimFranchise`.
- `ContinuityFrameKey`: Foreign key to `DimContinuityFrame`.
- `ClaimType`: Controlled string (`Attribute`, `Relationship`, `Ordering`, `Identity`, `Other`).
- `SubjectEntityKey`: Foreign key to `DimEntity`.
- `Predicate`: Predicate label (snake_case recommended).
- `ObjectValue`: MVP literal value or entity reference stored as text.
- `ObjectValueType`: Controlled string (`EntityRef`, `String`, `Number`, `Date`, `Range`, `Other`).
- `WorkKey`: Nullable foreign key to `DimWork`.
- `SceneKey`: Nullable foreign key to `DimScene`.
- `ConfidenceScore`: Decimal 0-1.
- `EvidenceRef`: Nullable internal pointer only.
- `ExtractionMethod`: Controlled string (`AI`, `Manual`, `Rules`, `Hybrid`).
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `AttributesJson`: JSON object string for one-off fields.

### Common patterns / examples

- Store subject entities as `SubjectEntityKey` and keep object flexible.
- Use `ObjectValueType` to control interpretation downstream.
- Keep `Predicate` names stable to enable aggregation.

---

## BridgeContinuityIssueClaim

### What it is
A mapping between continuity issues and the claims that compose them.

### Why it exists
Issues typically arise from clusters of related claims; this bridge captures those relationships and roles.

### How it's used
Link `ContinuityIssue` to `FactClaim` with a role indicating how the claim participates.

### Design intent
Enable transparent reasoning graphs without embedding narrative text.

### Columns (dictionary)

- `ContinuityIssueKey`: Foreign key to `ContinuityIssue`.
- `ClaimKey`: Foreign key to `FactClaim`.
- `Role`: Controlled string (`Conflicting`, `Context`, `Supporting`, `ResolutionBasis`).
- `Notes`: Freeform notes; avoid copyrighted text.
- `SourceSystem`: See cross-cutting conventions.
- `SourceRef`: See cross-cutting conventions.
- `IngestBatchId`: See cross-cutting conventions.
- `RowCreatedUtc`: See cross-cutting conventions.
- `RowUpdatedUtc`: See cross-cutting conventions.
- `AttributesJson`: JSON object string for one-off fields.

### Common patterns / examples

- Use `Role` to classify the claim's contribution to the issue.
- Keep `Notes` focused on structural context.
- Preserve provenance for all links to maintain auditability.


# Documentation-to-website future goal (placeholder)

This documentation is currently maintained as Markdown, but the longer-term goal is for it to be:
- rendered into a **documentation section of the local web interface**
- cross-linked to **live schema objects** and example queries
- optionally exported as static assets for easier browsing

Agent policy note: when updating schema documentation, prefer writing it in a way that is:
- easily renderable in a website (headings, anchors, short paragraphs)
- internally linkable (stable file paths, relative links)
- safe for public repositories (no payloads, no copyrighted text)
