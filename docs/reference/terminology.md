# Terminology

Cross-domain terms used throughout the repository. This page is a navigational
index: it gives a one-line definition and points to the **canonical** location
for each term. It does not replace subsystem glossaries.

For LLM-subsystem terms (interrogation, manifest, derived artifact, status
values, evidence source types), the canonical glossary is
[LLM Glossary](../llm/glossary.md).

| Term | One-line definition | Canonical location |
| --- | --- | --- |
| Entity | A character, organization, location, or tech instance with stable identity. | [`dbo.DimEntity`](data-model.md#dbodimentity) |
| Entity classification | Assigning a canonical type and normalized attributes to an entity. | [Entity classification resume](../llm/entity-classification-resume.md) |
| Entity resolution | Linking/deduplicating candidate entities to a conformed record. | [`entity_matcher.py`](../../src/ingest/discovery/entity_matcher.py) |
| Ingest record | One raw HTTP fetch result stored as JSON. | [`ingest.IngestRecords`](data-model.md#ingestingestrecords) |
| Work item | A durable, resumable unit of acquisition work. | [`ingest.work_items`](data-model.md#ingestwork_items) |
| Ingest run | A batch execution of the ingest runner. | [Ingest runner](jobs-and-runners.md#ingest-runner) |
| Classifier resume | Skipping already-classified entities on re-run. | [Entity classification resume](../llm/entity-classification-resume.md) |
| Evidence bundle | The bounded evidence assembled for one inference. | [`llm.evidence_bundle`](data-model.md#llmevidence_bundle) |
| Evidence item | A single piece of evidence within a bundle. | [Glossary: Evidence Item](../llm/glossary.md#evidence-item) |
| Artifact | Stored request/response/output of an LLM run. | [`llm.artifact`](data-model.md#llmartifact) |
| Artifact version | The `content_sha256` identity of an artifact. | [Artifact version and provenance](lake-and-artifacts.md#artifact-version-and-provenance) |
| Artifact provenance | The lineage chain recorded on a run. | [Artifact version and provenance](lake-and-artifacts.md#artifact-version-and-provenance) |
| OpenAlex work | A single OpenAlex record (planned thin SQL + lake payload). | [OpenAlex work](lake-and-artifacts.md#openalex-work) |
| Lake raw layer | Filesystem store for large/raw payloads. | [Lake raw layer](lake-and-artifacts.md#lake-raw-layer) |
| Decompressed OpenAlex snapshot | Locally expanded OpenAlex JSONL tree. | [Decompressed OpenAlex snapshot](lake-and-artifacts.md#decompressed-openalex-snapshot) |
| PDF artifact | A PDF stored in the lake for an OpenAlex work (planned). | [PDF artifact](lake-and-artifacts.md#pdf-artifact) |
| Page classification | Type inference for an ingested page. | [`sem.PageClassification`](data-model.md#sempageclassification) |
| Feature series | A multi-PR effort named `YYYY_MM_<name>_phase_<n>`. | [Feature series](feature-series.md) |

See also: [Reference index](README.md) · [Data model](data-model.md) ·
[LLM Glossary](../llm/glossary.md).
