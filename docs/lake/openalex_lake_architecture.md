# OpenAlex Lake-First Architecture Plan

> **Status:** Planning / scaffolding — no full ETL or PDF download in this phase.

This document describes how OpenAlex snapshot data, artifact blobs (PDFs), and
metadata flow through the Holocron lake into a curated SQL subset and evidence
layer.

---

## 1. Data Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        Holocron Lake                            │
│                                                                 │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐  │
│  │  Raw (compressed)   │  │  Expanded (decompressed JSONL)   │  │
│  │  lake/openalex-     │  │  lake/openalex-                  │  │
│  │    snapshot/         │→ │    snapshot_decompressed/         │  │
│  │  *.gz (source of    │  │  *.jsonl (processing/indexing)   │  │
│  │   truth archives)   │  │                                  │  │
│  └─────────────────────┘  └──────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────┐                                        │
│  │  Artifacts          │                                        │
│  │  lake/openalex-     │                                        │
│  │    artifacts/       │                                        │
│  │    pdfs/<work_id>/  │                                        │
│  │      <file>.pdf     │                                        │
│  └─────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘

            │ selective ingest
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SQL Server (openalex schema)                  │
│                                                                 │
│  Thin metadata tables     Crosswalk / mapping     Evidence      │
│  ─────────────────────    ──────────────────────  ──────────    │
│  openalex.Work            openalex.EntityCrosswalk  llm.*       │
│  openalex.Author          (OpenAlex ↔ DimEntity)                │
│  openalex.ArtifactManifest                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Gravity Rules

| Data type | Where it lives | Why |
|---|---|---|
| Compressed `.gz` archives | Lake (raw) | Source of truth; immutable snapshots |
| Decompressed JSONL | Lake (expanded) | Processing, search, indexing |
| PDFs / binary blobs | Lake (artifacts) | Too large for SQL; referenced by pointer |
| Identifiers, titles, DOIs, dates | SQL thin tables | Fast queries, joins, discoverability |
| Crosswalks (OpenAlex ↔ DimEntity) | SQL mapping tables | Linking to Holocron core model |
| Evidence bundles & items | SQL (`llm.*` schema) | Existing evidence layer |

---

## 2. Artifact Blobs (PDFs)

### Lake Path Convention

```
lake/openalex-artifacts/
  pdfs/
    <work_id>/
      <work_id>.pdf
```

Where `<work_id>` is the OpenAlex Work ID (e.g., `W2741809807`).

### Artifact Manifest Record

Each acquired artifact is tracked by a manifest record (SQL or JSON sidecar):

| Field | Type | Description |
|---|---|---|
| `SourceSystem` | NVARCHAR(50) | `'openalex'` |
| `WorkExtKey` | NVARCHAR(100) | OpenAlex Work ID (e.g., `W2741809807`) |
| `ArtifactType` | NVARCHAR(20) | `'pdf'` |
| `License` | NVARCHAR(100) | OA license / status from OpenAlex |
| `OaStatus` | NVARCHAR(50) | e.g., `gold`, `green`, `hybrid`, `closed` |
| `HostVenue` | NVARCHAR(255) | Source venue name |
| `SourceUrl` | NVARCHAR(2048) | URL the PDF was retrieved from |
| `Sha256Hash` | CHAR(64) | SHA-256 hex digest |
| `ByteSize` | BIGINT | File size in bytes |
| `LakePath` | NVARCHAR(500) | Relative path in lake |
| `RetrievedUtc` | DATETIME2(3) | When the artifact was downloaded |
| `RetrievalStatus` | NVARCHAR(20) | `'success'`, `'failed'`, `'pending'` |
| `ErrorDetail` | NVARCHAR(MAX) | Error message if failed |

> **Note:** PDF downloading is **not implemented** in this phase.  This schema
> documents the intended contract for Phase 3.

---

## 3. SQL Schema Strategy

### A) Thin Metadata Tables (selective subset)

