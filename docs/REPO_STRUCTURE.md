# Repo Structure

## Purpose

This repository is a learning-focused data engineering and analytics workbench. It is designed to model narrative media as structured data while keeping source payloads, copyrighted text, and secrets out of version control.

## Guiding Principles

- Separation of concerns: sources, staging, modeling, and presentation are isolated.
- Local-only data: raw inputs and credentials stay outside the repo.
- Reproducibility: deterministic ordering and clear structure for future automation.

## Top-Level Folders

- `agents/`: Tool-agnostic policies, playbooks, and templates for contributors and automation.
- `config/`: Example configuration templates only (no secrets).
- `db/`: Database DDL/DML placeholders and migration structure.
- `docs/`: Vision, modeling notes, runbooks, ADRs, and diagrams.
- `exercises/`: Learning exercises and scenarios (no real data).
- `local/`: Local-only caches, logs, and backups (gitignored).
- `prompts/`: Runtime prompts used by code (separate from agent templates).
- `scripts/`: Helper scripts for database and pipeline workflows.
- `sources/`: Source definitions and mapping templates (no payloads).
- `src/`: Future ingestion, transformation, and loading code (placeholders only).
- `web/`: Future web app and visualization assets (placeholders only).

## What Does Not Belong Here

- Source payloads or scraped text
- Media files of any kind
- Credentials, tokens, or connection strings
- Local caches, backups, or logs

## Where Work Will Start

Early work will focus on `db/` and `docs/` to define schemas and document modeling decisions.

## Execution Philosophy (Future)

`db/runner/manifest.json` will define deterministic execution order for scripts in `db/ddl/`.

## Agent Guidance

`AGENTS.md` and the `agents/` folder define tool-agnostic rules and playbooks for contributions. Follow those documents when adding or modifying files.
