# Ollama Interrogation Orientation (Focused + Actionable)

Below is a focused, Ollama-interrogation-oriented orientation that maps **docs → code entrypoints → run modes → extensibility**.

---

## Top docs to read first (in order)

1) **`phase1-runner.md`**  
   - End-to-end runner flow: CLI, artifacts, SQL queue semantics, retries, lake layout  
   - Reference: `phase1-runner.md:1-230`

2) **`ollama.md`**  
   - Ollama API endpoints, operational modes, config knobs  
   - Reference: `ollama.md:1-220`

3) **`README.md`** (module overview + runner commands)  
   - High-level overview and “how to run” notes  
   - Reference: `README.md:1-140`

4) **`README.md`** (Ollama API patterns + client strategy)  
   - How we call Ollama + patterns for structured responses  
   - Reference: `README.md:1-70`

5) **`README.md` + `README.md` + `README.md`** (interrogation/prompt/schema contract model)  
   - Prompt definitions, interrogation definition, schema contracts  
   - Reference: `README.md:1-120`, `README.md:1-120`, `README.md:1-120`

---

## Secondary but relevant (Ollama interrogation + ops)

- **`ollama-docker.md`** — Dockerized Ollama notes (`ollama-docker.md`)  
- **`README.md`** — manual API interrogation harness (`README.md`)

---

## Key entrypoints (runner + Ollama interrogation)

- **Phase 1 runner entrypoint:** `phase1_runner.py:1-170`  
- **Queue helpers:** `llm_enqueue_job.py`, `llm_inspect_jobs.py`  
- **Ollama smoke tests:** `llm_smoke_test.py`, `ollama_capture_models.py`  
- **Semantic staging dry run (page classification interrogation):**  
  `dry_run_page_classification.py:350-870`  
- **Semantic CLI (non-LLM now + future LLM stage):** `README.md:120-210`

---

## Dry-run vs full-run (what the code actually does)

### A) Dry run (semantic staging script)

**What it does**
- Pulls candidate records, extracts signals, calls Ollama with a strict JSON schema, and produces classification output.
- Optionally dumps raw Ollama request/response JSON to `logs/ollama` when `--dump-ollama` is set.  
  - Reference: `dry_run_page_classification.py:350-661`

**What it explicitly does NOT do**
- It does **not** use the LLM SQL job queue or lake artifact system from the Phase 1 runner.
- There is no “queue claim → run → lake artifact” workflow here; it is a direct local driver.  
  - Reference: `dry_run_page_classification.py:350-661`

**Artifacts it writes**
- When `--dump-ollama` is enabled, writes request/response JSON under `logs/ollama` (or `OLLAMA_DUMP_DIR`).  
  - Reference: `dry_run_page_classification.py:640-661`

**Important nuance**
- Despite the “dry run” naming, it **can persist to SQL** if those tables exist:
  - `sem.SourcePage`, `sem.PageSignals`, `sem.PageClassification`
  - optionally `dbo.DimEntity` + tags  
  - Reference: `dry_run_page_classification.py:742-812`

---

### B) Full run (LLM derived data runner)

**Canonical entrypoint**
- Phase 1 runner with `--once` or `--loop` modes  
  - References: `phase1-runner.md:90-140`, `phase1_runner.py:1-170`

**What it does**
- Claims jobs from SQL → builds evidence bundles → renders prompts → calls Ollama with structured output  
- Validates against schema → writes artifacts to the lake → records metadata in SQL  
  - Reference: `phase1-runner.md:1-220`

**Persistence**
- Artifacts: `lake/llm_runs/...`  
- Metadata: `llm.job`, `llm.run`, `llm.artifact`  
  - Reference: `phase1-runner.md:150-230`

**Checkpoint / resume**
- Queue state in SQL + retries/backoff/deadlettering enables resume by re-running the runner  
  - Reference: `phase1-runner.md:1-220`

**Config knobs (Ollama + runtime)**
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_TEMPERATURE`  
- `LAKE_ROOT`, `POLL_SECONDS`, `WORKER_ID`, plus generic `LLM_*` settings  
  - References: `phase1_runner.py:33-90`, `config.md:1-140`

---

## Extensibility model (conceptual; no code changes yet)

### What already fits cleanly
- **Interrogation types:** definitions (YAML/JSON), rubrics, prompt templates, schema contracts exist  
  - Reference: `README.md:1-120` (multiple relevant READMEs)
- **Run modes:** Phase 1 runner supports `--once` and `--loop` with queue semantics  
  - Reference: `phase1-runner.md:90-140`
- **Artifacts:** runner writes request/response/evidence/prompt/output to lake + metadata to SQL  
  - Reference: `phase1-runner.md:150-230`
- **State/queue:** SQL job queue with retries/backoff/deadlettering  
  - Reference: `phase1-runner.md:1-220`

### What’s missing (or scattered)
- A first-class **“dry run” mode** for Phase 1 runner (skip SQL writes but still capture lake artifacts)
- A unified artifact manifest for the semantic staging “dry run” (currently writes `logs/ollama` but not lake/manifest metadata)
- A shared interrogation registry entry for page classification so it can run through the same runner framework

### Next incremental step (minimal, modular)
1) Add a config-driven run mode to Phase 1 runner  
   - e.g., `RUN_MODE=dry_run` (skip SQL updates but still write lake artifacts)
2) Register page classification as a first-class interrogation in the LLM catalog  
   - definition + schema + rubric + prompt
   - invoke via runner instead of bespoke script
3) Add an “artifact-only” output path for semantic staging  
   - produce the same request/response/evidence/prompt/output structure as the Phase 1 lake

---

## Concrete extension ideas (2–3)

1) **Config-driven run modes**
   - `dry_run`, `persist`, `replay` (re-validate stored responses), `audit_only` (no Ollama calls; validate schema + lineage)

2) **Interrogation plugin registry**
   - Load definitions from `interrogations/definitions/`
   - Auto-bind prompt templates + schemas
   - Add new interrogation types without code changes

3) **Unified artifact manifest**
   - Always write a manifest JSON alongside request/response
   - Applies to both Phase 1 runner and semantic staging scripts

---

## Optional next focus
If you want a more Ollama-API-specific walk-through next, we can focus on `ollama.md` plus the Ollama client implementation and show the exact request/response payloads used by the runner.
