# Feature-Series Naming Convention

This document governs how multi-phase bodies of work are named and tracked in the
Holocron Analytics repository. It exists because the repository historically used
generic, unqualified phase terminology (`Phase 0`, `Phase 1`, `next phase`, …)
across **several unrelated initiatives at once**. Because more than one initiative
each had its own "Phase 1" and "Phase 2", these bare references became ambiguous and
are no longer meaningful without additional context.

For the reconstructed history of past series, see
[`docs/history/feature-series/`](../history/feature-series/README.md). For the
catalogue of legacy references and how each was resolved, see
[`docs/history/phase-reference-inventory.md`](../history/phase-reference-inventory.md).

---

## When to use a phased feature series

Most changes do **not** need a feature series. Small, independent changes are
adequately documented through pull-request descriptions, commit history,
changelogs, audit records, and ordinary implementation documentation.

Use a phased feature series only when one or more of the following is true:

- the work is intentionally split across multiple pull requests;
- scaffolding is added before the functionality that uses it;
- implementation dependencies require an ordered sequence of deliverables;
- an initial capability is expected to be expanded in successive increments;
- multiple coordinated deliverables belong to one named initiative;
- later work needs to understand what an earlier PR intentionally left incomplete.

Do **not** force every change into the feature-series convention.

---

## Canonical identifier

When work *is* divided into related phases, use this canonical identifier:

```text
YYYY_MM_<short_feature_name>_phase_<number>
```

Examples:

```text
2026_01_llm_derived_data_phase_0
2026_01_llm_derived_data_phase_1
2026_02_entity_extraction_phase_0
2026_02_entity_extraction_phase_1
2026_02_vector_runtime_split_phase_2
```

### Formatting rules

- `YYYY` is the four-digit year in which the **series began**.
- `MM` is the two-digit month in which the **series began**.
- `<short_feature_name>` is a concise, stable, lowercase `snake_case` name.
- The literal word `phase` must be included.
- `<number>` is an integer that begins at `0` or `1`, matching the actual series.
- Use underscores between all identifier components.
- Do not use spaces inside the canonical identifier.
- **Do not change the year/month for later phases in the same series.** The date
  identifies the start of the series, not the date of each individual phase.

Correct — one series, one date prefix:

```text
2026_02_entity_extraction_phase_0
2026_02_entity_extraction_phase_1
2026_02_entity_extraction_phase_3
```

Incorrect — the date must not advance per phase:

```text
2026_02_entity_extraction_phase_0
2026_03_entity_extraction_phase_1
2026_04_entity_extraction_phase_3
```

### Base series identifier

The base series identifier omits the phase suffix and is used in indexes and
cross-references:

```text
2026_02_entity_extraction
```

---

## Human-readable form

In prose, pair the canonical identifier with a readable title:

```markdown
## Evidence Assembly — `2026_01_llm_derived_data_phase_2`
```

Do not use only a bare phase heading:

```markdown
## Phase 2
```

When qualifying an existing readable sentence, attach the canonical ID rather than
deleting the prose:

> Before: `Phase 2 adds leasing.`
>
> After: Lease-based claiming is planned for `2026_02_ingest_orchestration_phase_2`.

---

## Status vocabulary

Use a consistent status vocabulary for both series and individual phases:

| Status | Meaning |
| --- | --- |
| `planned` | Defined but not started. |
| `active` | Currently being implemented. |
| `paused` | Started, intentionally on hold. |
| `complete` | Objectives implemented, validated, documented; no material phase outstanding. |
| `partially_complete` | Some phases complete; later planned phases outstanding, or implementation exists but validation/documentation is incomplete. |
| `superseded` | The original phased plan was replaced by a materially different design. |
| `abandoned` | Work stopped and is not expected to resume. |
| `unknown` | Insufficient evidence to determine status. |

Do **not** assume the highest-numbered referenced phase was completed. Preserve
historical truth: if a phase was planned but never implemented, record it as
`planned`; if it was superseded, mark it `superseded`; if there is no evidence it
ever began, do not mark it `complete`.

---

## Rules for agents and contributors

1. **Never** use an unqualified feature-development reference such as `Phase 0`,
   `Phase 1`, or `next phase` to describe a body of multi-PR work. Always qualify
   it with a canonical base series ID (`YYYY_MM_<short_feature_name>`).
2. A phased body of work must have a canonical base series ID before its first PR
   merges, and each phase appends `_phase_<number>`.
3. The series date prefix is fixed at the start of the series and never changes for
   later phases.
4. When you start, extend, or complete a series, update its history document under
   [`docs/history/feature-series/`](../history/feature-series/README.md) and the
   index there.
5. When an entire series is complete, remove obsolete phase-by-phase scaffolding
   comments from the code and replace them with a durable explanation of what the
   code does and why. Convert any still-outstanding placeholder into a qualified
   `TODO(<series_id>_phase_<n>): …`.
6. Do **not** rewrite historical plans to imply work was completed when it was not.
   Distinguish direct evidence from inference.
7. The word "phase" remains valid for genuine domain or technical terminology
   (for example, "execution phase", "parsing phase", "lifecycle phase", "second-phase
   retrieval"). The goal is to qualify ambiguous **feature-development** phases, not
   to remove the English word "phase" from the repository.

### Structured TODO form

When a placeholder represents legitimate outstanding work in a known series:

```python
# TODO(2026_02_entity_extraction_phase_4):
# Add governance queue and human review of relationship assertions.
```

This keeps the outstanding work discoverable and tied to the correct series.
