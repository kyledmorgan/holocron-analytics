# Feature-Series History

This directory reconstructs the history of multi-phase feature efforts in Holocron
Analytics. It exists because the repository historically used generic, unqualified
phase terminology (`Phase 0`, `Phase 1`, …) across several unrelated initiatives at
the same time, which made bare phase references ambiguous.

- For the naming rules that govern new work, see
  [`docs/contributing/feature-series-convention.md`](../../contributing/feature-series-convention.md).
- For the catalogue of legacy references and how each was resolved, see
  [`../phase-reference-inventory.md`](../phase-reference-inventory.md).

## How this history was reconstructed

Git history in this repository is squashed (a shallow clone presents the imported
history as a single commit), so commit-level archaeology is limited. The primary
evidence used for reconstruction was:

- `docs/pr_prompts_and_reports/*.md` — numbered exports of historical PRs, including
  each PR's title, creation/merge dates, and **head branch name**. These supply the
  series start dates and the Git-branch backfill requested as a stretch goal.
- Roadmap and status documents (`docs/llm/vision-and-roadmap.md`,
  `docs/llm/status.md`, `docs/fga/`, `docs/vector/`, `docs/lake/`).
- Source code, tests, and SQL migration headers.

Confidence reflects how directly the evidence ties a reference to a series.

## Index of feature series

| Series | Description | Began | Highest planned phase | Highest completed phase | Status | Detail |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `2026_01_llm_derived_data` | LLM-Derived Data subsystem: evidence-led structured extraction (runner, evidence assembly, retrieval). | 2026-01 | 7 | 3 | `partially_complete` | [link](2026_01_llm_derived_data.md) |
| `2026_02_entity_extraction` | Entity & relationship extraction expansion driven by the Functional Gap Analysis (droid → relationships → generic). | 2026-02 | 7 | 3 | `partially_complete` | [link](2026_02_entity_extraction.md) |
| `2026_02_vector_runtime_split` | Schema refactor splitting the `llm` schema into independent chat and `vector` runtimes. | 2026-02 | 2 | 2 | `complete` | [link](2026_02_vector_runtime_split.md) |
| `2026_02_openalex_lake` | OpenAlex snapshot decompression, lake layout, and the planned curated SQL/evidence/artifact loaders. | 2026-02 | 3 | 0 | `partially_complete` | [link](2026_02_openalex_lake.md) |

### Phase-numbering collision (the core ambiguity)

`2026_01_llm_derived_data` and `2026_02_entity_extraction` **both** number their
phases 1/2/3, but they mean different things:

| Bare phrase | `2026_01_llm_derived_data` | `2026_02_entity_extraction` |
| --- | --- | --- |
| "Phase 1" | MVP derive runner (migration `0005`) | Droid entity extraction (migration `0026`) |
| "Phase 2" | Evidence assembly (migration `0007`) | Relationship extraction (migrations `0027`, `0028`) |
| "Phase 3" | Retrieval augmentation (migration `0008`) | Generic multi-type extraction |

This collision is exactly why bare phase references must be qualified with a series
ID going forward.

## Not feature series

Some `Phase N` usage in the repository is **not** a multi-PR feature series and is
intentionally left as-is or only clarified in place:

- `docs/vision/Roadmap.md` uses Phases 0–7 as **program-level/product roadmap
  milestones**, not a single PR-delivered feature series. These are clarified as
  program milestones rather than converted to a `YYYY_MM_*` series.
- Genuine technical/domain stages such as "execution phase", "parsing phase",
  "lifecycle phase", and "second-phase retrieval" (for example in
  `src/ingest/analysis/inbound_link_analyzer.py` and
  `src/ingest/analysis/ranked_queue_seeder.py`) are legitimate English/algorithmic
  terms and are kept.
