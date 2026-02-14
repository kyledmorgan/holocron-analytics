# Agent Database Documentation

This folder contains canonical rules, templates, and checklists for database work in holocron-analytics. Any agent or contributor working on SQL DDL, migrations, or schema changes should start here.

## Quick Start

1. **Read the policies** in `db_policies.md` before writing any DDL
2. **Use templates** from `db_templates.md` for new tables/views
3. **Follow the checklist** in `db_review_checklist.md` before submitting PRs

## Contents

| Document | Description |
|----------|-------------|
| [db_policies.md](db_policies.md) | Canonical naming conventions, key patterns, datetime standards, schema ownership |
| [db_templates.md](db_templates.md) | Copy-paste templates for tables, views, migrations |
| [db_review_checklist.md](db_review_checklist.md) | PR review checklist for SQL changes |

## Key Rules Summary

### Naming Conventions

| Pattern | Usage | Example |
|---------|-------|---------|
| `...Key` | Internal surrogate keys (INT for dims, BIGINT for facts) | `EntityKey INT`, `EventKey BIGINT` |
| `...Guid` | Public-facing stable identifiers | `EntityGuid UNIQUEIDENTIFIER DEFAULT (NEWID())` |
| `...ExtKey` | External/source system numeric IDs | `WookieepediaExtKey INT` |
| `...NaturalKey` | External/source system text IDs | `SourceNaturalKey NVARCHAR(400)` |
| `...Utc` | All UTC timestamps | `CreatedUtc DATETIME2(3)` |

### Schema Ownership

| Schema | Purpose |
|--------|---------|
| `dbo` | Core dimensional model (Dim*, Fact*, Bridge*) |
| `ingest` | Raw ingestion tables and work queues |
| `llm` | LLM chat/interrogation runtime |
| `vector` | Embedding and retrieval runtime |
| `sem` | Semantic layer views and curated tables |

### Anti-Patterns to Avoid

- ❌ `...Id` for any column (use `...Key`, `...Guid`, or `...ExtKey`)
- ❌ `NEWSEQUENTIALID()` for public GUIDs (security risk - use `NEWID()`)
- ❌ `DATETIME` type (use `DATETIME2(3)`)
- ❌ `dbo.sem_*` views (should be `sem.vw_*`)
- ❌ Ambiguous timestamps without `Utc` suffix

## Related Documentation

- [Schema Refactor Report](../db/schema_refactor_report.md) — Changes from the standardization migration
- [ERD Explained](../diagrams/mermaid/ERD_Explained.md) — Full schema documentation with column dictionaries
- [DDL Ordering and Manifest](../../agents/playbooks/db/ddl_ordering_and_manifest.md) — DDL file organization
