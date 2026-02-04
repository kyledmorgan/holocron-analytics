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
