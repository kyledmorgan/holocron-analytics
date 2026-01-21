# LLM Providers

## Overview

This directory contains client implementations for LLM providers. The primary provider is **Ollama** for local LLM inference.

## Provider Strategy

The LLM module supports two API patterns for Ollama:

### 1. Native Ollama API

Direct usage of Ollama's native REST API:
- **Base URL**: `http://localhost:11434/api`
- **Endpoints**: `/api/generate`, `/api/chat`
- **Pros**: Full access to Ollama features, streaming support
- **Cons**: Ollama-specific, not portable to other providers

### 2. OpenAI-Compatible API

Ollama's OpenAI-compatible endpoints:
- **Base URL**: `http://localhost:11434/v1`
- **Endpoints**: `/v1/chat/completions`
- **Pros**: Portable to other OpenAI-compatible providers
- **Cons**: Subset of Ollama features

### Decision Status: TBD

The choice between native and OpenAI-compatible APIs has not been finalized. The current implementation supports both, with configuration-driven selection.

## Available Clients

### `ollama_client.py`

Thin HTTP client for Ollama:
- Supports both native and OpenAI-compatible endpoints
- Non-streaming by default (for deterministic capture)
- Configurable timeouts and retries

## Adding New Providers

To add a new provider:

1. Create a new client file (e.g., `openai_client.py`)
2. Implement the same interface as `OllamaClient`
3. Register in the provider factory
4. Document configuration options

## Related Documentation

- [Ollama Integration Guide](../../../docs/llm/ollama.md) — Detailed API documentation
- [Configuration](../config/config.md) — Provider configuration options
