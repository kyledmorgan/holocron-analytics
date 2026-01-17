# Doc Updates and Cross-Links

When adding or moving documentation:
- Update `docs/REPO_STRUCTURE.md` if the structure changes.
- Keep links in `README.md` and `AGENTS.md` current.
- Add short context for new docs and link them from the relevant area.

---

## Documentation Update Workflow

When asked to update documentation, follow this standard process:

1. **Consult the documentation index** first: Open `docs/DOCS_INDEX.md` to understand the current documentation landscape and identify authoritative docs.

2. **Identify the correct document(s)** to modify. Avoid creating redundant or duplicate documentation—edit existing docs in-place when possible.

3. **Apply additive edits** to the correct doc(s). Prefer minimal, surgical changes over large rewrites.

4. **Update the index** only if:
   - New documents are added
   - Documents are renamed or relocated
   - Major structural changes occur
   - You are explicitly asked to refresh the index

5. **Do not regenerate the entire index** unless the prompt explicitly asks to refresh or regenerate it.

---

## Adding New Documentation

When creating a new document:

1. Place it in the appropriate directory per `docs/REPO_STRUCTURE.md`
2. Add a TODO entry for index refresh, OR update `docs/DOCS_INDEX.md` if explicitly requested
3. Use clear headings and stable anchor names for linking
4. Keep content transformative and analytical—avoid copyrighted text

**TODO note format for PR descriptions:**
```
TODO: Add new doc to docs/DOCS_INDEX.md during next documentation refresh
- File: docs/path/to/new_doc.md
- Description: Brief one-line description
```

---

## Cross-Linking Best Practices

- Use relative paths for all internal links
- Prefer linking to specific sections using anchor links when headings are stable (e.g., `docker_local_dev.md#troubleshooting`)
- Verify links work before committing
- Keep link text descriptive and concise
