# Seed Cleanup Report (2026-01-18)

## Summary
- Updated **1,224 FactEvent** rows to replace placeholder summaries with concise, context-aware text derived from event type, scene name, and work title.
- No seed rows were added or removed; keys, GUIDs, and relationships remain unchanged.
- Remaining placeholders requiring manual review:
  - **500 FactClaim** rows with `ObjectValue` like “Object value n” (insufficient context to correct).
  - **50 ContinuityIssue** rows with synthetic summaries/descriptions (no reliable replacement available).

## Table-by-table changes
- **FactEvent**: Rewrote `SummaryShort` and `SummaryNormalized` for all 1,224 events. New text now uses the pattern “{EventTypeName} in {SceneName} ({WorkTitle})” instead of the generic “ANH scene X event Y”, avoiding incorrect character references.
- All other seed files: **no changes** (placeholders noted below need manual review).

## Before/after samples (FactEvent)
| EventKey | Work / Scene | Before (placeholder) | After (context-aware) |
| --- | --- | --- | --- |
| 1 | A New Hope / Opening Crawl | “ANH scene 1 event 1” | “Strike in Opening Crawl (A New Hope)” |
| 25 | A New Hope / Jawas Capture Droids | “ANH scene 5 event 5” | “Wingman Assist in Jawas Capture Droids (A New Hope)” |
| 50 | A New Hope / R2 Escape | “ANH scene 10 event 5” | “Hyperspace Jump in R2 Escape (A New Hope)” |

## Manual review candidates
- **FactClaim (500 rows)** — `ObjectValue` placeholders remain. Sample rows:
  - Luke Skywalker — `pilots` → “Object value 1”
  - Darth Vader — `usesWeapon` → “Object value 2”
  - Han Solo — `belongsToOrg` → “Object value 3”
- **ContinuityIssue (50 rows)** — synthetic summaries/descriptions remain, and some Work/Scene pairings look inconsistent (e.g., a Tantive IV scene tied to *Attack of the Clones*). Sample rows:
  - “Continuity issue 1 - synthetic” (Work: The Phantom Menace, Scene: Opening Crawl)
  - “Continuity issue 2 - synthetic” (Work: Attack of the Clones, Scene: Tantive IV Captured)
  - “Continuity issue 3 - synthetic” (Work: Revenge of the Sith, Scene: Droids Escape)

## Validation
- JSON seeds remain loadable (structure unchanged; only descriptive fields edited).
- Recommended checks after dependency setup:
  - Run the seed-loader harness via `docker compose up --build` to confirm the database builds and loads successfully.
  - If Python tests are available, install pytest with `pip install pytest` and run `python -m pytest` to exercise any seed validation suites.

## Next steps (recommended manual cleanup)
- Replace placeholder FactClaim `ObjectValue` values with real strings or entity references where source context is available.
- Replace synthetic ContinuityIssue summaries/descriptions with concrete issue statements once source material is reviewed.
