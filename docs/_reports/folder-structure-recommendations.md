# Folder Structure Recommendations Report

**Date:** 2026-01-21  
**Scope:** Documentation-only review; code moves are explicitly out of scope  
**Status:** Proposal only — no code path changes in this pass

---

## Purpose

This report identifies opportunities to improve the repository's folder structure and file placement. It is produced as part of a documentation refresh and root-directory cleanup pass.

**Important:** This report contains recommendations only. No code files, source directories, or runtime paths were moved or renamed as part of this review.

---

## Summary of Changes Made (This Pass)

| Old Path | New Path | Reason |
|----------|----------|--------|
| `/OPENALEX_IMPLEMENTATION.md` | `/docs/integrations/openalex-implementation-summary.md` | Implementation summary belongs in docs, not root |

---

## Root Directory Inventory

### Files That Belong at Root (Operational/Config)

| File | Reason for Root Placement |
|------|---------------------------|
| `README.md` | Standard OSS convention: primary project entry point |
| `LICENSE` | Standard OSS convention: must be at root for discoverability |
| `.env.example` | Common pattern: environment template at root for visibility |
| `.gitignore` | Git convention: must be at root |
| `.dockerignore` | Docker convention: must be at root |
| `.editorconfig` | Editor tooling convention: must be at root |
| `requirements.txt` | Python convention: pip expects at root for simple projects |
| `Dockerfile` | Docker convention: commonly at root for single-image projects |
| `compose.yaml` | Docker Compose convention: primary compose file at root |
| `docker-compose.yml` | Docker Compose convention: alternative naming |
| `compose.debug.yaml` | Docker Compose convention: override file at root |
| `_effective-compose.yml` | Appears to be generated/debug output; see recommendations below |
| `AGENTS.md` | Agent policy reference; intentionally at root per `docs/DOCS_INDEX.md` |
| `Ingest.session.sql` | Editor session file; see recommendations below |

### Documentation Files at Root (Reviewed)

| File | Status | Notes |
|------|--------|-------|
| `README.md` | ✅ Stays at root | Primary entry point |
| `AGENTS.md` | ✅ Stays at root | Intentional by design; serves as quick-reference for agents |
| `OPENALEX_IMPLEMENTATION.md` | ✅ Moved | Now at `docs/integrations/openalex-implementation-summary.md` |

---

## Root-Level Files: Analysis and Recommendations

### Files That Should Stay at Root

1. **`README.md`** — Required at root by OSS convention
2. **`LICENSE`** — Required at root for license discoverability
3. **`AGENTS.md`** — Intentionally placed at root as a quick-reference pointer to agent policies
4. **`.env.example`** — Visibility convention for environment templates
5. **`.gitignore`, `.dockerignore`, `.editorconfig`** — Tooling conventions require root placement
6. **`requirements.txt`** — Python ecosystem expects this at root for simple pip installs
7. **`Dockerfile`** — Docker build context expects this at root unless overridden
8. **`compose.yaml`, `docker-compose.yml`, `compose.debug.yaml`** — Docker Compose convention

### Files Recommended for Review (Proposal Only)

| File | Current Location | Proposed Location | Rationale |
|------|------------------|-------------------|-----------|
| `_effective-compose.yml` | Root | `docker/` or `.gitignore` | Appears to be generated/debug output; should not be committed or should be in `docker/` subfolder |
| `Ingest.session.sql` | Root | `local/` (gitignored) or delete | Editor session artifact; should not be committed |

---

## Proposed Target Structure

The following tree view illustrates a proposed ideal structure. **This is a recommendation only; no structural changes to code directories were made in this pass.**

