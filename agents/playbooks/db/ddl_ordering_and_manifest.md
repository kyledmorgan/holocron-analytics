# DDL Ordering and Manifest

- Place DDL files in `db/ddl/` using numeric prefixes.
- Group by purpose in subfolders (dimensions, facts, bridges, views, procs).
- Track execution order in `db/runner/manifest.json`.
- Keep the manifest deterministic and reviewable.
