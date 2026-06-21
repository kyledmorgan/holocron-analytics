# Feature-Series Reference

Multi-PR efforts in this repository use the canonical identifier
`YYYY_MM_<short_feature_name>_phase_<number>` (the date marks the **series
start**, not each phase). Never use a bare `Phase N` for multi-PR work.

- **Rules:** [Feature-series convention](../contributing/feature-series-convention.md)
- **Reconstructed history:** [Feature-series history](../history/feature-series/README.md)
- **Legacy inventory:** [Phase-reference inventory](../history/phase-reference-inventory.md)

## Known series

| Series | Domain | History record |
| --- | --- | --- |
| `2026_01_llm_derived_data` | LLM derived data | [history](../history/feature-series/2026_01_llm_derived_data.md) |
| `2026_02_entity_extraction` | Entity extraction | [history](../history/feature-series/2026_02_entity_extraction.md) |
| `2026_02_openalex_lake` | OpenAlex lake | [history](../history/feature-series/2026_02_openalex_lake.md) |
| `2026_02_vector_runtime_split` | Vector runtime split | [history](../history/feature-series/2026_02_vector_runtime_split.md) |

## How history links to current state

Historical feature-series documents explain **how** a subsystem was built. They
should link forward to current architecture, implementation, and runbooks.
Current-state documents may link back to history but must remain understandable
without it (see
[current vs. historical](../contributing/documentation-and-links.md#current-state-vs-historical)).
