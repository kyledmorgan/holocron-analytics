# Web Directory

This directory is a placeholder for future web application components related to visualization, data exploration, and analytics reporting.

---

## Directory Structure

```
web/
├── app/        # Web application code (placeholder)
├── static/     # Static assets (CSS, JS, images) (placeholder)
└── viz/        # Data visualization components (placeholder)
```

---

## Status

🚧 **Under Development** — This directory structure is reserved for future web-based features.

---

## Planned Features

The web directory will eventually contain:

### Web Application (`app/`)

- **Query Interface** — Web UI for exploring the database
- **Schema Browser** — Interactive schema documentation
- **Data Explorer** — Browse entities, events, and relationships
- **API Endpoints** — RESTful API for data access

### Static Assets (`static/`)

- CSS stylesheets
- JavaScript libraries
- Images and icons
- Web fonts

### Visualizations (`viz/`)

- **Timeline Visualizations** — Event chronology and continuity
- **Relationship Graphs** — Character and entity relationships
- **Data Quality Dashboards** — Coverage and quality metrics
- **LLM Derive Analytics** — Job status and artifact exploration

---

## Technology Stack (Planned)

When implemented, the web components will likely use:

- **Backend Framework:** Flask or FastAPI (Python)
- **Database Access:** SQLAlchemy or direct pyodbc
- **Frontend:** HTML5, CSS3, vanilla JavaScript (initially)
- **Visualization:** D3.js, Mermaid.js, or similar
- **Static Site Generation:** Optional (for docs rendering)

---

## Design Principles

When building web components, follow these principles:

1. **Read-Only by Default** — Web UI should be primarily for data exploration, not modification
2. **Static-First** — Prefer static HTML generation over dynamic rendering when possible
3. **No Authentication (Yet)** — Assume local/trusted environment initially
4. **Mobile-Friendly** — Responsive design for tablets and phones
5. **Performance** — Lazy loading, pagination, and efficient queries
6. **Accessibility** — Follow WCAG guidelines for accessible web content

---

## Current State

All subdirectories currently contain only `.gitkeep` files. No web application code exists yet.

To contribute web components:

1. Follow the repository's [agent policies](../agents/README.md)
2. Document any new frameworks or dependencies
3. Keep web components optional (database should work without them)
4. Add tests for any API endpoints or server-side logic
5. Update this README with usage instructions

---

## Alternative: Static Site

As an alternative to a full web application, consider generating a static site from the documentation and data:

- **Markdown → HTML:** Convert docs to a browsable site
- **Data Snapshots:** Export JSON/CSV for offline exploration
- **Embedded Visualizations:** Mermaid diagrams, timeline charts
- **No Server Required:** Pure static HTML + CSS + JS

This approach aligns with the project's focus on local development and reproducibility.

---

## Related Documentation

- [Root README](../README.md) — Project overview
- [Documentation Index](../docs/DOCS_INDEX.md) — All documentation files
- [Project Vision](../docs/vision/ProjectVision.md) — Long-term goals
- [Repository Structure](../docs/REPO_STRUCTURE.md) — Folder organization

---

## Examples from Other Projects

For inspiration, consider:

- **Datasette** — Lightweight data exploration tool (https://datasette.io/)
- **Superset** — Open-source BI platform
- **Metabase** — Simple analytics and dashboards
- **Observable** — Notebook-style data exploration
- **D3 Gallery** — Interactive visualization examples

---

## Contributing

If you want to work on web features:

1. Open an issue to discuss the proposed feature
2. Start small (e.g., a single static page or API endpoint)
3. Document dependencies and setup in this README
4. Ensure the web components are optional (don't break non-web workflows)
5. Add tests for any server-side logic

---

## Questions?

For questions about the web directory or to propose new features, open an issue in the repository.
