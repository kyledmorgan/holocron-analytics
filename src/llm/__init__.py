"""
LLM-Derived Data Module

This module provides infrastructure for generating structured JSON artifacts
from evidence bundles using Large Language Models (LLMs). It supports
reproducibility through manifest tracking and artifact persistence.

Key components:
- contracts/: JSON schemas for manifests and derived outputs
- core/: Core types, exceptions, and logging utilities
- prompts/: Prompt templates for LLM interrogation
- providers/: LLM provider clients (Ollama, etc.)
- runners/: Orchestration logic for derive operations
- storage/: Artifact and queue persistence
- config/: Configuration management
"""

__version__ = "0.1.0"