```sql
-- openalex.Work  (thin — only columns needed for search / linking)
CREATE TABLE openalex.Work (
    WorkKey             BIGINT IDENTITY(1,1) NOT NULL,
    WorkGuid            UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    WorkExtKey          NVARCHAR(100) NOT NULL,         -- OpenAlex ID e.g. W2741809807
    Doi                 NVARCHAR(500)     NULL,
    Title               NVARCHAR(2000)    NULL,
    PublicationYear     INT               NULL,
    PublicationDate     DATE              NULL,
    PrimaryVenue        NVARCHAR(500)     NULL,
    OaStatus            NVARCHAR(50)      NULL,
    CitedByCount        INT               NULL,
    ConceptsCsv         NVARCHAR(MAX)     NULL,         -- lightweight denorm
    AuthorshipJson      NVARCHAR(MAX)     NULL,         -- lightweight denorm
    IsActive            BIT NOT NULL DEFAULT 1,
    CreatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_Work PRIMARY KEY CLUSTERED (WorkKey),
    CONSTRAINT UQ_Work_ExtKey UNIQUE (WorkExtKey)
);
```

Optional companion tables (thin stubs):

```sql
-- openalex.Author
CREATE TABLE openalex.Author (
    AuthorKey           BIGINT IDENTITY(1,1) NOT NULL,
    AuthorGuid          UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    AuthorExtKey        NVARCHAR(100) NOT NULL,
    DisplayName         NVARCHAR(500)     NULL,
    Orcid               NVARCHAR(100)     NULL,
    IsActive            BIT NOT NULL DEFAULT 1,
    CreatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_Author PRIMARY KEY CLUSTERED (AuthorKey),
    CONSTRAINT UQ_Author_ExtKey UNIQUE (AuthorExtKey)
);

-- openalex.ArtifactManifest
CREATE TABLE openalex.ArtifactManifest (
    ArtifactManifestKey BIGINT IDENTITY(1,1) NOT NULL,
    SourceSystem        NVARCHAR(50)  NOT NULL DEFAULT 'openalex',
    WorkExtKey          NVARCHAR(100) NOT NULL,
    ArtifactType        NVARCHAR(20)  NOT NULL DEFAULT 'pdf',
    License             NVARCHAR(100)     NULL,
    OaStatus            NVARCHAR(50)      NULL,
    HostVenue           NVARCHAR(255)     NULL,
    SourceUrl           NVARCHAR(2048)    NULL,
    Sha256Hash          CHAR(64)          NULL,
    ByteSize            BIGINT            NULL,
    LakePath            NVARCHAR(500)     NULL,
    RetrievedUtc        DATETIME2(3)      NULL,
    RetrievalStatus     NVARCHAR(20)  NOT NULL DEFAULT 'pending',
    ErrorDetail         NVARCHAR(MAX)     NULL,
    CreatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_ArtifactManifest PRIMARY KEY CLUSTERED (ArtifactManifestKey)
);
```

### B) Crosswalk / Mapping Table

```sql
-- openalex.EntityCrosswalk
--   Links an OpenAlex external ID to a Holocron DimEntity.
CREATE TABLE openalex.EntityCrosswalk (
    EntityCrosswalkKey  BIGINT IDENTITY(1,1) NOT NULL,
    SourceSystem        NVARCHAR(50)  NOT NULL DEFAULT 'openalex',
    ExternalIdType      NVARCHAR(50)  NOT NULL,          -- 'openalex_work', 'doi', etc.
    ExternalIdValue     NVARCHAR(500) NOT NULL,
    EntityKey           BIGINT            NULL,           -- FK → dbo.DimEntity.EntityKey
    MatchMethod         NVARCHAR(50)      NULL,           -- 'auto', 'manual', 'doi_match'
    MatchConfidence     DECIMAL(5,4)      NULL,           -- 0.0000–1.0000
    IsOverride          BIT NOT NULL DEFAULT 0,
    IsActive            BIT NOT NULL DEFAULT 1,
    CreatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedUtc          DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_EntityCrosswalk PRIMARY KEY CLUSTERED (EntityCrosswalkKey),
    CONSTRAINT UQ_EntityCrosswalk_Ext UNIQUE (SourceSystem, ExternalIdType, ExternalIdValue)
);
```