```
holocron-analytics/
├── .github/                    # GitHub workflows, issue templates (future)
├── .vscode/                    # Editor config
├── agents/                     # Agent policies, playbooks, templates
│   ├── policies/
│   ├── playbooks/
│   └── templates/
├── config/                     # Configuration templates (no secrets)
├── docker/                     # Docker-related scripts and overrides
│   └── (propose moving _effective-compose.yml here if needed)
├── docs/                       # All documentation
│   ├── _reports/               # Generated reports (this file)
│   ├── adr/                    # Architecture Decision Records (future)
│   ├── data-quality/           # Data quality reports
│   ├── diagrams/               # Mermaid diagrams, ERDs
│   ├── integrations/           # Integration guides (NEW)
│   │   └── openalex-implementation-summary.md
│   ├── lessons/                # SQL learning content
│   ├── modeling/               # Data modeling notes (future)
│   ├── runbooks/               # Operational runbooks
│   ├── vision/                 # Project vision and roadmap
│   ├── DOCS_INDEX.md           # Documentation home
│   ├── REPO_STRUCTURE.md       # Repository layout guide
│   └── openalex-integration.md # User guide (existing)
├── exercises/                  # Learning exercises
├── local/                      # Local-only data (gitignored)
├── prompts/                    # Runtime prompts
├── scripts/                    # Helper scripts
├── sources/                    # Source definitions
├── src/                        # Source code
│   ├── db/                     # Database DDL, seeds
│   ├── ingest/                 # Ingestion framework
│   └── ...
├── web/                        # Web application assets
├── AGENTS.md                   # Agent quick-reference (stays at root)
├── README.md                   # Project entry point (stays at root)
├── LICENSE                     # License file (stays at root)
├── requirements.txt            # Python dependencies (stays at root)
├── Dockerfile                  # Docker build (stays at root)
├── compose.yaml                # Docker Compose (stays at root)
└── docker-compose.yml          # Docker Compose alt (stays at root)
```

---

## Specific Recommendations (Proposal Only)

### 1. Move or Gitignore Editor Session Files

**File:** `Ingest.session.sql`

**Issue:** This appears to be a database IDE session file (Azure Data Studio, VS Code SQL extension). It should not be committed.

**Recommendation:**
- Add `*.session.sql` to `.gitignore`, OR
- Delete the file if it was committed accidentally

**Priority:** Low (cosmetic)

### 2. Review `_effective-compose.yml`

**File:** `_effective-compose.yml`

**Issue:** The leading underscore suggests this is a generated or temporary file. If it's needed, it should be documented; if not, it should be gitignored.

**Recommendation:**
- If generated: add to `.gitignore`
- If needed for reference: move to `docker/` with documentation
- If intentionally committed: add a comment at the top explaining its purpose

**Priority:** Low (cosmetic)

### 3. Consider Consolidating Docker Files

**Current State:** Multiple compose files at root (`compose.yaml`, `docker-compose.yml`, `compose.debug.yaml`, `_effective-compose.yml`)

**Observation:** Having multiple compose files at root is acceptable per Docker conventions. However, if the number grows, consider using a `docker/` subdirectory for override files.

**Recommendation:** No change needed currently. If more Docker configurations are added, consider:
- Keep primary `compose.yaml` or `docker-compose.yml` at root
- Move override files to `docker/overrides/`

**Priority:** Low (future consideration)

### 4. Integrate `docs/integrations/` with Index

**Status:** Completed in this pass. The new `docs/integrations/` folder has been added and will be referenced in `docs/DOCS_INDEX.md`.

---

## Out of Scope (Explicitly Not Changed)

The following items were reviewed but are **explicitly out of scope** for this documentation refresh:

1. **Source code reorganization** — No changes to `src/` structure
2. **Script refactoring** — No changes to `scripts/` organization
3. **Database structure changes** — No changes to `src/db/` layout
4. **CI/CD configuration** — No changes to workflow files
5. **Package structure changes** — No changes to Python module organization
6. **Breaking path changes** — No changes that would affect imports or file references

---

## Next Steps (Suggested)

1. **Review this report** and decide which recommendations to implement
2. **Create follow-up issues** for approved structural changes
3. **Schedule a future "structure cleanup" pass** if needed, separate from documentation
4. **Update `.gitignore`** for `*.session.sql` files (minor, low-risk)

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-21 | Documentation Agent | Initial report during doc cleanup pass |
