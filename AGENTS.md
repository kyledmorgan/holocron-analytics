# AGENTS

These instructions apply to any automated or human agent working in this repository. Keep changes small, documented, and aligned with the repo structure.

Key rules:
- Stay tool-agnostic and model-agnostic.
- Prefer placeholders and templates over real data or secrets.
- Follow the repo layout and keep documentation links up to date.

More details:
- `agents/README.md`
- `agents/policies/00_global.md`
- `agents/policies/10_ip-and-data.md`
- `agents/policies/20_security-and-secrets.md`
- `agents/policies/30_style-and-structure.md`

Subsystem-specific guidance:
- `agents/llm-derived-data.md` — LLM-Derived Data subsystem rules (docs-first, contract-first, evidence-only citations)

## Documentation and cross-reference requirements

The repository uses a **link-first** navigation system. The central concept
catalog is [`docs/reference/README.md`](docs/reference/README.md); the full
standard is
[`docs/contributing/documentation-and-links.md`](docs/contributing/documentation-and-links.md).

When adding a new major concept, SQL object, job, runner, CLI, persistent data
structure, or architectural boundary:

1. Determine whether it requires a canonical definition.
2. Add it to the appropriate grouped reference document under `docs/reference/`.
3. Link the definition to its primary implementation.
4. Link major implementation entry points back to architecture or runbook
   documentation where useful.
5. Add links selectively; do not hyperlink every occurrence of a term.
6. Use repository-relative Markdown links (not hardcoded GitHub URLs).
7. Use stable Markdown headings for canonical definitions.
8. Update related architecture diagrams when relationships change.
9. Distinguish implemented state from planned state (label planned work).
10. Run Markdown link validation before completing the change:
    `python scripts/quality/check_markdown_links.py`.
11. Do not rely on IDE-only references as the sole navigation method.
12. Do not document internal helper functions unless they are architecturally
    meaningful.

Also update the
[concept inventory](docs/reference/repository-concept-inventory.md) when you:
create a new SQL schema or major table; introduce a new CLI; add a new job or
runner; add a new lake dataset; create a new artifact type; add a new evidence
relationship; introduce a new domain concept; or materially change an existing
subsystem relationship.

## Feature-Series Naming Convention

When a body of work is intentionally split across multiple phases or pull requests,
it must use a canonical feature-series identifier of the form
`YYYY_MM_<short_feature_name>_phase_<number>` (for example,
`2026_02_entity_extraction_phase_1`). **Never** use a bare, unqualified reference
such as `Phase 0`, `Phase 1`, or `next phase` to describe multi-PR feature work,
because multiple unrelated initiatives have historically each had their own
`Phase 1`/`Phase 2`.

- Rules: `docs/contributing/feature-series-convention.md`
- Reconstructed history of past series: `docs/history/feature-series/README.md`
- Legacy reference inventory: `docs/history/phase-reference-inventory.md`

Not every change needs a feature series — small, independent changes are fine to
document via PR descriptions and changelogs. The word "phase" remains valid for
genuine domain terminology (for example, "execution phase", "parsing phase").


## Bruno API Collection Syntax

When working with Bruno `.bru` files in `tools/bruno/`:

### File Structure
Bruno requests use a block-based format with specific sections:

```
meta {
  name: Request Name
  type: http
  seq: 1
}

get|post|put|delete|patch {
  url: {{VARIABLE}}/path
  body: none|json|text|xml|form-urlencoded|multipart-form
  auth: none|basic|bearer
}

body:json {
  {
    "key": "{{VARIABLE}}",
    "nested": {
      "value": 123
    }
  }
}

tests {
  test("Description", function() {
    expect(res.status).to.equal(200);
    expect(res.body).to.have.property('key');
  });
}

docs {
  Markdown documentation here
}
```

### Variables
- Use `{{VARIABLE_NAME}}` syntax for variable interpolation
- Variables are defined in environment files: `environments/*.bru`
- Can be nested: `{{BASE_URL}}/api` where `BASE_URL` contains `http://localhost:8080`

### Environment Files
Located in `environments/` folder at collection root:

```
vars {
  BASE_URL: http://localhost:8080
  API_KEY: placeholder-key
  TIMEOUT: 30
}
```

### Tests
Use Chai-style assertions:
- `expect(res.status).to.equal(200)`
- `expect(res.body).to.have.property('field')`
- `expect(data.array).to.be.an('array')`
- Access response via `res.status`, `res.body`, `res.headers`

### Best Practices
1. **File naming:** Use descriptive names with spaces (e.g., `Get version.bru`)
2. **Request organization:** Group related requests in folders with numeric prefixes (e.g., `00 - Setup/`)
3. **Variables:** Define all configurable values as environment variables
4. **Documentation:** Use `docs` block to explain request purpose and expected responses
5. **Tests:** Add basic assertions for status codes and response structure
6. **Git-friendly:** Bruno files are plain text and work well with version control

### Collection Metadata
Each collection needs a `bruno.json` at its root:

```json
{
  "version": "1",
  "name": "Collection Name",
  "type": "collection"
}
```

### Example: Ollama Smoke Tests
Reference implementation: `tools/bruno/ollama-smoke-tests/`
- Environment-based configuration (local vs. docker-network)
- Request taxonomy by functionality
- JSON contract validation with tests
- Comprehensive documentation
