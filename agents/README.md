# Agents Overview

This folder contains tool-agnostic policies, playbooks, and templates for contributors and automation.

Start here:
- `agents/policies/00_global.md`
- `agents/policies/10_ip-and-data.md`
- `agents/policies/20_security-and-secrets.md`
- `agents/policies/30_style-and-structure.md`

Playbooks:
- `agents/playbooks/docs/update_docs_and_links.md`
- `agents/playbooks/db/ddl_ordering_and_manifest.md`
- `agents/playbooks/db/seed_expansion_framework.md`
- `agents/playbooks/pipeline/ingest_transform_load.md`

Templates:
- `agents/templates/prompts/extraction_template.md`

---

## Documentation Maintenance

### Periodic Documentation Refresh

Documentation should be refreshed periodically to ensure accuracy. A documentation refresh pass includes:

1. **Review deltas** since the last cleanup (commits touching docs, README files, or indexes)
2. **Update stale content** to reflect current state
3. **Move misplaced documentation** (e.g., root-level markdown that belongs in `/docs/`)
4. **Update the docs index** at `docs/DOCS_INDEX.md`
5. **Produce a folder structure report** if structural improvements are identified

### Folder Structure Reports

Structural improvement proposals are documented in `docs/_reports/`:

- [Folder Structure Recommendations](../docs/_reports/folder-structure-recommendations.md) — Current proposals for repository organization improvements

These reports are **proposal-only** and do not represent implemented changes. Code moves require a separate, explicit approval and implementation pass.

### Next Steps for Future Agents

When performing documentation work:

1. **Consult `docs/DOCS_INDEX.md`** first to understand the documentation landscape
2. **Follow `agents/playbooks/docs/update_docs_and_links.md`** for the standard update workflow
3. **Check `docs/_reports/`** for pending structural proposals before making changes
4. **Avoid moving code files** unless explicitly instructed — documentation moves are safe; code moves may break paths
