# Seed Cleanup Report (2026-01-18)

## Summary
- Updated **190 FactEvent** rows to replace placeholder summaries with context-aware descriptions derived from event type, scene, and participants.
- No seed rows were added or removed; keys, GUIDs, and relationships remain unchanged.
- Remaining placeholders requiring manual review:
  - **500 FactClaim** rows with `ObjectValue` like “Object value n” (insufficient context to correct).
  - **50 ContinuityIssue** rows with synthetic summaries/descriptions (no reliable replacement available).

## Table-by-table changes
- **FactEvent**: Rewrote `SummaryShort` and `SummaryNormalized` for all 190 events. New text now references event type, key participants, and scene name instead of the generic “ANH scene X event Y”.
- All other seed files: **no changes** (placeholders noted below need manual review).

## Before/after samples (FactEvent)
| EventKey | Work / Scene | Before (placeholder) | After (context-aware) |
| --- | --- | --- | --- |
| 1 | ANH / Opening Crawl | “ANH scene 1 event 1” | “Strike involving Luke Skywalker and Darth Vader during Opening Crawl” |
| 25 | ANH / Jawas Capture Droids | “ANH scene 5 event 5” | “Wingman Assist involving Black Two and Black Three during Jawas Capture Droids” |
| 50 | ANH / R2 Escape | “ANH scene 10 event 5” | “Hyperspace Jump involving Anakin Skywalker, Padme Amidala, and Qui-Gon Jinn during R2 Escape” |

## Manual review candidates
- **FactClaim (500 rows)** — `ObjectValue` placeholders remain. Sample rows:
  - Luke Skywalker — `pilots` → “Object value 1”
  - Darth Vader — `usesWeapon` → “Object value 2”
  - Han Solo — `belongsToOrg` → “Object value 3”
- **ContinuityIssue (50 rows)** — synthetic summaries/descriptions remain. Sample rows:
  - “Continuity issue 1 - synthetic” (Work: The Phantom Menace, Scene: Opening Crawl)
  - “Continuity issue 2 - synthetic” (Work: Attack of the Clones, Scene: Tantive IV Captured)
  - “Continuity issue 3 - synthetic” (Work: Revenge of the Sith, Scene: Droids Escape)

## Validation
- JSON seeds remain loadable (structure unchanged; only descriptive fields edited).
- Tests: `python -m pytest` not run (pytest not installed in environment).

## Next steps (recommended manual cleanup)
- Replace placeholder FactClaim `ObjectValue` values with real strings or entity references where source context is available.
- Replace synthetic ContinuityIssue summaries/descriptions with concrete issue statements once source material is reviewed.
