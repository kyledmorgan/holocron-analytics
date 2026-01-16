# Project Roadmap

This roadmap outlines the **phased evolution** of the project from an educational, hands-on data modeling exercise into a robust, extensible analytics platform for narrative universes. While learning and experimentation are first-class goals early on, the roadmap is intentionally structured to support long-term growth, automation, and public-facing exploration.

---

## Guiding Principles

- **Start simple, design for scale**
- **Event-first (spine-based) modeling**
- **Transformative, not reproductive**
- **High tolerance early; higher rigor later**
- **Automation before completeness**
- **Non-destructive, history-preserving data evolution**

---

## Phase 0 — Foundations (Setup & Framing)

**Goal:** Establish the conceptual and technical baseline.

**Focus areas:**
- Define the core ERD (dimensions, facts, bridges)
- Establish repository structure and documentation standards
- Create the initial SQL Server DDL (tables only)
- Codify modeling principles:
  - Event spine
  - Entity core
  - Built-thing hierarchy (tech assets / instances)
  - Continuity frames and claims
- Define conventions:
  - JSON overflow (`AttributesJson`)
  - Governance columns
  - Non-destructive updates (SCD mindset)

**Deliverables:**
- Stable ERD (Mermaid)
- Vision + modeling documentation
- DDL scripts for core tables
- Empty but runnable database schema

---

## Phase 1 — Learning-First MVP (Manual + Semi-Automated)

**Goal:** Make the system usable and educational with minimal automation.

**Scope:**
- ~8–12 core tables (subset of full model)
  - Franchise
  - Work / Scene
  - Entity / Character
  - Location
  - Event / EventType
  - Appearance
- Middle-layer **views** (optional, limited)
  - Shape data into more approachable, “transaction-like” forms
  - Reduce join complexity for learners
- Manual or lightly assisted data entry
  - Seed data by hand or via ad-hoc LLM prompts
  - Accept hallucinations and inaccuracies intentionally

**Domain focus:**
- Narrow content scope:
  - Original trilogy
  - Select characters, scenes, and events
- Depth over breadth:
  - Hundreds to thousands of rows
  - Rich event sequences
  - Character appearances and interactions

**Deliverables:**
- Seeded data with meaningful volume
- Example queries for:
  - Timelines
  - Character interactions
  - Appearance changes
- Learning exercises (SQL practice)

---

## Phase 2 — AI-Assisted Transformation (Batch, Tolerant)

**Goal:** Introduce automation for scale without enforcing strict accuracy.

**Capabilities introduced:**
- LLM-driven semantic transformation:
  - Semi-structured input → structured rows
  - Use local models where possible (e.g., Ollama)
- Early RAG patterns (optional):
  - Chunked source material
  - Context injection for prompts
- Batch processing:
  - Run “interrogations” against source data
  - Populate dimensions and fact tables
- JSON overflow used heavily:
  - Capture anything unmapped or ambiguous
  - Mine later for schema evolution

**Operational considerations:**
- Accept inaccuracies
- Prioritize coverage and scale
- Focus on throughput, not precision

**Deliverables:**
- Tens of thousands of rows in key tables
- Repeatable batch scripts
- Clear separation between:
  - Raw source lake (external)
  - Transformed analytical core

---

## Phase 3 — Sourcing & Scraping Infrastructure

**Goal:** Automate data acquisition responsibly and reproducibly.

**Features added:**
- Web/API scraping engine (likely Python):
  - Configurable endpoints
  - Intelligent branching / link-following
- Local data lake:
  - Raw source storage (non-public)
  - Versioned, immutable ingests
- Source metadata tracking:
  - Where data came from
  - When it was ingested
  - What processed it

**Governance:**
- Track acquisition method
- Track analysis status (queued, processed, reviewed)
- Prepare for future risk/legal review

**Deliverables:**
- Source ingestion framework
- Metadata tables or logs
- Repeatable crawl-and-lake workflows

---

## Phase 4 — Task Queues & Orchestration

**Goal:** Treat transformation as a managed pipeline.

**Enhancements:**
- Job/task queue system:
  - What needs processing
  - What has been processed
  - What failed or needs review
- LLM runner/orchestrator:
  - Batch prompts
  - Retry logic
  - Model/version tracking
- State tracking:
  - Ingested → analyzed → promoted

**Deliverables:**
- Queue/backlog tracking tables
- Batch runners
- Observability into processing state

---

## Phase 5 — Accuracy, Provenance & SCD Maturity

**Goal:** Increase trust and analytical rigor.

**Key improvements:**
- Source attribution:
  - Claims linked to source references
  - Confidence scoring
- Continuity-aware reasoning:
  - Multiple frames coexist cleanly
- Slowly Changing Dimensions (SCD):
  - Non-destructive updates
  - Versioned records
  - Historical state preserved
- Promotion logic:
  - From exploratory/middle-tier → core analytical tables

**Deliverables:**
- Version-aware dimensions
- Claim provenance tracking
- Improved governance and lineage

---

## Phase 6 — Analytics & Visualization Layer

**Goal:** Make the data explorable and engaging.

**Options explored:**
- Web-based UI:
  - Timelines
  - Relationship graphs
  - Event sequences
- JavaScript-based visualization frameworks
- Optional BI tooling (e.g., Power BI) for internal use
- Exportable datasets and views

**Design intent:**
- Analytics-first, not narrative reproduction
- Visualize structure, not content

**Deliverables:**
- Interactive dashboards
- Graph and timeline views
- Documentation-driven UI modules

---

## Phase 7 — Public Readiness & Expansion

**Goal:** Prepare for broader visibility and reuse.

**Steps:**
- Legal and risk review
- Explicit usage policies
- Clear separation of:
  - Internal processing
  - Public-facing outputs
- Potential expansion to:
  - Other franchises
  - Historical domains
  - Non-media datasets

**Non-goals (at this stage):**
- Monetization
- Canon arbitration
- Replacement of original works

---

## Summary Timeline (High-Level)

- **Short-term:** Learn, seed, explore (manual + tolerant automation)
- **Mid-term:** Automate ingestion, transformation, and orchestration
- **Long-term:** Analyze at scale, visualize richly, and extend responsibly

The roadmap is intentionally **iterative**. Each phase delivers value on its own, while laying foundations for the next—without requiring a rewrite or reset.

This project is meant to grow organically, guided by curiosity, rigor, and respect for both data and source material.
