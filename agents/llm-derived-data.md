# Agent Guidance: LLM-Derived Data

## Scope

This document provides guidance for agents (human or automated) working on the **LLM-Derived Data** subsystem (`src/llm/`).

## Principles

### Docs-First

1. **Document before implementing** — Create or update documentation before writing code
2. **Contract-first** — Define JSON schemas before implementing extraction logic
3. **Evidence-only citations** — All derived data must trace to explicit evidence

### Minimal Changes

1. **Additive changes preferred** — Add new files/modules rather than restructuring existing ones
2. **No broad refactors** — Do not reorganize existing modules (ingest, db, etc.) as part of LLM work
3. **Surgical edits** — When modifying existing files, make the smallest possible change

### Coding Conventions

Follow existing repository patterns:

1. **Module structure** — Mirror patterns from `src/ingest/`:
   - `core/` for types and exceptions
   - `config/` for configuration loading
   - `storage/` for persistence
   - `runner/` for orchestration

2. **Type hints** — Use Python type hints on all functions

3. **Docstrings** — Include docstrings on all public classes and methods

4. **Dataclasses** — Use `dataclasses` for data models (not Pydantic, unless repo-wide adoption occurs)

5. **Logging** — Use `logging.getLogger(__name__)` pattern

6. **Error handling** — Define custom exceptions in `core/exceptions.py`

## Guardrails

### DO NOT

- **Refactor broadly** — Do not move files outside `src/llm/` as part of LLM work
- **Change ingest module** — Do not modify `src/ingest/` (patterns can be referenced but not touched)
- **Commit secrets** — Never commit API keys, passwords, or sensitive data
- **Implement full features** — Scaffolding and interfaces only in Phase 0

### DO

- **Follow existing patterns** — Look at how `src/ingest/` does things first
- **Update documentation** — Keep docs current with code changes
- **Test imports** — Ensure new modules are importable without errors
- **Use stubs** — Prefer interface definitions over full implementations in early phases

## File Locations

| Purpose | Location |
|---------|----------|
| Source code | `src/llm/` |
| JSON schemas | `src/llm/contracts/` |
| Configuration | `src/llm/config/` (docs), `config/llm.yaml` (runtime) |
| Documentation | `docs/llm/` |
| Agent guidance | `agents/llm-derived-data.md` (this file) |
| Smoke tests | `scripts/llm_smoke_test.py` |

## Testing

### Import Tests

Before committing, verify that modules import without error:

```bash
python -c "from src.llm import *"
python -c "from src.llm.core import *"
python -c "from src.llm.providers import OllamaClient"
python -c "from src.llm.runners import DeriveRunner"
```

### Smoke Tests

Run the smoke test to verify provider connectivity:

```bash
python scripts/llm_smoke_test.py
```

### No Breaking Changes

Ensure existing tests still pass:

```bash
# Run any existing tests (if present)
pytest src/llm/tests/ -v  # (tests may not exist yet)
```

## Related Documents

- [LLM-Derived Data Overview](../docs/llm/derived-data.md)
- [LLM Module README](../src/llm/README.md)
- [Global Policy](policies/00_global.md)
- [Style and Structure](policies/30_style-and-structure.md)
