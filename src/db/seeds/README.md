# Seed Data Framework

A deterministic, repeatable framework to TRUNCATE + RESEED SQL Server dimensional model tables (dims/facts/bridges) with synthetic JSON seed data.

## Purpose

- Populate development/test databases with minimal, consistent data
- Provide a framework for adding new seed data files
- Enable repeatable seeding for integration tests and demos

## Non-Goals

- This is NOT for production data migration
- Large datasets or real source content are not included
- Incremental merge/upsert is not supported (full reload only)

---

## Directory Structure

```
src/db/seeds/
├── README.md           # This file
├── schema/             # (Optional) JSON schema files for validation
├── data/               # Seed JSON files (one per table)
│   ├── 001_DimFranchise.json
│   ├── 002_DimContinuityFrame.json
│   └── ...
└── logs/               # Runtime logs (gitignored)
```

---

## JSON Seed Format Specification

Each seed file follows a standardized envelope format:

```json
{
  "seedVersion": "0.1.0",
  "generatedUtc": "2026-01-16T00:00:00Z",
  "target": {
    "schema": "dbo",
    "table": "DimFranchise",
    "naturalKey": ["UniverseCode"],
    "loadBehavior": "truncate-insert"
  },
  "options": {
    "allowIdentityInsert": false,
    "ignoreUnknownFields": false,
    "defaults": {
      "IsActive": true,
      "IsLatest": true,
      "VersionNum": 1
    }
  },
  "rows": [
    {
      "FranchiseGuid": "11111111-1111-1111-1111-111111111111",
      "Name": "Star Wars",
      "UniverseCode": "SW",
      "Notes": "Example franchise"
    }
  ]
}
```

### Envelope Fields

| Field | Required | Description |
|-------|----------|-------------|
| `seedVersion` | Yes | Semantic version of the seed format (currently `0.1.0`) |
| `generatedUtc` | Yes | ISO 8601 timestamp when seed was generated |
| `target.schema` | Yes | Database schema (typically `dbo`) |
| `target.table` | Yes | Target table name |
| `target.naturalKey` | No | Array of column names forming natural key (documentation) |
| `target.loadBehavior` | Yes | Load strategy: `truncate-insert` |
| `options.allowIdentityInsert` | No | If true, loader uses `SET IDENTITY_INSERT ON` (default: false) |
| `options.ignoreUnknownFields` | No | If true, skip columns not in table (default: false) |
| `options.defaults` | No | Default values for missing columns |
| `rows` | Yes | Array of row objects |

### Row Field Rules

1. **Identity columns** (e.g., `FranchiseKey`): Omit from rows unless `allowIdentityInsert: true`
2. **GUID columns** (e.g., `FranchiseGuid`): Required in seed rows for deterministic reloads
3. **JSON columns** (e.g., `AttributesJson`): Provide as nested objects; loader serializes to JSON string
4. **SCD columns** (`IsActive`, `IsLatest`, `VersionNum`): Use `options.defaults` or provide in each row
5. **Timestamp columns** (`ValidFromUtc`, `CreatedUtc`): Auto-filled by loader if missing
6. **RowHash**: Auto-computed by loader (SHA-256 of row values)

---

## Connection Configuration

The seed loader uses environment variables for database connection:

### Option 1: ODBC Connection String

```bash
export SEED_SQLSERVER_CONN_STR="Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=Holocron;UID=sa;PWD=YourPassword;TrustServerCertificate=yes"
```

### Option 2: Discrete Variables

```bash
export SEED_SQLSERVER_HOST=localhost
export SEED_SQLSERVER_DATABASE=Holocron
export SEED_SQLSERVER_USER=sa
export SEED_SQLSERVER_PASSWORD=YourPassword
export SEED_SQLSERVER_PORT=1434
export SEED_SQLSERVER_DRIVER="ODBC Driver 18 for SQL Server"
```

You can also use a `.env` file (gitignored) in the repository root.

---

## Running the Seed Loader

### Load All Tables

```bash
python src/ingest/seed_loader.py --all
```

### Load Specific Tables

```bash
python src/ingest/seed_loader.py --tables DimFranchise,DimWork,DimScene
```

### Dry Run (Validation Only)

```bash
python src/ingest/seed_loader.py --all --dry-run
```

### Verbose Logging

```bash
python src/ingest/seed_loader.py --all --verbose
```

---

## Load Order

Tables are loaded in dependency order to satisfy foreign key constraints:

