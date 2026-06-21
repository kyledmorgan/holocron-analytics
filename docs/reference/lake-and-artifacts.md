# Lake and Artifacts Reference

Storage layers for large payloads and derived artifacts. This page links the
lake/artifact concepts to their canonical definitions, architecture, and
implementation. Headings are stable anchor targets.

## Contents

- [Lake raw layer](#lake-raw-layer)
- [Decompressed OpenAlex snapshot](#decompressed-openalex-snapshot)
- [OpenAlex work](#openalex-work)
- [PDF artifact](#pdf-artifact)
- [Artifact version and provenance](#artifact-version-and-provenance)

---

## Lake raw layer

**Kind:** Lake dataset &nbsp; **Domain:** Lake storage &nbsp; **Status:** Active

**Purpose:**
Filesystem-backed store for raw and large payloads that do not belong in SQL.
Written by [`FileLakeWriter`](../../src/ingest/storage/file_lake.py) and the LLM
[`LakeWriter`](../../src/llm/storage/lake_writer.py).

**Architecture:** [OpenAlex lake-first architecture](../lake/openalex_lake_architecture.md)

> **Implementation status:** The OpenAlex lake-first layering is a **plan**; the
> generic file lake writers are **active**. Treat lake-path conventions in the
> architecture doc as target state unless the code confirms otherwise.

Lake payload contents (`local/data_lake/`, `/lake/`) are git-ignored and are
**excluded** from documentation scans — see
[Documentation and links](../contributing/documentation-and-links.md#excluded-paths).

---

## Decompressed OpenAlex snapshot

**Kind:** Lake dataset &nbsp; **Domain:** OpenAlex &nbsp; **Status:** Active (tooling)

**Purpose:**
A locally expanded OpenAlex `.gz` snapshot tree (JSONL records) used as an ingest
source. The compressed source data is immutable and excluded from edits.

**Tooling:**
[`scripts/lake/decompress_gz_tree.py`](../../scripts/lake/decompress_gz_tree.py)
(see [CLI reference](cli-reference.md#lake-utilities)).

**Runbook:** [OpenAlex decompression](../lake/openalex_decompression.md)

---

## OpenAlex work

**Kind:** Concept / source record &nbsp; **Domain:** OpenAlex &nbsp; **Status:** Planned

**Purpose:**
A single OpenAlex work (paper/record) as represented for ingest and, in target
state, as a thin SQL metadata row plus a lake-stored payload.

> **Implementation status:** Planned. There is an
> [`OpenAlexConnector`](../../src/ingest/connectors/openalex/openalex_connector.py)
> and discovery support, but no dedicated `openalex` SQL schema yet. The thin
> metadata tables and crosswalk are described as target state in the
> [lake-first architecture](../lake/openalex_lake_architecture.md#3-sql-schema-strategy).

**Integration guide:** [OpenAlex integration](../openalex-integration.md)

---

## PDF artifact

**Kind:** Artifact &nbsp; **Domain:** Artifact processing &nbsp; **Status:** Planned

**Purpose:**
A PDF acquired for an [OpenAlex work](#openalex-work), stored as bytes in the
lake with a manifest record describing its provenance.

> **Implementation status:** Planned. The acquisition and manifest conventions
> are documented in
> [Artifact blobs (PDFs)](../lake/openalex_lake_architecture.md#2-artifact-blobs-pdfs);
> there is not yet a dedicated artifact-bytes table.

---

## Artifact version and provenance

**Kind:** Concept &nbsp; **Domain:** Evidence and provenance &nbsp; **Status:** Active

**Purpose:**
The identity and lineage of LLM-derived artifacts. An **artifact version** is the
`content_sha256` of an [`llm.artifact`](data-model.md#llmartifact). **Artifact
provenance** is the chain recorded on [`llm.run`](data-model.md#llmrun)
(request → response → output, with `parent_run_id` chaining).

**Architecture:** [SQL-first artifact storage](../llm/sql-first-artifact-storage.md)
&nbsp; **Lineage:** [Lineage](../llm/lineage.md)

**Related concepts:**

- [`llm.evidence_bundle`](data-model.md#llmevidence_bundle) — the evidence that
  justified the derived artifact.
- [Pipeline observability](../llm/llm-pipeline-observability-current-state.md).
