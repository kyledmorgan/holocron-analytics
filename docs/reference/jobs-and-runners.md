# Jobs and Runners Reference

Long-running workers and orchestration entry points. Headings here are stable
anchor targets. For the data structures these runners read and write, see
[Data model](data-model.md); for one-shot commands, see
[CLI reference](cli-reference.md).

## Contents

- [Phase 1 LLM runner](#phase-1-llm-runner)
- [Job dispatcher](#job-dispatcher)
- [Ingest runner](#ingest-runner)
- [Concurrent ingest runner](#concurrent-ingest-runner)

---

## Phase 1 LLM runner

**Kind:** Job runner &nbsp; **Domain:** LLM and analysis &nbsp; **Status:** Active

**Implementation:**
[`src/llm/runners/phase1_runner.py`](../../src/llm/runners/phase1_runner.py)
(`Phase1Runner`)

**Invocation:**
`python -m llm.runners.phase1_runner --once|--loop --worker-id <id> [--poll-seconds N]`

End-to-end derive flow:

1. Claim a job from [`llm.job`](data-model.md#llmjob) via
   [`llm.usp_claim_next_job`](../../src/db/dml/stored_procedures/llm.usp_claim_next_job.sql).
2. Build an [`llm.evidence_bundle`](data-model.md#llmevidence_bundle) from the
   job input ([`src/llm/evidence/builder.py`](../../src/llm/evidence/builder.py)).
3. Render the prompt from an interrogation definition.
4. Call Ollama ([`src/llm/providers/ollama_client.py`](../../src/llm/providers/ollama_client.py)).
5. Validate the response against a contract.
6. Persist [`llm.artifact`](data-model.md#llmartifact) records (SQL-first).
7. Update the [`llm.run`](data-model.md#llmrun) and job status.

**Operations:** [LLM operational guide](../llm/operational.md) &nbsp;
**Usage:** [Phase 1 runner guide](../llm/phase1-runner.md) &nbsp;
**Resilience:** [`tests/unit/llm/test_phase1_runner_resilience.py`](../../tests/unit/llm/test_phase1_runner_resilience.py)

---

## Job dispatcher

**Kind:** Orchestration class &nbsp; **Domain:** LLM &nbsp; **Status:** Active

**Implementation:**
[`src/llm/runners/dispatcher.py`](../../src/llm/runners/dispatcher.py)
(`JobDispatcher`)

Routes claimed jobs to the appropriate handler based on interrogation type
(see [`src/llm/handlers/`](../../src/llm/handlers)).

---

## Ingest runner

**Kind:** Job runner &nbsp; **Domain:** Ingest and orchestration &nbsp; **Status:** Active

**Implementation:**
[`src/ingest/runner/ingest_runner.py`](../../src/ingest/runner/ingest_runner.py)
(`IngestRunner`)

Dequeues [`ingest.work_items`](data-model.md#ingestwork_items), fetches content
through connectors ([`src/ingest/connectors/`](../../src/ingest/connectors)),
stores [`ingest.IngestRecords`](data-model.md#ingestingestrecords) via writers,
discovers new work, and updates state.

**Runbook:** [Wookieepedia ingestion](../runbooks/wookieepedia_ingestion.md)

---

## Concurrent ingest runner

**Kind:** Job runner &nbsp; **Domain:** Ingest and orchestration &nbsp; **Status:** Active

**Implementation:**
[`src/ingest/runner/concurrent_runner.py`](../../src/ingest/runner/concurrent_runner.py)

Multi-worker variant of the [ingest runner](#ingest-runner). Uses lease columns
on [`ingest.work_items`](data-model.md#ingestwork_items) (added in
[`db/migrations/0011_concurrent_runner_support.sql`](../../db/migrations/0011_concurrent_runner_support.sql))
and worker heartbeats for distributed claiming.

**Tests:** [`tests/unit/test_concurrent_runner.py`](../../tests/unit/test_concurrent_runner.py)
