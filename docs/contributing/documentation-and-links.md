# Documentation and Links Standard

How to keep documentation, code, and the database catalog navigable. This is the
canonical standard for cross-reference navigation in Holocron Analytics. It
complements the existing
[Doc Updates and Cross-Links playbook](../../agents/playbooks/docs/update_docs_and_links.md).

The goal is a **link-first** navigation system that works identically in VS Code,
GitHub, repository search, and agentic tooling — without depending on any IDE-only
feature. Links must be **intentional and useful**, not exhaustive noise.

## Contents

- [When to create a canonical concept](#when-to-create-a-canonical-concept)
- [Choosing the right reference document](#choosing-the-right-reference-document)
- [Relative-link conventions](#relative-link-conventions)
- [Stable headings](#stable-headings)
- [Selective linking](#selective-linking)
- [Linking code and SQL to docs](#linking-code-and-sql-to-docs)
- [Current state vs. historical](#current-state-vs-historical)
- [Excluded paths](#excluded-paths)
- [Validation](#validation)
- [Good and bad examples](#good-and-bad-examples)

---

## When to create a canonical concept

Create a canonical definition when you add or materially change a:

- SQL schema or major table; CLI; job or runner;
- lake dataset; artifact type; evidence relationship;
- domain concept; or architectural boundary.

A concept gets **one** canonical definition. If the same term is defined in
several places, consolidate to one and link the rest to it. Do not manufacture
definitions for concepts the codebase does not actually implement — mark
uncertain or future items as `planned`/`unknown`.

## Choosing the right reference document

| If the concept is a… | Define it in… |
| --- | --- |
| SQL table / dimension / fact | [`docs/reference/data-model.md`](../reference/data-model.md) |
| CLI command | [`docs/reference/cli-reference.md`](../reference/cli-reference.md) |
| Job / runner / worker | [`docs/reference/jobs-and-runners.md`](../reference/jobs-and-runners.md) |
| Lake dataset / artifact / OpenAlex | [`docs/reference/lake-and-artifacts.md`](../reference/lake-and-artifacts.md) |
| Cross-domain term | [`docs/reference/terminology.md`](../reference/terminology.md) |
| Multi-PR effort | [`docs/reference/feature-series.md`](../reference/feature-series.md) |

Then add the concept to the grouped [reference index](../reference/README.md) and
the [concept inventory](../reference/repository-concept-inventory.md).

## Relative-link conventions

- Use **repository-relative** Markdown links: `[text](../reference/data-model.md)`.
- Link into source with relative paths: ``[`classify_entities.py`](../../src/llm/cli/classify_entities.py)``.
- Do **not** use hardcoded GitHub URLs for current-state links, absolute/Windows
  paths, hardcoded branch names, or generated line numbers.
- Commit-specific GitHub permalinks are allowed **only** in historical/audit
  documents to show what code existed at a point in time.

## Stable headings

Canonical definitions use predictable headings (e.g. `## dbo.DimEntity`,
`## ingest.IngestRecords`). These generate anchors that other documents link to,
so:

- Do not rename a canonical heading casually.
- GitHub anchor slugs **drop punctuation** rather than converting it to hyphens:
  `## dbo.DimEntity` → `#dbodimentity` (not `#dbo-dimentity`). When in doubt,
  run the [link checker](#validation).
- When a rename is unavoidable, update every relative link and re-run validation.

## Selective linking

Link on:

- the first meaningful occurrence within a section;
- points where two subsystems interact;
- a SQL/code object central to the paragraph;
- "Related concepts" or reference-card sections.

Do **not** link every repeated occurrence of the same term. Prefer one clear link
plus prose over three links to the same target in one paragraph.

## Linking code and SQL to docs

At **major** entry points (public CLIs, job runners, orchestration classes, core
tables, SQL procedures, complex transforms), add a short docs reference:

```python
"""
Architecture: docs/architecture/...   # if present
Runbook:      docs/runbooks/...
Data model:   docs/reference/data-model.md#dbodimentity
"""
```

Rules: repository-relative paths, short, near boundaries only, no unstable line
numbers, not repeated in every helper. Internal helpers should rely on native Go
to Definition / Find References.

## Current state vs. historical

Distinguish three things explicitly and label planned work:

- **Current state** — what is implemented now.
- **Target state** — intended but not built; mark `**Implementation status:**
  Planned`.
- **Historical** — how it evolved; feature-series records link forward to current
  architecture/implementation/runbooks.

Never link a planned design as though it were the implementation. Current-state
docs must be understandable without reading history.

## Excluded paths

Do not scan, link into, or edit generated/external/payload data: `.git/`, virtual
environments, caches, vendored deps, build output, immutable OpenAlex source,
lake payloads (`local/data_lake/`, `/lake/`), decompressed JSONL, downloaded
PDFs, and other binaries. The
[link checker](../../scripts/quality/check_markdown_links.py) excludes these
automatically.

## Validation

Run the Markdown link checker before completing a documentation change:

```bash
python scripts/quality/check_markdown_links.py          # whole repo
python scripts/quality/check_markdown_links.py docs/    # a subtree
```

It validates relative file links and heading anchors, ignores external URLs,
reports `file:line`, and exits non-zero on failure. Tests live at
[`tests/unit/test_check_markdown_links.py`](../../tests/unit/test_check_markdown_links.py).

## Good and bad examples

**Good** — selective, relative, separates concerns:

```markdown
The [`classify_entities` CLI](../reference/cli-reference.md#classify_entities)
writes classification results into
[`dbo.DimEntity`](../reference/data-model.md#dbodimentity). Subsequent evidence
processing reads the completed entity record.
```

**Bad** — repeated, noisy linking of the same term:

```markdown
[`DimEntity`](...) is populated by [`classify_entities`](...) and then
[`DimEntity`](...) is read by [`evidence`](...) before [`DimEntity`](...) is
updated again.
```
