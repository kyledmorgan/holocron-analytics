# SQL Source-of-Truth & Repo Synchronization Policy

> **Mandatory** for any PR that touches SQL or any pipeline component dependent on SQL objects.

This policy keeps **SQL Server (Docker)** and the **Git repository** in tight, auditable sync for:

- **Tables / Schemas (DDL)**
- **Stored procedures / functions / triggers (programmable objects)**
- **Views**
- **Migrations** (forward-only scripts that apply incremental changes)

---

## 1. Repository Folder Conventions

We maintain two categories of SQL artifacts:

### A) Canonical Object Definitions ("current state")

These are the **authoritative "what it is now"** definitions and must match what exists in SQL Server after the latest migrations.

| Category | Location | Contents |
|----------|----------|----------|
| **DDL** | `src/db/ddl/` | Full CREATE definitions for schemas, tables, types, constraints |
| **DML** | `src/db/dml/stored_procedures/` | Stored procedure definitions |
| | `src/db/dml/functions/` | Scalar + table-valued function definitions |
| | `src/db/dml/triggers/` | Trigger definitions |
| **Views** | `src/db/views/{schema}/` | View definitions (1 file per view) |

**Rule:** Each object must have a single canonical file that represents the *latest definition*.

### B) Migrations ("how we got there")

| Category | Location | Contents |
|----------|----------|----------|
| **Migrations** | `db/migrations/` | Incremental forward-only scripts, sequentially numbered |

**Rule:** If a PR changes SQL behavior or schema:
1. Add a migration script (forward-only change), **AND**
2. Update the canonical definition file(s) in `ddl/`, `dml/`, and/or `views/`.

**No exceptions.** Migrations are not a substitute for updating the canonical definitions.

---

## 2. File Naming Conventions

One file per object. Include schema prefix in the filename:

```
src/db/dml/stored_procedures/dbo.usp_claim_next_job.sql
src/db/dml/stored_procedures/llm.usp_enqueue_run.sql
src/db/dml/functions/dbo.fn_calculate_score.sql
src/db/dml/triggers/dbo.trg_audit_insert.sql
src/db/views/sem/sem.vw_event.sql
src/db/views/llm/llm.vw_queue_health.sql
```

---

## 3. Synchronization Expectations

### Repo ↔ SQL Server Must Match

At any point in time:

- If an object exists in SQL Server → it **must** exist as a definition file in the repo.
- If a definition exists in the repo → it **must** exist in SQL Server (or be intentionally pending via migration).

---

## 4. Baseline Sync (One-Time Backfill)

Use the extraction script to perform the initial synchronization:

```bash
python scripts/db/extract_sql_objects.py --extract --verbose
```

This connects to the Docker SQL Server instance, extracts all programmable object and view definitions, and writes them to:

- `src/db/dml/**` for stored procedures / functions / triggers
- `src/db/views/**` for views

After baseline sync:
- The repo becomes the **paper trail** of definitions.
- Migrations become the **paper trail** of changes.

---

## 5. Ongoing PR Requirements

Any PR that modifies SQL **MUST** include:

1. **Migration script** — adds/changes columns, constraints, indexes, views, procs, functions, or triggers.
2. **Updated canonical definition file(s)** — full object definition reflecting the post-migration end state.
3. **Reconciliation check** — confirm repo files match SQL Server after applying migrations.

### Reconciliation Command

```bash
# Report-only (no file changes):
python scripts/db/extract_sql_objects.py --reconcile --verbose

# Extract + reconcile:
python scripts/db/extract_sql_objects.py --extract --reconcile --verbose

# Dry-run (see what would be written):
python scripts/db/extract_sql_objects.py --extract --dry-run
```

---

## 6. Agent Operating Instructions

When performing SQL work, agents **MUST**:

1. **Locate existing definitions in the repo first**
   - Search: `src/db/ddl/`, `src/db/dml/`, `src/db/views/`

2. **If missing or suspected out of sync**
   - Extract the object definition from SQL Server
   - Create/update the appropriate canonical file

3. **Always produce a migration**
   - Even if the object "already exists" in SQL Server, the migration documents the change

4. **Never "patch" SQL objects only via migrations**
   - Canonical definitions must be updated so the repo represents the latest end state

5. **When unsure whether SQL Server or repo is correct**
   - Treat SQL Server as "runtime truth" and repo as "desired truth"
   - Reconcile explicitly by extracting from SQL Server and deciding what becomes canonical

---

## 7. Reconciliation / Diff Strategy

The extraction script uses a repeatable **extract → diff → update** workflow:

- Queries `sys.objects`, `sys.schemas`, and `sys.sql_modules` to extract definitions
- Normalizes output for stable diffs:
  - Consistent line endings (LF)
  - Strips `USE [database]` statements
  - Removes environment-specific database qualifiers
  - Trims trailing whitespace
- Compares extracted output to repo files:
  - **SQL has objects not in repo** → baseline gap (add them)
  - **Repo has objects not in SQL** → stale file or pending migration (confirm intent)
  - **Definitions differ** → update canonical file(s) or fix migration ordering

---

## 8. Related Documentation

- [DB Naming Conventions](DB_NAMING_CONVENTIONS.md)
- [DB Schema Change Workflow](DB_SCHEMA_CHANGE_WORKFLOW.md)
- [DB Review Checklist](db_review_checklist.md)
- [DB Policies](db_policies.md)
- [SQL Style Guide](SQL_STYLE_GUIDE.md)