1. `DimFranchise` (no FK dependencies)
2. `DimIssueType` (no FK dependencies)
3. `DimContinuityFrame` → DimFranchise
4. `DimEra` → DimFranchise
5. `DimWork` → DimFranchise
6. `DimEventType` → DimFranchise (self-referencing parent)
7. `DimEntity` → DimFranchise
8. `DimScene` → DimWork
9. `DimSpecies` → DimEntity
10. `DimLocation` → DimEntity (self-referencing parent)
11. `DimCharacter` → DimEntity, DimSpecies
12. `DimTechAsset` → DimFranchise
13. `DimTechInstance` → DimEntity, DimTechAsset
14. `DimDroidModel` → DimTechAsset
15. `DimDroidInstance` → DimTechInstance
16. `FactEvent` → DimFranchise, DimContinuityFrame, DimWork, DimScene, DimEventType, DimLocation, DimEra (self-referencing parent)
17. `ContinuityIssue` → DimFranchise, DimContinuityFrame, DimIssueType, DimWork, DimScene
18. `FactClaim` → DimFranchise, DimContinuityFrame, DimEntity, DimWork, DimScene
19. `BridgeEventParticipant` → FactEvent, DimEntity
20. `BridgeEventAsset` → FactEvent, DimTechInstance
21. `BridgeContinuityIssueClaim` → ContinuityIssue, FactClaim

For TRUNCATE operations, tables are processed in **reverse order** to avoid FK violations.

---

## Adding New Seed Files

### Step 1: Choose Deterministic GUIDs

For reproducible seeding, use stable hard-coded GUIDs. Suggested naming convention:

```
TablePrefix + 8-digit sequence: 11111111-1111-1111-1111-111111111111
```

Or use UUIDv5 generation based on natural key values. The loader supports auto-generating GUIDs if `target.naturalKey` is defined and a row is missing its GUID column.

### Step 2: Handle Foreign Keys

Reference GUIDs from parent tables to determine FK values. The loader resolves GUID → Key mappings automatically when using `allowIdentityInsert: false`.

**Important**: Use a consistent cross-reference approach. For FK columns, you can either:

1. **Reference by stable integer** (when using `allowIdentityInsert: true` and controlling identity values)
2. **Let loader resolve** via GUID lookups (planned future enhancement)

Currently, FK integer keys must be known at seed-file creation time based on load order.

### Step 3: Add JSON/AttributesJson Columns

For tables with `AttributesJson` (NVARCHAR(MAX) column), provide a nested object:

```json
{
  "FranchiseGuid": "...",
  "Name": "Star Wars",
  "AttributesJson": {
    "founded": 1977,
    "creator": "George Lucas"
  }
}
```

The loader serializes this to `{"founded": 1977, "creator": "George Lucas"}` before insert.

### Step 4: Update Load Order

If adding a new table, update the `LOAD_ORDER` constant in `seed_loader.py`.

---

## RowHash Computation

The loader computes `RowHash` as:

1. Concatenate all non-excluded column values (excluding identity PK, UpdatedUtc, RowHash itself)
2. Compute SHA-256 hash
3. Store as `varbinary(32)` in the database

This enables change detection for future SCD operations.

---

## Safety Notes

- **Synthetic data only**: Seed files contain fictional Star Wars-themed data
- **No copyrighted content**: Do not commit real source material
- **Test environment only**: Seeds are designed for dev/test, not production
- **Backup first**: Running the loader will TRUNCATE target tables

---

## Smoke Test

1. Ensure SQL Server is running with the Holocron database created
2. Apply DDL scripts from `src/db/ddl/`
3. Configure connection environment variables
4. Run: `python src/ingest/seed_loader.py --all --dry-run`
5. If validation passes, run: `python src/ingest/seed_loader.py --all`
6. Verify with: `SELECT COUNT(*) FROM dbo.DimFranchise;`

---

## Troubleshooting

### FK Constraint Violation During TRUNCATE

The loader attempts TRUNCATE in reverse dependency order. If that fails (e.g., circular references), it falls back to:

1. `ALTER TABLE ... NOCHECK CONSTRAINT ALL`
2. `DELETE FROM <table>`
3. `ALTER TABLE ... WITH CHECK CHECK CONSTRAINT ALL`

### Missing GUID Column

If a row is missing its GUID column and no `naturalKey` is defined, the loader fails with an error. Either:

- Add the GUID explicitly in the seed row
- Define `naturalKey` in the seed file for auto-generation

### Column Validation Errors

Ensure all row fields match actual database column names. Run with `--dry-run` to validate before inserting.