**Design decisions:**

- Supports **multiple external IDs per entity** (DOI + OpenAlex ID + ORCID…).
- `MatchMethod` + `MatchConfidence` support auto-matching and manual overrides.
- `IsOverride` flag lets curators pin a mapping regardless of auto-matching.
- `IsActive` enables soft-delete / versioning.

### C) Evidence Attachment Pattern

OpenAlex works become evidence through the existing `llm.evidence_*` tables:

```
openalex.Work  ──(WorkExtKey)──→  openalex.EntityCrosswalk  ──(EntityKey)──→  dbo.DimEntity
                                                                                     │
                                                                                     ▼
                                                                          llm.evidence_bundle
                                                                                     │
                                                                          llm.evidence_item
                                                                            ├─ source_system = 'openalex'
                                                                            ├─ source_uri = '<openalex_work_url>'
                                                                            ├─ selector_json  (excerpt/span)
                                                                            └─ role = 'citation'
```

- An `llm.evidence_item` references the OpenAlex work via `source_system` +
  `source_uri`.
- Optional `selector_json` stores excerpt/quote spans for PDF evidence.
- `llm.evidence_bundle` groups related items and links to DVO fact rows via
  `EvidenceBundleGuid`.

---

## 4. Indexing / Search Strategy

### Strategy 1: SQL-First Subset

1. Filter decompressed JSONL by concepts, topics, or author affiliations.
2. Ingest matching records into `openalex.Work` thin table.
3. Build crosswalks to `dbo.DimEntity`.
4. Query via standard SQL joins.

**Pros:** Simple, uses existing infrastructure.  
**Cons:** Limited to pre-selected subset; re-ingestion required for new filters.

### Strategy 2: External Index (Plan Only)

1. Build a search index from decompressed JSONL (e.g., SQLite FTS, Tantivy,
   or a lightweight full-text engine).
2. Query the index to discover relevant works.
3. Store only pointers (WorkExtKey, lake path) in SQL.
4. Optionally extract text from PDFs and add to the index.

**Pros:** Search across entire snapshot without SQL ingestion.  
**Cons:** Requires additional tooling; consistency management with SQL.

> The choice between strategies depends on scale and query patterns.  Strategy 1
> is recommended for the initial phase.

---

## 5. Repo Integration Plan

### Folder Structure

```
scripts/lake/
  decompress_gz_tree.py      ← Phase 0 (this PR)
  decompress_gz_tree.ps1     ← Phase 0 (this PR)

docs/lake/
  openalex_decompression.md  ← Phase 0 (this PR)
  openalex_lake_architecture.md  ← Phase 0 (this PR, this file)

src/db/ddl/00_ingest/
  (existing ingest tables)

src/db/ddl/
  04_openalex/               ← Phase 1 (future)
    openalex.Work.sql
    openalex.Author.sql
    openalex.EntityCrosswalk.sql
    openalex.ArtifactManifest.sql

db/migrations/
  NNNN_openalex_schema.sql   ← Phase 1 (future)

configs/
  openalex_ingest_filter.example.yaml  ← Phase 1 (future)
```

### Phase Plan

| Phase | Scope | Deliverables |
|---|---|---|
| **0** | Decompression + lake layout | `decompress_gz_tree.py/ps1`, docs |
| **1** | Thin metadata loader + crosswalk | `openalex.*` schema DDL, selective JSONL → SQL loader, `EntityCrosswalk` population |
| **2** | Evidence linkage | Work → `llm.evidence_item` pipeline, DVO bundle attachment |
| **3** | Artifact blobs | PDF acquisition script, `ArtifactManifest` population, optional text extraction |
